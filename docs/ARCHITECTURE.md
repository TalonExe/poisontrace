# PoisonTrace backend architecture

Current structure after compatibility retirement, 2026-11-03. This guide describes the source tree as it exists now. STATUS.md records verification and prior slices. ADRs 0001, 0002 and 0003 remain authoritative. Earlier architecture-guide versions are review artifacts in .scratch/backend-cleanup-docs-before.zip.

## Where code belongs

The package is backend/src/poisontrace. It has 48 Python source files, including package initializers, down from 67 before compatibility retirement.

| Location | Owns |
| --- | --- |
| domain/values.py | Scenario, tools, model decisions, experiment modes and results |
| domain/rules.py | Injection marker and pure output redaction |
| domain/metrics.py | Benchmark metric calculations |
| application/runs.py | Run creation, history, detail and summaries |
| application/campaigns.py | Campaign creation, execution, aggregation, child associations and reruns |
| application/credentials.py | Credential operations, provider matching support and masked responses |
| application/scenarios.py | Scenario CRUD, identity allocation and usable-scenario lookup |
| application/accounts.py | Account/session use cases, hashing, lifecycle rules and transactional account interfaces |
| application/execution.py | ScenarioRunner execution coordination and trace recording |
| application/benchmark.py | Repeated-trial execution coordination |
| application/gateway.py | ToolGateway manifest checks and protected-action approval |
| application/ports.py | Application-owned model, scenario, trace/run, campaign and secret interfaces |
| application/contracts.py | Request/response types used by the implementation |
| application/errors.py | ScenarioNotFound, the explicit run lookup error |
| adapters/models/ | Fake, OpenAI and Gemini implementations |
| adapters/persistence/ | Trace, campaign and account records; in-memory stores; shared SQLite setup |
| adapters/scenarios/ | YAML parsing, filesystem documents, atomic writes and campaign filename selection/reload |
| adapters/secrets/storage.py | Encrypted SQLite and injected managed-secret implementations |
| interfaces/http/ | HTTP translation, authentication/role checks and routers |
| interfaces/cli.py | Benchmark CLI argument parsing and output |
| config.py | Immutable paths, encryption-key validation and repr-redacted seed configuration |
| bootstrap.py | Concrete dependency construction and explicit composition |
| web.py, __main__.py | Thin HTTP and CLI entrypoints |
| launcher.py | Local API/dashboard process launcher used by scripts/launch.py |

Package __init__.py files identify packages. domain/__init__.py also provides the intentional public domain-value interface. They do not eagerly import concrete providers or application startup.

## How to enter the backend

- Use bootstrap.build_backend(WebConfig(...), secrets, model_factory=...) for explicit application composition. The model factory is injectable; omitted secret storage remains unavailable to credential use cases.
- Use bootstrap.build_web_backend(config=..., managed_secret_client=...) for configured web startup. Local storage requires a valid encryption key; an injected managed client does not need a local key/database.
- Use bootstrap.build_accounts(database, seeds=...) for account composition. Omitting seeds reads the existing environment configuration; explicit seeds support isolated tests.
- Use bootstrap.create_app(backend) to compose HTTP with one shared authentication instance. No-argument construction remains provider-key optional. interfaces/http/app.py receives authentication explicitly and does not construct dependencies or call back into bootstrap.
- Launch HTTP with uvicorn poisontrace.web:app. Launch benchmark commands with python -m poisontrace. scripts/launch.py starts the local API/dashboard processes.

Backend is a group of constructed dependencies, not another use-case facade. Call backend.runs, backend.campaign_service, backend.scenario_service or backend.credentials directly. backend.store, backend.campaigns and backend.scenarios are the concrete run, campaign and scenario stores supplied to those use cases.

## Interfaces and dependency direction

Domain modules depend only on the standard library and other domain modules. Metrics operate on completed experiment results without models, transport or storage. Application modules depend on domain values and application-owned interfaces, never concrete adapters, configuration, HTTP, CLI or bootstrap. Bootstrap supplies the concrete adapters. HTTP and CLI translate user inputs/results and invoke the application modules.

ScenarioRunner receives AgentModel, TraceStore and ToolGateway. ToolGateway remains the only tool invocation seam. Model responses, discoveries, decisions, blocked attempts, results and recommendations retain their ordered traces. BenchmarkRunner receives a runner factory; bootstrap creates fresh model/trace state for every trial and preserves the distinct single-run approval and benchmark high-impact policies.

ScenarioRepository hides YAML serialization and paths. ScenarioService owns identifier allocation, immutable update identity, draft creation fallback and the usable-scenario gate. Invalid files remain visible and repairable. CampaignScenarioFiles deliberately retains sorted poisoned-filename selection and reload, including the known invalid-file selection issue.

