# T02: Investigate one clean case through a real read-only MCP server

Published: https://github.com/TalonExe/poisontrace/issues/21

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher runs one deterministic clean case through actual MCP discovery and evidence retrieval, receives a structured evidence-based decision, and reopens the saved investigation.

## Acceptance criteria

- [ ] One trusted local synthetic SOC MCP server exposes read-only alert/evidence/context reads for one representative case. A pinned MCP client actually discovers schemas and invokes the server; emitting trace names alone does not satisfy this.
- [ ] A bounded scripted model substitute uses returned evidence before final verdict, P1-P4 priority, handling and evidence-referenced explanation. A controlled evidence change changes the scripted final decision while expected-case labels are not supplied as model instructions.
- [ ] Invocation carries server/tool identity and arguments. Actual results/errors, model continuation, final output and policy-relevant ordering persist and are visible through run detail and the available result interface.
- [ ] Define a narrow fixture and output contract sufficient for the later providers, attacks and scoring. Use an incremental compatibility path so existing adapters/scenarios/history remain usable; do not perform a wide rewrite.
- [ ] Tool processes have bounded calls/time/output and deterministic reset/cleanup. Their interface cannot modify incidents or invoke production response operations; permitted filesystem/network use is limited to the synthetic testbed.
- [ ] Invalid results, model/tool errors and time/call limits become safely classified saved attempts with unscored unavailable outcomes and returned IDs.
- [ ] An offline transport integration test proves the separate process really ran and returned evidence; application/API/persistence and user-visible inspection checks verify the complete clean path.

## Blocked by

None (can start immediately).

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
