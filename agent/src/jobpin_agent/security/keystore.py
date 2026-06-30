"""OS-keystore master-key handling — DPAPI / Keychain / dev fallback (§1.9 at-rest encryption).

EN —
The master key is the root of at-rest encryption: every data subkey (``cipher.derive_subkey``) descends
from it, and it must NEVER sit in plaintext on disk. Each ``KeyStore`` backend generates the key once
(32 random bytes) and then protects it at rest using the platform's facility: Windows DPAPI
(``CryptProtectData`` — the wrapped bytes are bound to the user/machine and unreadable elsewhere) or
macOS Keychain (the ``security`` CLI). ``DevKeyStore`` is an explicitly INSECURE fallback for CI / Linux
/ tests (it only obfuscates with a fixed pad) so the encryption path can be exercised without a real
keystore — it must not be used in production. The whole module is stdlib-only (``ctypes`` / ``subprocess``
/ ``secrets``); no third-party dependency.

中文 —
主密钥是静态加密之根：每个数据子密钥（``cipher.derive_subkey``）都由它派生，且绝不能以明文落盘。每个 ``KeyStore``
后端只生成一次密钥（32 随机字节），随后用平台设施在静态时保护它：Windows DPAPI（``CryptProtectData``——封装字节绑定
到用户/机器，他处不可读）或 macOS Keychain（``security`` 命令行）。``DevKeyStore`` 是显式不安全的回退，供 CI / Linux /
测试使用（仅用固定 pad 做混淆），使加密路径在没有真实 keystore 时也能被演练——生产中绝不可用。整个模块仅用标准库
（``ctypes`` / ``subprocess`` / ``secrets``）；无第三方依赖。
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
from abc import ABC, abstractmethod


class KeyStore(ABC):
    """A source of the 32-byte master key, protected at rest by the platform.

    EN — Subclasses implement ``get_or_create_master_key``: create-once then protect, idempotent.
    中文 — 子类实现 ``get_or_create_master_key``：一次创建随后保护，幂等。
    """

    @abstractmethod
    def get_or_create_master_key(self) -> bytes:
        """Return the master key, creating + persisting it (protected) on first call.

        EN — Returns: 32 bytes. 中文 — 返回：32 字节。
        """
        raise NotImplementedError


def _new_key() -> bytes:
    """Generate a fresh 32-byte master key. 中文 — 生成全新的 32 字节主密钥。"""
    return secrets.token_bytes(32)


class DevKeyStore(KeyStore):
    """INSECURE dev/CI keystore — obfuscates the key with a fixed pad (never for production).

    EN — Args: path (file holding the padded key). Stores ``key XOR pad`` so the raw key is not on disk
        verbatim, but the pad is public — this provides NO real protection and exists only so Linux/CI
        can run the encryption tests.
    中文 — 参数：path（保存被 pad 的密钥的文件）。存储 ``key XOR pad``，使原始密钥不逐字落盘，但 pad 是公开的——
        这不提供任何真实保护，仅为使 Linux/CI 能运行加密测试而存在。
    """

    _PAD = b"jobpin-dev-pad-not-secure-000000"  # 32 bytes

    def __init__(self, path: str) -> None:
        """Args: path. 中文 — 参数：path。"""
        self._path = path

    def get_or_create_master_key(self) -> bytes:
        """Read (de-obfuscate) or create+persist the padded key. 中文 — 读取（去混淆）或创建并持久化被 pad 的密钥。"""
        if os.path.exists(self._path):
            wrapped = open(self._path, "rb").read()
            return bytes(a ^ b for a, b in zip(wrapped, self._PAD))
        key = _new_key()
        with open(self._path, "wb") as fh:
            fh.write(bytes(a ^ b for a, b in zip(key, self._PAD)))
        return key


class WindowsDpapiKeyStore(KeyStore):
    """Windows keystore — protects the master key with DPAPI ``CryptProtectData``.

    EN — Args: path (file holding the DPAPI-wrapped key). The on-disk bytes are ciphertext bound to the
        current user/machine; another account or machine cannot unwrap them.
    中文 — 参数：path（保存 DPAPI 封装密钥的文件）。落盘字节是绑定当前用户/机器的密文；其他账户或机器无法解封。
    """

    def __init__(self, path: str) -> None:
        """Args: path. 中文 — 参数：path。"""
        self._path = path

    def get_or_create_master_key(self) -> bytes:
        """Unwrap the stored key, or create + DPAPI-wrap + persist it. 中文 — 解封已存密钥，或创建并 DPAPI 封装后持久化。"""
        if os.path.exists(self._path):
            return _dpapi_call(open(self._path, "rb").read(), protect=False)
        key = _new_key()
        with open(self._path, "wb") as fh:
            fh.write(_dpapi_call(key, protect=True))
        return key


class MacKeychainKeyStore(KeyStore):
    """macOS keystore — stores the master key in the login Keychain via the ``security`` CLI.

    EN — Args: service, account (Keychain item identity). The hex key lives in the Keychain, never in a
        project file.
    中文 — 参数：service、account（Keychain 条目标识）。十六进制密钥存于 Keychain，绝不落入项目文件。
    """

    def __init__(self, service: str = "jobpin-agent", account: str = "master-key") -> None:
        """Args: service, account. 中文 — 参数：service、account。"""
        self._service = service
        self._account = account

    def get_or_create_master_key(self) -> bytes:
        """Find the Keychain item, or create + store it. 中文 — 查找 Keychain 条目，或创建并存储。"""
        found = subprocess.run(
            ["security", "find-generic-password", "-s", self._service, "-a", self._account, "-w"],
            capture_output=True,
            text=True,
        )
        if found.returncode == 0 and found.stdout.strip():
            return bytes.fromhex(found.stdout.strip())
        key = _new_key()
        subprocess.run(
            ["security", "add-generic-password", "-s", self._service, "-a", self._account,
             "-w", key.hex(), "-U"],
            check=True,
        )
        return key


def default_keystore(path: str) -> KeyStore:
    """Pick the platform keystore (DPAPI on Windows, Keychain on macOS, else the dev fallback).

    EN — Args: path (used by the file-backed backends). Returns: a ``KeyStore``.
    中文 — 参数：path（文件型后端使用）。返回：一个 ``KeyStore``。
    """
    if sys.platform == "win32":
        return WindowsDpapiKeyStore(path)
    if sys.platform == "darwin":
        return MacKeychainKeyStore()
    return DevKeyStore(path)


def _dpapi_call(data: bytes, *, protect: bool) -> bytes:
    """Call Windows DPAPI CryptProtectData / CryptUnprotectData on ``data``.

    EN —
    Args: data (bytes to wrap/unwrap); protect (True = encrypt, False = decrypt). Returns: the
    transformed bytes. Raises: OSError (``WinError``) on API failure. Learning note: the input buffer is
    held in a local so it outlives the ctypes struct that points into it, and the output buffer is freed
    with ``LocalFree`` as the API requires.

    中文 —
    参数：data（待封装/解封字节）；protect（True=加密，False=解密）。返回：变换后的字节。抛出：API 失败时抛
    OSError（``WinError``）。学习笔记：输入缓冲保存在局部变量中，使其存活过指向它的 ctypes 结构体；输出缓冲按 API
    要求用 ``LocalFree`` 释放。
    """
    import ctypes
    from ctypes import wintypes

    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
