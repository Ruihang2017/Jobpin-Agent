"""Tests for deterministic system-prompt assembly.

EN —
Locks Key Invariant #1: identical input yields byte-identical output, via a golden
snapshot and a 100x-stability check.
中文 —
锁定关键不变量 #1：相同输入产生逐字节一致的输出——通过黄金快照与 100 次稳定性检查。
"""
from pathlib import Path
from jobpin_agent.core.system_prompt import SystemPromptParts, build_system_prompt
from jobpin_agent.core.tools import echo_tool

GOLDEN = Path(__file__).parent / "data" / "system_prompt_golden.txt"


def _parts():
    """Build a fixed sample ``SystemPromptParts`` for the assertions.

    EN: A small, representative set of sections used by both tests.
    中文：两个测试共用的、有代表性的小型章节集合。
    """
    return SystemPromptParts(
        org_policy="Be helpful.",
        compliance="Australia only.",
        role_permissions="recruiter",
        tools=[echo_tool()],
    )


def test_matches_golden_snapshot():
    """Assembled output equals the committed golden file byte-for-byte.

    EN: Detects any accidental change to wording, order, or spacing.
    中文：检测对措辞、顺序或空白的任何意外改动。
    """
    assert build_system_prompt(_parts()) == GOLDEN.read_text(encoding="utf-8")


def test_is_byte_identical_across_100_builds():
    """Building 100 times yields a single unique output (determinism).

    EN: Proves the assembler has no order/randomness dependence.
    中文：证明装配器不依赖顺序/随机性。
    """
    outputs = {build_system_prompt(_parts()) for _ in range(100)}
    assert len(outputs) == 1
