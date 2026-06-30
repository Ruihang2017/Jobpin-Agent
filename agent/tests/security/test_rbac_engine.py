"""Tests for ``security/rbac.py`` — principal derivation + the unauthorised-access matrix.

EN — Proves org/tenant isolation is structural, and that ``authorize`` denies cross-org access, missing
permissions, and sensitivity-ceiling breaches (each with ``rejected:rbac``), while permitting in-scope
actions — the §1.9 "RBAC passes an unauthorised-access test" exit criterion.

中文 — 证明 org/tenant 隔离是结构性的，且 ``authorize`` 拒绝跨 org 访问、缺失权限与敏感度上限越界（各返回
``rejected:rbac``），同时放行范围内动作——即 §1.9 “RBAC 通过越权访问测试”退出标准。
"""
from jobpin_agent.data.schema import Org, User
from jobpin_agent.security.rbac import ResourceRef, authorize, principal_for


def _org(t="acme", o="apac"):
    """Build a test Org. 中文 — 构造测试用 Org。"""
    return Org(org_id=o, tenant_id=t, name="Acme APAC")


def _user(role, t="acme", o="apac"):
    """Build a test User with a role. 中文 — 构造带角色的测试用 User。"""
    return User(user_id="u1", tenant_id=t, org_id=o, role=role)


def test_recruiter_scoped_to_own_org():
    """A recruiter's scopes are templated with their own tenant/org only. 中文 — recruiter 范围仅以自身 tenant/org 模板化。"""
    p = principal_for(_user("recruiter"), _org())
    assert any(s.startswith("acme:apac") for s in p.allowed_scopes)
    assert not any("emea" in s for s in p.allowed_scopes)


def test_cross_org_read_denied():
    """A recruiter in org apac cannot read an emea candidate. 中文 — apac 的 recruiter 不能读 emea 候选人。"""
    p = principal_for(_user("recruiter"), _org())
    d = authorize(p, "read", ResourceRef(type="candidate", org_id="emea",
                                          memory_key="acme:emea:candidate:c9"))
    assert d.allowed is False and d.reason == "rejected:rbac"


def test_missing_permission_denied():
    """An interviewer (read-only) cannot export. 中文 — interviewer（只读）不能导出。"""
    p = principal_for(_user("interviewer"), _org())
    d = authorize(p, "export", ResourceRef(type="candidate", org_id="apac",
                                            memory_key="acme:apac:candidate:c1"))
    assert d.allowed is False and d.reason == "rejected:rbac"


def test_sensitivity_ceiling_denied():
    """A recruiter (normal ceiling) cannot read a sensitive record. 中文 — recruiter（normal 上限）不能读敏感记录。"""
    p = principal_for(_user("recruiter"), _org())
    d = authorize(p, "read", ResourceRef(type="candidate", org_id="apac",
                                          memory_key="acme:apac:candidate:c1", sensitivity="sensitive"))
    assert d.allowed is False and d.reason == "rejected:rbac"


def test_in_scope_allowed():
    """A recruiter may read an in-scope candidate. 中文 — recruiter 可读范围内候选人。"""
    p = principal_for(_user("recruiter"), _org())
    d = authorize(p, "read", ResourceRef(type="candidate", org_id="apac",
                                          memory_key="acme:apac:candidate:c1"))
    assert d.allowed is True and d.reason == "ok"


def test_admin_scoped_to_whole_org():
    """An admin's scope is the whole org, but not another org. 中文 — admin 范围为整个 org，但不含他 org。"""
    p = principal_for(_user("admin"), _org())
    d_in = authorize(p, "configure", ResourceRef(type="org", org_id="apac",
                                                  memory_key="acme:apac:org:policy"))
    d_out = authorize(p, "read", ResourceRef(type="candidate", org_id="emea",
                                             memory_key="acme:emea:candidate:c9"))
    assert d_in.allowed is True and d_out.allowed is False


def test_unknown_role_deny_all():
    """An unknown role yields a deny-all principal, no exception. 中文 — 未知角色得到拒绝一切的 principal，不抛异常。"""
    p = principal_for(_user("who"), _org())
    assert p.allowed_scopes == ()
    d = authorize(p, "read", ResourceRef(type="candidate", org_id="apac",
                                         memory_key="acme:apac:candidate:c1"))
    assert d.allowed is False and d.reason == "rejected:rbac"
