# Bounded-core ticket plan

Approved and published 2026-11-11. The user approved ticket granularity and blocking edges. All twelve issues were created in TalonExe/poisontrace and read back to verify exact titles, full bodies, open state, labels and dependency references. No existing/parent issue was modified. Application implementation and paid experiments remain unrequested.

T identifiers are stable planning aliases; use the real GitHub issues below for implementation. Local Markdown files are publication snapshots, not a second active tracker. Machine-readable mapping is [publication.json](tickets/bounded-core/publication.json).

## Published slices

| Alias | GitHub issue | Blocked by | Completion coverage | Label | Local snapshot |
| --- | --- | --- | --- | --- | --- |
| T01 | [#20: Separate execution from saved-results review](https://github.com/TalonExe/poisontrace/issues/20) | None | F08, F09 | ready-for-agent | [Body](tickets/bounded-core/01-separate-execution-from-saved-results-review.md) |
| T02 | [#21: Investigate one clean case through a real read-only MCP server](https://github.com/TalonExe/poisontrace/issues/21) | None | F02, F03, F07, F09 | ready-for-agent | [Body](tickets/bounded-core/02-investigate-one-clean-case-through-a-real-read-only-mcp-server.md) |
| T03 | [#22: Run evidence-based investigations with Gemini](https://github.com/TalonExe/poisontrace/issues/22) | [#21](https://github.com/TalonExe/poisontrace/issues/21) | F06, F07, F09 | ready-for-agent | [Body](tickets/bounded-core/03-run-evidence-based-investigations-with-gemini.md) |
| T04 | [#23: Run evidence-based investigations with OpenAI](https://github.com/TalonExe/poisontrace/issues/23) | [#21](https://github.com/TalonExe/poisontrace/issues/21) | F06, F07, F09 | ready-for-agent | [Body](tickets/bounded-core/04-run-evidence-based-investigations-with-openai.md) |
| T05 | [#24: Demonstrate poisoning and cross-server shadowing](https://github.com/TalonExe/poisontrace/issues/24) | [#21](https://github.com/TalonExe/poisontrace/issues/21) | F02, F04, F07 | ready-for-agent | [Body](tickets/bounded-core/05-demonstrate-poisoning-and-cross-server-shadowing.md) |
| T06 | [#25: Enforce manifest policy before exposure and invocation](https://github.com/TalonExe/poisontrace/issues/25) | [#24](https://github.com/TalonExe/poisontrace/issues/24) | F05, F07, F09 | ready-for-agent | [Body](tickets/bounded-core/06-enforce-manifest-policy-before-exposure-and-invocation.md) |
| T07 | [#26: Score structured decisions and explicit attack goals](https://github.com/TalonExe/poisontrace/issues/26) | [#24](https://github.com/TalonExe/poisontrace/issues/24) | F01, F07, F09 | ready-for-agent | [Body](tickets/bounded-core/07-score-structured-decisions-and-explicit-attack-goals.md) |
| T08 | [#27: Complete the fifteen-case synthetic research corpus](https://github.com/TalonExe/poisontrace/issues/27) | [#26](https://github.com/TalonExe/poisontrace/issues/26) | F01, F03, F04, F07, F09 | ready-for-agent | [Body](tickets/bounded-core/08-complete-the-fifteen-case-synthetic-research-corpus.md) |
| T09 | [#28: Run repeatable matched groups and compare them on Results](https://github.com/TalonExe/poisontrace/issues/28) | [#20](https://github.com/TalonExe/poisontrace/issues/20), [#25](https://github.com/TalonExe/poisontrace/issues/25), [#26](https://github.com/TalonExe/poisontrace/issues/26) | F07, F08, F09 | ready-for-agent | [Body](tickets/bounded-core/09-run-repeatable-matched-groups-and-compare-them-on-results.md) |
| T10 | [#29: Prepare the evaluation protocol and complete an offline rehearsal](https://github.com/TalonExe/poisontrace/issues/29) | [#27](https://github.com/TalonExe/poisontrace/issues/27), [#28](https://github.com/TalonExe/poisontrace/issues/28) | F01, F07, F08, F10 | ready-for-agent | [Body](tickets/bounded-core/10-prepare-the-evaluation-protocol-and-complete-an-offline-rehearsal.md) |
| T11 | [#30: Verify the bounded software release and align research documentation](https://github.com/TalonExe/poisontrace/issues/30) | [#22](https://github.com/TalonExe/poisontrace/issues/22), [#23](https://github.com/TalonExe/poisontrace/issues/23), [#29](https://github.com/TalonExe/poisontrace/issues/29) | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10 | ready-for-agent | [Body](tickets/bounded-core/11-verify-the-bounded-software-release-and-align-research-documentation.md) |
| T12 | [#31: Conduct the authorized one-model research evaluation](https://github.com/TalonExe/poisontrace/issues/31) | [#30](https://github.com/TalonExe/poisontrace/issues/30) | Research demonstration, separate from software F01-F10 | needs-info | [Body](tickets/bounded-core/12-conduct-the-authorized-one-model-research-evaluation.md) |

## Work frontier and scope

Initial frontier is [#20](https://github.com/TalonExe/poisontrace/issues/20) and [#21](https://github.com/TalonExe/poisontrace/issues/21). They are independent. The UI split can reuse current results; the first MCP investigation can use the currently available inspection interface. Choose one when implementation is requested; neither ticket authorizes parallel agents automatically.

Provider tickets independently build on the working investigation contract. Attack paths then enable the manifest and scoring branches. The 15-case corpus follows scoring; repeated comparisons need Results, policy and scoring. Protocol/offline rehearsal combines the full corpus and comparisons. Software readiness waits for both provider implementations and the rehearsal.

[#31](https://github.com/TalonExe/poisontrace/issues/31) is the separate live evaluation, labelled needs-info. It requires the completed software plus user-approved model/version, repetitions, spending cap and explicit authorization of live calls. It never blocks calling the software complete. ready-for-agent means a specified ticket can be picked once its prerequisites are complete, not that every ticket is unblocked or API spending is authorized.

Each behavior ticket owns its complete applicable data/application/persistence/API/interface/test path. No independent broad prefactor was justified by the inspected architecture. Keep the first clean MCP path incremental and compatible. If a genuinely wide mechanical migration becomes necessary, propose expand/migrate/contract rather than breaking every caller at once.

[SCOPE_REFINEMENT.md](SCOPE_REFINEMENT.md) defines the smaller agreed boundary and F01-F10 checks. [ADR 0004](adr/0004-bounded-research-core.md) records the breadth-versus-completion trade-off. The original PDF audit remains historical evidence against the original promises, not the new release backlog.

## Dependency representation and verification

Every issue contains exact Blocked by issue links, created in dependency order. Native GitHub blocking relationships were not created. The connected GitHub tools expose issue creation/update but no dependency mutation; a read-only CLI connectivity check failed because this environment blocks its connection to GitHub. This is a tooling limitation, not absent native GitHub functionality. The [GitHub dependency API](https://docs.github.com/en/rest/issues/issue-dependencies) documents the native option for a later environment with permitted access. Do not claim textual links are native edges.

The readback verified all twelve bodies and labels, and all fifteen textual dependency edges. Do not recreate the issues or ask for breakdown approval again. Refresh current issue bodies/comments and blocker completion before implementation. No parent issue was supplied, so none was invented or attached.

## Preserved baseline

Issues #15-#19 were previously fetched in full with all comments: open, ready-for-agent, zero comments at inspection, despite their slice-one implementation being present in the uncommitted working tree. They were left unchanged. Their open labels do not mean they need reimplementation. Earlier marker-only issue wording has historical semantics; preserve current independent outcomes instead.

[NEXT_SESSION_HANDOFF_BOUNDED_CORE.md](NEXT_SESSION_HANDOFF_BOUNDED_CORE.md) contains the copyable next-session prompt, reading order, uncommitted baseline, agreed exclusions, source/test context and live-evaluation gates. Scope/ticket approval does not itself start implementation, spend credits, merge or deploy.
