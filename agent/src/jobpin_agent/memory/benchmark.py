"""Recall + P95 benchmark scaffold (§1.4) — data for the §1.15 / Phase 1 exit criteria.

EN —
A tiny harness to measure a retrieval provider's **recall@k** (does the expected ``memory_key`` show
up in the recall for each labelled query?) and **P95 latency** (so the §1.15 thin slice and Phase 1
can assert the PRD's recall-P95 target on real hardware/scale). It is deliberately minimal and
backend-agnostic — point it at the §1.4 stdlib store now, or the production backend after §1.12.

中文 —
一个小型测量框架，度量检索 provider 的 **recall@k**（每个带标注查询的召回中是否出现期望的 ``memory_key``）与
**P95 延迟**（使 §1.15 薄切片与 Phase 1 能在真实硬件/规模上断言 PRD 的召回-P95 目标）。它刻意最小且后端无关——现在
指向 §1.4 标准库存储，§1.12 后指向生产后端。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple


def run_recall_benchmark(provider, queries: List[Tuple[str, str]], *, k: int = 4) -> Dict[str, Any]:
    """Measure recall@k and P95 latency over labelled queries.

    EN —
    Args: provider (anything with ``prefetch(query)``); queries (``(query, expected_memory_key)``
    pairs); k. Returns: ``{"n", "recall_at_k", "p95_ms", "mean_ms"}``. ``recall_at_k`` is the share
    of queries whose expected key appears in the recall text.
    中文 —
    参数：provider（任何带 ``prefetch(query)`` 者）；queries（``(query, expected_memory_key)`` 对）；k。
    返回：``{"n", "recall_at_k", "p95_ms", "mean_ms"}``。``recall_at_k`` 为期望键出现在召回文本中的查询占比。
    """
    n = len(queries)
    if n == 0:
        return {"n": 0, "recall_at_k": 0.0, "p95_ms": 0.0, "mean_ms": 0.0}
    hits = 0
    latencies: List[float] = []
    for query, expected_key in queries:
        started = time.monotonic()
        recall = provider.prefetch(query)
        latencies.append((time.monotonic() - started) * 1000.0)
        if expected_key in recall:
            hits += 1
    latencies.sort()
    p95_index = min(n - 1, int(round(0.95 * (n - 1))))
    return {
        "n": n,
        "recall_at_k": hits / n,
        "p95_ms": round(latencies[p95_index], 3),
        "mean_ms": round(sum(latencies) / n, 3),
    }
