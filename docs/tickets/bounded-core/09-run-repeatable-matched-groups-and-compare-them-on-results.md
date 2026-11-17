# T09: Run repeatable matched groups and compare them on Results

Published: https://github.com/TalonExe/poisontrace/issues/28

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher runs repeated clean, attacked and defended investigations of the same case and compares compatible persisted outcomes on Results.

## Acceptance criteria

- [ ] Create an explicit linked run group with selected case/version, attack family, one provider/model, condition schedule and positive repeat count. Preserve selected inputs/evidence/targets across its conditions and keep each attempt directly attributable.
- [ ] The run group executes all requested conditions/repeats and retains failures, safe errors and unavailable outcomes. A rerun creates/retains a separate attempt rather than erasing evidence.
- [ ] The research corpus is selected explicitly rather than only by the historical poisoned-filename rule. Preserve the existing campaign/history compatibility path without a wholesale scheduling/worker rewrite.
- [ ] Results compares verdict, priority, handling correctness, attacker outcome, observed policy restriction/rejection, duration and errors, with links to individual evidence and traces.
- [ ] Group by compatible case/model/attack/input/scoring conditions; do not silently compare a changed incident, incompatible historical data or arbitrary pooled history as a matched experiment.
- [ ] Expose counts, denominators, missing conditions, failed attempts and unavailable values. Keep configuration/execution on Dashboard and detailed rates/comparison on Results.
- [ ] Use deterministic offline repeated runs and browser/API/persistence checks to verify the full group, reload and comparison journey. Real API spending is outside this ticket.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/20: Separate execution from saved-results review
- https://github.com/TalonExe/poisontrace/issues/25: Enforce manifest policy before exposure and invocation
- https://github.com/TalonExe/poisontrace/issues/26: Score structured decisions and explicit attack goals

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
