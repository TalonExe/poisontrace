# T07: Score structured decisions and explicit attack goals

Published: https://github.com/TalonExe/poisontrace/issues/26

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher authors expected case decisions and attack targets, then sees independent correctness, goal achievement, evidence-reference validity and policy observations in saved results and rates.

## Acceptance criteria

- [ ] Case validation/editor support expected verdict, P1-P4 priority, handling and explicit supported attacker predicates. False-positive dataset category remains separate from the benign/malicious verdict.
- [ ] Persist and expose verdict, priority and handling correctness independently, plus explicit goal outcome for attacked trials; unrelated wrong decisions are not automatically attacker success.
- [ ] Validate evidence references against evidence actually returned in the attempt. Report invalid/missing references without pretending to verify all natural-language reasoning.
- [ ] Keep exact raw-output marker influence separate. Missing attack ground truth, clean attacker outcomes, failed attempts and incompatible historical measurements remain unscored/not applicable.
- [ ] Counts/denominators and scoring versions distinguish new decisions from recommendation-v1 equality and legacy marker semantics. Include observed discovery restrictions/call rejections only where actual evidence exists.
- [ ] Persisted/API/result presentation and aggregate rates use consistent meanings. Saved failures enter reliability denominators; configuration rejections remain separate.
- [ ] Counterexamples cover correct output with marker, attacker target without marker, wrong-but-not-target output, invalid references, withheld definitions versus rejected invocation, and historical/unavailable cases.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/24: Demonstrate poisoning and cross-server shadowing

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