AccountStore supplies transaction-scoped AccountRecords. Application accounts own normalization, scrypt hashing, token generation/hashing, active-account checks and last-active-superadmin restrictions. SQLite owns SQL and the existing commit/rollback scope. Seed usernames, missing-passcode skipping and INSERT OR IGNORE semantics are unchanged. Browser investigation configurations remain distinct from authentication sessions.

Shared SQLite setup remains in adapters/persistence/support.py. Trace, campaign and account stores initialize the same schema. No schema or data migration accompanied this cleanup. Secret storage retains encryption, masks, revocation and managed-client behavior; managed reference metadata still resides in memory.

## Compatibility retirement

There is now one canonical import path for each implementation. The old root agent, provider-model, trace, persistence, scenario, secrets, users, runner, gateway, benchmark, metrics and CLI modules are removed. web_adapter.py and RunWebAdapter are removed. bootstrap.build_adapter was replaced by build_web_backend, which returns Backend directly. The ScenarioStore alias is removed; use YamlScenarioRepository.

This intentionally retires the old Python imports, database-path UserSessionService constructor and forwarding methods. Repository consumers and behavioral tests use the canonical modules. HTTP routes, request/response behavior, CLI commands and storage formats are unchanged. External Python callers must migrate to the paths and factories above.

Unused placeholder errors, duplicate trace protocols and unconsumed scenario/campaign DTOs were removed. Actual TraceEvent and storage interfaces remain in application/ports.py. Tests of retired export identity were removed; behavior tests were migrated, and isolated import checks are consolidated in backend/tests/test_imports.py.

## Verification and remaining behavior work

Run .venv/Scripts/python.exe -m pytest -q and .venv/Scripts/python.exe -m compileall -q backend/src backend/tests. Dependency checks live in test_architecture_boundaries.py; behavior tests exercise application, adapter and HTTP interfaces. The source/test pre-cleanup snapshot is .scratch/backend-cleanup-before.zip. It contains source review copies, not runtime input.

The reorganization did not fix run attribution. Slice one now returns saved run identifiers directly; non-atomic campaign claims, campaign eligibility, request-bound execution without recovery or missing per-user credential/run/campaign/child-trace ownership. Public BYOK privacy, curated read-only scenarios, bounded sessions, runtime packaging and deployment prerequisites remain pending under ADR 0003. Keep those as separately tested behavior changes. Do not infer concurrency, live-provider, clean-install, full-e2e or deployment readiness from the structural checks.


## Slice-one execution and measurement, 2026-11-11

ScenarioRunner selects matched-v1 condition inputs, catches started-attempt failures, records independent recommendation-v1 outcomes and gateway-v1 observations, and returns the saved run ID on ExperimentResult. Model factories are deferred into the attempted execution boundary. Single-run/campaign attribution uses that returned ID. For metadata experiments, ToolGateway.invoke remains the post-completion simulated permission seam; it executes no external MCP tool. The separately versioned MCP path described below uses invoke_evidence for actual reads.

SqliteTraceStore adds outcome_evidence JSON without rewriting historical records. Domain metrics exclude incompatible historic security/task measurements and report counts/denominators per condition; system errors include all saved attempts. RunApplicationService.metrics and GET /api/runs/summary expose history aggregation. Campaign rates include retained rerun attempts, while scenario rows show latest associated children. Results reuses MeasurementSummary and outcomePresentation for accurate labels; Dashboard retains execution and brief recent activity. See [measurement contract](research/SLICE_ONE_MEASUREMENTS.md) for nullable outcomes, compatibility aliases and formulas.

Non-atomic claims, invalid-file campaign selection, mutable campaign inputs, request-bound execution without recovery, and missing per-user ownership remain. Automated tests demonstrate offline implementation behavior only.


## Dashboard and Results separation, 2026-11-11

Ticket #20 moves review into frontend/src/features/results/. RunInspection and CampaignHistory retain existing outcome/trace and campaign inspection behavior. ResultsPage owns saved selection, loading/errors and Overview/Runs/Campaigns views. Dashboard owns configuration, launch, pending status and up to three recent entries. Both use the existing runner API; no backend, scoring or persistence contract changed.

Routes /results, /results/runs, /results/runs/:runId, /results/campaigns and /results/campaigns/:campaignId are analyst-only. App checks the authenticated role before rendering Results. Direct result review does not require a browser investigation configuration. Router content subscribes to pathname changes so parameter-only navigation updates the inspected record. Run and campaign completion navigate with the returned identifiers, never a global-latest lookup. Child links use saved child_run_id. Same-case comparison remains ticket #28.


