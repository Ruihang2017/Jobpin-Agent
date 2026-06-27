from pathlib import Path
from jobpin_agent.core.system_prompt import SystemPromptParts, build_system_prompt
from jobpin_agent.core.tools import echo_tool

GOLDEN = Path(__file__).parent / "data" / "system_prompt_golden.txt"


def _parts():
    return SystemPromptParts(
        org_policy="Be helpful.",
        compliance="Australia only.",
        role_permissions="recruiter",
        tools=[echo_tool()],
    )


def test_matches_golden_snapshot():
    assert build_system_prompt(_parts()) == GOLDEN.read_text(encoding="utf-8")


def test_is_byte_identical_across_100_builds():
    outputs = {build_system_prompt(_parts()) for _ in range(100)}
    assert len(outputs) == 1
