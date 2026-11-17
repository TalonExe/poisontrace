# T04: Run evidence-based investigations with OpenAI

Published: https://github.com/TalonExe/poisontrace/issues/23

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher selects OpenAI and receives a structured evidence-based investigation through the same bounded MCP workflow.

## Acceptance criteria

- [ ] OpenAI implements the same tool-choice/result-continuation/final-output contract as the core, including evidence before the final recommendation.
- [ ] Single runs, campaigns and reruns forward the selected actual OpenAI model identifier consistently. The current provider-name-as-model discrepancy is covered by an offline regression check.
- [ ] Tool calls/results, model continuation and final structured output survive safe persistence/API and result inspection.
- [ ] Provider-specific parsing, refusal/incomplete output, malformed arguments and bounded-loop errors become safe attributable saved failures with unavailable security/task scores.
- [ ] Offline captured-request/response checks prove provider sequencing and actual model selection without keys, requests to the live provider or charges.
- [ ] Historical OpenAI records and the other provider remain readable/usable. Adding OpenAI support does not require a cross-model research study.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/21: Investigate one clean case through a real read-only MCP server

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