## First clean MCP investigation, 2026-11-11

application/investigation.py owns the bounded clean loop and safe saved failures. Application ports define InvestigationModel, EvidenceTransport/EvidenceSession and InvestigationCases. Domain values contain the fixture/model-input, qualified definition/call, observation, step and decision contracts. Model input deliberately excludes fixtures and ground truth. ToolGateway.invoke_evidence owns qualified read-only invocation; existing invoke retains its simulated legacy behavior. The new loop does not claim approved-manifest enforcement.

adapters/mcp/ owns the fixed JSON case library, separate stdio server and pinned SDK client/lifecycle. adapters/models/scripted_investigation.py implements offline evidence-dependent continuation. bootstrap supplies these to InvestigationRunner and RunApplicationService. No MCP SDK or transport types enter domain/application. The fixed case snapshot, full discovered definitions, connection identity, call/result ordering and final or partial evidence persist through existing run storage and HTTP detail, using additive outcome_evidence.investigation.

GET /api/runs/investigation-cases lists the bundled fixture. POST /api/runs with workflow=mcp-investigation-v1 requires clean and scripted, without a credential. Existing requests default to metadata-v1. Results renders InvestigationOutcome only for investigation-unscored-v1; historical outcomes and recommendation-v1 remain unchanged. The new observations are excluded from existing security/correctness denominators. See research/CLEAN_MCP_INVESTIGATION.md for contracts, bounds, safety limits and real versus mocked verification.


## Gemini investigations, ticket #22, 2026-11-11

adapters/models/gemini_investigation.py translates the provider-independent next_step contract into asynchronous SDK requests with structured JSON tool choice and returned-observation feedback. It does not invoke tools. RunApplicationService validates explicit Gemini configuration and supplies a request-local deferred model factory to InvestigationRunner. Bootstrap owns provider construction and permits an injected investigation model factory for offline checks. Keys remain in the factory/provider and never enter the MCP transport or saved configuration. The runner bounds provider cleanup and retains configured model identity on initialization failure. Existing metadata/campaign paths remain separate; MCP repeat groups belong to #28.


## OpenAI investigations, ticket #23, 2026-11-12

adapters/models/openai_investigation.py implements asynchronous Responses requests, strict structured call-or-decision output, local schema validation and owned-client cleanup. Provider types and JSON Schema mechanics remain in the adapter. Existing InvestigationRunner owns evidence feedback, gateway calls, validation, safe saved failures and returned IDs. RunApplicationService accepts explicit OpenAI model/credential references through the same request-local deferred factory as Gemini; bootstrap supplies the concrete provider. No new domain or persistence format is needed. Dashboard single-run and campaign requests share actual provider-model identifiers, fixing OpenAI single-run forwarding. Existing metadata reruns retain the campaign's saved model. MCP batch/repeats remain #28.


## Controlled attacks, ticket #24, 2026-11-12

Domain InvestigationAttack values select two fixed family/payload identities through the public domain interface. InvestigationRunner validates the condition, supplies the family to the EvidenceTransport port and saves attack/expected-decision provenance on completed and failed attempts. SyntheticCase.expected_decision stays outside model_input and the child process snapshot. No new storage schema or scoring version is introduced.

LocalSocTransport composes two fresh ClientSession connections with AsyncExitStack and dispatches only by configured server identity. Each SocSession owns discovery and schema validation for its connection. The fixed FastMCP server builder has trusted SOC and controlled advisory roles; the latter receives the selected description before real discovery. Clean uses the same topology with an ordinary advisory description. RunApplicationService validates family/payload selections before credential resolution. Dashboard/Results reuse the existing launcher and inspection components. See research/CLEAN_MCP_INVESTIGATION.md for payloads, offline counterexamples and deferred defense/scoring boundaries.


## Evidence manifest, ticket #25, 2026-11-12

ToolGateway retains the unchanged metadata permission simulation and separately owns evidence_call_policy/invoke_evidence. Application EvidenceManifest compares complete qualified EvidenceTool values against a copied trusted tuple. InvestigationRunner checks every discovered definition before next_step and uses the same manifest at invocation. Bootstrap loads the reviewed static adapters/mcp/approved_manifest.json through approved_evidence_manifest; JSON Schema validation remains in that adapter. Explicit empty approvals are never replaced by discovery. No new SDK dependencies or persistence schema are needed.

