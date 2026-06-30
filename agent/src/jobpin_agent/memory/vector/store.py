"""The vector store — interface + a stdlib SQLite reference implementation (§1.4).

EN —
``VectorStore`` is the interface the retrieval providers depend on; ``SqliteVectorStore`` is a
dependency-free reference impl: vectors live in one SQLite table, nearest-neighbour is
brute-force cosine (fine at the stated hundreds–thousands local scale), and a production
backend (sqlite-vec / LanceDB, post-§1.12) swaps in behind the same interface. Two safety
properties matter for a regulated product: (1) a **drift guard** — the store pins one
``embed_version`` and rejects a record from a different vector space (no silent mixing); (2)
**erasure cascade** — ``delete_by_key_prefix`` removes a data subject's derived vectors by
``memory_key`` prefix (the mechanism §1.5 erasure calls). ``search`` accepts a ``key_prefix``
so a caller (§1.5 RBAC) can **filter before** nearest-neighbour, not after.

中文 —
``VectorStore`` 是检索 provider 依赖的接口；``SqliteVectorStore`` 是无依赖参考实现：向量存于单张 SQLite 表，近邻为
暴力余弦（在所述数百–数千的本地规模下足够），生产后端（sqlite-vec / LanceDB，§1.12 后）在同一接口背后替换。对受监管
产品有两个关键安全性质：(1) **漂移守卫**——存储固定一个 ``embed_version`` 并拒绝来自不同向量空间的记录（不静默混用）；
(2) **擦除级联**——``delete_by_key_prefix`` 按 ``memory_key`` 前缀删除数据主体的派生向量（§1.5 擦除所调用的机制）。
``search`` 接受 ``key_prefix``，使调用方（§1.5 RBAC）可在近邻**之前过滤**，而非之后。
"""
from __future__ import annotations

import json
import sqlite3

from ...security.db_encryption import open_encrypted_db
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from ..embedding import cosine
from .record import VectorRecord

# A search hit: the record and its cosine score against the query.
Hit = Tuple[VectorRecord, float]


class VectorStore(ABC):
    """Interface for an embedded vector store (§1.4).

    EN —
    Implementations persist ``VectorRecord``s and answer nearest-neighbour queries. The
    production backend (post-§1.12) implements this same surface.

    中文 —
    实现持久化 ``VectorRecord`` 并回答近邻查询。生产后端（§1.12 后）实现同一接口。
    """

    @abstractmethod
    def add(self, records: List[VectorRecord]) -> None:
        """Persist records (enforcing the single-``embed_version`` drift guard).

        EN: Args: records. Raises: ValueError if a record's embed_version is incompatible.
        中文：参数：records。抛出：若记录的 embed_version 不兼容则 ValueError。
        """

    @abstractmethod
    def delete(self, vector_ids: List[str]) -> int:
        """Delete records by id. Returns the number removed.

        EN: Args: vector_ids. Returns: count deleted.
        中文：参数：vector_ids。返回：删除数。
        """

    @abstractmethod
    def delete_by_key_prefix(self, prefix: str) -> int:
        """Delete all records whose memory_key equals or is nested under ``prefix`` (erasure cascade).

        EN: Args: prefix (a memory_key). Returns: count deleted.
        中文：参数：prefix（一个 memory_key）。返回：删除数。
        """

    @abstractmethod
    def search(
        self,
        query: List[float],
        k: int,
        *,
        key_prefix: Optional[str] = None,
        scope: Optional[Callable[[str], bool]] = None,
    ) -> List[Hit]:
        """Return the top-``k`` nearest records, filtering BEFORE the top-``k`` truncation.

        EN: Args: query (vector); k; key_prefix (SQL prefix pre-filter); scope (a memory_key
            predicate applied BEFORE scoring/truncation — the no-leak ordering). Returns: hits, score-desc.
        中文：参数：query（向量）；k；key_prefix（SQL 前缀预过滤）；scope（在打分/截断**之前**应用的 memory_key 谓词
            ——无泄漏顺序）。返回：按分数降序的命中。
        """

    @abstractmethod
    def current_version(self) -> Set[str]:
        """Return the distinct embed_versions on disk (drift detection).

        EN: Returns: the set of embed_versions present (size 1 in steady state).
        中文：返回：磁盘上存在的 embed_version 集合（稳态下大小为 1）。
        """

    @abstractmethod
    def all_records(self) -> List[VectorRecord]:
        """Return every stored record (a bulk scan, used by the re-embed migration).

        EN: Returns: all records (backend-agnostic so re-embed works on any backend).
        中文：返回：全部记录（后端无关，使重嵌入可在任何后端工作）。
        """


