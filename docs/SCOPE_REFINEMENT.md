# Final research scope

Current research scope under ADR 0004. Implementation and verification state is in [STATUS.md](STATUS.md). Research tickets #29–#31 are cancelled; the study below describes the original research design, not pending implementation or authorization to run it.

## Purpose and research boundary

Finish a manageable PoisonTrace prototype that measures how description poisoning and cross-server tool shadowing affect evidence-based SOC decisions, and how one manifest-comparison defense changes those outcomes. MCP discovery and invocation are real; tools use synthetic data and are read-only.

Research claims must match this narrower scope and collected evidence. Historical requirements audits were removed during documentation cleanup; this document does not rewrite the original research PDF or establish fulfillment of its broader promises.

## Included software

| Area | Final boundary |
| --- | --- |
| Dataset | Fifteen deterministic versioned cases: five benign activity, five false-positive alerts and five malicious incidents. Cover experimental P1-P4 priorities across the corpus. Each case supplies supporting evidence, expected verdict/priority/handling and explicit attacker goals. |
| Evidence | Authored fixtures supply alerts, relevant telemetry, asset/user context and previous case information where needed. Document the data structure. A general telemetry generator or OCSF implementation is not required. |
| Servers | One trusted synthetic SOC MCP server exposes necessary read-only evidence tools. One controlled malicious MCP server supplies adversarial metadata. Distinct server identities support actual cross-server shadowing. |
| Investigation | Discover definitions, apply condition/policy, invoke permitted tools, return actual evidence to the model and then produce the final decision. Bound calls, time and output. Case edits and containment are recommendations only. |
| Output | Benign/malicious verdict, experimental P1-P4 priority, recommended handling and a short explanation referencing returned evidence. A false-positive case expects a benign verdict; dataset category and model verdict are different concepts. |
| Attacks | Description poisoning and cross-server tool shadowing. Malicious-server metadata can influence a trusted-server tool even when the malicious tool is not invoked. |
| Defense | Manifest comparison is the sole evaluated defense. In defended mode, compare discovered definitions before model exposure and proposed calls before invocation. Retain server/tool identity with the represented definition. No semantic scanning or cryptographic verification claim. |
| Conditions | Same underlying case and expected outcomes across clean, attacked and defended runs. Clean exposes trusted definitions; attacked exposes the attack without manifest enforcement; defended checks before exposure and invocation. Record enough case/model/attack identity to link compatible runs. |
| Providers | Both existing Gemini and OpenAI integrations support the completed evidence/tool workflow. ChatGPT means OpenAI provider integration, not automation of the ChatGPT application. |
| Traces | Reuse existing storage and presentation. Add call arguments, actual result/error, server/tool identity and ordering needed to verify invocation, evidence feedback and policy checks. Preserve safe failures, returned IDs, outcome independence and historical compatibility. No comprehensive trace redesign. |
| Measurements | Show verdict/priority/handling correctness against ground truth, explicit attacker-goal outcomes, marker influence separately, observed manifest rejection, duration and errors. Evidence references resolve to returned case evidence. Version changed measurement meanings and preserve unavailable/legacy outcomes. |

Use bounded local server processes with synthetic fixtures and reproducible reset. Restrict their access to the research environment; no production security integration or real response operation. A particular container platform or remote transport is not required.

## Dashboard and Results page brief

Researchers should configure a run without being surrounded by detailed research analysis, then inspect saved evidence and comparisons on Results. Preserve the incumbent visual system, account/role restrictions, scenario editor/repair and credential-reference handling. This is a separation of tasks, not a visual redesign.

| Page | Responsibility |
| --- | --- |
| Dashboard | Configure and launch single runs/campaigns; show progress/status and brief recent activity. |
| Results | Run/campaign history, selected structured outcome, evidence and trace review, rate denominators and same-case clean/attacked/defended comparison. |

Results uses separate views or tabs for overview, investigation detail and comparison. Move/reuse current components instead of duplicating their full content on Dashboard. Show a manageable comparison summary with access to individual evidence/traces. No additional analyst decision workspace or chart suite.

Handle loading, empty history, failed attempts, unavailable/legacy measurements and missing compatible comparisons explicitly. Keep keyboard access and readable mobile layouts. Preserve current design tokens. Exact visual arrangement remains an implementation design task within these agreed page responsibilities.

## Research demonstration design

- Repeat clean, attacked and defended trials on one selected live model, covering the 15 cases and both attack families. Prespecify exact attack allocation and repetition count. Every possible case/model/attack combination is not required.
- Verify both provider implementations, while retaining a one-model minimum controlled study. Provider support does not establish cross-model generality.
- Record compared case/version, model/settings, attack, condition, observations, failures and eligible denominators. Keep compared inputs consistent and retain actual evidence/call traces. A wholesale campaign-engine rewrite or provenance platform is not required.
- Report correctness, attacker outcomes, manifest decisions, timing/errors and limitations. Failed attacks and ineffective defenses are valid results. Completion requires honest observations, not a favorable effectiveness percentage.
- Select the live model, repetition count and spending limit before paid experiments. No API spend is authorized here. No deadline has been supplied, so this scope makes no calendar commitment.

