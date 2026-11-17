# T01: Separate execution from saved-results review

Published: https://github.com/TalonExe/poisontrace/issues/20

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher launches experiments from a readable Dashboard and reviews saved runs, campaigns, rates and traces on a dedicated Results page, without losing existing workflows.

## Acceptance criteria

- [ ] The Dashboard keeps single-run/campaign configuration, launch, execution status and brief recent activity. Detailed history, rates and trace analysis move to Results.
- [ ] Results has authenticated navigation and reopenable run/campaign selection using real persisted identifiers; direct navigation/refresh and permission failures are handled.
- [ ] Overview and selected-result/trace views reuse existing components and API contracts. Preserve rate condition selection, expandable calculation notes and independently scrollable history where appropriate.
- [ ] Navigation from a completed or failed attempt opens its corresponding result, never a globally latest result.
- [ ] Loading, empty, failure and legacy/unavailable states remain readable on desktop/mobile and keyboard accessible, with the incumbent design system.
- [ ] Browser journeys verify execution-to-result navigation, run/campaign inspection, refresh and role boundaries. No new charts suite or approval workflow.

## Blocked by

None (can start immediately).

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
