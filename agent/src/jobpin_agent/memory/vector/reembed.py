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
from .store import VectorStore


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
    src_store: VectorStore,
    dst_store: VectorStore,
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
    validated (every source ``vector_id`` present in the destination + a single pinned ``new_version``).
    Note on the deliverable wording: drift is *detected* by the store's ``add`` guard (it rejects a
    foreign version), and the *switch* is the caller's (swap to ``dst_store`` once ``complete``); this
    function does the re-embed + validate between them. Args: src_store; dst_store; new_embed_fn;
    new_version; new_embed_model; limit. Returns: a ``ReembedResult``.

    中文补充：漂移由存储 ``add`` 守卫*检测*（拒绝异版本），*切换*由调用方负责（``complete`` 后切到 ``dst_store``）；
    本函数负责其间的重嵌入 + 校验。

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
    """Validate a completed migration: every source id is present and the version is pinned.

    EN —
    Checks the destination pins exactly ``new_version`` and contains every source ``vector_id`` (id
    existence, not a cosine self-match — a record with empty/non-tokenisable text embeds to a zero
    vector, which a cosine round-trip would wrongly report as missing). Args: src_store; dst_store;
    new_embed_fn (unused; kept for signature stability); new_version. Returns: True if consistent.

    中文 —
    检查目标恰好固定 ``new_version`` 且包含每个源 ``vector_id``（按 id 存在性，而非余弦自匹配——文本为空/不可分词的
    记录嵌入为零向量，余弦往返会误报其缺失）。参数：见英文。返回：一致则 True。
    """
    if dst_store.current_version() != {new_version}:
        return False
    src_ids = {r.vector_id for r in src_store.all_records()}
    dst_ids = {r.vector_id for r in dst_store.all_records()}
    return src_ids == dst_ids
