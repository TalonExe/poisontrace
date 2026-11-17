# Matched investigation groups

Implemented locally for issue #28, 2026-11-17. These are offline implementation checks, not a live-model study. The existing metadata campaign still uses its historical poisoned-filename selection and retains its history. Research groups select a corpus case explicitly.

## Configure, run and reopen

Open Experiment using a saved configuration, choose Matched group, then select a synthetic case, provider, conditions and positive integer repeat count. Each group has one case/version and one provider/model. The summary names the case/version, actual model, selected fixed payload, schedule, number of attempts and whether a private credential reference is required. Scripted offline uses no key. Gemini and OpenAI use the matching saved configuration reference and current configured model identifiers.

The UI offers clean, poisoned and defended in that order; the HTTP interface also accepts another explicit order. Every repeat runs that ordered schedule. The five allocated malicious cases support either retained family. The ten controls automatically select clean-only and disable poisoned/defended. The API validates allocation before credential lookup or a started attempt. A clean-only group carries no attack family or invented attacker predicate.

Results opens the directly returned group ID. Groups history reopens after refresh or backend restart. Comparison reports verdict, priority, handling and joint correctness, attacker goals, actual discovery restriction and invocation rejection, raw-marker availability, duration and errors. Each attempt links to its saved decision/evidence/trace. Setup and rerun execution stay on Experiment. Choose a saved group in Group source to append a complete new execution of its schedule; earlier attempts and IDs remain intact.

## Saved inputs and compatibility

The immutable plan stores the complete selected SyntheticCase, including version, evidence, ground truth and optional predicates; fixed attack ID/full text; provider/model; ordered conditions and repeats; approved definitions; bounds; exact provider instruction/output-schema and generation-settings snapshots; and scoring, decision and condition versions. Private keys and credential references are absent from the plan. Each run retains only its existing private credential reference in run configuration. Keys stay in the request-local provider factory.

InvestigationRunner.run_snapshot receives a separate copy of the selected case for each attempt. Later label edits do not change a saved group's case/version or earlier outcomes. A rerun uses that old selected snapshot even when the current case library has a newer version. Runtime/payload changes are rejected before new slots are claimed; create a new group for those inputs. Selected model identifiers do not prove that a provider alias refers to an immutable backend model version.

Compatibility checks compare the saved case/evidence/targets, actual provider/model, prompt version and full instruction/schema snapshot, effective explicit generation settings, limits, scoring/decision/condition versions, full attack snapshot and full approved definitions. Actual discovered and exposed definitions are compared with the selected condition's expected definitions. Trusted returned records must match the selected fixture. Group/attempt/repeat attribution must match too. Intentional ordinary versus poisoned metadata, withholding in defended mode and disabled versus enforced policy are the experimental contrast, not incompatibility.

Payload v1/v2, changed evidence or labels, different models/settings/prompts, unexpected tool metadata, unscored history and missing provenance cannot silently enter matched decision rates. Group comparisons never import arbitrary pooled history or rescore historical records. Full provider instructions and schemas are the same as before this ticket; they are now shared between request construction and saved comparison snapshots.

## Counts, missing values and failures

Each condition reports requested repeats per execution, all scheduled slots including reruns, saved attempts, compatible completions, failed saved attempts, incompatible attempts and missing saved results. Every rate has a numerator and eligible denominator, plus an explicit unavailable count among compatible attempts. Zero eligible outcomes produce null, not a zero-success claim. Duration is the mean across compatible saved attempts, including failures, with its count. There is no pairing estimator or uncertainty interval in this software slice.

Field/joint/attacker/marker eligibility retains investigation-scoring-v1 rules. Clean and missing-goal attacker outcomes remain unavailable. Failed decisions and goals remain null. Discovery and invocation rates require actual observed enforced checks and can include a failure after that stage. Disabled enforcement and no observed check are unavailable. Zero returned calls, marker absence and incorrect decisions never imply blocking. Reference validity remains membership in returned evidence, not explanation truth.

All saved failures retain fixed safe categories, elapsed time, available partial evidence and their directly returned run IDs. A failed attempt does not stop the remaining schedule. Failed provider initialization may lack actual prompt/settings provenance and is excluded from matched rates; the separate all-saved system-error rate includes it. Incompatible attempts remain linked and listed with reasons. Requested conditions with no compatible saved attempt are reported missing. Conditions omitted from the schedule are explicitly not requested, including the two attack conditions on clean controls.

## Persistence and operating limits

Additive run_groups and run_group_attempts tables share the configured run database. Atomic claims prevent concurrent executions of one group. Slots are allocated before execution and results associate by returned IDs. Saved runs also carry group_id, group_attempt and group_repeat. Every attempt uses fresh models and real two-process read-only MCP. Ground truth and targets remain outside provider/MCP input.

