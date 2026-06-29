"""Memory-recall RBAC — a Principal to a memory_key scope predicate (§1.5).

EN —
Least privilege over recall (APP 11): a request runs as a ``Principal`` whose ``allowed_scopes`` are
namespace-key prefixes; ``scope_predicate`` turns that into the ``memory_key`` predicate the retrieval
providers already accept as ``scope_filter`` and pass to ``VectorStore.search(scope=)`` — applied
BEFORE the top-k truncation, so an out-of-scope candidate's very existence never leaks. The auth source
(who the principal is, single-user desktop vs shared backend) is PRD open-question #8 and is deferred:
§1.5 builds the filter abstraction and injects the principal; ``FULL_ACCESS`` is the default so existing
demos/tests are unaffected. The §1.9 security-baseline RBAC/ABAC engine is the same source as this.

中文 —
对召回的最小权限（APP 11）：请求以 ``Principal`` 身份运行，其 ``allowed_scopes`` 为命名空间键前缀；``scope_predicate``
将其转为检索 provider 已接受为 ``scope_filter`` 并传给 ``VectorStore.search(scope=)`` 的 ``memory_key`` 谓词——在
top-k 截断**之前**应用，使范围外候选人的存在性绝不泄漏。鉴权来源（principal 是谁，单机 vs 共享后端）是 PRD 开放问题 #8，
推迟处理：§1.5 构建过滤抽象并注入 principal；``FULL_ACCESS`` 为默认，使既有演示/测试不受影响。§1.9 安全基线 RBAC/ABAC
引擎与此同源。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple


@dataclass(frozen=True)
class Principal:
    """The identity a recall request runs as.

    EN: Attributes: user_id; role; allowed_scopes (a tuple of namespace-key prefixes the principal may
        recall; ``""`` means everything).
    中文：属性：user_id；role；allowed_scopes（principal 可召回的命名空间键前缀元组；``""`` 表示全部）。
    """

    user_id: str
    role: str
    allowed_scopes: Tuple[str, ...]


# The default full-access principal (system / single-user MVP) — keeps existing demos and tests green.
FULL_ACCESS = Principal(user_id="system", role="system", allowed_scopes=("",))


def scope_predicate(principal: Principal) -> Callable[[str], bool]:
    """Build the ``memory_key`` predicate enforcing a principal's allowed scopes.

    EN —
    Args: principal. Returns: ``allow(memory_key) -> bool`` — True iff the key equals or is nested under
    one of the principal's allowed scope prefixes (an empty scope ``""`` allows everything).

    中文 —
    参数：principal。返回：``allow(memory_key) -> bool``——当且仅当键等于或嵌套于 principal 某个许可范围前缀之下时为
    True（空范围 ``""`` 允许全部）。
    """
    scopes = principal.allowed_scopes

    def allow(memory_key: str) -> bool:
        for scope in scopes:
            if scope == "" or memory_key == scope or memory_key.startswith(scope + ":"):
                return True
        return False

    return allow
