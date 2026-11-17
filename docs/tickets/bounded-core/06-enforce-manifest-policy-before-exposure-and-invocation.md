# T06: Enforce manifest policy before exposure and invocation

Published: https://github.com/TalonExe/poisontrace/issues/25

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher compares clean, attacked and defended executions and can see which discovered definitions were withheld and which calls were rejected by the single manifest policy.

## Acceptance criteria

- [ ] Clean uses approved trusted metadata; attacked exposes the selected attack without manifest enforcement; defended validates all discovered definitions before constructing the model-visible context.
- [ ] Changed/unapproved definitions are withheld with server/tool-qualified reasons. Post-discovery proposed calls are checked against the same approved identity/definition boundary immediately before real invocation.
- [ ] Cover both attack paths, including a shadowing source whose malicious tool is never invoked. Also reject unknown/colliding qualified identities and invalid approved definitions without substituting attacked metadata for an empty trusted list.
- [ ] Persist discovered versus exposed metadata and separate discovery restriction, invocation rejection, executed call and no-call observations. Zero calls or marker absence is not invented blocking evidence.
- [ ] API/results explain observed restrictions and allow them to coexist with a wrong final decision. Do not fabricate a safe fallback or correct recommendation after rejection.
- [ ] Offline policy and transport integration tests prove withheld metadata never reaches the model and rejected calls never reach either server, while legitimate clean calls still retrieve evidence.
- [ ] Manifest comparison remains the only defense. No scanner, second-model validator, signature/hash system or layered-defense framework is added.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/24: Demonstrate poisoning and cross-server shadowing

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
