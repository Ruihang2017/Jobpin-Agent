"""Encrypted SQLite open — SQLCipher when keyed, plain sqlite3 passthrough when not (§1.9).

EN —
``open_encrypted_db`` is the single seam every SQLite store opens through. With a key it returns a
SQLCipher connection (transparent AES-256 page encryption — the on-disk file is ciphertext, durable,
with normal SQLite transaction semantics) keyed by a ``db``-labelled subkey of the master key. With
``key=None`` it returns a plain ``sqlite3`` connection — the default, so existing tests, ``:memory:``
databases, and the encryption-disabled deployment behave exactly as before. ``connect_kwargs`` (e.g.
``check_same_thread=False``) are forwarded to whichever backend is used.

中文 —
``open_encrypted_db`` 是每个 SQLite 存储打开时经过的唯一接缝。带密钥时返回 SQLCipher 连接（透明 AES-256 页加密——
落盘文件为密文、持久、具备正常 SQLite 事务语义），以主密钥的 ``db`` 标签子密钥加密。``key=None`` 时返回普通
``sqlite3`` 连接——此为默认，使既有测试、``:memory:`` 数据库与禁用加密的部署行为与此前完全一致。``connect_kwargs``
（如 ``check_same_thread=False``）被转发给所用的后端。
"""
from __future__ import annotations

import sqlite3

from .cipher import derive_subkey


def open_encrypted_db(path: str, key: bytes | None, **connect_kwargs):
    """Open ``path`` encrypted (SQLCipher) if ``key`` is given, else plain ``sqlite3``.

    EN —
    Args: path (DB path or ``:memory:``); key (master key, or None to disable encryption);
        connect_kwargs (forwarded to the backend, e.g. ``check_same_thread``). Returns: a DBAPI
        connection. Learning note: a ``db``-labelled subkey is derived so the same master key can also
        protect the flat memory files under a different subkey without sharing key material.

    中文 —
    参数：path（数据库路径或 ``:memory:``）；key（主密钥，或 None 以禁用加密）；connect_kwargs（转发给后端，
        如 ``check_same_thread``）。返回：DBAPI 连接。学习笔记：派生 ``db`` 标签子密钥，使同一主密钥也能以不同子密钥
        保护扁平记忆文件而不共享密钥材料。
    """
    if key is None:
        return sqlite3.connect(path, **connect_kwargs)
    import sqlcipher3

    conn = sqlcipher3.connect(path, **connect_kwargs)
    db_key = derive_subkey(key, "db")
    conn.execute("PRAGMA key = \"x'" + db_key.hex() + "'\"")
    return conn
