# PoisonTrace architecture

This document describes current module ownership and test seams. [STATUS.md](STATUS.md) owns implementation and verification state. The [domain glossary](DOMAIN_GLOSSARY.md) and accepted [ADRs](adr/) define terminology and decisions. Dated implementation-pending statements in ADRs record their adoption context; current source and STATUS establish what is implemented.

## Module map

Paths are relative to `backend/src/poisontrace/` unless stated otherwise.

| Module | Responsibility |
| --- | --- |
| `domain/` | Scenario/investigation values, fixed attacks, independent scoring and pure aggregation, including matched-comparison eligibility. |
| `application/runs.py`, `execution.py`, `benchmark.py` | Metadata execution, history, detail and repeat coordination. Saved IDs return directly; callers never infer attribution from the latest record. |
| `application/investigation.py` | Bounded evidence loop, model continuation, reference validation, manifest observations and safe saved failures. |
| `application/gateway.py` | Simulated metadata permission decisions and separately qualified read-only MCP invocation policy. |
| `application/run_groups.py` | Validate and pin matched plans, authorize reads, calculate progress and compare retained attempts. Old request-bound create/execute entrypoints fail closed. |
| `application/jobs.py` | Durable MCP investigation, matched-group, metadata run and campaign submissions, idempotency, schedule limits and execution under the recorded analyst scope. |
| `application/campaigns.py` | Filename-based campaign selection, pre-admission validation, retained reruns and child summaries. |
| `application/accounts.py`, `principals.py` | Transactional account/session rules and trusted caller identity. |
| `application/credentials.py`, `scenarios.py`, `content_policy.py` | Credential operations, YAML identity/repair and local/hosted mutation policy. |
| `application/ports.py`, `contracts.py`, `errors.py` | Application-owned interfaces, exchanged values and explicit errors. |
| `adapters/models/` | Metadata and evidence-continuation provider adapters; fake/scripted models support offline checks. |
| `adapters/mcp/` | Immutable corpus/manifest, versioned local ground-truth overrides, two fixed stdio servers, discovery/schema validation and child lifecycle. |
| `adapters/persistence/` | SQLite schemas and account/run/campaign/group/job records; in-memory stores support trusted callers and CLI execution. |
| `adapters/execution/jobs.py` | Supervised spawned executor, exclusive OS lock, watchdog and descendant cleanup. |
| `adapters/scenarios/`, `adapters/secrets/` | YAML/filesystem persistence and owner-authorized encrypted or injected managed-secret storage. |
| `interfaces/http/`, `interfaces/cli.py` | HTTP/auth/role translation and CLI argument/result translation. |
| `bootstrap.py`, `config.py` | Concrete dependency construction and immutable validated configuration. |
| `production.py`, `web.py`, `__main__.py`, `launcher.py` | Production composition, development web/CLI entrypoints and local process launch. |

## Dependency rules

Domain modules use only the standard library and other domain modules. Application modules use domain values and application-owned interfaces; they never import adapters, bootstrap, configuration, HTTP, SQLite, vendor SDKs or MCP transport types. Bootstrap supplies concrete adapters. HTTP and CLI translate requests and results rather than constructing execution dependencies.

Model adapters translate provider requests and responses without invoking tools or owning persistence. MCP transport owns SDK connections, fixed child commands and schema validation. SQL belongs in persistence adapters; account transactions are expressed through application-owned account-record interfaces. ToolGateway remains the invocation seam.

Keep one canonical implementation for each responsibility. Retired root compatibility modules and RunWebAdapter must not return. A module earns its interface by owning behavior; forwarding-only aliases and speculative interfaces add no depth. Keep independently meaningful modules rather than merging them merely to reduce file count.

## Composition and runtime

`build_backend(WebConfig(...), secrets, ...)` supports injected model factories and explicit application composition. `build_web_backend` supplies encrypted local secrets or an injected managed client. `build_accounts` supplies transactional accounts; explicit empty seeds prevent development seeding. HTTP receives one authentication instance and the executor factory.

