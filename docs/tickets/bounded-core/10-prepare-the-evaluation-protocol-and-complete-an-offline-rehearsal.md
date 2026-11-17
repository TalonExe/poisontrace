# T10: Prepare the evaluation protocol and complete an offline rehearsal

Published: https://github.com/TalonExe/poisontrace/issues/29

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher can reproduce a no-cost rehearsal over the final corpus and has a concrete protocol ready for a separately authorized one-model live evaluation.

## Acceptance criteria

- [ ] Define the 15-case coverage, both attack families, clean/attacked/defended comparisons, repeated-trial procedure and failure/exclusion rules. Record that one evaluated model is sufficient and both providers remain supported.
- [ ] Keep exact live model, repetition count and spending cap explicit pending decisions when not supplied. A rehearsal count is not an approved research sample size or spend authorization.
- [ ] Use the actual MCP transport and deterministic provider substitutes to rehearse the planned groups, including a safe failure, missing outcome and independent marker/goal observations.
- [ ] Produce a safe trial-level result export and readable summary with case/version/model/settings/attack/condition/repeat, trace associations, observed outcomes and eligible counts. No secrets/auth records enter exports.
- [ ] Check that fixtures/definitions/settings used by compared trials are consistent and that each required case/condition is represented; show why any trial is excluded.
- [ ] Clearly label rehearsal artifacts as synthetic implementation verification, not live-model research results. Record exact commands and limitations without claiming effectiveness or cross-model generality.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/27: Complete the fifteen-case synthetic research corpus
- https://github.com/TalonExe/poisontrace/issues/28: Run repeatable matched groups and compare them on Results

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
