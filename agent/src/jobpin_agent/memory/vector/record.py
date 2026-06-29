"""The vector-store record schema (§1.4).

EN —
One ``VectorRecord`` = a semantic vector + the pointers a regulated, local-first product
needs around it: ``memory_key`` (the ``tenant:org:entity_type:entity_id`` namespace key —
the anchor for RBAC scoping and the §1.5 erasure cascade), ``embed_model`` / ``embed_version``
(pinned; a mismatch forbids mixed retrieval and triggers re-embed), ``struct_ref`` (back-link
to the structured row), and ``source_ref`` (back-link to the original-text chunk — the "back to
source" citation on recall). ``text`` is kept inline so recall can render the citation and the
re-embed migration can recompute the vector without a second store.

中文 —
一个 ``VectorRecord`` = 一个语义向量 + 受监管、本地优先产品在其周围所需的指针：``memory_key``
（``tenant:org:entity_type:entity_id`` 命名空间键——RBAC 范围与 §1.5 擦除级联的锚点）、``embed_model`` /
``embed_version``（固定；不一致则禁止混合检索并触发重嵌入）、``struct_ref``（指回结构化行）、``source_ref``
（指回原文片段——召回时的“回到来源”引用）。``text`` 内联保留，使召回可渲染引用、重嵌入迁移可在无第二存储下重算向量。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List


def new_id() -> str:
    """Generate a fresh vector id.

    EN: Returns: a random hex uuid. 中文：返回：随机十六进制 uuid。
    """
    return uuid.uuid4().hex


@dataclass
class VectorRecord:
    """A semantic vector plus its provenance/namespace pointers.

    EN —
    Attributes: memory_key (namespace key); embed_model / embed_version (pinned signature);
    struct_ref (structured-row back-link); source_ref (original-chunk back-link, the citation);
    text (the chunk, kept inline); embedding (the vector); vector_id (defaults to a fresh uuid).

    中文 —
    属性：memory_key（命名空间键）；embed_model / embed_version（固定签名）；struct_ref（结构化行回链）；
    source_ref（原片段回链，即引用）；text（内联保留的片段）；embedding（向量）；vector_id（默认新 uuid）。
    """

    memory_key: str
    embed_model: str
    embed_version: str
    struct_ref: str
    source_ref: str
    text: str
    embedding: List[float]
    vector_id: str = field(default_factory=new_id)