Production uses `python -m poisontrace.production serve`, one Uvicorn worker, built frontend assets and same-origin HTTP. Configuration is validated before storage creation. Packaged immutable seeds initialize missing YAML once without replacing edits or reintroducing deletions after the marker exists. Health readiness probes storage and assets without recreating missing databases. See [CONTAINER.md](../CONTAINER.md) for paths, recovery commands, isolation and proxy requirements.

The main SQLite database contains accounts/sessions, traces/runs, campaigns, groups/attempts and execution jobs. Encrypted credentials use a separate database; YAML scenarios and JSON ground-truth overrides are separate state. Browser configurations are account-scoped localStorage. Coordinated backup must include all durable state and separately recovered encryption material.

## Workflow and measurement seams

Metadata execution selects matched trusted/discovered definitions, produces a recommendation, then evaluates simulated permissions. It retrieves no evidence or external tool result. Recommendation-v1 scoring and gateway-v1 observations preserve nullable outcomes and legacy meanings. [The metadata measurement contract](research/SLICE_ONE_MEASUREMENTS.md) defines denominators.

MCP investigations discover two fixed servers, apply manifest policy before exposure/invocation, gather permitted evidence and feed observations back to the model before a structured final decision. Ground truth and attacker targets never enter model input or the child snapshot. The loop retains four calls, a cooperative 20-second deadline and 16,384-byte output bounds. Provider/transport cleanup is bounded.

The fifteen-case corpus, canonical close/escalate handling, fixed v2 payloads and investigation-scoring-v1 keep field correctness, joint correctness, explicit attacker predicates, raw marker availability, reference membership and actual policy observations independent. Historical v1 payloads and saved records are not reinterpreted through the active catalog. See [investigation](research/CLEAN_MCP_INVESTIGATION.md), [corpus](research/SYNTHETIC_RESEARCH_CORPUS.md) and [payload](research/MCP_PAYLOAD_REVISION_V2.md) contracts.

Matched groups pin case/evidence/ground truth/targets, provider/model, payload, prompts/schema/settings, approved definitions and scoring contracts. Intended condition exposure/enforcement differences are eligible; unrelated historical runs are not recruited. Reruns append attempts, using saved inputs and a current owned credential reference. Changed runtime/payload requires a new group. Missing or incompatible observations never become scored failures. See [matched groups](research/MATCHED_RUN_GROUPS.md).

## Ownership, content and accounts

HTTP establishes a `Principal` solely from backend authentication. Context-managed scope propagates to worker threads/async tasks and resets on exit. Credential stores filter the analyst owner before metadata or decryption. Run, group and campaign modules authorize before reading outcomes, plans or children. Foreign and unknown identifiers share safe denials. Persistence mutation transactions recheck parent/child ownership. NULL legacy owners remain quarantined without reassignment or rescoring.

Provider execution resolves an owned credential reference at use time, with no web fallback to host provider keys. Revocation prevents later retrieval but cannot recall an in-flight client. Managed-secret reference metadata remains process-local; the injected adapter is not a configured durable cloud integration.

Hosted content policy denies YAML and ground-truth mutations before lookup/validation/persistence. Local authoring, invalid-file repair, immutable IDs and stale-version checks remain. The browser capability controls presentation; application enforcement is authoritative.

Sessions have a fixed eight-hour expiry without sliding renewal. Logout, disable, role changes and passcode reset invalidate affected sessions. Hosted policy validates HTTPS, exact configured Host/write Origin and explicit immediate proxy peers; Secure cookies do not depend on untrusted headers. Login reserves bounded persistent account/client/global throttle buckets before hashing. API responses are no-store; hosted docs/OpenAPI are denied. Uvicorn proxy rewriting stays disabled.

Superadmins manage users without analyst-workspace access. Analyst passcode reset reauthenticates the actor inside the write transaction and revokes only the target's sessions. Operator-only hidden-input recovery requires an existing superadmin, never creates/promotes accounts and requires explicit disabled-account enablement. Reset/recovery preserves identity, private credentials/history and already admitted execution.

## Durable execution

Single and matched-group POSTs require owner-scoped idempotency intents and return HTTP 202 with durable identifiers. Exact intent/input repeats reopen the original job, including terminal jobs. Conflicting reuse or busy work allocates nothing. Requests are bounded to 4,096 body bytes and 200 UTF-8 bytes per selection string. Hosted groups permit one repeat and at most three unique conditions, rechecked at execution after a profile switch.

