# T08: Complete the fifteen-case synthetic research corpus

Published: https://github.com/TalonExe/poisontrace/issues/27

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher selects and investigates the complete reproducible 15-case corpus, with meaningful case diversity, expected outcomes and both retained attack families.

## Acceptance criteria

- [ ] The research corpus has exactly five benign-activity, five false-positive and five malicious incidents. Metadata conditions/attack variants do not count as additional incidents; existing legacy/smoke fixtures remain identifiable and preserved.
- [ ] Cases cover experimental P1-P4 across the corpus, with a short documented rubric and category definitions. Avoid cosmetic rewrites of a single alert.
- [ ] Authored versioned fixtures provide the authentication/endpoint/process/network/context/prior-case evidence needed by each incident. Expected decisions and evidence references agree with the fixtures.
- [ ] Explicit supported attacker goals and allocation of poisoning/shadowing cases make both families testable. A full cross-product of every case/attack is not mandatory.
- [ ] All cases load/validate, are selectable in the scenario interface, retrieve deterministic evidence through the trusted MCP server and produce reopenable structured results under offline model substitutes.
- [ ] Preserve scenario identities, invalid-file repair and failed-edit atomicity; add no general telemetry generator, production integration or standards-conformance project.
- [ ] Document corpus coverage and run deterministic corpus-level checks demonstrating all 15 are runnable, including benign/false-positive/malicious and every priority band.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/26: Score structured decisions and explicit attack goals

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
