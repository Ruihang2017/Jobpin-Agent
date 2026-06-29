"""Namespace keys — ``tenant:org:entity_type:entity_id`` parse / format / validate (§1.5).

EN —
The shared key format defined in Production Plan §1.0, used by §1.3 provider routing, §1.5 governance
(RBAC scoping + erasure prefix cascade), and §1.8 schema. A key isolates a memory entry to a tenant,
an organisation, an entity type, and a stable entity id. The MVP is single-tenant, so ``tenant`` /
``org`` use fixed placeholders, but the field abstraction is retained for §1.8 multi-tenancy.

中文 —
生产计划 §1.0 定义的共享键格式，供 §1.3 provider 路由、§1.5 治理（RBAC 范围限定 + 擦除前缀级联）与 §1.8 schema
使用。键把一条记忆隔离到租户、组织、实体类型与稳定实体 id。MVP 为单租户，故 ``tenant`` / ``org`` 使用固定占位符，
但保留字段抽象以备 §1.8 多租户。
"""
from __future__ import annotations

from dataclasses import dataclass

# The entity types a memory_key may name (Production Plan §1.0).
ENTITY_TYPES = frozenset({"candidate", "employee", "job", "org", "recruiter", "semantic"})
# Single-tenant MVP placeholders — the field abstraction is kept; values are fixed until §1.8.
DEFAULT_TENANT = "acme"
DEFAULT_ORG = "apac"
# How many key parts each prefix level spans (used by RBAC scoping + erasure cascades).
_LEVELS = {"tenant": 1, "org": 2, "entity_type": 3}


@dataclass(frozen=True)
class MemoryKey:
    """A parsed namespace key (``tenant:org:entity_type:entity_id``).

    EN —
    Attributes: tenant (top-level isolation boundary); org (organisation); entity_type (one of
    ``ENTITY_TYPES``); entity_id (the entity's stable primary key). Immutable (frozen) so it is safe to
    use as a dict key / in sets.

    中文 —
    属性：tenant（顶层隔离边界）；org（组织）；entity_type（``ENTITY_TYPES`` 之一）；entity_id（实体稳定主键）。
    不可变（frozen），可安全用作 dict 键 / 放入集合。
    """

    tenant: str
    org: str
    entity_type: str
    entity_id: str

    def format(self) -> str:
        """Render back to the canonical colon-joined string.

        EN: Returns: ``tenant:org:entity_type:entity_id``.
        中文：返回：``tenant:org:entity_type:entity_id``。
        """
        return f"{self.tenant}:{self.org}:{self.entity_type}:{self.entity_id}"

    def prefix(self, level: str) -> str:
        """Return the key prefix up to a level (for RBAC scoping / erasure cascade).

        EN: Args: level (``"tenant"`` / ``"org"`` / ``"entity_type"``). Returns: the colon-joined prefix.
        中文：参数：level（``"tenant"`` / ``"org"`` / ``"entity_type"``）。返回：以冒号连接的前缀。
        """
        parts = [self.tenant, self.org, self.entity_type, self.entity_id]
        return ":".join(parts[: _LEVELS[level]])


def parse(key: str) -> MemoryKey:
    """Parse a namespace key, validating its shape and entity type.

    EN —
    Args: key (a ``tenant:org:entity_type:entity_id`` string). Returns: the ``MemoryKey``.
    Raises: ValueError if the key does not have exactly four non-empty parts or names an unknown
    entity type.

    中文 —
    参数：key（``tenant:org:entity_type:entity_id`` 字符串）。返回：``MemoryKey``。
    抛出：若键不是恰好四个非空部分或命名了未知实体类型则 ValueError。
    """
    parts = key.split(":")
    if len(parts) != 4 or not all(parts):
        raise ValueError(f"malformed memory_key: {key!r} (want tenant:org:entity_type:entity_id)")
    if parts[2] not in ENTITY_TYPES:
        raise ValueError(f"unknown entity_type in {key!r}: {parts[2]!r}")
    return MemoryKey(*parts)


def is_valid(key: str) -> bool:
    """Whether ``key`` is a well-formed namespace key.

    EN: Args: key. Returns: True if ``parse`` would succeed, else False.
    中文：参数：key。返回：若 ``parse`` 会成功则 True，否则 False。
    """
    try:
        parse(key)
        return True
    except ValueError:
        return False
