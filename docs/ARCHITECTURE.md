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

The reorganization does not fix latest_run_id correlation after execution, non-atomic campaign claims, campaign eligibility, request-bound execution without recovery or missing per-user credential/run/campaign/child-trace ownership. Public BYOK privacy, curated read-only scenarios, bounded sessions, runtime packaging and deployment prerequisites remain pending under ADR 0003. Keep those as separately tested behavior changes. Do not infer concurrency, live-provider, clean-install, full-e2e or deployment readiness from the structural checks.
