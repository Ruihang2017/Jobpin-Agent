"""Re-embed migration (§1.4) — switch embedding models without silently mixing vector spaces.

EN —
Switching the embedding model (or its dimension) makes the old vectors incompatible with the new
ones — querying a mix is meaningless. So a model swap is an explicit **migration**: re-embed every
record's ``text`` into a fresh store at the new ``embed_version``, validate, then switch to it. It is
**resumable**: the destination store *is* the checkpoint — records already migrated (same
``vector_id``) are skipped on a re-run, so an interrupted migration finishes where it left off. The
source store stays queryable at its old version until the switch, so retrieval never mixes versions.

中文 —
切换嵌入模型（或其维度）会使旧向量与新向量不兼容——混查无意义。故模型切换是显式**迁移**：把每条记录的 ``text``
在新 ``embed_version`` 下重嵌入到一个新存储、校验、再切换过去。它**可恢复**：目标存储即检查点——已迁移的记录
（相同 ``vector_id``）在重跑时跳过，故被中断的迁移可续。源存储在切换前仍以旧版本可查，故检索绝不混用版本。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..embedding import EmbedFn
from .record import VectorRecord
from .store import SqliteVectorStore


@dataclass
class ReembedResult:
    """The outcome of a (possibly partial) re-embed run.

    EN —
    Attributes: total (records in the source); migrated (this run); done (cumulative in the
    destination); complete (done == total); validated (count + sample checks passed); new_version.
    中文 —
    属性：total（源中记录数）；migrated（本次）；done（目标中累计）；complete（done == total）；
    validated（计数 + 抽样校验通过）；new_version。
    """

    total: int
    migrated: int
    done: int
    complete: bool
    validated: bool
    new_version: str


def reembed(
    src_store: SqliteVectorStore,
    dst_store: SqliteVectorStore,
    new_embed_fn: EmbedFn,
    new_version: str,
    *,
    new_embed_model: str = "hash",
    limit: Optional[int] = None,
) -> ReembedResult:
    """Re-embed source records into a destination store at ``new_version`` (resumable).

    EN —
    Skips records already in ``dst_store`` (resume). With ``limit`` set, migrates at most that many
    this call (used to simulate an interrupt). When the destination holds every source record, it is
    validated (count + a sample round-trip). The caller switches to ``dst_store`` once ``complete``.
    Args: src_store; dst_store; new_embed_fn; new_version; new_embed_model; limit.
    Returns: a ``ReembedResult``.

    中文 —
    跳过已在 ``dst_store`` 中的记录（续传）。设 ``limit`` 时本次最多迁移这么多（用于模拟中断）。当目标含全部源记录时
    做校验（计数 + 抽样往返）。``complete`` 后由调用方切换到 ``dst_store``。
    参数：src_store；dst_store；new_embed_fn；new_version；new_embed_model；limit。返回：``ReembedResult``。
    """
    src_records = src_store.all_records()
    total = len(src_records)
    done_ids = {r.vector_id for r in dst_store.all_records()}
    migrated = 0
    for rec in src_records:
        if rec.vector_id in done_ids:
            continue
        if limit is not None and migrated >= limit:
            break
        dst_store.add([VectorRecord(
            memory_key=rec.memory_key, embed_model=new_embed_model, embed_version=new_version,
            struct_ref=rec.struct_ref, source_ref=rec.source_ref, text=rec.text,
            embedding=new_embed_fn(rec.text), vector_id=rec.vector_id,
        )])
        migrated += 1
    done = len(dst_store.all_records())
    complete = done == total
    validated = complete and _validate(src_store, dst_store, new_embed_fn, new_version)
    return ReembedResult(total=total, migrated=migrated, done=done,
                         complete=complete, validated=validated, new_version=new_version)


def _validate(src_store, dst_store, new_embed_fn, new_version) -> bool:
    """Validate a completed migration: count match, single new version, and a sample round-trip.

    EN: Args: src_store; dst_store; new_embed_fn; new_version. Returns: True if consistent.
    中文：参数：见英文。返回：一致则 True。
    """
    if dst_store.current_version() != {new_version}:
        return False
    src_records = src_store.all_records()
    if len(src_records) != len(dst_store.all_records()):
        return False
    sample = src_records[0]
    hits = dst_store.search(new_embed_fn(sample.text), k=1, key_prefix=sample.memory_key)
    return bool(hits)
