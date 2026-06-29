"""Context-window security (§1.6) — injection defence ported from Hermes (MIT).

EN —
The product's defence against prompt-injection / promptware / exfiltration in the context window.
Résumés, emails, and JDs are untrusted input and a real attack surface (prompt-injection via résumé),
so every piece of external text is scanned and fenced before it reaches the model's context or memory.
This package ports Hermes's mechanisms to local, owned code (PRD §2.7 — "port the code" for injection
defence): the threat-pattern library, the streaming fence scrubber, and a unified external-text door.

中文 —
产品对上下文窗口中提示注入 / promptware / 外泄的防御。简历、邮件与 JD 是不可信输入且为真实攻击面（经简历的提示注入），
故每段外部文本在进入模型上下文或记忆前都被扫描与围栏。本包把 Hermes 的机制移植为本地、自有代码（PRD §2.7——注入防御
“移植代码”）：威胁模式库、流式围栏清洗器，以及统一的外部文本入口。
"""
