"""Tests for ``governance/write_gate.py`` — reject missing provenance/consent/bias, accept labelled writes.

EN — Each rejection path returns the right code and records an audit row; a well-labelled write is
accepted and returns the governance header. 中文 — 每条拒绝路径返回正确码并记一条审计；标注良好的写入被接受并返回
治理头。
"""
from jobpin_agent.governance.audit import AuditLog
from jobpin_agent.governance.labels import ConsentLabel, Provenance
from jobpin_agent.governance.write_gate import GovernanceGate


def _gate() -> GovernanceGate:
    """Build a gate over a fresh in-memory audit log.

    EN: Returns: a GovernanceGate. 中文：返回：GovernanceGate。
    """
    return GovernanceGate(AuditLog())


def test_rejects_missing_provenance():
    """A write whose provenance has no source_ref is rejected and audited.

    EN: rejected:no_provenance. 中文：rejected:no_provenance。
    """
    gate = _gate()
    prov = Provenance("acme:apac:org:policy", "recruiter_input", source_ref="")
    decision = gate.validate("add", "acme:apac:org:policy", "weight reliability",
                             prov, ConsentLabel("legitimate_interest"), "not_hired_180d", actor="a")
    assert not decision.ok and decision.code == "rejected:no_provenance"
    assert gate.audit.query()[-1].result == "rejected:no_provenance"


def test_rejects_missing_consent_when_required():
    """A candidate-sourced write with no consent_id is rejected.

    EN: rejected:no_consent. 中文：rejected:no_consent。
    """
    gate = _gate()
    prov = Provenance("acme:apac:candidate:x", "candidate_submitted", source_ref="cv#1")
    decision = gate.validate("add", "acme:apac:candidate:x", "5y python",
                             prov, ConsentLabel("consent", consent_id=""), "not_hired_180d", actor="a")
    assert not decision.ok and decision.code == "rejected:no_consent"


def test_blocks_biased_content():
    """A write referencing a protected attribute is blocked.

    EN: rejected:bias. 中文：rejected:bias。
    """
    gate = _gate()
    prov = Provenance("acme:apac:org:policy", "recruiter_input", source_ref="rubric#1")
    decision = gate.validate("add", "acme:apac:org:policy", "Prefer candidates under 30 years old",
                             prov, ConsentLabel("legitimate_interest"), "not_hired_180d", actor="a")
    assert not decision.ok and decision.code == "rejected:bias"


def test_accepts_well_labelled_write_returns_header():
    """A fully-labelled, attribute-free write is accepted and returns the governance header.

    EN: ok + header. 中文：ok + 头。
    """
    gate = _gate()
    prov = Provenance("acme:apac:org:policy", "recruiter_input", source_ref="rubric#1",
                      collected_by="recruiter:alice")
    decision = gate.validate("add", "acme:apac:org:policy", "weight distributed-systems experience",
                             prov, ConsentLabel("legitimate_interest", "hiring_calibration"),
                             "not_hired_180d", actor="a")
    assert decision.ok and "key: acme:apac:org:policy" in decision.header


def test_remove_skips_content_checks():
    """A remove carries no new content, so it passes the gate without provenance/consent.

    EN: remove → ok. 中文：remove → ok。
    """
    gate = _gate()
    decision = gate.validate("remove", "acme:apac:org:policy", "",
                             Provenance("acme:apac:org:policy", ""), ConsentLabel("legitimate_interest"),
                             "not_hired_180d", actor="a")
    assert decision.ok
