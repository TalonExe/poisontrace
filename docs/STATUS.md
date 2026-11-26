# PoisonTrace status

Current documentation snapshot (2026-11-26). Accepted ADR decisions remain authoritative. Their dated implementation-pending statements record adoption context. Current source and this status establish what is implemented. Replace superseded status instead of appending session narratives.

## Implementation and working tree

Results → Groups uses a lazy-loaded React Aria table for Retained attempts. It sorts by attempt number, shows 10 attempts per page, and keeps saved failures distinct from slots without a saved result. The condition filter and exact trace links still apply. Back to group restores the selected condition. The initial production build reported a 57.1 kB gzip table chunk.

Pilot verification passed the build, 52 frontend unit tests, 91 mocked browser tests, nine connected browser tests, and five browser tests in each production profile across separate runs. The unfiltered backend suite passed all 413 tests. Desktop and mobile screenshots were reviewed. The keyboard browser test covers focus, trace activation, and condition restoration. A manual screen-reader check remains open before broader adoption.

Issue [#53](https://github.com/TalonExe/poisontrace/issues/53), Slice 1, replaces Saved attempts over time on the analyst Dashboard at `/activity` with a responsive Recharts stacked bar chart. Completed and failed counts use the existing browser-local week and month buckets. Each nonzero bucket and status has a labeled Results link with its date range and count. The bar and link open the same Results filter. Empty periods show a message. Provider activity counts saved attempts, matched-group activity shows creations and rerun submissions, and interrupted jobs have a separate total. Token totals remain deferred until saved records include provider-reported usage.

The Vite production build reports 131.05 kB gzip for the entry JS, up 0.56 kB. The lazy chart chunk is 107.36 kB gzip and shares a 0.23 kB gzip chunk with Retained attempts. Total emitted JS increased from 187.62 to 295.68 kB gzip, and CSS increased from 16.52 to 16.59 kB gzip. The pre-pilot build log is `.scratch/verify-20261126-162515-7b73b7e1/build.log`.

The Dashboard Playwright journey failed first on the missing link and passed after implementation. It covers week/month selection, the saved failure and separate interrupted count, exact pointer and keyboard drill-down, and the empty period. The populated desktop and 390px mobile captures were reviewed, including visible keyboard focus on the failure link. The empty production Dashboard capture passed at both sizes in `.scratch/issue-53-activity-empty/summary.json`. Playwright verified the chart description, the link name, Tab focus and Enter activation. Manual keyboard and screen-reader checks could not be completed because the browser access host was unavailable.

The complete verification run recorded `source_stable=true` and `complete=false`. The build, 413 backend tests, 52 frontend unit tests, 91 mocked browser tests, five browser tests in each production profile, and tracked whitespace checks passed. Two of nine connected Experiment journeys failed at the job status assertion, which expected “queued” or “active” and received “Investigation running.” All nine passed in a focused rerun with the same source hash. The complete run and populated captures are in `.scratch/verify-20261126-163014-011cc93d`. The retry is in `.scratch/issue-53-connected-retry/summary.json`.

Issue #53 Slice 2 uses the React Aria pending state for matched-group launch, rerun and uncertain-response retry, and for Single run. The focused control stays in the tab order while the request is pending. Repeated activation submits one intent. Retrying an uncertain response reuses the saved intent, and accepted jobs continue through durable progress and the app-wide notification.

Slice 3 pages the filtered Runs history in groups of 10. Search starts at the first page of matches and respects the Dashboard selection. An exact run opened from filtered history retains the Dashboard query. Reloading an exact run opens the page containing that record. Retained attempts was reviewed using the browser accessibility tree, keyboard tests and desktop/mobile captures. The review confirmed the sort indicator, page range, named trace links and distinct interrupted status.

Slice 4 applies pending controls to API key changes, local ground-truth and YAML saves, user edits and passcode resets. API key revocation, saved-configuration deletion, scenario deletion and user role/status changes use named confirmations. Cancel receives initial focus and the trigger regains focus on dismissal. Recoverable request failures stay in the dialog for retry. Passcode reset retains its two masked fields and explicit confirmation. Hosted authoring stays read-only.

Slices 2–4 add 13.39 kB gzip of emitted JS relative to Slice 1. The entry and its static preloads total 155.62 kB gzip, up 24.57 kB. The confirmation dialog is a 6.25 kB gzip lazy JS chunk. The production build log is `.scratch/issue-53-final/build.log`.

All 92 mocked journeys passed in `.scratch/issue-53-slice-4-green/summary.json`. Desktop and 390px mobile captures cover the pending matched-group control, Runs history, Retained attempts and revocation error. Playwright verifies repeat activation, keyboard focus, exact links, cancel and retry. The browser access host remained unavailable for a manual keyboard and screen-reader pass.

The full Windows run after Slice 4 passed with `complete=true` and `source_stable=true`. It passed the production build, 413 backend tests, 52 frontend unit tests, 92 mocked browser tests, nine connected browser tests, five browser tests per production profile, tooling, static, dependency and whitespace checks. All browser ports closed and both debug logs returned to their entry bytes. The report is `.scratch/issue-53-final/summary.json`.

Issue #52 is implemented in the working tree. On Single run, the sample sets a bundled synthetic SOC case, Clean and Scripted offline for review. The analyst starts execution explicitly and opens the saved record from the completion action. The gear next to the analyst profile opens Settings for analyst-owned API keys and saved investigation configurations. The legacy Configurations URL remains usable.

Verification for #52 includes 413 backend tests, 52 frontend unit tests, 88 mocked browser tests, the production build, five production browser tests in each of the local and hosted profiles, and desktop and mobile screenshot review. The next UX slice is the matched-group Results layout.

Single run, Matched group and Research cases now group case options by authored dataset category. The updated production build and all 89 mocked browser tests passed.

Results → Groups now opens a selected group with performance and attempt cards, condition filters and a Retained attempts card. Saved attempts open their exact recorded trace, and Back to group restores the selected condition. The full mocked browser suite passed 90 tests.

Single runs and matched groups show a bottom-right run notification in the analyst workspace. It follows the accepted job across pages, reconnects to queued or active work after refresh, and opens the exact saved outcome through See the results. The existing inline progress and automatic Results navigation still apply. The production frontend build, 413 backend tests, 52 frontend unit tests, 90 mocked browser tests, nine connected browser tests and five production browser tests in each of the local and hosted profiles passed. Notification coverage includes desktop and mobile review.

Tickets #38–#48 and all five cleanup slices are implemented locally. This includes runtime packaging, analyst ownership, hosted content and session policy, account recovery, durable MCP investigations and matched groups, and durable metadata execution. Tickets #29–#31 remain cancelled.

Last inspected branch: `cleanup/bounded-research-workflow`.
HEAD: `a5b4ea42bb2d36ad2b900b611243423a90e1b694`.
The accumulated implementation, packaging, verification-tool and documentation changes remain uncommitted. The #49 entry index was empty, with 106 modified paths, 37 deleted paths and 72 Git-visible untracked paths. Closeout has zero staged paths, 106 modified paths, 37 deleted paths and 73 Git-visible untracked paths.

Single investigations and matched groups share owner-scoped idempotency, one outstanding queued/active admission slot and a supervised executor. Submissions return durable IDs promptly. Groups pin experimental inputs, atomically associate results with attempt slots, retain prior attempts on explicit reruns and reconnect progress after refresh. Recovery preserves saved children, marks active slots interrupted/uncertain and unstarted slots missing, and never automatically replays interrupted work. Queued undispatched jobs may execute after restart. Older missing slots remain missing.

Metadata singles, campaign executions and per-scenario reruns use that same admission slot. Metadata singles use `POST /api/investigation-jobs` with `workflow=metadata-v1`. Campaign execution and rerun endpoints require an idempotency key and return HTTP 202 with the owned job ID. The legacy `POST /api/runs` rejects request-bound execution. Campaign admission claims the campaign and allocates child slots atomically. Each save links the actual run ID to the slot and campaign row in the same transaction. Reruns retain earlier runs and their scoring and trace interpretation.

Campaign setup lists malformed poisoned files as exclusions and allows the usable selection after review. Execution validates saved file identities again before admission and requires acknowledgement when a saved input has become unusable. Local repair remains available. Accepted work snapshots the usable inputs. A campaign can run up to 15 scenarios, and a metadata job snapshot can use up to 256 KiB. Each attempt has a 45-second process watchdog. The synchronous provider clients use 20-second transport timeouts and disable automatic retries. A reported provider timeout saves an unscored failure. On executor loss, recovery retains saved children and marks unfinished slots interrupted or missing. Metadata recommendations and simulated permission decisions retain their separate scoring and provenance.

## Local deployment readiness rehearsal

GitHub issue #49 was closed as not planned at the user's request. The [operator rehearsal](../DEPLOYMENT_REHEARSAL.md) records the planned five-session workload, resource sampling, execution and access checks, image and schema cutover, rollback and alert responses. It prepares two Singapore pilot sizing options at published prices of USD 17 and USD 29 per month including independent object storage. There is no measured sizing decision or vendor quote. Operator assignments, key custody and retention targets remain pending.

The Windows verification preflight reproduced a source-fingerprint error caused by the existing database executor lock being classified as a dependency input. The focused regression failed before the fix and passed afterward. The runner now fingerprints `requirements-runtime.lock` without opening the application executor lock. See `.scratch/ticket-49-complete/summary.json` for the first attempt, which stopped before running any checks.

The fresh isolated Windows retry passed in 1060.12 seconds with `complete=true` and `source_stable=true`. It passed 413 backend tests with one existing Starlette deprecation warning, 52 frontend unit tests, 85 mocked browser tests, nine connected local MCP browser tests and five browser tests in each production edition. It also passed 22 tooling tests, static checks, installed dependency checks, a fresh build and whitespace. All browser ports closed and both debug logs returned to their entry bytes. See `.scratch/ticket-49-complete-retry/summary.json`. The run's source fingerprint is `4d94ed06e9bb1323d6223135bc21b2ef2f1fd2681da4316a30352ed37fd69258`.

The agent session could not connect to a Linux engine. `docker info --format '{{.OSType}}'` exited 1 with access denied to `npipe:////./pipe/docker_engine` even with a workspace-local CLI configuration. The Docker Desktop Linux pipe was absent. `podman info --format '{{.Host.OS}}'` exited 125 on both attempts with access denied to the configured Podman machine identity. `docker -H npipe:////./pipe/podman-machine-default info --format '{{.OSType}}'` exited 1 with access denied to the alternative pipe. `wsl --list --verbose` returned `Wsl/E_ACCESSDENIED`. See `.scratch/ticket-49-linux-preflight.log`.

The operator ran `.venv\Scripts\python.exe scripts/verify_container.py --engine podman` outside the agent session. The fresh Linux build and startup reached readiness, then the first interactive container probe failed with exit 1 in 1m41s. The probe suppressed its runtime output and the cause remains unknown. See `.scratch/ticket-49-podman-20261124-104000.log`. The operator reran using `.venv\Scripts\python.exe .scratch/ticket-49-container-diagnostic.py --engine podman`. This scratch copy changes only failure reporting. It emits the probe exit code and stdin traceback line numbers. The rerun exited 0 in 2m03s and passed the fresh build, non-root resource limits, packaged assets, offline local MCP, child cleanup, restart persistence and storage failure checks. See `.scratch/ticket-49-podman-diagnostic-20261124-104231.log`.

The five-session workload, resource measurements, complete current-image execution and hosted proxy checks, coordinated Linux restore, identified image/schema rollback and end-to-end diagnostic scan were deferred. The #48 Windows restore times remain prior evidence. GitHub issues #50 and #51 were also closed as not planned at the user's request. The invited pilot and public release did not begin.

## Backup, restore and expiry

The production runtime takes a maintenance lock across admission and executor
shutdown. The recovery CLI requires the runtime and executor to stop before
using SQLite's backup API on both databases and archiving YAML, JSON overrides and
the seed marker. It publishes an authenticated encrypted archive to a separate
destination. The application key, archive key and current recovery ledger are
independently recovered. Restore targets a new root and blocks startup pending
operator activation. The ledger reconciles superseded or revoked credential
ciphertexts, application-issued YAML deletes and history expiry. Activation
clears backed-up sessions and marks active and queued jobs interrupted without
replay. Saved attempts, actual links, scoring and pinned provenance are
preserved. The cutover runbook requires review of account changes and content
operations performed outside the application before reopening admission.
See [data recovery](../DATA_RECOVERY.md).

History expiry operates on linked groups, campaigns, jobs, runs and traces.
A pending job, known newer record or undated legacy record protects its
connected history. Operators choose the retention periods explicitly. The
30-day history window, seven days of daily backups, 24-hour RPO and one working
day RTO remain proposals. The local rehearsal used synthetic state only and
does not establish operating targets.

## Verification record

The #48 focused rehearsal passed four tests with one existing Starlette
deprecation warning in 23.52 seconds. The loaded restore journey took 2.50
seconds including negative key checks and restored HTTP verification.
It covered login, owner isolation, revoked credentials, YAML deletion,
JSON override versions, saved results and pinned comparisons, a preserved
interrupted job and a restored queued job marked interrupted. The other checks
covered linked retention including historical campaign reruns, missing final
archive on partial snapshot failure, and the existing storage startup error.
See `.scratch/ticket-48-rehearsal-verified.log`. A separate CLI smoke test
passed backup, restore, activation and both expiry commands using generated
keys and an operator account. The missing archive key returned exit 1.
Restore, activation, expiry and verified operator login took 3.98 seconds.
See `.scratch/ticket-48-cli-rehearsal.log`.

The first complete #48 attempt was stopped during backend verification to
correct the startup storage error and retention of historical campaign links.
Its summary is `.scratch/ticket-48-complete/summary.json`. The second was
stopped after reproducing an account-recovery compatibility regression.
Its summary is `.scratch/ticket-48-complete-final/summary.json`. The fix
keeps the maintenance lock at the recovery command boundary. The subsequent
production, account recovery and application recovery selection passed all
18 tests with one existing Starlette warning in 46.59 seconds. The third
complete attempt stopped during backend verification to move the runbook to
a Git-visible path. See `.scratch/ticket-48-integrated/summary.json`.

The final integrated #48 Windows run passed in 958.14 seconds with
`complete=true` and `source_stable=true`. It passed 412 backend tests with
one existing Starlette deprecation warning, 52 frontend unit tests, 85 mocked
browser tests, nine connected real-local-MCP tests, and five browser tests
in each production edition. It also passed 21 tooling tests, static
compilation and annotation checks, installed dependency checks, a fresh
build, and tracked whitespace. All browser ports closed, the runner
removed synthetic state, and both debug logs matched their entry bytes.
See `.scratch/ticket-48-complete-integrated/summary.json`.

Final integrated source fingerprint:
`cc60ffce0dcf62066d08a6775b8e2250611fbea84bd9f7e6e48b49a363712ddb`.

The integrated #47 Windows run passed with `complete=true` and `source_stable=true` in `.scratch/ticket-47-complete-integrated/summary.json`. It passed 409 backend tests with one Starlette deprecation warning, 52 frontend unit tests, a fresh build, 85 mocked browser tests, nine connected real-local-MCP tests, and five browser tests in each production edition. It also passed 21 tooling tests, static compilation and annotation preservation, installed dependency checks, and tracked whitespace. All browser ports closed, synthetic state was removed, and both opaque debug logs returned to their entry bytes.

Integrated application source fingerprint: `61936bb0e44cace7a562c6a1131fcf18e1927a0f189a0936d616427a79a9ff63`. The focused browser rerun is recorded in `.scratch/ticket-47-browsers/summary.json`. The earlier `.scratch/ticket-47-complete/summary.json` was interrupted during backend verification after failures in tests for the superseded HTTP contract. In `.scratch/ticket-47-complete-final/summary.json`, one outdated scenario adapter assertion failed and mocked verification was interrupted after exposing a stale matched-group callback. The integrated pass covers both corrections.

The pre-#47 Windows baseline passed with `complete=true` in `.scratch/verify-20261123-230902-e4163776/summary.json` after the Experiment polling refactor. The following records cover earlier slices.

| Evidence | Recorded outcome |
| --- | --- |
| `.scratch/ticket-46-complete-final/summary.json` | Failed complete attempt, `complete=false`. Passed 404 backend tests, 52 frontend tests, 84 mocked journeys, nine connected real-local-MCP journeys, 21 tooling tests, static compilation/preservation, installed dependency, build and whitespace checks. Each production edition had four passes and one failure. |
| Production failure cause | The preceding privacy journey ended while its newly durable Bob-owned group remained active. The next submission correctly received shared busy rejection. The only subsequent source-input change added a wait for that exact owned job to complete. |
| `.scratch/ticket-46-production-focused/summary.json` | Passed focused attempt, `complete=false`: fresh build and all five production journeys in each edition, including actual local HTTPS hosted checks and cleanup. Backend, frontend-unit, mocked, connected, tooling, static, dependency and whitespace checks were not run by this command. |

Complete-attempt source fingerprint: `08ab9e6f50397e73588b9f61c8d9971d07dfc450d6bc5482d9460ad0d4008b6e`.
Final focused source fingerprint: `67240b46b2d6e06c27da544d4cc3fba54de1c1ce5ba4096345494f608149ad50`.
These are historical input identities, not fingerprints of this documentation cleanup. The user explicitly waived another complete run. Split evidence must not be described as a successful final complete run.

Earlier evidence remains distinct:

- `.scratch/ticket-46-browsers-dev` had one mocked and one connected assertion failure; local production was interrupted and hosted production was not run.
- `.scratch/ticket-46-browsers-focused` passed 84 mocked and nine connected assertions but failed the connected graceful-cleanup gate. A bounded test-server shutdown fix followed.
- `.scratch/ticket-46-complete` passed its early checks, then was interrupted during backend verification after discovering the legacy-running rerun gap. Later browser/whitespace phases were not run. A regression and fix preceded the later complete attempt.
- The focused durable-group/limit backend check passed 16 tests, including retained missing slots, contention, atomic link rollback, restart and actual executor/MCP-child termination.
- Historical #38 user-run Podman acceptance on 2026-11-18 passed clean Linux packaging, non-root constraints, packaged assets, routing, offline MCP, restart and failure checks. It does not establish Linux behavior after later changes.

## Evidence and preservation

Visual evidence remains in `.scratch/ticket-46-ui-before`, `ticket-46-ui-after-final`, `ticket-46-ui-hosted-final` and the complete attempt's mocked captures. Recorded review covered desktop/mobile empty, active and interrupted states without horizontal overflow. Capture success is not automatic accessibility or release approval.

The final application verification recorded stopped owned processes, ports 4173–4176 closed and both debug logs exactly matching session entry. Logs remain opaque bytes:

| File | Entry bytes | SHA256 |
| --- | --- | --- |
| `debug.log` | 21186 | `9D13B63BB61242911A888C6F88D23A53A077E04E2CA38B6C7D5F5C50FA25C4D1` |
| `frontend/debug.log` | 215 | `A7E6D123227C9878DCC8BA3DC1B9C38F21CCFAA5D3C780E519C2EC1D81D163BD` |

Complete appended-log archives remain inside the corresponding verification directories. Entry source/inventory evidence remains in `.scratch/ticket-46-entry`. Preserve existing scratch artifacts, local agent/tool directories, ignore rules, comments, private stores and historical saved records. Payload v1/v2 JSON archives remain required version evidence.

## Remaining work

The inactive frontend cleanup is complete locally after the agreed grilling loop. Removed the unused session re-export, obsolete sidebar helpers and their four tests, and the repository-unused getInvestigationJob frontend adapter operation. Live navigation, session utilities, collection polling and backend job routes remain unchanged. No comments were present in the retained runApi.js file.

Focused verification passed in `.scratch/verify-20261123-223053-5615e2c3/summary.json`, with `complete=false`: frontend unit tests, a fresh production build, all 84 mocked browser tests and tracked whitespace. Browser coverage includes mobile navigation, account switching and job reconnect. The preview listener was owned, its port closed and synthetic state removed. The user waived the backend suite for this slice; connected and production-edition browser checks were not selected. This is not a complete verification run.

The forwarding route cleanup is complete locally after the agreed grilling loop. Removed all seven frontend route wrappers; App.jsx directly renders the existing feature modules and LoginPage with their prior props and scenario flags. Stable create/detail editor keys preserve mode isolation; dashboard/account keys, router behavior and editor loading logic remain unchanged. A browser regression covers rejected creation, successful create-to-detail navigation, saved notice and unsaved-draft isolation on browser back to creation.

Focused verification passed in `.scratch/verify-20261123-224128-e530d1da/summary.json`, with `complete=false`: frontend unit tests, a fresh production build, all 85 mocked browser tests and tracked whitespace. The user waived the backend suite for this slice; connected and production-edition browser checks were not selected. The preview listener was owned, its port closed, synthetic state removed and both opaque debug logs preserved byte-for-byte. Status/architecture/handoff prose was updated afterward and whitespace rechecked.

The superseded matched-group writer cleanup is complete locally. Removed `RunGroupStore.claim`, `finish_attempt`, `finish` and their SQLite authorization helper. Tests cover foreign rerun denial and atomic result-link rollback through the durable path. The legacy fixture builds the historical missing slot directly and verifies that an explicit rerun appends a new attempt and leaves the original slot unscored. The request-bound `RunGroupService.create` and `execute` guards still fail closed.

The focused ownership, limits and durable-group tests passed (21 tests). The full backend suite passed (405 tests, one Starlette TestClient deprecation warning). Browser and production verification were outside this slice.

Experiment now uses one observer for single-investigation and matched-group job polling. It owns job selection, one-second retries and suppression of late responses, including group progress fetches. The views still own submission intent, presentation and navigation. Four focused observer tests passed. The complete Windows result is recorded above.

#48 depends on the locally verified #46 and #47. The recorded deployment sequence had #49 depending on #42, #44 and #48, followed by #50 with pilot authorization and #51 with release authorization.

Current Linux-container lifecycle, actual-host proxy correctness, capacity, recovery with representative data on the intended storage, live-provider effectiveness and release readiness remain unverified. Vendor/region/quote, approved capacity, retention/backup expiry, restore targets and operator responsibility still require decisions. One persistent Linux host, one replica/worker and one HTTPS origin remain the intended topology; no purchase or provisioning is authorized.

## Documentation maintenance

Current guidance is [context](CONTEXT.md), [glossary](DOMAIN_GLOSSARY.md), [architecture](ARCHITECTURE.md) and this status. Consult [verification](VERIFICATION.md), [local launch](LAUNCH.md), [container/operator instructions](../CONTAINER.md), [research scope](SCOPE_REFINEMENT.md) and research contracts for the relevant task. Superseded plans, reviews and handoff narratives were removed at the user's request; their removal changes no application behavior. The deployment-handoff path remains a short pointer for the preserved local skill.

At documentation-cleanup completion, all local Markdown targets resolved across the maintained documentation/entry files checked, and tracked whitespace passed. Comparison with the final application verification input hashes found only the intentional AGENTS.md and CONTAINER.md edits; application, test, build-input and verification-tool bytes matched that recorded input set before the later inactive frontend cleanup. Both debug-log lengths/hashes matched entry without reading their contents. No suites, providers, staging or publication ran during documentation cleanup. The later focused frontend verification is recorded above; both debug logs were again preserved byte-for-byte.
