# Next-session prompt: audit PoisonTrace against the research PDF

Prepared 2026-11-11 after slice one and the rates/history UI refinements. This replaces the earlier handover for the pre-slice research review.

## Task

I want a detailed, understandable assessment of whether every aspect promised in my research PDF is present in the current PoisonTrace system. Audit the actual working tree, not just the last commit or the earlier review. Explain what works, what is simulated or incomplete, what is absent, and what exists without enough research evidence. Complete the review before proposing implementation. This request authorizes an audit and documentation, not application changes or automatic implementation of slice two.

Workspace: `C:\Users\TalonExe\Documents\FYP-implementation\Project`

Expected branch: `testing/slice-1-matched-conditions-and-scoring`

Research source: `C:\Users\TalonExe\Documents\FYP-implementation\Havyn Liew Investigation Report.pdf`, also `../Havyn Liew Investigation Report.pdf` from Project.

## Start in this order

1. Inspect branch, Git status, current diff and new files. Preserve existing work. At handover, HEAD remains `3a3bc6dd640c04d8d6292b51ff205fc99d5e1f33`, the pre-slice checkpoint. The slice-one implementation and subsequent UI refinements are uncommitted modified/untracked files. Reviewing HEAD alone misses them. Recheck local/remote state rather than assuming this is still true.
2. Read `AGENTS.md`, then its required documents in order: `docs/CONTEXT.md`, `docs/DOMAIN_GLOSSARY.md`, `docs/IMPLEMENTATION_BRIEF.md`, `docs/ARCHITECTURE.md`, and the latest entries in `docs/STATUS.md`.
3. Read `docs/ARCHITECTURE_RULES.md`, `docs/adr/`, `docs/RESEARCH_OBJECTIVES_REVIEW.md`, `docs/research/IMPLEMENTATION_REVIEW_EVIDENCE.md`, and `docs/research/SLICE_ONE_MEASUREMENTS.md`.
4. Read the PDF itself using the PDF skill and available extraction/rendering tools. Verify the document before citing it. Tooling availability may differ from the older handover; keep temporary review tools out of application dependencies.
5. Build a requirement inventory from the PDF before assigning verdicts. Then inspect source, tests, analyst workflows and safe research artifacts for each item.

PDF identity rechecked at handover: SHA-256 `90D3949DA9A402E97A6834F0169FA94096EA1BC1061C5347025D215717F9C82F`, 2,775,223 bytes. The earlier review recorded 118 pages. Verify page count and use one-based PDF page positions plus zero-based indices; distinguish printed numbering if present.

## Audit the full research commitment

Extract atomic requirements across objectives, research questions if explicitly stated, scope, threat model, proposed technical design, evaluation methodology and promised deliverables. Split compound requirements so a working UI or adapter cannot conceal a missing execution step. Give every requirement an ID and a PDF page/section reference.

Use the earlier page references as navigation aids, then verify the complete source passages:

- p15 contains the five objectives.
- pp16-22 describe scope, requirements and validity boundaries.
- p60 describes the proposed technical design/MCP approach.
- p72 repeats objectives with expanded threat-model and defense wording.
- pp91-92 connect findings to policy outcomes and trace reproducibility.

Inspect the rest of the report for additional commitments and qualifications. Distinguish requirements for this project from literature descriptions, interview findings, examples, optional suggestions and future work. Explain any conflict between versions of the objectives, including the expanded p72 wording. Interview questions are not automatically research questions. Literature benchmark percentages are not PoisonTrace results.

Ensure the inventory covers, where required by the PDF:

- Reproducible poisoning, shadowing, impersonation/name collisions, attacker control and trust boundaries.
- Dataset/scenario count and diversity, benign/false-positive/malicious cases, priorities, expected handling, attack goals and telemetry schema/categories.
- Synthetic telemetry generation, normalization, storage/retrieval, SIEM/context/case tools and evidence references.
- MCP discovery and transport, actual invocation, server separation, controlled malicious servers and process/container isolation.
- Agent investigation steps, evidence-result feedback, verdict, priority, escalation and structured report outputs.
- Defense placement, manifest integrity/hashing/signatures, metadata scanning, semantic/intent checking, runtime policy, independent/layered controls and human approval/review.
- Matched conditions, repeats, model coverage, version/configuration provenance, frozen inputs, failure handling and reproducibility.
- Each named metric and its meaning, ground truth, numerator, denominator, exclusions, unavailable cases and historical compatibility.
- Trace completeness: model inputs/settings, definitions, proposed calls/arguments, actual results, policy decisions, approvals, timestamps, errors and final recommendations.
- Dashboard configuration, execution, evidence/trace review, comparative visualization and analyst decision workflows.
- Empirical model evaluation, security/utility tradeoffs, uncertainty where promised, usability study, participant evidence and final research documentation.

These are coverage prompts, not a replacement specification. Add any PDF requirements missing from this list, and identify items the PDF does not actually require. Keep later hosting/authentication product requirements separate unless the PDF connects them to the research.

## Current changes to verify, not assume

The 2026-11-10 review assessed all five objectives as partially fulfilled. It describes pre-slice behavior and is dated historical evidence. The report's objectives have not been formally reduced or revised. Determine the current verdicts afresh.

Approved issues #15-#19 were implemented in the working tree:

- Matched inputs: clean selects trusted definitions; poisoned/defended select discovered attacked definitions. Clean/defended enable the manifest policy; poisoned disables it. Effective safe definitions and condition provenance are retained. Explicitly empty trusted lists are not replaced with attacked metadata.
- Independent recommendation-v1 scoring: exact raw-output marker influence, explicit attacker-target recommendation matches, and legitimate recommendation correctness are separate nullable outcomes. Clean attacker outcomes and missing attack ground truth are unscored. Existing runtime payloads remain marker smoke cases with null attacker targets.
- gateway-v1 observations record actual manifest checks, mismatch detection, call rejection and reasons. Allowed permissions are labeled simulated. No-call and disabled-enforcement paths are explicit; marker absence does not establish blocking.
- Started failures retain safe categories, elapsed time, available traces and unscored security/task outcomes. Execution returns saved run IDs directly for run/campaign/rerun attribution. SQLite uses an additive outcome_evidence column; historical records remain readable with legacy semantics.
- Revised rates report counts and denominators by condition, exclude incompatible historical security/task measurements and include saved failures in system-error rates. Campaign metrics include retained rerun attempts. Configuration errors remain separate from started attempts.
- Run and campaign rates now use condition selection and groups for Model outcomes, Gateway decisions and Reliability. Calculation notes are expandable. Campaign history scrolls independently, with its heading and run action outside the scroll area.

Read `SLICE_ONE_MEASUREMENTS.md` for exact formulas and compatibility rules. If using GitHub acceptance criteria as evidence, fetch each relevant issue's current full body and comments from `TalonExe/poisontrace`. A ticket's implementation claim, label or open/closed state is not a fulfillment verdict for the research.

The known execution boundary remains central: the model generates its recommendation before the gateway decision. The gateway executes no external MCP tool, retrieves no evidence and returns no evidence result to the model. Recommendation correctness is exact recommendation equality, not demonstrated evidence-based investigation. A call rejection can coexist with manipulated output. Inspect these facts directly and assess them against the PDF.

Actual MCP execution/evidence feedback remains proposed slice-two work, not completed capability. Pre-exposure enforcement, new defenses, balanced multi-model campaigns, new comparison workspaces and deployment/auth redesign were outside slice one. Earlier discussion of reducing commitments was not a formal change to the report.

## Evidence and verdict rules

For every requirement, identify:

1. What the PDF asks for, with a short compliant excerpt or faithful paraphrase and page/section.
2. What the current system does, with current source paths and line numbers plus the relevant user workflow.
3. Whether the implementation is real execution, simulation, interface only, documentation only or absent.
4. Relevant named tests and what they prove, including what their substitutes cannot prove.
5. Actual research artifacts supporting effectiveness, utility, comparison or usability, or an explicit evidence gap.
6. The practical gap and the smallest change or evaluation needed to close it.