SqliteJobStore admits one outstanding queued/active job globally through an immediate transaction and partial unique index. It persists a group's parent, job and all slots atomically. One spawned worker holds the database-adjacent OS lock; claims have finite 60-second leases and one-time dispatch. Each group attempt renews the lease and receives a separate 45-second process watchdog. Windows uses Job Objects; POSIX uses process groups with Linux parent-death termination.

SqliteTraceStore commits result, directly returned run ID, trace association and owning attempt link together after validating the active owner/claim/lease. The last result also finishes the group/job. Ordinary saved failures do not stop a group schedule. Process/storage interruption preserves saved children, marks active slots interrupted/uncertain and unstarted slots missing, and never replays interrupted work. Queued undispatched work may start after restart. Explicit reruns can append to older request-bound groups retaining a running label; their old missing slots remain unchanged.

The same admission slot covers metadata singles, campaign executions and per-scenario reruns. Metadata submissions snapshot the selected scenario at admission. Campaign creation records the usable poisoned filenames and reports excluded files. Execution revalidates the saved selection before admission and requires acknowledgement of newly excluded files. Each campaign execution is limited to 15 scenarios and each metadata job snapshot to 256 KiB. The supervised executor applies its 45-second watchdog to each attempt, and the synchronous SDK clients use 20-second transport timeouts without automatic retries.

Campaign admission claims the parent and allocates the job and its attempt rows in one transaction. Saving each child atomically links its returned run ID to the job slot and campaign row. Explicit reruns append saved runs and replace the current child link only when a result saves. Interrupted jobs preserve saved links and report active or unstarted slots as interrupted or missing. Campaign runs retain simulated gateway permissions and recommendation scoring.

## Frontend

The analyst landing page at `/activity` uses browser-local calendar boundaries with an exclusive end. The owner-scoped `GET /api/runs/activity` read returns saved investigation attempts, new groups, explicit reruns and the interrupted investigation job count for that interval. The dashboard and filtered Results use the same read to keep chart counts and matching records aligned. Provider totals count saved attempts. Token usage is unavailable.

`frontend/src/app/App.jsx` composes authentication, account workspace remounts and route rendering directly from feature modules and LoginPage. The router owns URL normalization, navigation and parameter-only refresh. Distinct stable scenario create/detail keys retain editor state isolation; dashboard path and account workspace keys retain their existing remount behavior. Feature modules implement Configurations, Experiment, Results, content authoring and user management. HTTP calls use feature adapters and the shared client; reusable utilities do not import UI/app composition. Shared UI does not import pages or state utilities.

Account-captured storage keeps late writes in the original namespace; identity changes unmount cached execution and Results. Current-generation 401 responses end the workspace, while stale responses cannot sign out a later login. Focus rechecks external cookie changes. Unscoped historical preferences are preserved without adoption.

Experiment retains exact pending requests/intents after uncertain responses and polls owned jobs after refresh. Results links actual saved IDs and shows completed/failed/interrupted/missing/queued/active slots. Decision correctness, attacker outcomes, policy observations and unavailable scores retain independent presentation. The overall group indicator is a display-only correct/compatible-attempt ratio, not a validated security benchmark. The visual system remains in `frontend/DESIGN.md`.

## Verification seams

Test public application interfaces, authenticated HTTP behavior, persistence transactions, provider translation through offline SDK substitutes and real local MCP interactions. In-memory and SQLite trace adapters both have live uses; provider adapters vary at the model seam. Preserve foreign-owner denial, idempotency/concurrency, atomic association rollback, process loss, pinned reruns, legacy missing slots and nullable measurement reconstruction.

Architecture checks inspect dependency direction and retired imports. Browser checks cover account changes, deep links, reconnectable jobs, evidence references and role/content policy. [VERIFICATION.md](VERIFICATION.md) defines isolated Windows checks, cleanup and evidence semantics. Tests are consumers, never production dependencies. Current Linux/host/restore/capacity/live-provider gaps belong in STATUS, not inferred from passing offline checks.