class SqliteVectorStore(VectorStore):
    """A stdlib SQLite + brute-force-cosine reference vector store (§1.4).

    EN —
    One table; embeddings stored as JSON. All SQL is parameterised. ``search`` is O(n) cosine —
    acceptable at hundreds–thousands of rows and swapped for an indexed backend post-§1.12.

    中文 —
    单表；嵌入以 JSON 存储。所有 SQL 参数化。``search`` 为 O(n) 余弦——在数百–数千行下可接受，§1.12 后换为带索引后端。
    """

    def __init__(self, db_path: str = ":memory:", cipher_key: bytes | None = None) -> None:
        """Open (or create) the store and ensure the schema.

        EN: Args: db_path (``:memory:`` for an ephemeral DB); cipher_key (§1.9 at-rest encryption when set).
        中文：参数：db_path（``:memory:`` 为临时库）；cipher_key（设置时启用 §1.9 静态加密）。
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = open_encrypted_db(db_path, cipher_key)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS vectors ("
            "vector_id TEXT PRIMARY KEY, memory_key TEXT, embed_model TEXT, embed_version TEXT, "
            "struct_ref TEXT, source_ref TEXT, text TEXT, embedding TEXT)"
        )
        self._conn.commit()

    def add(self, records: List[VectorRecord]) -> None:
        """Persist records under the pinned embed_version (drift-guarded).

        EN —
        On an empty store the batch must share one embed_version (pins it); thereafter every
        record's embed_version must match the pinned set, else ValueError (no silent mixing).
        Args: records. Raises: ValueError on a version mismatch.

        中文 —
        空存储时该批必须共享一个 embed_version（据此固定）；其后每条记录的 embed_version 必须匹配固定集合，否则
        ValueError（不静默混用）。参数：records。抛出：版本不一致时 ValueError。
        """
        if not records:
            return
        pinned = self.current_version()
        if not pinned:
            batch_versions = {r.embed_version for r in records}
            if len(batch_versions) > 1:
                raise ValueError(f"Cannot pin store: batch mixes embed_versions {sorted(batch_versions)}.")
            pinned = batch_versions
        for r in records:
            if r.embed_version not in pinned:
                raise ValueError(
                    f"embed_version drift: record '{r.embed_version}' != pinned {sorted(pinned)}. "
                    f"Re-embed (migrate) before mixing vector spaces."
                )
        self._conn.executemany(
            "INSERT OR REPLACE INTO vectors VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (r.vector_id, r.memory_key, r.embed_model, r.embed_version,
                 r.struct_ref, r.source_ref, r.text, json.dumps(r.embedding))
                for r in records
            ],
        )
        self._conn.commit()

    def delete(self, vector_ids: List[str]) -> int:
        """Delete records by id.

        EN: Args: vector_ids. Returns: rows removed.
        中文：参数：vector_ids。返回：删除行数。
        """
        if not vector_ids:
            return 0
        placeholders = ",".join("?" for _ in vector_ids)
        cur = self._conn.execute(f"DELETE FROM vectors WHERE vector_id IN ({placeholders})", vector_ids)
        self._conn.commit()
        return cur.rowcount

    def delete_by_key_prefix(self, prefix: str) -> int:
        """Delete records whose memory_key == prefix or is nested under ``prefix:`` (erasure cascade).

        EN: Args: prefix. Returns: rows removed. Exact-or-nested match (no wildcard injection).
        中文：参数：prefix。返回：删除行数。精确或嵌套匹配（无通配注入）。
        """
        cur = self._conn.execute(
            "DELETE FROM vectors WHERE memory_key = ? OR memory_key LIKE ? ESCAPE '\\'",
            (prefix, _escape_like(prefix) + ":%"),
        )
        self._conn.commit()
        return cur.rowcount

    def search(
        self,
        query: List[float],
        k: int,
        *,
        key_prefix: Optional[str] = None,
        scope: Optional[Callable[[str], bool]] = None,
    ) -> List[Hit]:
        """Brute-force cosine nearest-neighbour, filtering BEFORE the top-k truncation.

        EN —
        Args: query; k; key_prefix (SQL prefix pre-filter); scope (a memory_key predicate applied
        BEFORE scoring/truncation — so an out-of-scope record can never displace an in-scope one from
        the top-k). Returns: the top-k ``(record, score)`` hits, score-descending (zero-score dropped).
        中文 —
        参数：query；k；key_prefix（SQL 前缀预过滤）；scope（在打分/截断**之前**应用的 memory_key 谓词——使范围外
        记录绝不会把范围内记录挤出 top-k）。返回：按分数降序的 top-k ``(记录, 分数)`` 命中（丢弃零分）。
        """
        if key_prefix is None:
            rows = self._conn.execute("SELECT * FROM vectors").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM vectors WHERE memory_key = ? OR memory_key LIKE ? ESCAPE '\\'",
                (key_prefix, _escape_like(key_prefix) + ":%"),
            ).fetchall()
        scored: List[Hit] = []
        for row in rows:
            rec = _row_to_record(row)
            if scope is not None and not scope(rec.memory_key):
                continue  # filter BEFORE scoring/truncation (no retrieve-then-filter leak)
            score = cosine(query, rec.embedding)
            if score > 0.0:
                scored.append((rec, score))
        scored.sort(key=lambda h: h[1], reverse=True)
        return scored[:k]

    def current_version(self) -> Set[str]:
        """Return the distinct embed_versions stored.

        EN: Returns: a set of embed_version strings (empty if the store is empty).
        中文：返回：embed_version 字符串集合（空存储则为空）。
        """
        rows = self._conn.execute("SELECT DISTINCT embed_version FROM vectors").fetchall()
        return {r[0] for r in rows}

    def all_records(self) -> List[VectorRecord]:
        """Return every stored record (used by the re-embed migration).

        EN: Returns: all records. 中文：返回：全部记录。
        """
        return [_row_to_record(r) for r in self._conn.execute("SELECT * FROM vectors").fetchall()]


def _escape_like(text: str) -> str:
    """Escape LIKE wildcards in a literal prefix (defensive; keys are controlled).

    EN: Args: text. Returns: text with ``\\`` ``%`` ``_`` escaped for an ESCAPE '\\' LIKE.
    中文：参数：text。返回：为 ESCAPE '\\' 的 LIKE 转义了 ``\\`` ``%`` ``_`` 的文本。
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _row_to_record(row) -> VectorRecord:
    """Rebuild a ``VectorRecord`` from a DB row.

    EN: Args: row (the 8-column tuple). Returns: the record.
    中文：参数：row（8 列元组）。返回：记录。
    """
    return VectorRecord(
        vector_id=row[0], memory_key=row[1], embed_model=row[2], embed_version=row[3],
        struct_ref=row[4], source_ref=row[5], text=row[6], embedding=json.loads(row[7]),
    )
