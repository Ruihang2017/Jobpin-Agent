"""Tests for ``governance/labels.py`` — header render/parse round-trip + the consent-required set.

EN — A rendered header parses back to its fields with the body intact; an unlabelled entry parses as
``(None, entry)``; the consent-required source types are correct. 中文 — 渲染的头可解析回其字段且正文完整；
未标注条目解析为 ``(None, entry)``；需要同意的来源类型正确。
"""
from jobpin_agent.governance.labels import (
    CONSENT_REQUIRED_SOURCE_TYPES,
    ConsentLabel,
    Provenance,
    parse_header,
    render_header,
    strip_governance_headers,
)
from jobpin_agent.memory.store import ENTRY_DELIMITER


def test_header_roundtrip():
    """A rendered header + body parses back to the labels and the original body.

    EN: round-trip. 中文：往返。
    """
    prov = Provenance("acme:apac:org:policy", "recruiter_input", "rubric#1",
                      "2026-06-30T00:00:00Z", "recruiter:alice")
    consent = ConsentLabel("legitimate_interest", "hiring_calibration")
    entry = render_header(prov, consent, "not_hired_180d") + "Backend roles weight reliability."
    labels, body = parse_header(entry)
    assert body == "Backend roles weight reliability."
    assert labels["key"] == "acme:apac:org:policy"
    assert labels["source_ref"] == "rubric#1"
    assert labels["legal_basis"] == "legitimate_interest"
    assert labels["retention_ttl"] == "not_hired_180d"


def test_parse_unlabelled_entry():
    """An entry with no header separator parses as unlabelled.

    EN: (None, entry). 中文：(None, entry)。
    """
    labels, body = parse_header("just a plain fact, no header")
    assert labels is None and body == "just a plain fact, no header"


def test_consent_required_set():
    """Candidate-sourced data requires consent; recruiter input does not.

    EN: the consent-required set. 中文：需要同意的集合。
    """
    assert "candidate_submitted" in CONSENT_REQUIRED_SOURCE_TYPES
    assert "recruiter_input" not in CONSENT_REQUIRED_SOURCE_TYPES


def test_strip_governance_headers_removes_headers_keeps_bodies():
    """strip_governance_headers removes every header block but keeps the bodies + render chrome.

    EN — two headered entries joined as a snapshot: headers gone, bodies + non-header text intact, and no
    governance metadata (consent_id/collected_by) leaks. 中文 — 两条带头条目作为快照连接：头消失、正文与非头文本完整、
    无治理元数据（consent_id/collected_by）泄漏。
    """
    e1 = (render_header(Provenance("acme:apac:org:policy", "recruiter_input", "rubric#1",
                                   collected_by="recruiter:alice"),
                        ConsentLabel("legitimate_interest"), "not_hired_180d") + "Weight reliability.")
    e2 = (render_header(Provenance("acme:apac:recruiter:prefs", "recruiter_input", "note#2",
                                   collected_by="recruiter:bob"),
                        ConsentLabel("legitimate_interest"), "not_hired_180d") + "Prefers concise updates.")
    snapshot = "ORG MEMORY [chrome]\n" + ENTRY_DELIMITER.join([e1, e2])
    stripped = strip_governance_headers(snapshot)
    assert "Weight reliability." in stripped and "Prefers concise updates." in stripped
    assert "ORG MEMORY [chrome]" in stripped     # render chrome preserved
    assert "key:" not in stripped and "collected_by:" not in stripped and "consent_id:" not in stripped
    assert "recruiter:alice" not in stripped     # actor identity does not leak to the model