The additive investigation.manifest stores discovered/exposed definitions and independent restriction, rejection, successful returned-call and no-call observations. New condition provenance is manifest-mcp-v1; scoring stays investigation-unscored-v1. Results reads this nested evidence and preserves unavailable observations on older records. Provider requests receive only exposed copies. See research/CLEAN_MCP_INVESTIGATION.md for exact stages, counters, failures and offline evidence.


## Structured investigation scoring, ticket #26, 2026-11-12

Domain investigation_scoring.py validates exact supported decision predicates and calculates independent field, goal, marker and reference observations. investigation_metrics.py aggregates separately versioned MCP rates; domain.metrics exposes them additively under investigations without changing recommendation-v1 rate eligibility. Application InvestigationRunner validates returned references, consumes request-local raw text without persisting it, and saves additive investigation.scores/candidate diagnostics. API summaries expose investigation_scores and use joint correctness for presentation tone.

SyntheticCase owns ground-truth validation. RunApplicationService handles restricted ground-truth editing through the InvestigationCases port; BundledCases owns local JSON overrides, stale-version checking and atomic replace. Bootstrap supplies a directory beside the run database. The editor changes only ground truth/category and increments case version; identity/evidence/payloads remain outside that API. Provider adapters attach raw output to InvestigationStep; provider/MCP types remain outside application/domain. Transport excludes all expected labels and targets from the child snapshot. Dashboard's small editor and Results/Overview consume these application contracts.

## Corpus and canonical output, ticket #27, 2026-11-12

BundledCases combines the retained authentication fixture with fourteen packaged corpus JSON files. Its catalog exposes category and immutable supported_attack_families; each case override uses its own identifier path. SyntheticCase checks nonempty read collections and unique evidence identifiers, and validates target allocation. Application creation rejects an unallocated attack before credential resolution or execution. ToolGateway remains the sole invocation seam. Transport excludes allocation along with ground truth from child snapshots. The wider event-evidence description has a matching reviewed manifest.

InvestigationDecision now requires close/escalate, with recommendation detail retained in explanation. Provider schemas/prompts are v2; ScriptedInvestigationModel is scripted-soc-v2/evidence-loop-v2. Runner provenance records canonical-handling-v2. Exact investigation-scoring-v1 calculations and historical persistence parsing are unchanged; there is no rescore or fuzzy conversion. Existing HTTP/editor contracts work across all cases and preserve immutable evidence/allocation. See research/SYNTHETIC_RESEARCH_CORPUS.md for the rubric and public-seam verification.

## Fixed payload revision v2, 2026-11-12

The domain attack catalog now supplies soc-auth-description-v2 and soc-auth-shadow-v2. The same two families, transport selection, case allocation and ToolGateway seam apply. No provider, scoring, manifest or persistence format changes accompany this revision. Exact historical v1 and active v2 descriptions are archived in docs/research/payloads/, with primary-source rationale in research/MCP_PAYLOAD_REVISION_V2.md. Saved records retain their original payload/definition snapshots; active catalog changes do not reinterpret history.

## Matched investigation groups, ticket #28, 2026-11-17

application/run_groups.py creates and executes explicit selected-case schedules through RunApplicationService.prepare_investigation and InvestigationRunner.run_snapshot. The runner receives a pinned case for every attempt while ToolGateway remains the invocation seam. Bootstrap supplies provider prompt/schema/settings profiles and the SQLite group adapter. No case/target snapshot enters model input or the MCP child environment.

adapters/persistence/run_groups.py owns additive run_groups/run_group_attempts tables, atomic execution claims and preallocated condition/repeat slots. Every saved result carries group_id/group_attempt/group_repeat and returns its run ID directly for association. Reruns append slots and preserve prior attempts. Execution stays synchronous and request-bound; process/storage-loss recovery is outside this slice. Unlinked slots remain missing, never fabricated failures.

domain/run_groups.py checks each linked result against the immutable plan and calculates separately eligible per-condition rates. Full prompt/schema/settings, case/evidence/targets, payload, approved/discovered/exposed definitions and contract versions participate. Intended clean/poisoned/defended differences are checked against condition-specific expectations. Initialization failures without known prompt/settings remain excluded from matched rates but count in all-saved reliability. Missing requested conditions and conditions intentionally not scheduled are separate. Historical campaign/history aggregation remains unchanged.

HTTP /api/run-groups supplies create/list/detail and POST /{group_id}/execute. Dashboard's Matched group controls execution and reruns; Results /results/groups/{group_id} supplies comparisons and individual run links. tests/test_run_groups.py exercises the application/HTTP/SQLite/real-MCP seams, including both offline SDK providers. Browser journeys cover group creation, refresh, evidence links, clean-control restrictions and retained reruns. See research/MATCHED_RUN_GROUPS.md for the exact contract and limitations.
