"""Tests for ``governance/retention.py`` — policy registry, TTL sweep, backup-ageing register.

EN — The policies exist with correct TTLs; sweep returns only the expired keys; the register reports
pending backups until they age out. 中文 — 策略存在且 TTL 正确；sweep 仅返回到期键；注册表在备份老化前报告待处理。
"""
from jobpin_agent.governance.retention import RETENTION_POLICIES, BackupAgeingRegister, sweep


def test_policies_present():
    """The differentiated retention policies are registered with the expected TTLs.

    EN: registry. 中文：注册表。
    """
    assert "not_hired_180d" in RETENTION_POLICIES
    assert RETENTION_POLICIES["not_hired_180d"].ttl_days == 180
    assert RETENTION_POLICIES["hired_5y"].ttl_days == 365 * 5


def test_sweep_returns_expired():
    """sweep returns only the key whose TTL has elapsed.

    EN: 190-0 > 180 expired; 190-100 < 180 kept. 中文：190-0 > 180 过期；190-100 < 180 保留。
    """
    items = [("k_old", 0.0, "not_hired_180d"), ("k_new", 100.0, "not_hired_180d")]
    assert sweep(190.0, items) == ["k_old"]


def test_sweep_skips_unknown_policy():
    """An item with an unknown policy key is never auto-expired.

    EN: unknown policy → kept. 中文：未知策略 → 保留。
    """
    assert sweep(10_000.0, [("k", 0.0, "no_such_policy")]) == []


def test_backup_register_ages_out():
    """A registered backup is pending until its ages-out day passes.

    EN: pending then gone. 中文：先待处理后消失。
    """
    reg = BackupAgeingRegister()
    reg.register("acme:apac:candidate:x", erased_at_days=10.0, ages_out_at_days=190.0)
    assert reg.pending(50.0) == ["acme:apac:candidate:x"]
    assert reg.pending(200.0) == []
