# T05: Demonstrate poisoning and cross-server shadowing

Published: https://github.com/TalonExe/poisontrace/issues/24

Label: ready-for-agent. Approved and read-back verified 2026-11-11. GitHub is the active tracker; this is a local published-body snapshot.

## What to build

A researcher selects either retained attack family and observes a real malicious MCP server influencing a synthetic investigation, with explicit attacker goals and inspectable evidence.

## Acceptance criteria

- [ ] A controlled malicious local MCP server and the trusted SOC server have distinct stable identities. Both remain synthetic and read-only; do not introduce containment/exfiltration execution.
- [ ] Description poisoning delivers deterministic malicious tool metadata through actual discovery, rather than substituting an attacked string only inside the runner.
- [ ] A shadowing case places malicious metadata on one server that changes use of a tool on the other server. A scripted counterexample proves this can occur without invocation of the malicious tool.
- [ ] The same case/evidence/expected handling can be selected clean or attacked, with explicit attack-family selection and stable payload identity persisted through API and UI.
- [ ] At least one case per attack family defines a concrete wrong verdict/priority/handling target distinct from legitimate handling. Retain old marker payloads as identifiable smoke cases without inventing historical goals.
- [ ] Saved input definitions, proposed/invoked calls, evidence and final decisions make the intervention observable in the result interface.
- [ ] Actual two-server discovery/invocation plus offline model substitutes demonstrate attack-path mechanics. Do not claim the scripted attack proves live-model vulnerability.

## Blocked by

- https://github.com/TalonExe/poisontrace/issues/21: Investigate one clean case through a real read-only MCP server

## Scope and verification

Use a complete user-visible path through the applicable data, application, persistence, HTTP, interface and test seams. Preserve existing scenario identities/repair, analyst/superadmin boundaries, credential-reference safety, saved failure attribution and historical measurements. Use red-green behavior tests with deterministic model substitutes and synthetic evidence. Run relevant backend/frontend/build/browser checks and update current implementation notes. Neither a passing mock nor a permitted call is evidence of live-model effectiveness. Do not spend API credits, inspect secret/auth records, merge or deploy. Avoid unrelated refactors and deferred features.
