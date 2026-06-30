"""Connector SDK + anti-corruption layer (§1.10) — the external→canonical contract.

EN —
Two abstractions isolate the rest of the product from external systems. A ``Connector`` performs a
read-only ``fetch`` returning opaque ``ExternalRecord``s (external field names, untouched). An
``AntiCorruptionLayer`` is the ONLY place those external field names are read: ``translate`` dispatches by
``kind`` and maps a raw external row into a well-formed §1.8 canonical dataclass (``Candidate``/``Job``/
``Application``). So an external ATS renaming a field touches only the ACL subclass — never the §1.8 schema
or any consumer. Unknown kinds fail closed (``ValueError``).

中文 —
两个抽象把产品其余部分与外部系统隔离。``Connector`` 执行只读 ``fetch``，返回不透明的 ``ExternalRecord``（外部字段名，
原样保留）。``AntiCorruptionLayer`` 是读取这些外部字段名的**唯一**之处：``translate`` 按 ``kind`` 分派，把一行原始外部
数据映射为良构的 §1.8 规范数据类（``Candidate``/``Job``/``Application``）。故外部 ATS 改名字段只触及 ACL 子类——绝不波及
§1.8 schema 或任何消费方。未知 kind 失败即关闭（抛 ``ValueError``）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union

from ..data.schema import Application, Candidate, Job


@dataclass(frozen=True)
class ExternalRecord:
    """One opaque row fetched from an external system.

    EN — Attributes: source (connector name, e.g. ``fake-ats``); kind (``candidate``/``job``/
        ``application``); raw (the external row with EXTERNAL field names — only the ACL reads it).
    中文 — 属性：source（连接器名，如 ``fake-ats``）；kind（``candidate``/``job``/``application``）；
        raw（带**外部**字段名的外部行——仅 ACL 读取）。
    """

    source: str
    kind: str
    raw: dict


class Connector(ABC):
    """A read-only source of external records.

    EN — Subclass sets ``name`` and implements ``fetch(kind)``. ``fetch`` is conceptually an outbound call
        (a real connector hits a network API); the §1.10 ``OutboundGuard`` gates whether it runs.
    中文 — 子类设置 ``name`` 并实现 ``fetch(kind)``。``fetch`` 概念上是出站调用（真实连接器访问网络 API）；§1.10
        ``OutboundGuard`` 决定其是否运行。
    """

    name: str = "connector"

    @abstractmethod
    def fetch(self, kind: str) -> list[ExternalRecord]:
        """Read-only pull of external records of ``kind``.

        EN — Args: kind. Returns: a list of ``ExternalRecord``. 中文 — 参数：kind。返回：``ExternalRecord`` 列表。
        """
        raise NotImplementedError


class AntiCorruptionLayer(ABC):
    """Translate external records into §1.8 canonical entities (the only translation point).

    EN — ``translate`` dispatches by ``rec.kind`` to a per-kind mapper the subclass implements; an unknown
        kind raises ``ValueError`` (fail closed).
    中文 — ``translate`` 按 ``rec.kind`` 分派到子类实现的按类映射器；未知 kind 抛 ``ValueError``（失败即关闭）。
    """

    def translate(self, rec: ExternalRecord) -> Union[Candidate, Job, Application]:
        """Map one external record to its canonical entity.

        EN — Args: rec. Returns: a §1.8 ``Candidate``/``Job``/``Application``. Raises: ValueError on an
            unknown ``kind``.
        中文 — 参数：rec。返回：§1.8 ``Candidate``/``Job``/``Application``。抛出：未知 ``kind`` 时抛 ValueError。
        """
        if rec.kind == "candidate":
            return self._to_candidate(rec.raw)
        if rec.kind == "job":
            return self._to_job(rec.raw)
        if rec.kind == "application":
            return self._to_application(rec.raw)
        raise ValueError(f"unknown external kind: {rec.kind}")

    @abstractmethod
    def _to_candidate(self, raw: dict) -> Candidate:
        """Map a raw external candidate row to a §1.8 ``Candidate``. 中文 — 把原始外部候选人行映射为 §1.8 ``Candidate``。"""
        raise NotImplementedError

    @abstractmethod
    def _to_job(self, raw: dict) -> Job:
        """Map a raw external job row to a §1.8 ``Job``. 中文 — 把原始外部职位行映射为 §1.8 ``Job``。"""
        raise NotImplementedError

    @abstractmethod
    def _to_application(self, raw: dict) -> Application:
        """Map a raw external application row to a §1.8 ``Application``. 中文 — 把原始外部申请行映射为 §1.8 ``Application``。"""
        raise NotImplementedError
