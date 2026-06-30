"""Acceptance: the file-backed Org/Recruiter MemoryStore (§1.2 port) encrypts at rest (§1.9).

EN — With an injected ``Cipher`` the ORG.md bytes on disk are ciphertext (no plaintext leak) yet the
entry round-trips through a fresh store with the same cipher; with no cipher (default) the file is
plaintext exactly as the §1.2 port always behaved.

中文 — 注入 ``Cipher`` 时磁盘上的 ORG.md 字节为密文（不泄漏明文），但条目可经同一 cipher 的新存储往返；无 cipher
（默认）时文件为明文，与 §1.2 移植一贯行为完全一致。
"""
from jobpin_agent.memory.store import MemoryStore
from jobpin_agent.security.cipher import Cipher


def test_file_store_encrypted_on_disk(tmp_path):
    """ORG.md is ciphertext at rest and round-trips through the cipher. 中文 — ORG.md 静态为密文且经 cipher 往返。"""
    cipher = Cipher(b"F" * 32)
    secret = "Acme policy: SECRET_POLICY_TOKEN must stay internal"
    s = MemoryStore(str(tmp_path), cipher=cipher)
    s.load_from_disk()
    assert s.add("org", secret)["success"] is True

    raw = (tmp_path / "ORG.md").read_bytes()
    assert b"SECRET_POLICY_TOKEN" not in raw  # ciphertext at rest

    s2 = MemoryStore(str(tmp_path), cipher=cipher)
    s2.load_from_disk()
    assert "SECRET_POLICY_TOKEN" in (s2.format_for_system_prompt("org") or "")


def test_file_store_plain_when_no_cipher(tmp_path):
    """Default (no cipher) writes plaintext — the §1.2 behaviour is unchanged. 中文 — 默认（无 cipher）写明文——§1.2 行为不变。"""
    s = MemoryStore(str(tmp_path))
    s.load_from_disk()
    s.add("org", "Acme policy: PLAIN_POLICY_TOKEN is visible")
    assert b"PLAIN_POLICY_TOKEN" in (tmp_path / "ORG.md").read_bytes()


def test_drift_backup_no_plaintext_leak_under_encryption(tmp_path):
    """Under encryption, a drift ``.bak`` holds raw ciphertext — never the decrypted plaintext.

    EN — Even when the drift path is handed the decrypted text, ``_backup_drift`` with a cipher set
    snapshots the on-disk BYTES (ciphertext), so no plaintext leaks into the ``.bak``.
    中文 — 即便漂移路径拿到了解密文本，设置了 cipher 的 ``_backup_drift`` 也只快照落盘字节（密文），故 ``.bak`` 不泄漏明文。
    """
    cipher = Cipher(b"F" * 32)
    s = MemoryStore(str(tmp_path), cipher=cipher)
    s.load_from_disk()
    s.add("org", "TOPSECRET_DRIFT_TOKEN policy")
    path = tmp_path / "ORG.md"
    bak = s._backup_drift(path, raw="TOPSECRET_DRIFT_TOKEN policy")
    bak_bytes = open(bak, "rb").read()
    assert b"TOPSECRET_DRIFT_TOKEN" not in bak_bytes      # ciphertext only — no plaintext leak
    assert bak_bytes == path.read_bytes()                # backed up the raw on-disk ciphertext
