"""RBAC/ABAC policy engine — the single source the §1.5 memory-recall filter reuses (§1.9).

EN —
This is the security-baseline authority for "who may see / do what". It closes the gap §1.5 left open:
``governance/rbac.py`` already has the ``Principal`` type and ``scope_predicate`` (the no-leak recall
filter), but nothing *derived* a real principal — ``FULL_ACCESS`` was hard-coded. Here, ``principal_for``
turns a §1.8 ``User``/``Org`` into a scoped ``Principal`` (RBAC: role → permitted entity types; ABAC:
org/tenant isolation is structural because scopes are templated with the user's own tenant/org), and
``authorize`` answers an action-level access question (RBAC permission ∧ ABAC sensitivity ceiling ∧ the
key is in scope). Because the recall path already consumes a ``Principal`` + ``scope_predicate``, there
is exactly ONE place that derives access (here) and ONE place that applies it to a key (the shared
predicate) — no permission-model drift. Both fail CLOSED: an unknown role yields a deny-all principal,
and a denied ``authorize`` returns ``rejected:rbac`` (the audit vocabulary §1.8 already records).

中文 —
这是“谁可看/可做什么”的安全基线权威。它弥合 §1.5 留下的缺口：``governance/rbac.py`` 已有 ``Principal`` 类型与
``scope_predicate``（不泄漏的召回过滤器），但无人*派生*真实 principal——``FULL_ACCESS`` 是硬编码。此处
``principal_for`` 将 §1.8 ``User``/``Org`` 转为带范围的 ``Principal``（RBAC：角色 → 许可的实体类型；ABAC：因范围以
用户自身 tenant/org 模板化，故 org/tenant 隔离是结构性的），``authorize`` 回答动作级访问问题（RBAC 权限 ∧ ABAC 敏感度
上限 ∧ 键在范围内）。由于召回路径已消费 ``Principal`` + ``scope_predicate``，派生访问只有一处（此处）、对键施用只有一处
（共享谓词）——无权限模型漂移。二者均失败即关闭：未知角色得到拒绝一切的 principal，被拒的 ``authorize`` 返回
``rejected:rbac``（§1.8 已记录的审计词汇）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple

from ..data.schema import Org, User
from ..governance.rbac import FULL_ACCESS, Principal, scope_predicate  # noqa: F401  (FULL_ACCESS re-exported)


@dataclass(frozen=True)
class Role:
    """A role's RBAC permissions + the entity scope + the ABAC sensitivity ceiling.

    EN — Attributes: name; permissions (action verbs the role may perform); scope_entity_types (entity
        types the role may reach — combined with the user's tenant/org into namespace-key prefixes; an
        empty tuple with name in {system, admin} is handled specially); sensitivity_ceiling
        (``normal``|``sensitive`` — the highest sensitivity the role may touch).
    中文 — 属性：name；permissions（角色可执行的动作动词）；scope_entity_types（角色可触达的实体类型——与用户的
        tenant/org 组合成命名空间键前缀；name 属 {system, admin} 且为空元组时特殊处理）；sensitivity_ceiling
        （``normal``|``sensitive``——角色可触达的最高敏感度）。
    """

    name: str
    permissions: FrozenSet[str]
    scope_entity_types: Tuple[str, ...]
    sensitivity_ceiling: str


_ALL_ACTIONS = frozenset({"read", "write", "delete", "export", "configure"})

# Starter policy table — data, not code, so adding a role is config (firms up with the §5.4 console).
ROLE_POLICIES: Dict[str, Role] = {
    "system": Role("system", _ALL_ACTIONS, (), "sensitive"),
    "admin": Role("admin", _ALL_ACTIONS, (), "sensitive"),
    "recruiter": Role(
        "recruiter", frozenset({"read", "write", "export"}),
        ("candidate", "job", "application"), "normal",
    ),
    "interviewer": Role("interviewer", frozenset({"read"}), ("candidate",), "normal"),
}

_SENSITIVITY_RANK = {"normal": 0, "sensitive": 1}


@dataclass(frozen=True)
class ResourceRef:
    """A reference to the thing an action targets (for ``authorize``).

    EN — Attributes: type (entity type); org_id (the resource's owning org); memory_key (the namespace
        key the scope filter checks); sensitivity (``normal``|``sensitive``, default ``normal``).
    中文 — 属性：type（实体类型）；org_id（资源所属 org）；memory_key（范围过滤器检查的命名空间键）；
        sensitivity（``normal``|``sensitive``，默认 ``normal``）。
    """

    type: str
    org_id: str
    memory_key: str
    sensitivity: str = "normal"


@dataclass(frozen=True)
class Decision:
    """The outcome of an ``authorize`` check.

    EN — Attributes: allowed (bool); reason (``ok`` or ``rejected:rbac`` — matches the §1.8 audit
        ``result`` vocabulary, so a denial records directly).
    中文 — 属性：allowed（布尔）；reason（``ok`` 或 ``rejected:rbac``——与 §1.8 审计 ``result`` 词汇一致，故拒绝可
        直接记录）。
    """

    allowed: bool
    reason: str


def principal_for(user: User, org: Org) -> Principal:
    """Resolve a §1.8 ``User`` (+ its ``Org``) into a scoped ``Principal``.

    EN —
    Args: user (the §1.8 user — carries role + tenant/org); org (the user's org, reserved for future
        org-attribute ABAC). Returns: a ``Principal`` whose ``allowed_scopes`` are templated with the
        user's own tenant/org (so cross-org scopes are impossible to mint). ``system`` → full access;
        ``admin`` → the whole org; a known scoped role → ``tenant:org:<entity_type>`` per permitted type;
        an UNKNOWN role → a deny-all principal (empty scopes), never an exception.

    中文 —
    参数：user（§1.8 用户——携带角色 + tenant/org）；org（用户所属 org，保留给未来的 org 属性 ABAC）。返回：
        ``Principal``，其 ``allowed_scopes`` 以用户自身 tenant/org 模板化（故无法铸造跨 org 范围）。``system`` → 全权；
        ``admin`` → 整个 org；已知的受限角色 → 按许可类型生成 ``tenant:org:<entity_type>``；未知角色 → 拒绝一切的
        principal（空范围），绝不抛异常。
    """
    role = ROLE_POLICIES.get(user.role)
    if role is None:
        return Principal(user_id=user.user_id, role=user.role, allowed_scopes=())
    if role.name == "system":
        return Principal(user_id=user.user_id, role="system", allowed_scopes=("",))
    if role.name == "admin":
        return Principal(
            user_id=user.user_id, role="admin",
            allowed_scopes=(f"{user.tenant_id}:{user.org_id}",),
        )
    scopes = tuple(f"{user.tenant_id}:{user.org_id}:{et}" for et in role.scope_entity_types)
    return Principal(user_id=user.user_id, role=role.name, allowed_scopes=scopes)


def authorize(principal: Principal, action: str, resource: ResourceRef) -> Decision:
    """Decide whether ``principal`` may perform ``action`` on ``resource`` (RBAC ∧ ABAC, fail closed).

    EN —
    Args: principal (from ``principal_for``); action (a verb in the role's permission set); resource.
    Returns: ``Decision(True, "ok")`` only if the role grants the action AND the resource's sensitivity
    is within the role's ceiling AND the resource's ``memory_key`` is inside the principal's scopes;
    otherwise ``Decision(False, "rejected:rbac")``. Unknown role / missing permission / over-ceiling /
    out-of-scope all deny.

    中文 —
    参数：principal（来自 ``principal_for``）；action（角色权限集中的动词）；resource。返回：仅当角色授予该动作、
    且资源敏感度在角色上限内、且资源 ``memory_key`` 在 principal 范围内时返回 ``Decision(True, "ok")``；否则返回
    ``Decision(False, "rejected:rbac")``。未知角色 / 缺权限 / 超上限 / 越范围均拒绝。
    """
    role = ROLE_POLICIES.get(principal.role)
    if role is None:
        return Decision(False, "rejected:rbac")
    if action not in role.permissions:
        return Decision(False, "rejected:rbac")
    if _SENSITIVITY_RANK.get(resource.sensitivity, 1) > _SENSITIVITY_RANK.get(role.sensitivity_ceiling, 0):
        return Decision(False, "rejected:rbac")
    if not scope_predicate(principal)(resource.memory_key):
        return Decision(False, "rejected:rbac")
    return Decision(True, "ok")
