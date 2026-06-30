"""AES-256-GCM data cipher + HKDF subkey derivation (§1.9 at-rest encryption).

EN —
The symmetric primitive behind at-rest encryption. ``Cipher`` wraps AES-256-GCM (an AEAD: it both
encrypts and authenticates, so tampering is detected on decrypt). A fresh random 12-byte nonce is
generated per ``encrypt`` and prepended to the ciphertext, so encrypting the same plaintext twice yields
different blobs and no nonce reuse occurs. ``derive_subkey`` uses HKDF-SHA256 to split one master key
into independent, labelled subkeys (e.g. one for the SQLite databases, one for the flat memory files),
so a single OS-keystore master key protects every surface without the surfaces sharing key material.
Stdlib has no AES, so this is the one place the ``cryptography`` dependency is unavoidable.

中文 —
静态加密背后的对称原语。``Cipher`` 封装 AES-256-GCM（一种 AEAD：同时加密与认证，故解密时可检出篡改）。每次
``encrypt`` 生成全新的随机 12 字节 nonce 并前置于密文，因此对同一明文加密两次得到不同密文且不会复用 nonce。
``derive_subkey`` 使用 HKDF-SHA256 将一个主密钥派生为相互独立、带标签的子密钥（如数据库一把、扁平记忆文件一把），
使单一 OS-keystore 主密钥保护各面而彼此不共享密钥材料。标准库没有 AES，故此处是 ``cryptography`` 依赖唯一不可避免之处。
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_NONCE_BYTES = 12


def derive_subkey(master: bytes, label: str) -> bytes:
    """Derive a 32-byte subkey from a master key for a named purpose.

    EN —
    Args: master (the OS-keystore master key, any length); label (purpose, e.g. ``db`` / ``file`` —
        different labels yield independent subkeys). Returns: a 32-byte AES-256 key.

    中文 —
    参数：master（OS-keystore 主密钥，任意长度）；label（用途，如 ``db`` / ``file``——不同标签产生相互独立的
        子密钥）。返回：32 字节的 AES-256 密钥。
    """
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"jobpin/" + label.encode()
    ).derive(master)


class Cipher:
    """AES-256-GCM authenticated encryption over byte payloads.

    EN —
    Args (constructor): key (exactly 32 bytes). Raises: ValueError if the key is not 32 bytes.
    Learning note: GCM is an AEAD, so ``decrypt`` raises on any tampering (a flipped bit fails the tag)
    rather than returning corrupt plaintext — this is what makes "fail safe" enforceable.

    中文 —
    参数（构造器）：key（恰好 32 字节）。抛出：密钥非 32 字节时抛 ValueError。
    学习笔记：GCM 是 AEAD，故 ``decrypt`` 在任何篡改时抛错（翻转一位即认证标签失败），而非返回损坏明文——这正是
    “失败即安全”可被强制执行的原因。
    """

    def __init__(self, key: bytes) -> None:
        """Build a cipher from a 32-byte key.

        EN — Args: key (32 bytes). Raises: ValueError. 中文 — 参数：key（32 字节）。抛出：ValueError。
        """
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes")
        self._aes = AESGCM(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt, returning ``nonce(12) || ciphertext || tag``.

        EN — Args: plaintext. Returns: a self-describing blob (random nonce prepended).
        中文 — 参数：plaintext。返回：自描述密文（前置随机 nonce）。
        """
        nonce = os.urandom(_NONCE_BYTES)
        return nonce + self._aes.encrypt(nonce, plaintext, None)

    def decrypt(self, blob: bytes) -> bytes:
        """Decrypt a blob produced by ``encrypt``.

        EN — Args: blob. Returns: the plaintext. Raises: cryptography ``InvalidTag`` on tamper/wrong key.
        中文 — 参数：blob。返回：明文。抛出：篡改/错误密钥时抛 cryptography 的 ``InvalidTag``。
        """
        return self._aes.decrypt(blob[:_NONCE_BYTES], blob[_NONCE_BYTES:], None)
