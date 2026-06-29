# Jobpin Agent — AI-Agent-Driven HR Platform
## Product Requirements Document (PRD)

> **Jobpin Agent**. A **local-first** AI-native human-resources platform, rebuilt on top of the Hermes Agent kernel and **memory system**, targeting the **Australian market** (internal pilot first, commercial later).
>
> Covers the five major modules across the full employee lifecycle: **Resume Matching, Talent Search, Recruitment, Training, and Supervision & KPI/Attendance**.
>
> **Compliance scope statement**: This system **runs a pilot in Australia only**, so this document **considers only Australian laws and regulations** (federal + relevant states/territories). Any expansion beyond Australia (including the cross-border parts after commercial launch) requires separate assessment of the target jurisdiction's compliance and is currently out of scope. This document's descriptions of the law are product-design inputs and **do not constitute legal advice**; they must ultimately be confirmed by Australian legal counsel.
>
> **Narrative perspective**: This document is written in a third-person neutral voice, consistently referring to the subject as "this product / Jobpin Agent / the system".

---

## 0. Document Control

| Item | Content |
|---|---|
| Document version | v0.3 (Draft; adds architecture selection and kernel comparison, in-depth treatment of the memory system; converged onto Australia + local-first) |
| Status | Approved baseline; implementation plan derived (`02-Production-Plan`); Phase 0 in progress (2026-06) — Agent Core §1.1 + Memory Subsystem §1.2–1.4 + HR memory governance §1.5 built (§1.2 merged to `main`; the rest stacked) |
| Author | Product owner (TBD) |
| Date | 2026-06-24 |
| Related documents | `02-Production-Plan.md` (industrial-grade delivery roadmap) |
| Decision premises | **Single-market Australian pilot**; **local-first deployment** (agent runtime/memory/data run on the customer's premises by default); internal first, then commercial; built from scratch with the Hermes memory architecture ported in; all five modules required |
| Reviewers | Product / Engineering / Legal & Compliance (Australia) / Security / HR business owner |

**Glossary (excerpt)**

| Term | Meaning |
|---|---|
| Agent Core | The agent runtime kernel ported from Hermes (tool-calling loop, sub-agent delegation, context compression, memory mounting) |
| Memory Subsystem | The memory system ported and extended from Hermes (`memory_tool.py` / `memory_provider.py` / `memory_manager.py`) |
| local-first | Local-first: the agent runtime, memory and HR data run and are stored by default on the customer's local devices / on-premises deployment environment, without depending on our cloud |
| Entity Memory | Long-term structured + semantic memory organised around candidates/employees/jobs/organisations |
| HITL | Human-in-the-loop (critical decisions must be reviewed by a human) |
| MCP | Model Context Protocol, the de facto standard protocol for tool/context integration |
| APP | Australian Privacy Principles (13 in total, Schedule 1 of the Privacy Act 1988) |
| ADM | Automated Decision-Making (Privacy Act APP 1 transparency obligation, effective 2026-12-10) |
| PIA | Privacy Impact Assessment (a systematic assessment of high-privacy-risk projects; OAIC-recommended / mandatory for government agencies) |
| OAIC / AHRC | Office of the Australian Information Commissioner (privacy regulator) / Australian Human Rights Commission (anti-discrimination) |
| Embedded vector store | A vector store that runs locally alongside the application (e.g. sqlite-vec / LanceDB / Chroma local mode), requiring no cloud database |

---

## 1. Executive Summary

**Vision**: Upgrade HR from "process operator" to "decision commander". Jobpin Agent is a **local-first** HR platform built around **Agent + long-term memory** at its core — not merely a Q&A bot, but an agent system that can **remember** the organisation's hiring standards, candidate history and employee growth trajectories across sessions and across entities, and that, under human supervision, automatically executes multi-step workflows (sourcing, screening, scheduling, training, tracking).

**Differentiation (relative to traditional HR SaaS / general-purpose Copilots)**:
1. **Memory = a sustainable moat (an honest framing)**: The memory **engine** itself is open source (Hermes, MIT; competitors can take it too) — it is a foundational capability, not the moat. The truly sustainable moat is the superposition of three things: ① the switching cost created by **per-customer, long-accumulated organisational memory** (note: local-first = single-tenant, **no cross-customer data flywheel**; this is per-customer lock-in, not market-level network effects); ② **built-in, legally-vetted Australian compliance content**; ③ **full-lifecycle workflow depth**. The mechanism and cold start are detailed in Section 9.4.
2. **Agent-native**: Not treating the LLM as a search box, but handing each HR sub-task to delegable, observable, auditable sub-agents (sourcing / screening / scheduling / training / KPI agent).
3. **Local-first, privacy-first**: In the commercial MVP, the agent runtime, memory and HR data run/are stored on the **customer's premises** by default, and candidate/employee data **does not leave the customer's machine** by default. This is both a strong privacy selling point (HR data is highly sensitive) and a natural way to satisfy Australian data residency and avoid APP 8 cross-border disclosure issues. Hermes was designed for file-based local memory in the first place, which fits this naturally.
4. **Embedded professional HR and compliance ("HR-in-a-box")**: Many SMBs/startups **cannot afford a dedicated HR function and are unfamiliar with professional recruitment processes and compliance**. This product makes "professional HR processes + Australian compliance guardrails" into **built-in organisational/procedural memory**, guiding non-expert users in plain language to complete HR work **safely, compliantly and with a low barrier to entry** — this is the sharpest core pain point and the primary marketing direction (design requirements in Section 11.8).

**Target customers (one engine, two customer types)**: ① enterprises that **already have an HR team** → enhance efficiency and consistency; ② SMBs/startups with **no dedicated HR** → the system **acts as their HR function**. The latter has the sharpest pain point and strong willingness to pay, and is the primary commercial direction.

**Commercial path**: First as an internal enterprise tool (local / on-premises) to refine real-world scenarios and ROI, then productised into a **local-first self-service product for "HR-less" SMBs** for commercial launch (Australian market first). An optional cloud/managed multi-tenant form is a later extension for customers who need it (not the default form).

**MVP one-sentence definition**: A **local, single-tenant, strong-HITL application of M1+M2+M3** (three sub-agents Sourcing/Screening/Scheduling + a self-built lightweight state machine); **M4 Training and M5 Supervision & Attendance come after the MVP** (see the phased delivery plan). "All five modules required" in this document refers to the **final scope**, not the MVP scope.

---

## 2. Agent Vision & Architecture Rationale

> This chapter answers: **What kind of agent are we building? Why borrow the Hermes architecture? Why not directly use Claude Code's architecture? Which existing frameworks (e.g. LangChain) do we use / not use? And how do we "own" the backbone (port vs rewrite)?** The conclusions are grounded in current (2025–2026) agent technology and application development, and will be re-validated through technical spikes in Phase 0 of the delivery plan.

### 2.1 This Product's Agent Positioning

Jobpin Agent is not "a chatbot with HR knowledge", but a **stateful, long-horizon, memory-driven, auditable multi-agent system**, operating in the paradigm of **perceive → plan → act → remember (under human supervision)**:

| Dimension | Traditional Chatbot / RAG Q&A | Jobpin Agent agent system |
|---|---|---|
| State | Stateless, single-turn Q&A | **Stateful, long-horizon** (a single hiring loop advances continuously across days/people) |
| Memory | Only the current context window | **Long-term memory across sessions and entities** (candidate/employee/organisation/recruiter) |
| Action | Only generates text | **Calls tools** (query the ATS, parse resumes, schedule interviews, write memory), multi-step orchestration |
| Structure | Single model | **Orchestrator + dedicated sub-agents** (sourcing/screening/scheduling/training/KPI) |
| Decision | Black box, one-shot result | **Human-in-the-loop + explainable + grounded citations**, every step traceable |
| Domain | General-purpose | **HR domain specialisation** on top of a general-purpose Agent kernel |

In one sentence: **On top of a general-purpose Agent kernel that can be fully owned, audited and governed, layer "organisational memory" as a moat, and build a specialised multi-agent system for the full HR lifecycle.**

### 2.2 The Current Development Context of Agents (2025–2026)

The technology has evolved from **"chain-based / RAG Q&A"** toward **"autonomous agents"**, and further toward **"stateful, memory-layered, protocol-interconnected, observable and governable multi-agent systems"**. The key judgements for this project:

- **Memory is becoming an independent architectural layer.** The rise of "memory middleware" such as Mem0 / Zep / Letta / Honcho shows that long-term memory is no longer an ancillary feature of some framework, but a layer worth designing and governing on its own. Hermes happens to have made memory a pluggable subsystem with lifecycle and security governance — aligned with the industry direction, and exactly where an HR product's value lies.
- **Protocols are being standardised.** **MCP** is becoming the de facto standard for "tool/context integration"; **A2A** is used for agent-to-agent communication. A new system should design its integration layer toward MCP, avoiding writing proprietary glue for every integration.
- **Frameworks carry an abstraction cost.** Production practice (and the guidance in Anthropic's *Building Effective Agents*) repeatedly shows that one should **prefer simple, composable, transparent patterns**, introducing heavy frameworks only where there is a clear benefit. In a **regulated, incrementally-auditable** HR domain, a framework that "hides the agent loop inside a black-box abstraction" is a burden rather than a help.
- **Production-grade agents = control + observability + evaluation + human-in-the-loop.** Checkpointing, tracing, eval gates and HITL interrupt points are key to turning a demo into a deployable system.

**This project's bet**: In a high-risk, heavily-regulated, high-trust and **local-first** scenario such as HR, **memory + governance + control** is what constitutes sustainable value and a moat — the architecture choice should maximise these three, rather than build a multi-agent demo as fast as possible.

### 2.3 Why Borrow the Hermes Architecture

> **What Hermes is**: an open-source agent runtime/CLI (released by Nous Research, **MIT-licensed**), notable for its **pluggable, file-based memory subsystem with lifecycle and security governance**. This product borrows/ports its kernel and memory code, rather than using it as an end-user tool.

- **It got the hardest parts right, and as ownable, transparent code**: the memory subsystem (pluggable Provider, prefetch/sync lifecycle, injection defence, context compression), sub-agent delegation, a provider-agnostic model layer, clean module boundaries. These "foundations" are extremely expensive to build from scratch, especially **memory governance**.
- **Memory is the moat**, and Hermes's memory architecture is its most mature part (see Section 9). Directly porting it gives this product a **head start** on its differentiating asset.
- **File-based local memory**: Hermes's built-in memory is local files (atomic writes, file locks, drift detection), which **fits this product's "local-first" goal naturally** — no need to introduce a cloud database for the MVP.
- **Provider-agnostic (multi-model)**: natively supports **local models** or switchable model backends, with no lock-in to a single vendor.
- **Owning the entire backbone**: in a regulated domain, this achieves **full auditability**, no framework lock-in, and freedom to adapt it however HR needs require.

### 2.4 Why Not Directly Adopt the Claude Code (Claude Agent SDK) Architecture

> Clarification: **"Not using the Claude Code architecture" ≠ "not using Claude models".** This product can still use Claude as its primary model and borrow several of Claude Code's excellent patterns (file-based memory "frozen snapshot", MCP, sub-agents, hooks).

The Claude Code architecture is now offered in the form of the **Claude Agent SDK**, a production-grade, highly mature framework (the industry often ranks it second in production-readiness, and it is exactly the foundation of Claude Code). But it **should not serve as this product's backbone**:

1. **Tight coupling to Anthropic / Claude**: it is Claude-centric, which conflicts with "switchable models + **local models** + avoiding single-vendor lock-in".
2. **Its lineage is a "coding/terminal harness"**: optimised for software-engineering tasks (file editing, bash, code search, CLI interaction), whereas this product needs a **multi-role portal + local/on-premises backend + large-scale per-entity memory + HR domain workflows** — a different product form.
3. **Building the product on someone else's runtime** binds the release cadence, operations and auditability to that harness's constraints and upgrade cycle; a regulated, long-lifecycle product needs to "own the backbone" all the more.

**Conclusion**: borrow its patterns and models, but **do not make it the backbone**; use an ownable Hermes-derived kernel as the backbone.

### 2.5 Trade-offs Among Existing Agent Frameworks (What to Use / Not Use / Why)

Overall principle: **Own the backbone (Hermes-derived kernel + memory) → standardise the protocol (MCP) → introduce specialised libraries at the edges as needed (RAG / orchestration / observability / evaluation) → reject monolithic frameworks that "obscure the agent loop".** All trade-offs are validated with spikes in Phase 0.

> The horizontal comparison below reflects the **public benchmarks/community state of play as of 2025–26** (which will evolve with versions); the actual trade-offs are determined by Phase 0 spike measurements and are not treated as foregone conclusions.

| Framework/option | Strengths | Trade-off and rationale |
|---|---|---|
| **LangGraph** | Highest production-readiness: explicit state graph, checkpointing/time travel, HITL interrupt points, observability, model-agnostic | **Selected at the edge (candidate)**: used only where there is a genuine "persistent, auditable state machine with human checkpoints" (e.g. the M3 recruitment process). **Not the backbone** |
| **LangChain (classic)** | Broadest ecosystem/integrations, fast to get started | **Not the backbone**: notorious for "leaky abstractions / frequent changes / over-abstraction", which weakens the debuggability and transparency that a regulated system requires |
| **CrewAI** | Role-based multi-agent, fastest to get started | **Not selected**: weak control, heaviest token overhead (about 3× others on simple tasks), rather opinionated |
| **AutoGen / AG2** | Friendly for multi-agent conversation research | **Not selected as the backbone**: went through Microsoft's v0.4 rewrite and the community AG2 fork, with an unstable ecosystem |
| **LlamaIndex** | Strong RAG/data indexing and retrieval | **Selected at the edge**: used as a RAG component, not the overall runtime |
| **Semantic Kernel** | .NET ecosystem | **Not selected**: mismatched with the Python stack |
| **Claude Agent SDK** | Anthropic-native, production-ready | **Borrowed but not the main backbone** (rationale in Section 2.4) |
| **MCP (protocol)** | De facto standard for tool/context integration | **Adopted**: the integration layer (ATS/HRIS/calendar/email) is exposed as MCP tools |
| **Observability/evaluation** (Langfuse / OTel GenAI / promptfoo) | Tracing, eval gates | **Adopted**: a regulated domain must have step-level tracing and eval gates; prefer locally-deployable options |

### 2.6 Layered Architecture

Break the "agent system" into clear layers, **selecting technology for each layer independently** — conflating these layers is precisely the source of the "should we use a framework" confusion:

| Layer | What it solves | Selection | Rationale |
|---|---|---|---|
| **A. Agent runtime + memory** | "Think — call tools — remember" within a single task (e.g. "screen these 50 resumes") | **Hermes-derived kernel** (owned) | Memory is the moat; must be auditable, must be owned, local-first |
| **B. Long-running orchestration** | Cross-day, cross-person, pausable/resumable business processes (the whole hiring loop) | **Self-built lightweight state machine → upgrade to Temporal/LangGraph when complex** | Hermes's conversation loop is not a business-process engine; this is the gap |
| **C. Integration** | Connecting to ATS/calendar/email | **MCP + a few hand-written connectors** | Only a handful needed, with strong control; LangChain's hundreds of connectors are unnecessary |
| **D. RAG / retrieval** | Retrieval over resumes/JDs/knowledge base | **LlamaIndex or a direct vector store + embedded local vector store** | A specialised library suffices; local-first favours embedded |
| **E. Observability / evaluation** | Tracing, eval gates | **Langfuse / OTel / promptfoo** | Essential for a regulated domain; prefer locally-deployable |

> **Key distinction (Layer A vs Layer B)**: The Hermes kernel solves "a single agent inference + memory" (Layer A); the recruitment process, however, is a **cross-day, multi-party, resumable business process** (Layer B) that requires state-machine/orchestration capabilities. The two are **complementary layers**, not competing ones — Layer B introduces orchestration components as needed, without touching Layer A's "own the backbone" principle.

### 2.7 Kernel Build Strategy: Port vs Rewrite (Build Strategy)

**Licensing conclusion**: Hermes uses the **MIT licence** (Copyright 2025 Nous Research). MIT allows free use, modification, redistribution and sale within a closed-source commercial product, with the sole obligation to retain the MIT copyright and licence notice in **substantial portions that are copied**. **Therefore "porting the code" is legally clean** (no obstacle to commercial use).

**Decision yardstick**:

> **Should port (lift the code)**: high value + clear boundary + hard to build from scratch + security-critical.
> **Should rewrite (borrow the design)**: generic components + tightly coupled with Hermes's own product + need a clean service form and ownership.

| Hermes component | Strategy | Rationale |
|---|---|---|
| **Memory subsystem** (`memory_tool.py` / `memory_provider.py` / `memory_manager.py`) | **Port the code** (lift + adapt) | The moat, clean boundary, most expensive to build from scratch — MIT allows taking it directly |
| **Injection defence / guardrails** (`threat_patterns.py`, `StreamingContextScrubber`) | **Port the code** | Security-critical, easy to get wrong, already refined |
| **Agent loop / runtime** (`conversation_loop.py`, etc.) | **Borrow the design, rewrite a trimmed-down version** | The loop concept is simple; Hermes's version is tightly coupled with its CLI/gateway; need local-first, clean ownership |
| **gateway / CLI / TUI / multi-provider pipeline** | **Do not take; build as needed** | These belong to its "product" part, not the backend this product needs |

**Engineering/legal hygiene (when porting code)**: ① retain the MIT copyright and licence notice (place in a `NOTICE`/`THIRD_PARTY` file); ② ported code **must undergo its own security review** (MIT is "as is" with no warranty; a regulated product must not blindly trust it); ③ also verify the respective licences of the **transitive dependencies** of the ported modules.

> **ADR summary**: Self-built backbone = **Hermes-derived Agent kernel + memory subsystem**; models = **local-first, provider-agnostic, optional Claude**; integration = **MCP**; orchestration (Layer B) introduce **Temporal/LangGraph** where genuinely needed; RAG uses **LlamaIndex/embedded vector store**; observability uses **Langfuse/OTel**. **Do not** use CrewAI/AutoGen as the backbone; **do not** build the product on the Claude Code/Agent SDK runtime.
> **To be validated (Phase 0 spike)**: the effort and boundary of porting the Hermes kernel; local-model availability/quality/hardware requirements; the scale ceiling of the embedded vector store; whether M3 needs Temporal/LangGraph.

---

## 3. Background & Problem Statement

| Module | Current pain points | Jobpin Agent's entry point |
|---|---|---|
| Resume matching | Poor keyword-matching recall, misses paraphrased capabilities, cannot explain "why it matches", recruiters drowning in masses of resumes | Hybrid semantic + structured matching + explainable scoring + organisational calibration |
| Talent search | Fragmented across channels (LinkedIn/internal database/historical candidates), passively waiting for applications, high barrier to Boolean search | Natural language → multi-source sourcing agent, proactively recalling dormant candidates, remembering "who was contacted, why rejected" |
| Recruitment | The process is fragmented across ATS/email/calendar/IM, interview scheduling is time-consuming, feedback is hard to converge, poor candidate experience | End-to-end process-orchestration agent + structured interview feedback + calibration-meeting support |
| Training | Training disconnected from role competencies, one-size-fits-all, forgotten as soon as learned, unable to track capability growth | Personalised learning paths based on a competency map + continuous enablement driven by employee memory |
| Supervision & KPI/Attendance | Goal–performance–attendance data silos, subjective bias, high compliance and privacy risk, "surveillance" harms trust | Goal alignment and KPI insights (**assistive, not automated punishment**) + strong human supervision + transparent and appealable |

**Root pain point**: HR systems do not lack data; what they lack is **memory and context across time** and **agents that can execute multi-step work**. This is exactly where the value of the Hermes memory architecture lies.

**An overlooked but sharpest segment — "companies with no HR"**: Many SMBs/startups **cannot afford a dedicated HR function**; the founders/operators are unfamiliar with professional recruitment processes and do not understand Australian employment compliance (APPs, anti-discrimination, Fair Work, workplace surveillance), yet still have to hire, manage and run performance. For them, market tools either assume "an HR expert already exists" or are merely task automation. **Jobpin Agent builds the professional processes and compliance guardrails into the product itself**, enabling non-HR people to do HR right — this is the product's strongest value proposition and marketing entry point (design requirements in Section 11.8).

**Why not existing solutions (alternatives analysis)**
- **General-purpose LLM / ChatGPT**: no organisational memory, no process orchestration, no compliance guardrails, and sends PII to the cloud — cannot remember the company's standards and does not solve compliance and privacy.
- **Traditional ATS/HRIS (Greenhouse/Workday, etc.)**: a system of record, not an agent; the process still relies on humans; SMBs mostly do not have one and cannot afford one.
- **Point AI-HR tools**: mostly single-point features (e.g. resume screening), lacking unified memory and full-lifecycle orchestration, rarely doing local-first + Australian compliance.
- **Jobpin Agent's position**: local-first + organisational-memory moat + a full-lifecycle agent with embedded expertise and compliance — particularly filling the gap for "HR-less" SMBs.

---

## 4. Goals & Non-Goals

### 4.1 Goals (Measurable)
> **Note**: The quantified goals below are **hypotheses to be validated in the pilot (not commitments)**; a human baseline must first be measured for comparison, and final thresholds will be set against the baseline in Phase 1.
- **G1**: The MVP (front-end of recruitment) shortens the "JD → quality candidate shortlist" cycle for a single job by ≥ 50%.
- **G2**: Resume-matching Top-10 hit rate (the share recruiters approve) ≥ human baseline, with 100% explainable scoring provided.
- **G3**: Every decision recommendation that affects an individual has a **HITL review entry point + an explainable rationale + an audit record** (a hard compliance metric; preparing for the Privacy Act ADM transparency obligation).
- **G4**: Bias audit (technical metrics such as adverse-impact ratio + indirect-discrimination risk review) meets the bar in every released module, producing a disclosable audit report (best practice, aligned with Australian anti-discrimination law and voluntary AI guidance).
- **G5**: At a scale of ~100,000 candidates / ~10,000 employees, the memory system recalls relevant context at P95 < 800 ms (on local hardware), and supports data-subject-level erasure (APP 11.2 destruction/de-identification, APP 13 correction).
- **G6 ("HR-less" segment)**: Enable users with no HR background to complete compliant recruitment/onboarding/performance processes under the system's guidance — key actions have compliance guardrails + plain-language explanations + safe defaults, and high-risk actions are automatically flagged and can be escalated to a professional in one click. Goal: compliance-check pass rate for core HR processes ≥ a set threshold, with a marked reduction in the omission rate of key steps.
- **G7 (local-first)**: In the commercial MVP, the agent runtime, memory and HR data run/are stored on the customer's premises by default; candidate/employee PII does not leave the customer's machine by default (supports a "fully local" mode).

### 4.2 Non-Goals (YAGNI, explicitly not doing)
- **N1**: The MVP does not make fully-automated reject/hire/fire decisions (always HITL; the supervision module does no automated punishment).
- **N2**: The MVP does not do cloud multi-tenancy/billing/self-service signup (keep a clean org abstraction, as an optional Phase 4 follow-up).
- **N3**: Do not build a core ATS/HRIS system; instead **integrate** (Workday / SuccessFactors / Greenhouse / BambooHR, etc.).
- **N4**: Do not do intrusive monitoring such as facial recognition / emotion recognition / keylogging (a compliance and ethics red line, directly excluded).
- **N5**: Do not replace legal judgement — all compliance designs require final confirmation by Australian legal counsel; what is embedded are guardrails and guidance, not a substitute for legal advice.
- **N6**: The pilot is limited to Australia; compliance in jurisdictions outside Australia is not handled in this phase.

---

## 5. Users & Personas

> Personas are split into two categories: **primary** (driving MVP design) and **secondary / scale-up phase**. **Key note**: In the "HR-less" SMB segment, most of the roles below are **merged into a single person (Dana)** — this is also the basis for the MVP's guided design (see Section 11.8).

**Primary personas (the MVP must serve well)**

| Persona | Role | Core needs | Key interactions |
|---|---|---|---|
| **Dana (founder/operations lead, no dedicated HR)** | Primary user ("HR-less" segment) | Does not understand HR processes and compliance, yet must hire/manage compliantly; needs hand-holding guidance, safe defaults, and prompts to find an expert when necessary | All modules (guided), compliance guardrails, template library |
| **Riya (recruiter)** | Primary user (has-HR segment) | Quickly produce a high-quality shortlist with less mechanical work | Resume matching, talent search, process orchestration |
| **Marco (hiring manager)** | Decision-maker | See explainable candidate comparisons, calibrate standards | Candidate evaluation, interview feedback, calibration |
| **Candidate** | External stakeholder | Be respected, informed, able to appeal | Notifications, privacy portal, status enquiry |
| **Employee** | Person being served | Growth, transparency, fair treatment | Training, goals, self-service enquiry |

**Secondary personas (scale-up / has-an-HR-team phase; in the "HR-less" segment merged into Dana)**

| Persona | Role | Concerns |
|---|---|---|
| HRBP / L&D lead / team supervisor | Business partner / training / supervision | Dashboards and insights, competency maps, goal alignment (not surveillance) |
| Admin / IT | Administration | Installation/deployment, SSO, permissions, backup, observability |
| Privacy Officer / compliance officer | Governance | Compliance, audit, PIA, bias audit, handling APP 12/13 requests |

---

## 6. Success Metrics / KPIs

**North Star (by segment)**: ① the has-HR / high-volume scenario — the number of "quality candidates accepted into interviews by the hiring manager" produced per user per week; ② **the "HR-less" SMB (the primary segment) — the proportion and time taken to complete one compliant recruitment/onboarding end-to-end without needing to escalate to an external expert** (a high-volume throughput metric does not apply to a Dana who hires only a few times a year).

| Dimension | Metric | Target |
|---|---|---|
| Efficiency | Time-to-shortlist, number of manual steps | ↓ (magnitude set after the baseline is measured; initial assumption ~50%, not a commitment) |
| Quality | Shortlist→interview conversion rate, interview→offer conversion rate | ≥ human baseline |
| Trust | Recommendation adoption rate, coverage/override rate | Monitor (too high = untrustworthy, too low = rubber stamp) |
| Fairness | Adverse-impact ratio (**a non-binding technical diagnostic metric, derived from the US 4/5 rule, not an Australian statutory threshold**) + indirect-discrimination risk review | Monitor continuously; the legal judgement is based on "indirect discrimination" under Australian anti-discrimination law + legal review, not on the ratio passing/failing |
| Compliance | HITL coverage, audit-completeness rate, APP 12/13 request response timeliness | 100% / 100% / within the statutory or agreed deadline |
| System | Recall P95, availability, LLM unit cost | See the NFRs in Section 12 |
| Training | Learning-path completion rate, capability growth (pre/post test), correlation with on-the-job performance | Positive |
| HR-less segment | Compliance-check pass rate for non-expert users, omission rate of key steps | Meets bar / markedly reduced |

> **Guardrail metrics**: override rate, appeal rate, bias-metric drift, hallucination/ungrounded-citation rate, number of PII leakage incidents — any deterioration blocks release.

---

## 7. Scope: Platform Model

Jobpin Agent is not five independent products, but a **"shared Agent kernel + shared memory system + shared data/integration/compliance foundation + five business modules"**, **deployed local-first by default**:

```
══════════════ Customer local device / on-premises (local-first) ══════════════
┌─────────────────────────────────────────────────────────────┐
│ Experience layer  Local app (desktop/local web): Owner /      │
│   Recruiter / Manager / Employee / Candidate                  │
│   (candidate portal optionally hosted)                        │
├─────────────────────────────────────────────────────────────┤
│ 5 business modules                                            │
│ M1 Resume Match | M2 Talent Search | M3 Recruitment Workflow  │
│ | M4 Training | M5 Supervision & KPI                          │
├─────────────────────────────────────────────────────────────┤
│ Agent Core (ported from Hermes, Layer A)                      │
│  tool-calling loop · sub-agent delegation · context           │
│  compression · skill/tool registry                            │
│ Long-running orchestration (Layer B: self-built state machine │
│  → upgradable to Temporal/LangGraph)                          │
├─────────────────────────────────────────────────────────────┤
│ Memory Subsystem (ported + extended from Hermes) ★core asset  │
│  org/candidate/employee/recruiter/semantic/procedural memory  │
│  (local files + embedded vector store)                        │
├─────────────────────────────────────────────────────────────┤
│ AI layer  local model(default) / optional cloud model · RAG · │
│  Evals · guardrails · LLMOps                                  │
├─────────────────────────────────────────────────────────────┤
│ Data & integration  local DB · embedded vector store · audit  │
│  log · MCP connectors                                         │
└─────────────────────────────────────────────────────────────┘
            │ (outbound only, optional, on-demand, can be disabled)
            ▼
   External cloud APIs: ATS/HRIS (Workday…), optional cloud LLM,
   (optional) hosted candidate portal
```

**The meaning and benefits of local-first**: data/memory/inference run on the customer's machine by default → ① privacy (HR data does not leave the premises, so "HR-less" SMBs dare to use it more readily); ② naturally satisfies data residency and avoids APP 8; ③ no cloud-infrastructure operations or multi-tenancy complexity (the MVP is simpler). Outbound calls (cloud ATS, optional cloud LLM) are all **optional, can be disabled, and follow minimum-necessary + de-identification**.

---

## 8. Agent Core (the agent kernel ported from Hermes)

### 8.1 The Original Hermes Kernel (Architecture Diagram)

```
┌──────────────────────── Hermes Agent (original) ────────────────────────┐
│ Entry/interfaces: CLI · TUI · Gateway (HTTP)                             │
│        │                                                                 │
│ Conversation loop conversation_loop.py                                   │
│  ├─ system-prompt assembly system_prompt.py (injects memory "frozen      │
│  │     snapshot")                                                        │
│  ├─ tool-calling loop (structured tool schema)                           │
│  ├─ sub-agent delegation (delegate tool; sub-agents skip_memory)         │
│  └─ context compression conversation_compression.py (on_pre_compress     │
│        notification hook)                                                 │
│        │                                                                 │
│ Memory management memory_manager.py                                      │
│  ├─ prefetch (recall before the turn) → <memory-context> fenced          │
│  │     injection                                                         │
│  ├─ sync_turn (persist after the turn; single background worker, serial) │
│  └─ built-in MemoryStore (MEMORY.md/USER.md) + ≤1 external Provider       │
│        │                                                                 │
│ Model layer: multi-provider (provider-agnostic)                          │
│ Session persistence: SQLite sessions; threat_patterns injection defence  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 The Jobpin Agent Kernel After Porting (Architecture Diagram, Local-First + HR-ised)

```
┌────────── Jobpin Agent Core (after porting/adaptation, runs locally) ──────────┐
│ Entry/interfaces: local app (desktop/local web), multi-role portal             │
│        │                                                                       │
│ Conversation loop (borrows Hermes's design, rewritten trimmed-down version)    │
│  ├─ system-prompt assembly (injects org policy/compliance constraints/role     │
│  │     permissions/memory snapshot)                                            │
│  ├─ tool-calling loop (HR tools, integrations via MCP)                         │
│  ├─ sub-agents: Sourcing/Screening/Scheduling/Training/KPI (parent agent       │
│  │     vets writes to memory)                                                  │
│  └─ context compression (extracts key candidate facts/decisions into memory    │
│        before compression)                                                     │
│        │                                                                       │
│ ▲ Long-running orchestration (Layer B, new): hiring-loop state machine         │
│     (self-built → upgradable to Temporal)                                      │
│        │                                                                       │
│ Memory Subsystem (ported code + HR governance extensions)                      │
│  ├─ prefetch / sync (ported) + CompositeMemoryProvider (relaxes "single        │
│  │     Provider")                                                              │
│  ├─ local-file MemoryStore (Org/Recruiter) + embedded vector store             │
│  │     (Candidate/Employee)                                                    │
│  └─ governance: tenant/entity namespaces · provenance · lawfulness labels ·    │
│        TTL · RBAC · audit · de-biasing                                         │
│        │                                                                       │
│ Model layer: local model(default) / optional cloud model; injection defence    │
│   (ported threat_patterns)                                                     │
│ Local data: relational DB + embedded vector store + append-only audit log      │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Section 8.2 legend (ported vs net-new)** — annotates the source of each component so readers can tell "existing vs to-be-built" apart:
- **[Port] Ported from Hermes**: MemoryStore, prefetch/sync orchestration, injection defence (threat_patterns).
- **[Adapt] Adapted after porting**: the conversation loop (rewritten trimmed-down version), system-prompt assembly, `CompositeMemoryProvider` (relaxes "single Provider").
- **[New] Net-new (the bulk of this project's work)**: the local multi-role application and data layer, the 5 HR sub-agents, the **Layer B long-running orchestration**, the embedded vector store for entity semantic memory, **HR memory governance** (namespaces/provenance/lawfulness/TTL/RBAC/audit/de-biasing), pre-compression fact injection (Hermes does not wire this automatically).
> Note: what Hermes gives directly is mainly the **memory engine and injection defence [Port]**; the **[New]** items above are where the bulk of this project's work and risk lie — the two diagrams share a layout, but the "gap" is mainly in the [New] parts.

### 8.3 Capability Mapping (Hermes → Jobpin Agent)

| Capability | Corresponding part from Hermes | HR-ising adaptation |
|---|---|---|
| Tool-calling loop | `conversation_loop.py` turn loop | Plug in HR tools, integrations via MCP; structured tool schema |
| Sub-agent delegation | `on_delegation(...)` | Dedicated sub-agents; the parent agent observes their output and vets writes to memory |
| Context compression | `conversation_compression.py` (provides the `on_pre_compress` notification hook; the backbone does not automatically merge it into the summary) | **Jobpin Agent must wire it up**: before compression, use the hook to extract key candidate facts/decisions and inject them into the summary/memory |
| System-prompt assembly | `system_prompt.py` | Inject org policy, compliance constraints, role permissions, memory snapshot |
| Memory | `memory_*` (see Section 9) | Ported code + HR governance extensions |
| Gateway/runtime | Hermes gateway | Rewritten as a **local-application runtime** (optionally service-ised to the cloud later) |

**Key invariants (inherited Hermes engineering discipline)**: tool calls are **structured and auditable**, and every agent decision step is traceable (supporting auditability and ADM transparency); sub-agents **do not write sensitive memory directly** (`skip_memory`) — the parent agent writes after vetting.

---

## 9. Memory Subsystem ★ (this product's core, porting and extending the Hermes memory system)

> This chapter first **explains clearly how the Hermes memory system is designed and why it gets better with use** (Sections 9.1, 9.4), then gives the porting mapping (Section 9.2), this product's layering (Section 9.3), HR governance (Section 9.5) and acceptance criteria (Section 9.6).

### 9.1 A Detailed Look at the Hermes Memory Mechanism (Load / Store / Optimise / Compress / Remove)

**Two-state model**: the built-in `MemoryStore` maintains two parallel states —
- **Frozen snapshot `_system_prompt_snapshot`**: generated once at `load_from_disk()`, injected into the system prompt, and **never changes for the whole session** (keeping the prefix/prompt cache stable, saving tokens/cost).
- **Active state `memory_entries` / `user_entries`**: modified in real time by tool calls and persisted to disk; tool responses always reflect the active state.

**Two files, separated by a delimiter (`§`, i.e. `ENTRY_DELIMITER` in the Hermes source, a section marker on its own line), with a fixed-length budget**: `MEMORY.md` (agent notes) and `USER.md` (user profile), with entries separated by `§` (`ENTRY_DELIMITER`); each has a character budget (default 2200 / 1375), enforcing "few but high-quality".

| Lifecycle | Hermes's actual mechanism (at the code level) |
|---|---|
| **Load** | `load_from_disk()`: read the two files → split by `§` / strip empties → **deduplicate** (`dict.fromkeys`, order-preserving, keeping the first occurrence) → scan each entry for threats with `threat_patterns` (strict); on a hit, replace it with a `[BLOCKED: …]` placeholder in the **snapshot** (the active state keeps the original text for the user to view/delete) → **freeze the snapshot**. The scan is deterministic over the on-disk bytes → the snapshot is stable for the whole session. |
| **Store** | `save_to_disk()` → `_write_file()`: write a temp file → `fsync` → **atomic `os.replace`** (readers only ever see the complete old file or the complete new file, with no truncation race); the read-modify-write occurs under an exclusive lock on a **separate `.lock` file**; before writing, the add/replace content is scanned for injection/exfiltration. |
| **Optimise** | ① deduplication; ② the **frozen snapshot** maximises prompt-cache hits; ③ the **fixed-length budget** forces a high signal-to-noise ratio; ④ successful responses are **deliberately trimmed** (not echoing all entries, to prevent the model's "let me find a bit more to change" jitter); ⑤ `apply_batch`: multiple operations are **all-or-nothing** and validated only against the **final budget** — within a single tool call you can "rearrange first, then add", avoiding multiple rounds of resending context. |
| **Compress** | Hermes provides a pre-compression hook `on_pre_compress(messages)`, and an external Provider can return "the key facts that should be retained". **Important correction: in Hermes's current backbone this return value is only a notification and is not automatically merged into the compression summary (the call site in `conversation_compression.py` discards the return value), and the built-in file-based `MemoryStore` is not a Provider and has no such hook.** So "compression does not lose key information" is in Hermes **an available extension point rather than a ready-made guarantee — Jobpin Agent must wire it up itself** (injecting the hook's output into the summary/memory). The fixed-length budget itself is a form of "continuous compression/curation". |
| **Remove** | `remove`/`apply_batch`: delete by **substring match** on `old_text`; if **multiple distinct entries** match, it errors and asks for something more specific (to prevent accidental deletion); **external drift detection** `_detect_external_drift`: on finding "content that cannot round-trip" or "an oversized giant entry" (suspected external write) → first snapshot a `.bak`, then **reject the current write** (to prevent silent data loss). |

### 9.2 Porting Mapping Table (Hermes → Jobpin Agent)

| Hermes mechanism | Direct port | HR-ising adaptation |
|---|---|---|
| Built-in file-based `MemoryStore` (fixed-length/atomic/lock/drift/backup) | ✅ Port the code | Carries **organisational memory** and **recruiter preferences** (a low-frequency, finely-curated, strongly-consistent, small-volume layer) |
| The abstract interface `MemoryProvider` (`initialize/prefetch/sync_turn/on_pre_compress/on_session_switch/...`) | ✅ Port the interface contract | Implement `CandidateMemoryProvider`/`EmployeeMemoryProvider`/`OrgMemoryProvider`/`SemanticRAGProvider` |
| `prefetch` before the turn / `sync_turn` after the turn (single background worker, serial, guaranteeing turn N precedes N+1) | ✅ Port | Recall relevant history before the turn; persist asynchronously after the turn; serial execution guarantees consistency |
| System-prompt **frozen snapshot** | ✅ Port | Saves cost at scale; org policy/compliance constraints as a stable prefix |
| Write-time **threat scan** + `<memory-context>` fence + streaming scrubbing | ✅ Port and **strengthen** | Resume/email prompt-injection is a real attack; external text is force-scanned + fenced before entering memory/context |
| Deduplication/batch merge (`apply_batch`/`dict.fromkeys`) | ✅ Port | Memory hygiene: merge duplicates, atomically update candidate profiles |
| "Only one external Provider at a time" | ⚠️ **Relaxed** | HR needs multiple dedicated Providers to coexist → `CompositeMemoryProvider` (routes and merges by entity/query) |

### 9.3 Jobpin Agent Memory Layers

```
Working memory      —— single-session draft (session-level, ephemeral)
       │
Entity memory       —— long-term, structured + semantic, aggregated by entity:
   ├─ Candidate     (skills/experience/past interactions/interview feedback/
   │                 preferences/consent/provenance)
   ├─ Employee      (role/competencies/OKRs/training history/performance
   │                 signals/1:1 highlights/growth)
   ├─ Job/Req       (requirements/ideal profile/calibration conclusions/
   │                 historical outcomes)
   ├─ Org           (hiring standards, competency framework, scoring rubrics,
   │                 historical decisions, policy) ★moat
   └─ Recruiter/Mgr preferences (personal preferences/communication style/
                     the hiring manager's "bar")
       │
Semantic/episodic   —— vectorise interactions/resumes/JDs/feedback (embedded
       │               local vector store), supporting RAG
       │
Procedural          —— learned workflows/playbooks ("how to run a SWE hiring
                       loop") + Section 11.8 compliance-process knowledge
```

- **Small-volume, finely-curated layers** (Org, Recruiter) → the ported file-based `MemoryStore` (fixed-length, atomic, strongly consistent, human-reviewable diffs).
- **Large-volume, retrieval layers** (Candidate, Employee, Semantic) → an **embedded local vector store** + a local structured store, encapsulated behind a unified `MemoryProvider` interface, reusing Hermes's prefetch/sync/lifecycle orchestration.

### 9.4 Why It "Gets Better With Use" — the Memory Learning Loop

```
      ┌─────────────────────────────────────────────┐
      │ Each turn / each decision                    │
      │                                              │
   Before the turn, prefetch ──► recall relevant     │
      │   entity memory (fenced injection)           │
      │                      ▼                       │
      │   agent reasoning + action + recommendation  │
      │                      ▼                       │
   User feedback (adopt/override/correct) + new facts │
      │                      ▼                       │
   After the turn, sync_turn ──► persist             │
      │   asynchronously (candidate/org memory)      │
      │                      ▼                       │
   Org-memory calibration ("this company's standard   │
      │   of a good X" continuously updated)         │
      └──────────────► next recall is sharper ───────┘
   (before compressing a long session, on_pre_compress
    extracts key facts to ensure nothing is lost)
```

Why it **gets better with use** mechanistically: ① every completed turn writes **new facts** back to memory (`sync_turn`), to be recalled again by the next `prefetch` — knowledge accumulates monotonically; ② recruiters' **adopt/override feedback** is written into organisational memory, making matching calibration approach "this company's real hiring standard" (learning-to-rank); ③ **fixed-length + deduplication + drift protection** keeps a high signal-to-noise ratio; ④ the Provider interface lets the memory backend be upgraded independently.

**Scope of applicability and two honest premises**: (a) the learning-to-rank flywheel **needs a volume of feedback** — for an "HR-less" SMB that hires only a few times a year, per-org calibration will not converge meaningfully in the short term, so **this segment's day-1 value comes mainly from the built-in expertise of the "cold start" below, not the calibration flywheel**; the strong "gets better with use" curve applies mainly to high-volume recruiters. (b) Writing preferences and a recruiter's "bar" into organisational memory may **amplify personal preferences or even bias**, which is in tension with Section 9.5's "prohibit protected attributes / proxy variables" — so a **feedback-bias-amplification control** must be set: scan preferences written into calibration for protected attributes/proxy variables, and bring them into bias-audit monitoring. **This also connects the "HR-less pain point"**: professional HR processes and compliance rules accumulate as **procedural/organisational memory** (Section 11.8), and the system increasingly becomes "like a knowledgeable HR person" for that company.

**Cold start (day-1 value)**: when organisational memory is empty, the system uses **built-in professional HR processes and Australian compliance knowledge** (Section 11.8) as the "factory seed" of procedural/organisational memory — there is a professional baseline available on day 1, with the company's specific standards then accumulating through use (**useful first, stronger later**), thereby avoiding the "memory moat" falling flat in the early period.

### 9.5 HR-Specific Memory Governance ★ compliance-critical (Australia)

| Governance capability | Design | Compliance driver (Australia) |
|---|---|---|
| Tenant/entity namespaces | Memory key = `tenant : org : entity_type : entity_id` | Isolation, least privilege, APP 11 |
| Provenance | Each memory records its source, with a link back to the original evidence | Explainable/appealable, auditable, ADM transparency (APP 1) |
| Lawfulness/consent labels | Labels for collection purpose/consent/use | APP 3/5/6 |
| Retention period / TTL | Candidate data expires per policy; separate strategies for hired/not-hired | APP 11.2 |
| Data-subject-level erasure/correction | Delete and **de-identify** all of an individual's memory + derived vectors from the **active store**; backups are not cascaded immediately but age out **naturally on retention-period expiry** (the erasure commitment is limited to active storage) | APP 11.2 (destruction/de-identification, not GDPR-style instant erasure), APP 13, complaint handling |
| Memory RBAC | Can only recall memory within the authorised scope | Least privilege, APP 11 |
| Full audit (read & write) | Record who/what/when/why (local audit log) | Accountability, NDB forensics |
| Bias hygiene | Prohibit storing/using protected attributes as decision features; scan for proxy variables | Federal anti-discrimination law, AHRC |
| Memory explainability | Any recommendation can be expanded to "based on which memory facts" | Trust, appealability, ADM transparency |

### 9.6 Memory System Acceptance Criteria
- Recall relevant entity context at P95 < 800 ms: **the default benchmark is real SMB scale (hundreds to thousands of candidates) on the published minimum hardware tier**; the ~100,000 scale is a standalone stress-test ceiling, with targets given by hardware tier.
- Data-subject-level erasure: instant deletion/de-identification within the active store (structured + vector + cache); backups age out by retention period (see Section 9.5), with no commitment to instant cascade.
- Injection test: all 1,000 "adversarial resumes/emails" are fenced, with 0 instructions executed.
- Memory writes carry provenance and lawfulness labels 100% of the time; writes without labels are rejected (inheriting Hermes's "reject invalid writes").

---

## 10. Functional Requirements by Module

> Each module gives: scenario, functional requirements, Agent tools, AI methods, key boundaries/compliance, metrics.

### M1 — Resume Matching
**Scenario (recruiter / Dana)**: Given a JD, the system finds the best-matching people from the candidate pool/applications and explains why each matches/does not match, to support a quick decision.
- F1.1 Resume parsing: PDF/Word/plain text/LinkedIn export → normalised structure (skills/experience/education/certifications).
- F1.2 JD parsing and "ideal profile": derive must-haves / nice-to-haves / negative signals from the JD + organisational-memory calibration.
- F1.3 Hybrid matching: semantic (embedding) + structured (skills/years/location/work rights) + organisational calibration.
- F1.4 **Explainable scoring**: itemised scores + natural-language rationale + evidence citations (traced to the original resume text).
- F1.5 De-biasing: mask protected attributes and proxy variables; name/gender/age/photo can optionally be anonymised (blind screening).
- F1.6 Feedback loop: adopt/override → written into candidate/organisational memory, continuously calibrating (learning-to-rank).

**Agent tools**: `parse_resume`, `parse_jd`, `match_candidates`, `explain_match`, `anonymize_profile`.
**AI methods**: local embedding retrieval + reranking + LLM structured extraction and explanation (model tiering: lightweight local model for extraction, strong model for explanation/scoring).
**Boundaries/compliance**: F1.4 explanation + HITL = preparing for ADM transparency (APP 1) and accountability; F1.5 de-biasing + bias audit = reducing indirect-discrimination risk (anti-discrimination law, AHRC); explanations must be **grounded** (no hallucinated qualifications).
**Metrics**: Top-10 hit rate, share of explanations approved, pass-rate ratios across groups.
**Day-1 (cold-pool) behaviour for "HR-less" SMBs**: such customers **have no candidate pool** — M1 works even with only a few emailed/file resumes: parse → use the **built-in professional baseline of organisational memory** (Section 9.4 cold start) + JD calibration to derive the ideal profile → produce an explainable ranking of the few resumes at hand with gap explanations. The value comes from "professional screening + explanation + compliance guardrails", not large-pool retrieval.

### M2 — Talent Search / Sourcing
**Scenario**: Describe the person to find in one sentence, and the system proactively recalls from the internal pool, historical candidates and (authorised) external channels, and remembers who was contacted and why they were passed over.
- F2.1 NL → multi-source sourcing: internal pool, historical candidates, (authorised API) LinkedIn/recruitment platforms.
- F2.2 "Dormant candidate" recall (**primarily for has-HR / customers with an existing historical candidate pool; not applicable to "HR-less" SMBs with a cold pool, listed as a follow-up**): proactively re-engage previously suitable people based on candidate memory (compliant re-contact).
- F2.3 Boolean/vector hybrid retrieval + similarity expansion.
- F2.4 Sourcing-agent orchestration: decompose → parallel retrieval → dedupe and merge → rank → remember the "sourcing trail".
- F2.5 Outreach drafts: personalised outreach drafts, **sent after human confirmation** (no automated mass-sending).

**Boundaries/compliance**: external channels must use an **authorised API** (no scraping that violates ToS); contacting candidates complies with APP 5 and electronic-marketing consent (Spam Act); outreach is not sent automatically.

### M3 — Recruitment Workflow
**Scenario (recruiter/hiring manager/Dana)**: The process from screening to offer is orchestrated by the agent, reducing back-and-forth across ATS/email/calendar/IM.
- F3.1 Process state machine (**Layer B**: starts with a self-built lightweight state machine, evaluating Temporal/LangGraph once complex), with two-way sync to the ATS.
- F3.2 Interview-scheduling agent: coordinates calendars/time zones/interviewer load, generating a draft schedule (human-confirmed).
- F3.3 Structured interview feedback: competency-based scorecards, with automatic aggregation and conflict flagging.
- F3.4 Calibration support: align standards across interviewers, identify scoring bias, write into organisational memory.
- F3.5 Candidate communication: status notifications, personalisation (including respectful rejection letters), human gatekeeping.
- F3.6 Candidate privacy portal: view status, exercise APP 12 (access) / APP 13 (correction) and complaints.

**Boundaries/compliance**: every "affecting the candidate" node has HITL; scorecards are based on job-relevant competencies; F3.6 satisfies APP 12/13 and complaint handling.

### M4 — Employee Training / L&D
**Scenario**: Based on role competency requirements and current gaps, generate a personalised learning path and track growth.
- F4.1 Competency map: role → competencies → learning resources.
- F4.2 Gap analysis: employee memory (existing competencies) × role requirements → gap.
- F4.3 Personalised learning paths (internal courses/external/mentor/project experience).
- F4.4 Learning-companion agent: Q&A, knowledge retrieval (RAG over the internal knowledge base), stage assessments.
- F4.5 Growth tracking: pre/post tests, capability growth, correlation with performance, written into employee memory.
- F4.6 Linkage with recruitment: during internal mobility/promotion, the data becomes the internal-candidate profile (connecting M1/M2).

**Boundaries/compliance**: using employee data for development purposes requires transparency (APP 5); if assessments affect promotion/performance, they enter high-sensitivity decisions requiring HITL + explanation.

### M5 — Supervision & KPI/Attendance ★ highest compliance sensitivity
> **Positioning (red line)**: An **assistive tool for goal alignment and performance insights**, **not surveillance**. **Does not do** intrusive monitoring (no keylogging/screenshots/facial/emotion recognition). **Does not do** automated punishment/dismissal. Every judgement affecting an individual = strong HITL + explainable + appealable.

**Scenario (supervisor)**: Connect team goals (OKRs/KPIs) with execution progress and attendance to gain insight into "who needs support / who is underestimated" in order to coach the team better.
- F5.1 Goal management: OKR/KPI setting, cascading alignment, progress tracking (data from integrated systems).
- F5.2 KPI insights: based on objective, job-relevant metrics, surface trend/anomaly/attention signals (**explanation takes priority over scoring**).
- F5.3 Attendance integration: connect to existing attendance/rostering (aggregation, **no new monitoring built**).
- F5.4 1:1/coaching support: based on employee memory, prepare topics/recognition/development suggestions for the supervisor.
- F5.5 Performance-review support: aggregate multi-source evidence to support a **human** evaluation; the system draws no conclusions.
- F5.6 Fairness and appeals: employees can see the evaluation data and criteria, can appeal and have errors corrected (APP 13).

**Boundaries/compliance (highest bar; depends on the pilot state)**:
- **State workplace surveillance/monitoring laws (vary greatly by state; must be adapted to the confirmed pilot state)**: NSW *Workplace Surveillance Act 2005* requires **≥14 days' written notice + a clear policy for computer/camera/tracking surveillance, and prohibits covert surveillance** (toilets/change rooms are absolute no-go areas); ACT *Workplace Privacy Act 2011* has its own notice/consent requirements (**not equivalent to NSW's 14-day rule; must be checked separately**); VIC *Surveillance Devices Act 1999* regulates the **covert use of listening/optical/tracking devices** (not a "notice period" regime; do not list it alongside the 14-day notice); QLD and the remaining states/territories mostly regulate via **general surveillance-devices laws** — "no dedicated workplace surveillance law" **does not mean no constraint**. This module **introduces no new monitoring** and only aggregates existing systems.
- **NSW WHS (Digital Work Systems) 2025/26 amendment**: brings AI work allocation and automated decision-making into WHS; if in NSW, the WHS (including psychosocial) obligations must be assessed.
- **Fair Work Act 2009**: general protections / adverse action / unfair dismissal — **any automated adverse treatment is prohibited**; performance actions must be human-decided.
- **Privacy Act / APPs** + ADM transparency (APP 1).
- **Employee consultation**: negotiate terms per the applicable modern award / enterprise agreement (award/EA) (Australia has no uniform mandatory union consultation, but a duty to consult may arise from the award/EA and good practice).
- **Pre-launch prerequisites**: PIA + legal sign-off + employee consultation + bias audit, none of which may be omitted (see the Phase 3 Gate in the delivery plan).
- **State decision matrix (whether/how M5 is launched depends on the pilot state; Section 14 Open Question #2)**: it must be clarified for the pilot state — ① which surveillance/privacy/WHS obligations apply; ② whether M5 is **on/off** by default; ③ if the state has no dedicated workplace surveillance law, this module still applies Privacy/Fair Work/general surveillance law strictly and **conservatively disables** sensitive capabilities by default. **"M5 being downgraded / not delivered for now in this pilot" is an allowed, planned, legitimate outcome**, not a failure — Fair Work and the Privacy Act always apply, regardless of whether the state has a dedicated surveillance law.

---

## 11. Cross-Cutting Requirements

### 11.1 Canonical Entities
`Candidate, Job/Requisition, Application, Employee, Skill, Competency, Course/LearningResource, Goal/OKR, KPI, Review/Feedback, Interview, Interaction/Event, Consent, Org, User(role), AuditRecord, MemoryRecord`.
- All entities carry an `org_id` (with a `tenant_id` abstraction reserved for future multi-tenancy; the single-tenant local MVP does not enable multi-tenancy infrastructure).
- **Audit**: an append-only audit log (local); the MVP **does not mandate full event sourcing** (see the simplification principle in Section 13.1).

### 11.2 Integrations
- **Minimal integration for the MVP ("HR-less" SMB)**: local **file/email import of resumes** (PDF/Word/email attachments/cloud drive) + calendar and email — SMBs usually **do not have** an ATS/HRIS, so the MVP does not depend on an enterprise ATS. (**Cold-pool reality**: such customers also **have no historical candidate pool**, so M1 works with "a few resumes + a built-in professional baseline", and M2 dormant-candidate recall is "has-HR / follow-up" — see Section 9.4 and M1/M2.)
- **HRIS/ATS (has-HR enterprises / follow-up)**: Workday, SAP SuccessFactors, Greenhouse, BambooHR, Lever (connector framework, OAuth; exposed as **MCP** tools).
- **Sourcing**: LinkedIn (official/authorised API), recruitment platforms.
- **Collaboration**: Google/Microsoft calendar and email, Slack/Teams, SSO (OIDC/SAML, SCIM).
- **Design**: a unified connector SDK + an anti-corruption layer translating into canonical entities; Webhook + polling two-way sync; rate limiting and retries. Integrations are **outbound, optional** calls (local-first).

### 11.3 AI / LLM Architecture (Local-First)
- **Model strategy (local-first + tiered)**:
  - **Local model by default** (running open-source models such as the Llama/Qwen/Mistral families via Ollama/llama.cpp, etc.) handles PII-heavy extraction/classification/parsing and most agent reasoning → data does not leave the premises.
  - **Optional cloud model** (e.g. Claude Sonnet/Opus) for hard reasoning/explanation, **requiring explicit enablement + PII minimisation/de-identification + APP 8 handling**; can be turned off entirely to enter "fully local" mode.
  - **Bring-your-own key / own model endpoint (BYO-key, the recommended compromise)**: the local app calls cloud models directly using the **customer's own** model account (e.g. the customer's own Anthropic / Bedrock Sydney key) — data goes from the customer's machine straight to the model provider, **without passing through any of our servers**: this obtains frontier-model quality while keeping us from touching PII. This option resolves the difficulty of "local hardware is insufficient to run a high-quality model". **Note: BYO-key/optional cloud still constitutes cross-border disclosure — the customer, as an APP entity, remains responsible for APP 8 (our not touching the data does not exempt the customer's obligation); the mitigation = choosing an Australian region (e.g. Bedrock Sydney) + contract/the APP 8.2 exception + outbound de-identification. Only "fully local" mode truly results in no cross-border disclosure.**
  - The model router dynamically selects by task difficulty/privacy level/hardware capability; a provider-agnostic abstraction avoids lock-in. **Routing-failure / key-expiry fallback**: if a cloud/BYO call fails or the key is revoked during a long-running process (the hiring loop), the state machine pauses and falls back to the local model or suspends for a human, without losing the process.
  - **De-identification must have an explicit pipeline** (not a slogan): before outbound, detect PII + mask/pseudonymise, and locally record the pre/post de-identification mapping — this is also a precondition for APP 8.
  - **Selectable model providers (pluggable adapter layer)**: the provider-agnostic abstraction exposes one adapter per backend behind a single interface. **Launch set: OpenAI (the first implemented adapter and the default active provider for the internal pilot / development, since an account already exists), Anthropic Claude, and DeepSeek**, alongside the local-model path. The active provider and its key are a **deployment / customer configuration (BYO-key)**, not a code change: the Claude and DeepSeek adapters are built to interface parity, so a customer can switch by supplying a key. **This does not change the local-first default for the commercial product** (Sections 1, 7, G7): choosing any cloud provider (OpenAI / Claude / DeepSeek) routes PII outbound and therefore invokes the explicit-enablement + de-identification + APP 8 controls above; only "fully local" mode results in no cross-border disclosure.
- **Embedding/vectors**: local embedding (e.g. the BGE family) + an **embedded vector store** (sqlite-vec / LanceDB / Chroma local). **The embedding model must be version-pinned and recorded alongside the vectors**; switching the embedding model/dimensions makes the vector space incompatible and requires a **re-embed migration**, which must not be silently mixed.
- **Prompt reuse**: reuse Hermes's "frozen snapshot" to stabilise the prefix and reduce cost (especially for cloud models).
- **RAG**: hybrid retrieval (BM25 + dense) + reranking; citation grounding, hallucination prevention (LlamaIndex may be used as a component).
- **Evals**: golden set + LLM-as-judge + offline regression + online A/B; **bias/fairness eval** enters the CI gate.
- **Guardrails**: input-side PII/injection detection; output-side grounding checks/sensitive filtering/over-permission blocking.

### 11.4 Security & Privacy (Local-First)
- Encrypt the local database and memory files at rest (keys managed by the OS keystore/DPAPI/Keychain); encrypt sensitive fields.
- RBAC + ABAC (by org/team/role/sensitivity); SSO + SCIM (enterprise scenarios); least privilege.
- Append-only local audit log; key/secret management; DLP.
- **Data residency**: data/inference are local by default (onshore is satisfied naturally); any outbound (cloud ATS, optional cloud LLM) follows APP 8 controls + minimum-necessary + de-identification + can be disabled. NDB data-breach notification process.
- Threat modelling + penetration testing + red teaming (including prompt-injection via resumes); update and integrity verification for the local app.
- **NDB (Notifiable Data Breaches) responsibility and runbook**: in local mode, **the customer is the APP entity holding the data and bears the 30-day assessment/notification obligation**; an SMB with no IT has high risk of local-machine loss/ransomware, with no visibility on our side. We must provide: local breach-detection signals, customer-side guided tooling for "assess → notify OAIC/individuals", and a responsibility-allocation statement; **encryption at rest** serves as the NDB remediation / safe harbour. Listed as a Phase 1 compliance deliverable.

### 11.5 Compliance & Responsible AI ★ Australia
> Australia currently **has no mandatory high-risk-AI-specific law** (the National AI Plan 2025 is not legislating for now, relying on existing technology-neutral law + industry regulation + voluntary guidance). This product is designed **strictly** for the highly-sensitive HR scenario and aligned with the voluntary guidance.

| Framework / law | Key obligations | Implementation in Jobpin Agent |
|---|---|---|
| **Privacy Act 1988 + 13 APPs** | Collection notice (APP 5), purpose limitation (APP 3/6), security (APP 11), destroy/de-identify when no longer needed (APP 11.2), access and correction (APP 12/13) | Memory governance Section 9.5, privacy portal, retention/TTL, local audit |
| **ADM transparency (APP 1, effective 2026-12-10)** | Disclose in the privacy policy "automated decisions that significantly affect an individual" | HITL + explainable + decision log + disclosure template |
| **APP 8 cross-border disclosure** | When disclosing PII overseas, **the customer as an APP entity is always responsible** (including BYO-key) | **Only "fully local" mode results in no cross-border disclosure**; optional cloud/BYO-key chooses an Australian region + contract/APP 8.2 + de-identification; do not overstate it as "avoidance" |
| **Federal anti-discrimination law + AHRC** (the four acts on race/sex/disability/age) | Prohibit direct/indirect discrimination | De-biasing, bias audit, job relevance, explainability |
| **Fair Work Act 2009** | General protections / adverse action / unfair dismissal | M5 prohibits automated adverse treatment; performance actions are human-decided |
| **State workplace surveillance laws** (NSW/ACT/VIC) | Notice (14 days), policy, prohibit covert surveillance | M5 hard Gate (depending on the pilot state); no new monitoring built |
| **NSW WHS Digital Work Systems (2025/26)** | AI work allocation/ADM brought into WHS | If in NSW, assess WHS (including psychosocial) obligations |
| **Voluntary AI guidance** | Transparency, accountability, risk management, human oversight, record-keeping | Aligned with the 2025 *Guidance for AI Adoption* (6 practices); the 10 guardrails of its predecessor, the *Voluntary AI Safety Standard*, can still serve as a reference control set. **Note: the "mandatory high-risk AI guardrails" proposed in 2024 have been shelved; do not confuse them with this.** |
| **Spam Act 2003 / Do Not Call** | Electronic-marketing consent | M2 outreach compliance (consent, unsubscribe) |

- **Handle the employee records exemption with care**: the Privacy Act provides an exemption for private-sector employers handling the "employee records" of **current/former employees**, which may partially cover M4/M5 employee data; but it **does not cover candidates** (pre-employment), its scope is contested and under review. **More importantly: the "statutory tort for serious invasion of privacy" effective 2025-06-10 already imposes a real constraint on reliance on this exemption** (especially M5 monitoring) — so applying APP-level protection to employee data is **partly a current legal necessity, not merely best practice / future-proofing**. The product does not rely on this exemption.
- **The statutory tort for serious invasion of privacy (introduced by the 2024 reforms)**: excessive employee monitoring/surveillance may trigger it — M5's proportionality, transparency and minimum-necessary are made strict accordingly.
- **HITL**: all "affecting an individual" outputs default to a recommendation state, requiring human confirmation, recording the decision-maker and the rationale.
- **Explainability**: every recommendation can be expanded to "based on which facts/memory/metrics", traced to the original evidence.
- **Fairness**: the launch gate includes a bias audit; continuously monitor group-metric drift.

### 11.6 Observability & Quality
- Step-level agent tracing (tool calls, sub-agents, memory reads/writes); a local cost/latency/quality dashboard (Langfuse/OTel, prefer locally-deployable).
- Evaluation dashboards (quality, fairness, hallucination); alerting; canary release and rollback (at the app-update level).
- **Telemetry boundary under local-first (key)**: **local retention** by default; only **de-identified, customer opt-in** aggregate metrics are sent back to us. **Fairness/bias metrics containing protected attributes do not leave the premises by default under local-first** — so the guardrail metrics in Section 6's "any deterioration blocks release" split into two classes: **local self-assessment + customer-side reporting** (for the customer's own roll-out decisions) vs **aggregate signals visible to us** (for product-level release gating); the document must mark which class each guardrail metric belongs to, to avoid a gate that "is committed to but for which the data cannot be obtained".

### 11.7 Internationalisation & Accessibility
- The pilot is Australia: **English (Australian) first**; multilingual is a later option (not a goal this phase). Multiple time zones as needed; WCAG 2.1 AA.

### 11.8 "Expertise & Compliance Embedded" for Non-Expert Users ★
For customers with "no dedicated HR", the product not only automates tasks but must **possess the expertise on the user's behalf**. Design requirements:
- **Guided workflows**: turn professional HR processes (structured hiring loop, compliant onboarding, performance review) into step-by-step guidance, rather than handing the user a blank tool.
- **Compliance guardrails for "people"** (not just for the AI): proactively intercept/prompt when the user is about to err — e.g. prohibited interview questions (age/marriage and children/health/ethnicity, etc., which may constitute discrimination), discriminatory wording in a JD, non-compliant dismissal actions.
- **Compliance template library**: JDs, interview scorecards, offer/rejection letters, privacy notices (APP 5), policies — compliant by default and localisable.
- **Plain-language explanations**: explain "why do it this way / what this law means" in terms a non-expert user can understand.
- **Safe defaults + escalation path**: default to the safest, most compliant path; for high-risk/edge cases, **clearly flag that it is beyond the tool's scope and recommend consulting professional HR/legal** (consistent with N5).
- **Memory carries the expertise**: the above process knowledge and compliance rules accumulate as **organisational/procedural memory** (see Sections 9.3, 9.4), making the system increasingly "like a knowledgeable HR person" for that company — directly connecting the "HR-less pain point" with the "memory moat".

> **⚠️ This section is the highest liability surface and must be engineered as a first-class module (not just a sales line)**: proactively judging for non-expert users whether "this interview question may be asked" or "this dismissal action is compliant" is **compliance guidance for those unable to judge for themselves**, which, compounded with LLM hallucination risk (Section 13.3), is the largest legal exposure. Therefore the requirements are: ① a **compliance rules library (golden set) + continuous eval**; ② the rules library **must be vetted and signed off by an Australian employment lawyer and periodically re-reviewed**; ③ clearly defined **accuracy/precision targets**, with **"confidently wrong guardrail advice" listed as a P0 anti-metric** (wrongly saying "you may ask" is worse than giving no prompt); ④ failure-mode analysis + fallback: **conservative by default + always one-click escalation to a professional**; ⑤ a liability/disclaimer stance consistent with N5 (guardrails and guidance, not a substitute for legal advice).

---

## 12. Non-Functional Requirements (NFR)
| Dimension | Target (MVP → scale-up) |
|---|---|
| Latency | **Targets given by published hardware tier**: memory recall (vector retrieval) P95 < 800 ms, decoupled from generation time-to-first-byte; time-to-first-byte < 2 s is committed only on **recommended hardware** or via cloud/BYO-key, degrades below the minimum tier (smaller local model / route the prompt to the cloud) with clear notice, and is not a blanket < 2 s commitment |
| Throughput | Whole-org concurrency for a single organisation; batch resume parsing processed asynchronously and locally |
| Local hardware baseline | Provide minimum/recommended configurations (CPU/memory/optional GPU); the local model is tiered by hardware; low-end can use the "optional cloud model" |
| Availability | Local-app stability + crash recovery; (optional cloud components) SLO 99.9% |
| Scalability | Real SMB scale is usually hundreds to thousands of candidates; the architecture ceiling on a single machine reaches ~100,000 candidates / ~10,000 employees (embedded vector store); the scale-up path is in Section 13.2 |
| Cost | The local model has near-zero marginal inference cost (hardware required); when using cloud models, set a unit-cost budget and alerts |
| Data residency | Local (onshore) by default; outbound is optional, can be disabled, APP 8-controlled |
| Recoverability | Local data backup/restore drills; RPO/RTO targets (per the customer's policy) |

---

## 13. System Architecture (Overview, Local-First)

**Deployment form**: a single **local app** (desktop or local server), self-contained with the agent runtime, memory, local database, embedded vector store, and (optional) local-model runtime; outbound calls are made only on demand (cloud ATS, optional cloud LLM, optional hosted candidate portal).

### 13.1 MVP Simplification Principle (Avoiding Over-Engineering)
To avoid enterprise-grade architecture being over-complex on a local MVP, the following heavyweight designs are **deliberately deferred** (keep the abstraction, do not build ahead):
- **Multi-tenancy infrastructure** → local is naturally single-tenant; keep the `org_id`/`tenant` abstraction, do not build multi-tenant isolation/billing (optional in Phase 4).
- **Full event sourcing** → for the MVP, a relational store + an **append-only audit log** suffices for auditability; event sourcing is left for the scale-up/cloud path.
- **`CompositeMemoryProvider` multi-Provider** → for the MVP, a "file-based MemoryStore + a single embedded vector store" is enough; multi-Provider merging is enabled later, at M4/scale-up.
- **Five sub-agents** → the MVP (M1–M3) launches the three Sourcing/Screening/Scheduling first; Training/KPI come online with their modules.
- **A heavyweight orchestration engine (Temporal/LangGraph)** → start with a self-built lightweight state machine, introducing one once complexity rises (Section 2.6, Layer B). **But "lightweight" does not mean weak guarantees**: the self-built state machine must satisfy a **minimum persistence contract** (recoverable after a crash, pause/resume across days, **idempotent** for external side effects such as sending emails / creating schedules), and this serves as a Phase 0/1 exit criterion; if it cannot meet it, adopt Temporal earlier — the "every step auditable" required for compliance depends on this persistence.

### 13.2 Scalability Path
- **Single-machine vertical**: an embedded vector store (LanceDB/sqlite-vec) can handle millions of vectors; the local model is tiered by hardware; a single machine suffices for most SMBs.
- **Local horizontal**: within an organisation, an optional "local server + multiple clients" deployment (sharing a single local backend, avoiding multi-copy conflicts in file-based memory).
- **Organisational-memory sync across multiple devices/copies is a real limitation of local-first**: two separately-installed machines each have an independent file-based MemoryStore + vector store, with **no built-in merge/conflict resolution**; so "multi-device/team collaboration" either goes through a "shared local backend" single instance or through the **optional cloud/managed form** — pure multi-copy local does not provide organisational-memory sync (this also means the memory moat in Section 1 does not automatically accumulate across devices in a multi-copy local scenario).
- **Optional cloud path (Phase 4)**: for customers needing multiple devices/team collaboration/hosting, offer a cloud/hybrid form — only then introduce multi-tenant isolation, a cloud vector store, and a horizontally-scaling agent runtime (the reserved abstraction makes migration controllable).
- **Product-level scaling**: a local-first product scales by "copying each installation", with simpler operations; centralised updates/observability are addressed via app reporting (optional, de-identified).

### 13.3 Major Risks
| Risk | Level | Mitigation |
|---|---|---|
| HR AI legal/compliance sensitivity (especially M5) | High | Compliance-first architecture, per-module PIA, legal Gate, M5 done last with a hard gate |
| Bias/discrimination risk | High | De-biasing, bias audit in CI, continuous monitoring, HITL, job relevance |
| Resume/email prompt-injection | Medium-high | Ported + strengthened Hermes threat scan and fence; red teaming |
| Insufficient local-model quality affecting matching/explanation | Medium-high | Model tiering; route hard tasks to a "bring-your-own-key" cloud model (data does not pass through us) or a de-identified cloud call; continuous eval for selection; hardware tiering |
| Operational/update/backup barrier of local deployment (especially SMBs with no IT) | Medium | One-click install / auto-update / automatic local backup; guided operations; optional hosting |
| Erroneous/stale memory contaminating decisions | Medium | Provenance, TTL, drift detection, human correctability, memory audit |
| LLM hallucinating fabricated qualifications | Medium | Grounded citations, output validation, eval gate |
| Data leaving the country (using a cloud LLM API) | Medium-high | Local by default; when using the cloud, de-identification + APP 8 + can be disabled |
| Scope too large (5 modules) | Medium | Platformised shared foundation + strict phasing + Section 13.1 simplification |
| Damaged employee trust (M5 seen as surveillance) | High | Transparency, assistive positioning, appealability, participatory design, employee consultation |
| **Section 11.8 compliance guardrails giving "confidently wrong" advice to non-expert users** | High | Lawyer-vetted rules library + eval + wrong guardrails as a P0 anti-metric + conservative by default + one-click escalation to an expert (Section 11.8) |
| Concurrent writes to local file memory by multiple users (single `.lock` / single-worker bottleneck) | Medium | Define the MVP concurrency model clearly (single-user desktop vs shared local backend); multi-user goes through a single-instance backend |
| Guardrail-metric data unobtainable under local-first (cannot truly gate) | Medium | Distinguish local self-assessment vs customer opt-in aggregate reporting; gate only on the class that can be obtained (Section 11.6) |
| Validation of HR-less SMBs deferred to Phase 4 (the core hypothesis validated only at the end) | High | The delivery plan brings in SMB design partners early + the pilot charter includes kill criteria |

---

## 14. Assumptions & Open Questions
**Assumptions**: the commercial MVP is **local-first**; local model by default, optional cloud model (provider-agnostic); English (Australian) first; integration targets are based on the enterprise's existing HR stack (to be confirmed).

**Open (require stakeholder confirmation)**:
1. The enterprise's existing HR tech stack (Workday? SuccessFactors? other) → determines the first batch of connectors.
2. **Which Australian state/territory the pilot is in** (especially NSW?) → determines the workplace surveillance law and WHS obligations applicable to M5.
3. **Local hardware baseline**: can the pilot users' machines run the required local model? How large is the low-end proportion? → determines the local-model tiering and the "optional cloud model" strategy.
4. Whether any PII is allowed to leave the country to a cloud LLM (even if de-identified) → determines whether a "fully local" hard constraint is needed.
5. The target job families for the internal MVP pilot.
6. Whether there are applicable award/EA consultation clauses (affecting the M5 employee-consultation bar).
7. Team size and budget (determining the delivery-plan timeline, see `02-Production-Plan.md`).
8. **The MVP concurrency model**: single-user desktop, or "shared local backend + multiple clients"? → determines authentication, memory RBAC and file-memory concurrency handling.
9. **Pilot design partner**: can an "HR-less" SMB be brought in as early as Phase 1 (the core commercial hypothesis) rather than waiting until Phase 4? → see the pilot charter in the delivery plan.

---

## References (excerpt, as of 2026-06; legal content must be confirmed by Australian legal counsel)
- Australian Government *Voluntary AI Safety Standard* / *Guidance for AI Adoption*: https://www.industry.gov.au/publications/voluntary-ai-safety-standard
- Overview of the shelving of mandatory AI guardrails and the National AI Plan: https://montrealethics.ai/ai-policy-corner-from-proposed-mandatory-guardrails-to-the-national-ai-plan-ai-governance-in-australia/
- Privacy and Other Legislation Amendment Act 2024 (including the commencement timetable): https://www.minterellison.com/articles/privacy-and-other-legislation-amendment-act-2024-now-in-effect
- Practical implications of the automated-decision-making transparency obligation (APP 1, effective 2026-12-10): https://jws.com.au/what-we-think/practical-implications-of-new-transparency-requirements-for-automated-decision-making/
- OAIC: Workplace monitoring and surveillance: https://www.oaic.gov.au/privacy/your-privacy-rights/surveillance-and-monitoring/workplace-monitoring-and-surveillance
- NSW *Workplace Surveillance Act 2005*: https://legislation.nsw.gov.au/view/html/inforce/current/act-2005-047
- Production comparison of agent frameworks (2026): https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026 ; https://openagents.org/blog/posts/2026-02-23-open-source-ai-agent-frameworks-compared
- Anthropic *Building Effective Agents* (engineering guidance on preferring simple, composable patterns over heavy frameworks)

---

*(End of PRD. The industrial-grade delivery roadmap is in `02-Production-Plan.md`.)*
