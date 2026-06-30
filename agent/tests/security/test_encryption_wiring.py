"""Acceptance: at-rest encryption wired into a store — ciphertext on disk, key-gated, opt-in (§1.9).

EN — The §1.9 exit criterion ("raw-disk read cannot yield plaintext") proven end-to-end through a real
store (the §1.8 ``CanonicalStore``, which carries candidate PII): with a key the candidate's name is
absent from the raw DB bytes yet reads back through the keyed connection; with no key the store is
plain (default), so existing behaviour is preserved.

中文 — §1.9 退出标准（“裸盘读取无法获得明文”）通过真实存储（§1.8 ``CanonicalStore``，承载候选人 PII）端到端证明：
带密钥时候选人姓名不出现在原始数据库字节中却能经带密钥连接读回；无密钥时存储为明文（默认），保留既有行为。
"""
from jobpin_agent.data.schema import Candidate
from jobpin_agent.data.store import CanonicalStore


def test_canonical_store_encrypted_on_disk(tmp_path):
    """A keyed CanonicalStore is ciphertext at rest and reads back through the key. 中文 — 带密钥的存储静态为密文且经密钥读回。"""
    db = str(tmp_path / "c.db")
    key = b"K" * 32
    s = CanonicalStore(db_path=db, cipher_key=key)
    s.upsert_candidate(Candidate(candidate_id="c1", name="ZARA_SECRET", skills=["py"]))
    s.close()
    assert b"ZARA_SECRET" not in open(db, "rb").read()
    s2 = CanonicalStore(db_path=db, cipher_key=key)
    assert s2.get_candidate("c1").name == "ZARA_SECRET"
    s2.close()


def test_canonical_store_plain_when_no_key(tmp_path):
    """The default (no key) store is plain sqlite — existing behaviour preserved. 中文 — 默认（无密钥）为普通 sqlite，保留既有行为。"""
    db = str(tmp_path / "p.db")
    s = CanonicalStore(db_path=db)
    s.upsert_candidate(Candidate(candidate_id="c1", name="ZARA_PLAIN"))
    s.close()
    assert b"ZARA_PLAIN" in open(db, "rb").read()


def test_keystore_to_store_end_to_end(tmp_path):
    """Join the halves: an OS-keystore master key encrypts a real store end-to-end (§1.9).

    EN — A master key from a ``KeyStore`` flows into ``open_encrypted_db`` (which derives the ``db``
    subkey), so the store is ciphertext at rest and reads back — proving keystore→cipher→store, not just
    the two halves in isolation.
    中文 — 来自 ``KeyStore`` 的主密钥流入 ``open_encrypted_db``（其派生 ``db`` 子密钥），故存储静态为密文且可读回——
    证明 keystore→cipher→store 全链路，而非孤立的两半。
    """
    from jobpin_agent.security.keystore import DevKeyStore

    master = DevKeyStore(str(tmp_path / "mk.bin")).get_or_create_master_key()
    db = str(tmp_path / "k.db")
    s = CanonicalStore(db_path=db, cipher_key=master)
    s.upsert_candidate(Candidate(candidate_id="c1", name="KEYSTORE_SECRET"))
    s.close()
    assert b"KEYSTORE_SECRET" not in open(db, "rb").read()
    s2 = CanonicalStore(db_path=db, cipher_key=master)
    assert s2.get_candidate("c1").name == "KEYSTORE_SECRET"
    s2.close()
