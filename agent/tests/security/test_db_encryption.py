"""Tests for ``security/db_encryption.py`` — encrypted-when-keyed, plain-when-not.

EN — With a key, the DB is ciphertext on disk and only the right key reads it back; with no key it is a
plain readable sqlite file (the default, preserving existing behaviour).

中文 — 带密钥时数据库落盘为密文且仅正确密钥可读回；无密钥时为普通可读的 sqlite 文件（默认，保留既有行为）。
"""
from jobpin_agent.security.db_encryption import open_encrypted_db


def test_plain_when_no_key(tmp_path):
    """key=None → plain sqlite (plaintext readable on disk). 中文 — key=None → 普通 sqlite（落盘明文可读）。"""
    db = str(tmp_path / "p.db")
    c = open_encrypted_db(db, None)
    c.execute("CREATE TABLE t (v TEXT)")
    c.execute("INSERT INTO t VALUES ('PLAINNAME')")
    c.commit()
    c.close()
    assert b"PLAINNAME" in open(db, "rb").read()


def test_encrypted_when_key(tmp_path):
    """key set → ciphertext on disk, key-gated read. 中文 — 设置 key → 落盘密文，按密钥门控读取。"""
    db = str(tmp_path / "e.db")
    key = b"k" * 32
    c = open_encrypted_db(db, key)
    c.execute("CREATE TABLE t (v TEXT)")
    c.execute("INSERT INTO t VALUES ('SECRETNAME')")
    c.commit()
    c.close()
    assert b"SECRETNAME" not in open(db, "rb").read()
    c2 = open_encrypted_db(db, key)
    assert c2.execute("SELECT v FROM t").fetchone()[0] == "SECRETNAME"
    c2.close()
