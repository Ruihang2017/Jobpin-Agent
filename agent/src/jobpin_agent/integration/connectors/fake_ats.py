"""FakeATSConnector + its anti-corruption layer (§1.10) — a synthetic read-only ATS for contract tests.

EN —
A network-free sample connector over fixtures, used to prove the §1.10 pipeline (external → anti-corruption
→ §1.8 canonical → local store) with no PII and no real ATS account. The fixture field names are
deliberately DIFFERENT from the canonical schema (``full_name``/``skill_tags``/``req_title`` …) so the
contract test proves the anti-corruption layer actually translates rather than passing fields through.

中文 —
基于固定数据、无网络的样例连接器，用于证明 §1.10 管线（外部 → 反腐层 → §1.8 规范 → 本地库），无 PII、无真实 ATS 账号。
固定数据的字段名刻意与规范 schema **不同**（``full_name``/``skill_tags``/``req_title`` 等），使契约测试证明反腐层确实在
翻译，而非字段透传。
"""
from __future__ import annotations

from ...data.schema import Application, Candidate, Job
from ..sdk import AntiCorruptionLayer, Connector, ExternalRecord

_FIXTURES = {
    "candidate": [
        {"ext_id": "A-1", "full_name": "Ada Lovelace", "skill_tags": ["Python", "Math"], "yrs": 7, "loc": "Sydney"},
        {"ext_id": "A-2", "full_name": "Grace Hopper", "skill_tags": ["COBOL", "Compilers"], "yrs": 12, "loc": "Remote"},
    ],
    "job": [
        {"ext_req": "R-9", "req_title": "Senior Engineer", "state": "open"},
    ],
}


class FakeATSConnector(Connector):
    """A read-only fake ATS over in-memory fixtures (no network).

    EN — Args (constructor): fixtures (override the default sample). ``fetch(kind)`` wraps each fixture row
        in an ``ExternalRecord``. 中文 — 参数（构造器）：fixtures（覆盖默认样例）。``fetch(kind)`` 把每行固定数据
        包装为 ``ExternalRecord``。
    """

    name = "fake-ats"

    def __init__(self, fixtures: dict | None = None) -> None:
        """Args: fixtures (defaults to the built-in sample). 中文 — 参数：fixtures（默认内置样例）。"""
        self._fixtures = fixtures if fixtures is not None else _FIXTURES

    def fetch(self, kind: str) -> list[ExternalRecord]:
        """Return the fixture rows of ``kind`` as ``ExternalRecord``s.

        EN — Args: kind. Returns: a list (empty if the kind has no fixtures).
        中文 — 参数：kind。返回：列表（该 kind 无固定数据则为空）。
        """
        return [ExternalRecord(source=self.name, kind=kind, raw=row) for row in self._fixtures.get(kind, [])]


class FakeATSAntiCorruption(AntiCorruptionLayer):
    """Map the fake ATS's external field names to §1.8 canonical fields.

    EN — The single place the fake ATS's schema is known; renaming a fixture field touches only here.
    中文 — 知晓伪 ATS schema 的唯一之处；改名固定字段只触及此处。
    """

    def _to_candidate(self, raw: dict) -> Candidate:
        """``full_name``→name, ``skill_tags``→skills, ``yrs``→years, ``loc``→location, ``ext_id``→candidate_id.

        中文 — ``full_name``→name，``skill_tags``→skills，``yrs``→years，``loc``→location，``ext_id``→candidate_id。
        """
        return Candidate(
            candidate_id=raw["ext_id"], name=raw.get("full_name", ""),
            skills=list(raw.get("skill_tags", [])), years=int(raw.get("yrs", 0)),
            location=raw.get("loc", ""),
        )

    def _to_job(self, raw: dict) -> Job:
        """``ext_req``→job_id, ``req_title``→title, ``state``→status. 中文 — ``ext_req``→job_id，``req_title``→title，``state``→status。"""
        return Job(job_id=raw["ext_req"], title=raw.get("req_title", ""), status=raw.get("state", "open"))

    def _to_application(self, raw: dict) -> Application:
        """``ext_app``→application_id, ``ext_cand``→candidate_id, ``ext_req``→job_id. 中文 — 见英文映射。"""
        return Application(application_id=raw["ext_app"], candidate_id=raw["ext_cand"], job_id=raw["ext_req"])
