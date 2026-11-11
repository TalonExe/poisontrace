# Architecture rules

Current after compatibility retirement, 2026-11-03. ARCHITECTURE.md is the source-ownership guide. These rules replace earlier transitional placement/compatibility rules; the prior document is retained in .scratch/backend-cleanup-docs-before.zip.

## Backend dependencies

- domain/ imports only the standard library and other domain modules. It contains pure values, rules and calculations, never frameworks, SQLite, YAML, vendor SDKs or execution coordination.
- application/ owns use cases and required interfaces. It may depend on domain and other application modules. It must not import adapters, bootstrap, configuration, HTTP/CLI or vendor SDKs. Account use cases use only standard-library dependencies.
- application/ports.py owns the actual model, scenario, trace/run, campaign and secret contracts. application/accounts.py owns account values and transaction-scoped account record interfaces. Do not add duplicate placeholder contracts or error hierarchies for hypothetical consumers.
- adapters/models/ depends on domain and provider SDKs. It must not import orchestration, persistence, secrets, YAML or entrypoints. FakeModel imports without optional packages.
- adapters/persistence/ depends on domain, application ports/account values and its shared schema helper. SQL and database setup do not belong in use cases. Shared setup includes the existing account/session tables; structural moves do not authorize migrations.
- adapters/scenarios/ owns YAML parsing/filesystem mechanics. application/scenarios.py owns CRUD/identity and usable lookup decisions, through ScenarioRepository. Preserve invalid-file repair, atomic writes and existing errors.
- adapters/secrets/ implements the application-owned secret interfaces. Masked response behavior stays in application/credentials.py. Never expose plaintext in responses, traces or source.
- config.py has only standard-library dependencies. It validates the existing web key and loads repr-redacted account seed configuration.
- bootstrap.py constructs concrete dependencies. Application modules never import it. HTTP composition requires an injected authentication instance, shared by auth/admin/middleware, and does not call back into bootstrap.
- interfaces/cli.py translates arguments/output and invokes bootstrap execution factories. It constructs no concrete models, runners, gateways or stores. CLI execution imports no web-only secret/account/auth modules. Keep its single-run and benchmark policies distinct.
- Tool invocation stays behind application/gateway.py. Execution coordination and benchmark trials remain outside domain.
- web.py and __main__.py stay thin. launcher.py owns local process startup; do not mix that with experiment CLI translation.

## One canonical implementation

- Production and tests import canonical modules. The retired root compatibility modules, persistence package, users constructor wrapper and RunWebAdapter facade must not return.
- Factories return already composed dependencies. Do not add forwarding-only facade classes or rename-only aliases. Use build_backend, build_web_backend, build_accounts and create_app in bootstrap.
- Keep module files when they own a coherent responsibility. Do not merge independent responsibilities merely to lower file count, and do not introduce speculative packages.
- Python import retirement is intentional. HTTP routes, CLI commands, schema/data, account policy and benchmark behavior remain unchanged. Behavior changes require focused red-green tests.

## Frontend rules retained

- Reusable frontend/src/utils modules do not import pages, UI or app composition.
- Shared frontend/src/components/common UI does not import pages or state utility modules.
- Pages/routes and app composition may compose lower-level modules. Tests are consumers, never production dependencies.

## Checks and limitations

backend/tests/test_architecture_boundaries.py inspects imports and construction placement, including retired imports in tests and source. backend/tests/test_imports.py exercises isolated optional-dependency-free imports. Behavioral tests cover use cases, storage, scenarios, secrets and HTTP roles.

These checks do not establish owner isolation, atomic campaign claims, saved-run identity, campaign eligibility, durable recovery, public-profile enforcement or deployment readiness. Preserve ADR 0001 identity/repair, ADR 0002 account/role restrictions and ADR 0003 public/local requirements. Browser investigation configurations are not auth sessions.
