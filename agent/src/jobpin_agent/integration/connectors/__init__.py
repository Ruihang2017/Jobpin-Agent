"""Concrete connectors (§1.10).

EN — One module per external system. Phase 0 ships only ``fake_ats`` (a read-only, synthetic, network-free
sample); live real connectors (with OAuth) are deferred until credentials + the §1.11 de-id pipeline exist.

中文 — 每个外部系统一个模块。Phase 0 仅交付 ``fake_ats``（只读、合成、无网络的样例）；真实连接器（含 OAuth）推迟到
具备凭据 + §1.11 脱敏管线时。
"""
