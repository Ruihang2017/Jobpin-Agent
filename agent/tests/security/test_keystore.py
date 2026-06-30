"""Tests for ``security/keystore.py`` — stable master key + never-plaintext-on-disk.

EN — The dev keystore is idempotent; the platform default round-trips a 32-byte key and its on-disk
bytes never equal the raw key; the DPAPI path is exercised on Windows.

中文 — dev keystore 幂等；平台默认往返一把 32 字节密钥且其落盘字节绝不等于原始密钥；DPAPI 路径在 Windows 上被演练。
"""
import sys

import pytest

from jobpin_agent.security.keystore import DevKeyStore, default_keystore


def test_dev_keystore_stable(tmp_path):
    """Two calls return the same 32-byte key. 中文 — 两次调用返回同一把 32 字节密钥。"""
    ks = DevKeyStore(str(tmp_path / "mk.bin"))
    k1 = ks.get_or_create_master_key()
    k2 = ks.get_or_create_master_key()
    assert k1 == k2 and len(k1) == 32


def test_default_keystore_not_plaintext_on_disk(tmp_path):
    """The wrapped on-disk bytes do not contain the raw key. 中文 — 封装后的落盘字节不包含原始密钥。"""
    ks = default_keystore(str(tmp_path / "mk.bin"))
    k = ks.get_or_create_master_key()
    assert len(k) == 32
    assert k not in open(tmp_path / "mk.bin", "rb").read()


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_roundtrip(tmp_path):
    """DPAPI wrap/unwrap is idempotent and never stores the raw key. 中文 — DPAPI 封装/解封幂等且不存原始密钥。"""
    from jobpin_agent.security.keystore import WindowsDpapiKeyStore

    ks = WindowsDpapiKeyStore(str(tmp_path / "mk.bin"))
    k = ks.get_or_create_master_key()
    assert ks.get_or_create_master_key() == k and len(k) == 32
    assert k not in open(tmp_path / "mk.bin", "rb").read()
