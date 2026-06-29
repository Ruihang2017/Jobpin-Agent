"""Tests for ``governance/namespace.py`` — key parse / format / validate / prefix.

EN — Pins the §1.0 key contract: round-trip parse/format, the three prefix levels, validation of part
count + entity type. 中文 — 锁定 §1.0 键契约：parse/format 往返、三个前缀级别、部分数 + 实体类型校验。
"""
import pytest

from jobpin_agent.governance.namespace import ENTITY_TYPES, MemoryKey, is_valid, parse


def test_parse_roundtrip():
    """parse() yields the four parts and format() reproduces the input.

    EN: a candidate key round-trips. 中文：候选人键可往返。
    """
    k = parse("acme:apac:candidate:cand_7f3a")
    assert (k.tenant, k.org, k.entity_type, k.entity_id) == ("acme", "apac", "candidate", "cand_7f3a")
    assert k.format() == "acme:apac:candidate:cand_7f3a"


def test_prefix_levels():
    """prefix() returns the tenant / org / entity_type spans.

    EN: three levels. 中文：三个级别。
    """
    k = parse("acme:apac:candidate:cand_7f3a")
    assert k.prefix("tenant") == "acme"
    assert k.prefix("org") == "acme:apac"
    assert k.prefix("entity_type") == "acme:apac:candidate"


def test_is_valid():
    """is_valid() accepts a well-formed key and rejects malformed / unknown-type keys.

    EN: validation + the entity-type set. 中文：校验 + 实体类型集合。
    """
    assert is_valid("acme:apac:org:policy")
    assert not is_valid("acme:apac:candidate")      # too few parts
    assert not is_valid("acme:apac:unicorn:x")      # unknown entity_type
    assert "candidate" in ENTITY_TYPES


def test_parse_rejects_malformed():
    """parse() raises ValueError on a key with the wrong part count.

    EN: malformed → ValueError. 中文：格式错误 → ValueError。
    """
    with pytest.raises(ValueError):
        parse("acme:apac:candidate")


def test_memory_key_is_hashable():
    """MemoryKey is frozen, so it can be used in a set / as a dict key.

    EN: frozen dataclass. 中文：frozen 数据类。
    """
    assert MemoryKey("acme", "apac", "org", "policy") in {MemoryKey("acme", "apac", "org", "policy")}