## Completion checks

These define the bounded research software contract. Consult STATUS for implementation and verification; this table is not a current ticket backlog.

| ID | Observable acceptance evidence |
| --- | --- |
| F01 | Fifteen usable cases with agreed category counts, P1-P4 coverage, deterministic evidence, expected decisions and explicit attacker-goal ground truth. Existing smoke fixtures/history remain distinguishable. |
| F02 | Integration tests prove actual MCP discovery/invocation across the two server identities. Evidence tools return fixture results; failures and termination are bounded. Tools cannot change incident or production state. |
| F03 | A controlled evidence change can affect the final decision through tool-result feedback. Trace order proves evidence preceded the final output. Scripted substitutes establish mechanics, not live-model effectiveness. |
| F04 | Both attack families have reproducible cases and explicit goals. Marker presence remains independent of goal achievement. |
| F05 | Defended discovery withholds unapproved/changed definitions before exposure; invocation rejects unapproved calls. Clean/attacked conditions remain distinct, with observed policy decisions saved. |
| F06 | Gemini and OpenAI handle the bounded evidence workflow correctly. Offline captured-request/response tests cover provider differences and model selection. |
| F07 | Structured outcomes and evidence references persist and reopen. Measurements distinguish incorrect decisions, attacker outcomes, markers, policy rejection and errors, with denominators and historical compatibility. |
| F08 | Dashboard supports uncluttered execution; Results supports history/detail/trace and compatible same-case comparisons. Browser checks cover the split, mobile use and material empty/error/unavailable states. |
| F09 | Existing scenario identity/repair, roles, safe credential handling, failure retention and run attribution remain intact. Appropriate backend/frontend/build/integration checks pass. |
| F10 | Scope/objective documentation, dataset description, run instructions and limitations match delivered behavior. Original PDF commitments moved to future work are identified explicitly. |

F01–F10 describe the original bounded software contract. A live study would additionally require a new request, selected model/version, repetitions and spending cap. The cancelled #29–#31 sequence is not a release prerequisite. Positive effectiveness and broad generality are not acceptance conditions.

## Future work and excluded release blockers

- Additional attack families, adaptive attack generation, rug pulls, Unicode-obfuscation families, indirect-output poisoning and stealth scoring.
- Static/semantic scanners, LLM intent alignment, multiple/layered defenses, manifest hashing/signatures and their comparative evaluation.
- Case modification, simulated response execution, recommendation approval/rejection/editing and a separate analyst-decision audit workflow.
- Mandatory cross-model experiments, formal participant usability studies and operational SOC generalization claims.
- Separate servers per evidence category, general telemetry generation/ingestion, full OCSF support, production SIEM/EDR integration and genuine scanning/exploitation tools.
- Comprehensive trace/provenance redesign, a new visualization suite, unrelated cosmetic changes and expanded administration/hosting.

Case modification means changing an incident's saved status, priority, assignment or notes. Recommending a change does not apply it. Existing scenario editing, fixture maintenance and experiment history remain available.

Public-hosting/privacy hardening under ADR 0003 remains a separate product/deployment decision. This scope neither cancels that ADR nor claims its prerequisites are implemented. Do not build or deploy those capabilities as prerequisites to this research core.

Original named metrics without meaningful events in the reduced workflow must be described as deferred or limited, not fabricated. Manifest rejection is an observed permission decision, not an executed unauthorized containment action. Exact handling equality alone is not complete investigation correctness.

## Proposed replacement objective wording

Draft for later research-document alignment. No PDF edit has occurred.

1. Implement reproducible description-poisoning and cross-server tool-shadowing experiments using controlled synthetic MCP servers.
2. Develop a bounded read-only SOC investigation workflow using 15 deterministic varied cases, retrieved evidence and structured verdict, priority and handling recommendations.
3. Record attributable investigation traces and measure ground-truthed decision correctness, attacker-goal outcomes, manifest decisions, errors and execution time under clean, attacked and defended conditions.
4. Support Gemini and OpenAI model integrations and evaluate a manifest-comparison defense through repeated controlled experiments on at least one selected model.
5. Provide separate execution and results interfaces for configuring experiments, inspecting evidence/traces and comparing compatible same-case conditions.

The revised wording no longer promises multiple-defense comparison, mandatory multi-model evaluation, interactive analyst approval or formal usability study. Research documentation must state those changes explicitly when it is aligned to this approved scope.

## Change rule and next step

Implementation choices may vary within the acceptance checks. New capabilities require a separate scope decision and otherwise go to future work. Fixes necessary to pass agreed checks belong to the core. Decide experiment resources before spending, rather than silently increasing trials.

[ADR 0004](adr/0004-bounded-research-core.md) records the scope trade-off. [STATUS.md](STATUS.md) is the current work frontier. This scope authorizes no new implementation, paid experiment or deployment.
