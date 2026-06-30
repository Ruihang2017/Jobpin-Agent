"""Tests for ``security/cipher.py`` — AES-256-GCM round-trip, nonce randomisation, tamper detection.

EN — Proves the AEAD round-trips, never reuses a nonce, fails closed on tampering, and that labelled
subkeys are independent and 32 bytes.

中文 — 证明该 AEAD 可往返、绝不复用 nonce、篡改时失败即安全，且带标签的子密钥相互独立并为 32 字节。
"""
import pytest

from jobpin_agent.security.cipher import Cipher, derive_subkey


def test_roundtrip():
    """Encrypt then decrypt returns the original bytes. 中文 — 加密后解密返回原始字节。"""
    c = Cipher(b"0" * 32)
    assert c.decrypt(c.encrypt(b"hello PII")) == b"hello PII"


def test_nonce_randomised():
    """Same plaintext yields different ciphertext (random nonce). 中文 — 同一明文产生不同密文。"""
    c = Cipher(b"0" * 32)
    assert c.encrypt(b"x") != c.encrypt(b"x")


def test_tamper_raises():
    """A flipped bit fails the auth tag. 中文 — 翻转一位即认证标签失败。"""
    c = Cipher(b"0" * 32)
    blob = bytearray(c.encrypt(b"x"))
    blob[-1] ^= 0x01
    with pytest.raises(Exception):
        c.decrypt(bytes(blob))


def test_bad_key_length():
    """A non-32-byte key is rejected. 中文 — 非 32 字节密钥被拒绝。"""
    with pytest.raises(ValueError):
        Cipher(b"short")


def test_subkeys_differ_by_label():
    """Different labels yield independent 32-byte subkeys. 中文 — 不同标签产生独立的 32 字节子密钥。"""
    m = b"1" * 32
    assert derive_subkey(m, "db") != derive_subkey(m, "file")
    assert len(derive_subkey(m, "db")) == 32