Keep implementation status separate from validation status. Use implementation labels `present`, `partial`, `absent` or `unclear`, with an execution-kind qualifier. Use evidence labels `demonstrated`, `partially demonstrated`, `not demonstrated` or `not applicable`. Summarize objectives using `fulfilled`, `partially fulfilled`, `not implemented` or `not yet demonstrated`, explaining the chosen label.

A provider adapter is not a completed multi-model evaluation. A trace event is not proof that a tool executed. A selectable defended mode is not proof of effective prevention. Offline tests demonstrate implementation behavior, not live-model effectiveness. Missing experiments do not automatically mean that a software feature is absent.

Inspect historical artifacts only through safe, non-secret fields/aggregates. Never inspect credential stores, decrypt keys or print authentication records. The previous review's database counts are historical; do not present them as current without rechecking. Scratch captures/comparison databases and mocked browser fixtures are not empirical research datasets.

## Deliverables

Write `docs/RESEARCH_REQUIREMENTS_AUDIT.md` with:

1. A plain-language answer to whether all requested aspects are present, followed by a verdict for each of the five objectives.
2. A complete requirement matrix with requirement ID, PDF reference, expected behavior, actual behavior/execution kind, implementation status, current source/test evidence, empirical evidence/validation status, gap and next action. Group rows by objective or subsystem for readability.
3. One traced representative investigation showing the actual input, model completion, proposed call, policy decision, persisted outcome and analyst-visible result. Mark the exact points where the PDF promises more than the implementation performs. Use synthetic offline inputs and clearly identify substitutes.
4. A change-since-review section explaining which previous deficiencies slice one resolved, narrowed or left unchanged. Check the old review row by row rather than repeating its verdicts.
5. A prioritized gap list separating missing software, insufficient experimental evidence, documentation ambiguity and remaining usability/evaluation work. Give a small verifiable next slice for each high-priority gap without silently narrowing the objectives.
6. A short list of targeted questions only where the PDF/session genuinely leaves a decision unresolved. Finish assessable work before asking them.
7. Verification commands/results, examined revision/working-tree state and limitations of this audit.

Keep the original dated review/evidence files intact. Add a pointer to the new audit if useful. Update `docs/STATUS.md` with the audit outcome and next recommendation. In the final response, explain the findings in ordinary language, not just a large technical matrix. Include a compact Present / Partial or simulated / Missing / Not yet demonstrated summary.

Completion requires a mapped assessment for every explicit project requirement found in the PDF, traceable evidence for each verdict or an explicit evidence gap, and a coverage check that no inventory item was silently dropped. Do not stop at five high-level objective labels or a feature inventory.

## Verification and boundaries

Latest checks at handover: 165 backend tests passed with an existing Starlette/httpx warning; 34 frontend tests passed; Vite production build passed; eight focused mocked browser journeys passed with clean exit. They cover slice-one outcomes, scenario-target editing, rate readability, history scrolling and existing redesign flows. They are not a full backend-integrated e2e or live-provider pass. Recheck only what the audit needs and report what was actually run.

From Project:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q backend/src backend/tests
$env:PATH='C:\Users\TalonExe\AppData\Local\Author Software\nvm\installs\v22.19.0;'+$env:PATH
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend exec -- playwright test e2e/slice-one.spec.js e2e/redesign.spec.js --config=frontend/playwright.config.js --global-timeout=60000
```

Use synthetic data and offline provider substitutes. Preserve all existing application changes, identities, scenario repair behavior, historical records and analyst/superadmin restrictions. Do not call live providers, spend API credits, send external messages, merge, deploy, rewrite the PDF or change research objectives. Application fixes and slice two require a subsequent implementation request; this session's deliverable is the evidence-based audit and clarification.
