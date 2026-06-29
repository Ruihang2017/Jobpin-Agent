"""Test for the §1.4 end-to-end recall demo.

EN — proves résumé recall (with citation) reaches a real §1.1 Agent's model through the Composite,
offline, no loop change. 中文 — 证明简历召回（带引用）经 Composite 到达真实 §1.1 Agent 的模型，离线，不改循环。
"""
from examples.recall_demo import run_demo


def test_recall_reaches_model_with_citation():
    """The candidate recall + citation reach the model as a fenced memory-context.

    EN: recall_in_prompt, has_citation, fenced all True; the turn answers.
    中文：recall_in_prompt、has_citation、fenced 均为 True；回合作答。
    """
    out = run_demo()
    assert out["recall_in_prompt"] is True
    assert out["has_citation"] is True
    assert out["fenced"] is True
    assert out["answer"]