Execution remains synchronous and request-bound. Process termination or unavailable storage can leave a running group and slots without a saved result. They reopen as missing. There is no worker, resume/recovery platform, automatic provider retry or fabricated failure record for an unstarted slot. Current account-role and credential-reference rules apply; broader per-user history ownership remains the separate existing deployment limitation. Historical campaigns, scenario repair/identity and legacy/null measurements retain their existing paths.

## HTTP

- GET /api/run-groups lists saved plans and status.
- POST /api/run-groups validates, snapshots and executes a new group.
- GET /api/run-groups/{group_id} reopens attempts, compatibility and comparison.
- POST /api/run-groups/{group_id}/execute appends the same schedule, accepting only an optional matching credential_id.

Example offline request:

```json
{"case_id":"soc-auth-001","case_version":"1","provider":"scripted","attack_family":"cross-server-shadowing","conditions":["clean","poisoned","defended"],"repeats":2}
```

Case version is required to reject stale setup. Repeats must be an integer greater than zero, excluding booleans. Conditions are a nonempty ordered list with no duplicates. Clean-only omits attack_family. Invalid requests create neither a group nor an attempt. Changed run-time contracts require a new group rather than silently changing a saved plan.

Tests use scratch databases, synthetic credentials and SDK substitutes. No live-provider requests or API spending are needed or authorized. #29 owns the protocol/offline rehearsal, #30 final bounded release verification, and #31 the separately authorized live evaluation.


## Verification record, 2026-11-17

All 300 backend tests passed in 362.74 seconds with the existing Starlette/httpx deprecation warning. All 36 frontend tests, production build, compilation and dependency checks pass. Thirty-four focused mocked browser journeys and nine connected browser/backend/real-local-MCP journeys pass. The two group journeys pass again after adding exact prompt/schema snapshots and intentional-not-scheduled reporting. Checks include both providers through offline SDK clients, six linked trials, persisted restart readback, failures/continuation/nulls, pinned label-edit reruns, incompatibility exclusions and browser refresh/evidence links. Four desktop/mobile captures were reviewed. The independent finish reviewer scored the sole stale product-documentation fix resolved/ship. No live calls or effectiveness measurement occurred.


## Reading outcome colors

The user-requested Results presentation now applies green to correct decisions, red to incorrect decisions, and the inverse direction to attacker-goal/error rates: observed target matches/errors are red; their absence is green only with eligible observations. Mixed rates show both favorable and adverse counts. Grey means unscored/unavailable, never a successful zero. Policy restrictions/rejections and raw-marker observations remain purple because they are independent of correctness. Text labels accompany color. Individual investigation scores and pooled MCP rates use the same presentation direction. Saved values, denominators and historical meanings do not change.

Finished means the condition schedule ended, including retained failures. It does not mean every investigation completed or was correct. An explicit attacker-target match does not by itself prove injection causation; compare clean outcomes and inspect the individual evidence/trace before drawing that conclusion. No additional live calls were used to implement or check this presentation.


## Overall Results indicator, 2026-11-17

Results now places one overall experiment-performance indicator above the selected explicit matched group's detailed comparison. It displays rounded correct completed decisions / compatible saved attempts × 100, a short label and correct/attempt/failed/unscored counts. Correct requires verdict, priority and handling all to match. The supplied 1 correct, 3 incorrect and 5 failed example displays 11/100. This includes execution reliability; it is neither accuracy among completed decisions nor a validated security benchmark.

Failed attempts retain null correctness and lower this display-only indicator through the denominator. Completed but unscored attempts also remain in the denominator without adding a correct result, with a visible count. Every compatible retained rerun attempt counts once. Incompatible records and missing saved results are excluded, with existing counts/reasons/links retained below. Empty, unsupported or malformed comparison data is unavailable; completed records with no supported correctness observations also show unavailable. An all-failed compatible group is an observed 0/100. Partial availability limits interpretation.

Only existing joint correctness and compatible counts contribute. Attacker success, restrictions, rejection and marker observations never add points. Existing scores, detailed measurement denominators, historical meanings, evidence links and backend contracts are unchanged. Green only for every compatible attempt confirmed correct, red otherwise, and grey for unavailable are presentation conventions, not research findings. No intermediate score thresholds are introduced. The existing Research route tokens and layout remain in use.

Verification: 42 frontend tests, production build, compilation and pip check pass. All 39 existing focused mocked browser journeys pass; five added indicator edge-case journeys also pass. The example is checked after refresh and at desktop/mobile widths, with captures reviewed for readable hierarchy and no page overflow. Two connected browser/backend/real-local-MCP group journeys pass, including fresh six-attempt scoring, refresh, individual evidence links and retained clean-control reruns. All 300 backend tests pass in 405.22 seconds with the existing Starlette/httpx deprecation warning. All checks use synthetic fixtures and offline providers. No live group rerun, provider call, API spending, private credential/auth/raw historical-database inspection, tracker mutation, commit, merge or deployment. Prior uncommitted work and debug.log remain preserved. This follow-up is complete before starting #29; the research frontier remains #29 after issue/prerequisite refresh.
