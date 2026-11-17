# T12: Conduct the authorized one-model research evaluation

Published: https://github.com/TalonExe/poisontrace/issues/31

Label: needs-info. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

After the user selects resources and authorizes spend, run the limited controlled study and report actual model performance across the final scenarios.

## Acceptance criteria

- [ ] External gate: user supplies or approves the exact live model/version, repetition count and spending limit and authorizes the live calls. Until then this ticket is needs-info and cannot execute.
- [ ] Use the completed protocol/corpus and repeated clean/attacked/defended groups with both attack families represented. Keep inputs/model settings fixed enough for the defined comparisons.
- [ ] Retain attributable trial-level outcomes/traces and safe provider/tool failures; report actual denominators, unavailable measurements, cost/usage when available and exclusions.
- [ ] Report verdict/priority/handling correctness, explicit attacker outcomes, marker observations separately, manifest decisions, duration/errors and limitations. Ineffective attacks/defenses are valid findings.
- [ ] Publish a local research-results summary/export; keep prior offline rehearsal artifacts clearly separate. Do not infer generality across models/providers or real SOC environments.
- [ ] One selected evaluated model is sufficient. Additional providers, defenses, attack families or participant studies are not required to complete this study.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/30: Verify the bounded software release and align research documentation

## Scope and verification

This is a research-evaluation task, not a software-release blocker. Do not make live calls until the explicit external gate is satisfied. Preserve synthetic-only/read-only tools, secrets safety and the approved narrow protocol; no deployment or external messages.
