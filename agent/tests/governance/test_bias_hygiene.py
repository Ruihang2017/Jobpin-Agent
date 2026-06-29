"""Tests for ``governance/bias_hygiene.py`` — reject protected attributes, flag proxies, pass clean text.

EN — A protected attribute → ``rejected:bias``; an elite-school hard threshold → flagged/blocked; clean
job-relevant text passes. 中文 — 受保护属性 → ``rejected:bias``；名校硬阈值 → 标记/阻断；干净的与岗位相关文本通过。
"""
from jobpin_agent.governance.bias_hygiene import scan


def test_protected_attribute_is_rejected():
    """An age reference is rejected as a protected attribute.

    EN: rejected:bias. 中文：rejected:bias。
    """
    finding = scan("Prefer candidates under 30 years old for this role.")
    assert finding is not None and finding.code == "rejected:bias"


def test_proxy_hard_threshold_is_flagged():
    """An elite-school hard threshold is flagged (a socio-economic proxy).

    EN: flagged/blocked. 中文：标记/阻断。
    """
    finding = scan("Must have graduated from a Group of Eight university to be considered.")
    assert finding is not None and finding.code in ("flagged:bias", "rejected:bias")


def test_clean_text_passes():
    """Job-relevant, attribute-free text passes the scan.

    EN: None. 中文：None。
    """
    assert scan("Strong distributed-systems and reliability experience; mentored engineers.") is None


def test_benign_words_embedding_a_token_do_not_false_positive():
    """Common HR words that merely embed a protected token must NOT trip the scanner (word boundaries).

    EN — regression for the substring-matching bug: "age" in management/manager/language/coverage,
    "race" in grace/embrace. These are exactly the words the gate must let through.
    中文 — 子串匹配缺陷的回归：management/manager/language/coverage 含 "age"，grace/embrace 含 "race"。这些正是门控
    必须放行的词。
    """
    benign = [
        "Weight strong people management experience.",
        "Looking for an experienced engineering manager.",
        "Comfortable building agent frameworks and tooling.",
        "Strong language skills and clear written communication.",
        "Broad test coverage and good leverage of automation.",
        "Able to show grace under pressure and embrace feedback.",
    ]
    for text in benign:
        assert scan(text) is None, f"false positive on: {text!r}"
