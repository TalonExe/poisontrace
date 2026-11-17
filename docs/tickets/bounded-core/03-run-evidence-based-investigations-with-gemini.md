# T03: Run evidence-based investigations with Gemini

Published: https://github.com/TalonExe/poisontrace/issues/22

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher selects Gemini, runs the bounded MCP investigation and inspects a structured final decision based on returned tool evidence.

## Acceptance criteria

- [ ] Gemini implements the agreed discovery/tool-choice/result-continuation/final-output contract without returning a final recommendation before evidence feedback.
- [ ] The selected configured Gemini model is forwarded consistently from single runs, applicable batch/repeat execution and reruns; credentials remain private references.
- [ ] Capture actual tool-result messages and final structured output in safe persisted trace/detail, readable through the existing result presentation.
- [ ] Malformed decisions, unknown tools, unsupported arguments, empty responses and bounded-loop failures retain safe attributable failure records.
- [ ] Offline SDK client substitutes verify request/response sequencing, evidence feedback, selected model/settings and structured fields. Do not substitute a scripted response for claimed live-model effectiveness.
- [ ] Existing Gemini workflows and non-network tests remain compatible. No live-provider calls are required to complete this implementation ticket.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/21: Investigate one clean case through a real read-only MCP server

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
