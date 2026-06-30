"""Smoke test: SQLCipher PRAGMA-key round-trip + raw-disk ciphertext (§1.9 Task 1).

EN — Proves the chosen dependency works on this platform before we build on it: a keyed SQLCipher
connection writes a row, a raw byte read of the file shows no plaintext, the wrong key cannot read,
and the right key reads back. This is the de-risking gate for the whole at-rest-encryption approach.

中文 — 在此基础之上构建前，先证明所选依赖在本平台可用：带密钥的 SQLCipher 连接写入一行，对文件的原始字节读取看不到明文，
错误密钥无法读取，正确密钥可读回。这是整个静态加密方案的去风险关口。
"""
import sqlcipher3


def test_sqlcipher_pragma_key_roundtrip(tmp_path):
    """Keyed DB is ciphertext on disk; wrong key fails, right key reads back.

    EN — Args: tmp_path (pytest fixture). Asserts ciphertext at rest + key-gated read.
    中文 — 参数：tmp_path（pytest 夹具）。断言静态密文 + 按密钥门控的读取。
    """
    db = str(tmp_path / "enc.db")
    key_hex = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
    conn = sqlcipher3.connect(db)
    conn.execute("PRAGMA key = \"x'" + key_hex + "'\"")
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t VALUES ('SECRETNAME')")
    conn.commit()
    conn.close()

    raw = open(db, "rb").read()
    assert b"SECRETNAME" not in raw

    bad = sqlcipher3.connect(db)
    bad.execute("PRAGMA key = \"x'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'\"")
    try:
        bad.execute("SELECT v FROM t").fetchall()
        assert False, "wrong key should fail"
    except Exception:
        pass
    bad.close()

    good = sqlcipher3.connect(db)
    good.execute("PRAGMA key = \"x'" + key_hex + "'\"")
    assert good.execute("SELECT v FROM t").fetchone()[0] == "SECRETNAME"
    good.close()
