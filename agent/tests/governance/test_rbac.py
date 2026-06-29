"""Tests for ``governance/rbac.py`` — Principal scope predicate (prefix match) + full access.

EN — A principal scoped to one org allows keys under it and denies others; ``FULL_ACCESS`` allows all.
中文 — 限定到某组织的 principal 允许其下键、拒绝其他；``FULL_ACCESS`` 允许全部。
"""
from jobpin_agent.governance.rbac import FULL_ACCESS, Principal, scope_predicate


def test_scope_predicate_prefix_match():
    """A principal scoped to acme:apac allows apac keys and denies emea keys.

    EN: prefix match. 中文：前缀匹配。
    """
    allow = scope_predicate(Principal("alice", "recruiter", ("acme:apac",)))
    assert allow("acme:apac:candidate:x")
    assert not allow("acme:emea:candidate:y")


def test_full_access_allows_all():
    """FULL_ACCESS (empty scope) allows any key.

    EN: allow all. 中文：允许全部。
    """
    allow = scope_predicate(FULL_ACCESS)
    assert allow("acme:emea:candidate:y") and allow("anything")
