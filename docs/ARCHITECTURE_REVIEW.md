# PoisonTrace architecture review

Current backend guide: [ARCHITECTURE.md](ARCHITECTURE.md). Compatibility retirement is complete: 67 source files became 48 by removing 19 obsolete compatibility files after caller migration. The final cleanup assessment below supersedes earlier retention/next-slice notes. Earlier frontend findings remain historical and were not changed in this cleanup.

Current authority: see [Current assessment and migration plan, 2026-11-03](#current-assessment-and-migration-plan-2026-11-03) below. Earlier sections are historical and include findings already fixed. Public/local requirements are in ADR 0003 and deployment evidence is in DEPLOYMENT_REVIEW.md.

The reorganization progress sections at the end track completed extractions after that assessment. Credentials, runs and campaigns now own behavior in application modules; web/CLI construction and the persistence, YAML, secrets, domain and account organizational slices are complete. The final current-ownership sections in ARCHITECTURE.md and this review supersede older next-slice notes.

Date: 2026-11-02

This is an organization review only. It does not change product behavior or
propose a big-bang rewrite.

## Current findings

### Frontend

- `src/pages/DashboardPage.jsx`, `SessionsPage.jsx`, and `ScenarioPage.jsx`
  contain route composition, data loading, mutations, local state, and large
  presentation trees in the same modules. The largest are approximately 515,
  412, and 330 lines.
- `src/utils/webAdapter.js` is a feature API client, but it sits beside
  unrelated auth, session, router, and sidebar helpers. The generic `utils`
  name hides ownership and makes dependency direction hard to enforce.
- `src/utils/router.js` contains both the canonical route declarations and
  compatibility navigation helpers. Routes are not represented as route
  modules, even though TanStack Router is already the application router.
- `src/components/common/Ui.jsx` is a mixed shared-component bucket, while
  feature-specific components remain inside oversized pages.
- `src/styles.css` is a 1,331-line global stylesheet. It contains tokens,
  layout, route-specific styles, and component styles without a visible
  ownership boundary.
- `AuthenticatedHeader.jsx` is at the `src` root rather than in the layout
  shell. `dashboard-preview/`, `reference-prototype.*`, and `dist/` are
  separate artifact surfaces and should be explicitly classified as source,
  preview, generated output, or disposable material.

### Backend

- `web_adapter.py` is a 428-line mixed boundary. It defines HTTP routes,
  translates payloads, selects model adapters, manages credentials, runs
  scenarios, executes campaigns, serializes responses, and handles HTTP error
  mapping.
- `trace.py` contains both trace persistence and campaign persistence. These
  are separate application concepts and should have separate repository
  modules even if they share one SQLite connection or database file.
- `scenario_loader.py` and `scenario_store.py` both participate in parsing and
  validation. The loader creates the domain object, while the store also
  validates documents and decides how invalid files are represented and
  repaired.
- The package is flat. Domain contracts, application use cases, HTTP
  interfaces, CLI interfaces, model adapters, persistence, and secret storage
  are all siblings under `poisontrace/`.
- Tests are mostly organized by behavior, which is good, but the module
  boundaries they exercise are not reflected in the production folders.

## Recommended target structure

### Frontend

Use feature-oriented modules with a thin application shell. Keep the HTTP
boundary in feature API modules and keep route files focused on URL params,
loaders/actions, and page composition.

```text
frontend/
├── src/
│   ├── app/
│   │   ├── App.jsx
│   │   ├── providers.jsx
│   │   └── router.jsx
│   ├── routes/
│   │   ├── __root.jsx
│   │   ├── login.jsx
│   │   ├── sessions/
│   │   │   ├── index.jsx
│   │   │   └── $sessionId.jsx
│   │   ├── dashboard.jsx
│   │   └── scenarios/
│   │       ├── index.jsx
│   │       ├── new.jsx
│   │       └── $scenarioId.jsx
│   ├── features/
│   │   ├── auth/
│   │   │   ├── api/authApi.js
│   │   │   ├── model/auth.js
│   │   │   ├── components/LoginForm.jsx
│   │   │   └── tests/auth.test.js
│   │   ├── sessions/
│   │   ├── scenarios/
│   │   │   ├── api/scenarioApi.js
│   │   │   ├── components/ScenarioLibrary.jsx
│   │   │   ├── components/ScenarioEditor.jsx
│   │   │   ├── model/scenarioDraft.js
│   │   │   └── tests/scenarioApi.test.js
│   │   ├── runs/
│   │   └── campaigns/
│   ├── components/
│   │   ├── layout/AuthenticatedShell.jsx
│   │   └── ui/
│   ├── lib/
│   │   ├── http/client.js
│   │   └── errors.js
│   ├── styles/
│   │   ├── tokens.css
│   │   ├── globals.css
│   │   └── components/
│   └── main.jsx
├── tests/
│   └── e2e/
└── public/
```

Do not create folders for every possible category up front. Create a feature
folder when it owns API calls, state, and more than one component. Keep shared
UI genuinely product-agnostic. Do not let feature modules import from other
feature modules; compose them in `app` or a route module.

### Backend

Use explicit layers inside feature/application boundaries. The domain must not
import FastAPI, SQLite, model SDKs, or filesystem details.

```text
src/poisontrace/
├── domain/
│   ├── models.py
│   ├── policies.py
│   ├── events.py
│   ├── errors.py
│   └── ports.py
├── application/
│   ├── scenarios.py
│   ├── runs.py
│   ├── campaigns.py
│   ├── credentials.py
│   └── dto.py
├── adapters/
│   ├── models/
│   │   ├── fake.py
│   │   ├── openai.py
│   │   └── gemini.py
│   ├── tools/
│   ├── persistence/
│   │   ├── sqlite_trace_store.py
│   │   ├── sqlite_campaign_store.py
│   │   └── sqlite_credentials.py
│   ├── scenarios/
│   │   └── yaml_repository.py
│   └── secrets/
├── interfaces/
│   ├── http/
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   ├── schemas.py
│   │   └── routers/
│   │       ├── scenarios.py
│   │       ├── runs.py
│   │       ├── campaigns.py
│   │       └── credentials.py
│   └── cli/
│       ├── commands.py
│       └── main.py
├── bootstrap.py
└── __main__.py
```

The application layer should receive ports and return typed application DTOs.
HTTP routers should validate request schemas, call one use case, and map
application errors to responses. The bootstrap module should construct the
SQLite, YAML, model, tool, and secret adapters. This gives tests a direct seam
without importing the HTTP app.

## Safe migration order

1. Add import-boundary tests and a short architecture rule document. Do not
   move files yet.
2. Split `web_adapter.py` into HTTP routers, application services, and a
   bootstrap composition root. Preserve the existing public adapter temporarily
   as a compatibility facade until tests move.
3. Split `trace.py` into trace and campaign persistence modules behind the same
   protocols.
4. Finish the scenario boundary: one scenario document validator, one YAML
   repository, and one scenario application service for CRUD and usable lookup.
5. Move frontend HTTP calls from `utils/webAdapter.js` into feature API modules.
6. Split the three largest pages into route components plus feature components.
7. Convert the canonical route tree to route modules only after the compatibility
   navigation tests cover every settled route and auth redirect.
8. Split CSS by ownership after component moves. Keep tokens global and avoid
   copying selectors into feature files without a real owner.
9. Classify or remove generated/disposable frontend artifacts and add ignore
   rules for `dist/`, `node_modules/`, local databases, and preview output where
   appropriate.

## References

- FastAPI, "Bigger Applications - Multiple Files":
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI full-stack template, showing separate backend and frontend
  development surfaces and a modern FastAPI/React/Vite stack:
  https://github.com/fastapi/full-stack-fastapi-template
- TanStack Router, "Route Trees":
  https://tanstack.com/router/latest/docs/routing/route-trees
- TanStack Router, "File-Based Routing":
  https://tanstack.com/router/latest/docs/routing/file-based-routing
- Bulletproof React, "Project Structure":
  https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md
- Bulletproof React, repository architecture rules and feature layout:
  https://github.com/alan2207/bulletproof-react/blob/master/AGENTS.md

These references are patterns, not templates to copy wholesale. PoisonTrace is
small enough to keep a simpler version of each pattern.

## Confirmed review, 2026-11-03

This review supersedes the earlier path inventory, not its historical record. Runtime code is unchanged. Existing working-tree moves and edits were preserved.

| Rank | Severity / value | Evidence and finding | Small refactoring slice, benefit and risk |
| --- | --- | --- | --- |
| 1 | High verification gap / high | Full suite returns 59 passed, 17 failed. Campaign HTTP tests receive 401; other tests reference absent canonical scenarios. Current STATUS baselines understate failures. | Repair synthetic test fixtures and authenticate HTTP clients through login. Preserve explicit unauthenticated/forbidden checks. Restores trustworthy interface tests; risk is accidentally weakening authorization to satisfy old tests. Never bypass production middleware. |
| 2 | Medium / high | App.jsx writes window.__poisontraceUser, Auth and SignOut; Sidebar, SessionWorkspace and AdminUsers consume global defaults. Shared layout depends on render order outside its declared interface. | Pass existing identity and sign-out values explicitly through route modules and dashboard layout. This improves locality and test leverage at the auth seam. Risk: sign-out callback ordering and navbar-free sessions regression. Cover role destinations and logout before removing globals. Strong. |
| 3 | Medium / high | application/services.py delegates runs/campaigns to RunWebAdapter through WebOperations.__getattr__ returning Any. Credentials reach operations.secrets and private _credential_dict. RunWebAdapter still owns execution, serialization and persistence coordination. | Move credential orchestration first into its existing module, retaining the compatibility adapter interface. Test public masked outputs and rejected credentials. Depth increases when callers no longer know storage internals. Risk: secret disclosure or altered exception mapping. Strong. |
| 4 | Medium / medium | interfaces/http/app.py creates two UserSessionService instances from adapter.store.database. Middleware and admin router both resolve user and role. users.py owns hashing, seeding, SQL and account rules. | Compose one existing user module instance and inject it into routers. Later centralize request identity resolution with tests for disabled accounts and both roles. Improves locality; risk: dropping a protection while deduplicating checks. Do not split users.py into hypothetical adapters merely for file size. Worth exploring. |
| 5 | Medium / medium | App.jsx manually dispatches paths through routeRenderer while route modules mostly forward props. Scenario routes repeat Sidebar composition; dashboard owns its own layout. | Consolidate authenticated analyst layout only after explicit auth props. Keep sessions navbar-free and admin isolated. Deletion test: forwarding route modules alone add little depth; removing them now would only move route knowledge back into App. Risk: navigation and responsive drawer behavior. Worth exploring. |
| 6 | Low / medium | authApi re-exports utils/auth; adminApi implements its own JSON transport while lib/http/client lacks status metadata and always decodes successful bodies. | Define consistent status and empty-body behavior before moving auth/admin onto shared transport. Tests must retain 401 session-null behavior and admin error detail. Leverage comes from shared error handling, not another forwarding module. Risk: changing login error semantics. Worth exploring. |
| 7 | Low / high | web_adapter.py create_app returns create_http_app before a complete legacy HTTP implementation. | Delete only the unreachable reference block in a separate small slice after baseline repair. Active routers are authoritative. Improves navigability without altering the interface. Risk is low but diff must confirm only unreachable code removal. Strong. |

### Domain and ADR alignment

ADR 0001 is reflected by the scenario repository and ScenarioService usable-scenario gate. Keep invalid-file repair separate from execution. ADR 0002 is reflected by backend role enforcement, active-user lookup and last-active-superadmin checks. Browser globals are ownership friction, not evidence of a backend authorization bypass. Frontend investigation sessions are browser-stored experiment configurations in utils/sessions.js; backend auth_sessions identify authenticated users. Keep these concepts distinct.

ARCHITECTURE.md still describes intended external seams accurately, but does not describe the transitional HTTP delegation. ARCHITECTURE_RULES.md still describes PT-ARCH-002 as future work. The import checks cover domain and selected frontend folders, not runtime role policy, global state, or all feature dependency directions. Passing them is limited evidence.

### Keep unchanged for now

Keep domain contracts independent of frameworks, gateway-only tool invocation, scenario identity and invalid-file behavior, trace/campaign persistence separation, masked credential references and the compatibility facade. Do not redesign the user database, add session expiry or audit history deferred by ADR 0002, introduce a general repository framework, or move all styles as part of this review. No ADR revision is justified by the confirmed findings.

### Verification and next slice

Full Python suite: 59 passed, 17 failed, one Starlette/httpx deprecation warning. Focused architecture/contracts/scenario tests: 9 passed. Python compilation passed. Frontend tests and build were attempted but no active Node.js version is configured. Next recommended slice is test-baseline repair, followed by explicit authenticated-layout props. Runtime implementation is deferred because the current baseline cannot reliably protect route behavior.

### Baseline repair follow-up, 2026-11-03

The verification gap ranked first above is repaired: 76 Python tests pass. Test-owned scenarios now isolate the suite from editable development files, HTTP investigation clients authenticate explicitly, and stale result/trace expectations match current behavior. Frontend verification remains blocked by unavailable Node.js. The next architectural candidate is explicit authenticated-layout dependencies.

## Current assessment and migration plan, 2026-11-03

This section supersedes the earlier inventories, rankings and baseline claims above. It assesses the current working tree, including the completed redesign. Paths below are relative to Project. ADRs 0001 and 0002 remain authoritative; ADR 0003 records the newly agreed public BYOK and local distribution requirements. No broad folder migration was performed.

### Confirmed fixes and useful compatibility seams

- Explicit identity and auth props replaced browser globals. `frontend/src/app/App.jsx:103-105` supplies them; `components/layout/Sidebar.jsx:4` accepts them. A current source search finds no `__poisontrace` references. Do not re-plan this completed work.
- HTTP routers already live under `backend/src/poisontrace/interfaces/http/routers/`. Trace and campaign storage already live in `persistence/traces.py` and `persistence/campaigns.py`. `trace.py:1-6` deliberately preserves old import paths. Deleting this compatibility module moves import churn to callers without improving locality.
- Feature HTTP modules already exist for scenarios, runs, campaigns and credentials. `frontend/src/utils/webAdapter.js` composes their interface for existing callers. This is a useful transitional adapter, rather than evidence that all transport still lives in utils.
- Tests use test-owned scenarios and authenticated investigation clients. Node 22 is usable through a process-local PATH. Earlier broken-baseline and unavailable-Node claims are historical.

### Ranked findings

Severity describes current correctness or deployment impact. Value describes implementation value; effort/risk and prerequisites determine sequencing.

| Priority | Severity / value | Current evidence | Small slice, depth and risk |
| --- | --- | --- | --- |
| P0 | High public-launch blocker / high | `persistence/support.py:9-12` has no user owner on runs/campaigns; `secrets.py:105-109` has no credential owner. `interfaces/http/app.py:25-34` authorizes roles without supplying an owner to use cases. | Carry backend-resolved identity through one credential interface, persist ownership, enforce it for every operation, then extend to runs/campaigns/traces. Cross-user HTTP tests must deny reads and mutations. High risk; requires a migration policy for existing ownerless data. Do not infer owners from browser configuration IDs. |
| P0 | High concurrent correctness / high | `web_adapter.py:138,265,318` reads global latest run ID after execution. `runner.py` discards the ID returned by `save_result`. Campaign check and state update at `web_adapter.py:226-240` are separate. | Return the actual saved run ID, then atomically claim campaign execution. Test overlapping completions and duplicate execution through the execution interface. Medium risk; preserve existing runner callers using an intentional compatibility path. One worker alone does not serialize requests. |
| P1 | Medium / high | `application/services.py:21-22` permits arbitrary attributes through `Any`; lines 83-103 expose secrets and private serialization. `web_adapter.py:340-351` owns credential writes. | Give credential orchestration direct ownership of the existing secrets adapter and masked output. Cover missing storage, provider mismatch, save/replace/revoke, and redaction before moving bodies. Then add owner-aware contracts for the public profile. Medium risk because exception mapping and secret handling must remain stable. |
| P1 | Medium / high | `web_adapter.py:159-162` directly loads every filename matching poisoned instead of using usable-scenario lookup. Malformed matches can fail campaign creation. | Test a library containing valid and invalid poisoned files, then route eligibility through the existing scenario module. Preserve filename-based campaign selection and ADR 0001 repair behavior. Behavior change requires red-green tests. |
| P1 | Medium / medium | `interfaces/http/app.py:17,40` constructs authentication twice; middleware line 26 and `routers/admin.py:9-16` repeat identity resolution. | First inject the same existing user module instance into auth/admin routers. Deduplicate request identity only separately, retaining disabled-account and both-role checks. Low initial risk; no speculative user repository hierarchy. |
| P2 | Low / medium | `frontend/src/app/App.jsx:71-190` dispatches paths; scenario branches repeat Sidebar at 102,125,148. Route modules mostly forward props. | Consolidate analyst layout in composition, preserving navbar-free sessions and isolated admin. Route forwarding alone adds little depth: deletion merely moves props back to App. Route ownership should move with behavior, with focused browser checks. Medium risk. |
| P2 | Low / medium | `utils/auth.js:31-61` and `features/admin/api/adminApi.js:1-14` own transport behavior separately from `lib/http/client.js`. | Agree status/error/empty-body handling in the shared HTTP interface before migrating auth/admin callers. Preserve session-null on 401 and logout 204 semantics. Medium risk; use existing transport interface tests. |
| P2 | Low / medium | `utils/sessions.js:11-16` loads unvalidated JSON; `App.jsx:27-30` and `features/sessions/SessionWorkspace.jsx:22-39` separately consume browser persistence. | Concentrate configuration parsing, validation and selection in the sessions feature. Preserve current saved settings. The public edition also needs owner-scoped browser state or clearing on account change to meet private-data requirements. Keep backend authentication sessions distinct. |
| P2 | Low / medium | `main.jsx:3,7` loads legacy then redesign styles. Session styles occur in `styles.css:194-423` and `redesign.css:227-237`; SessionWorkspace additionally imports layout CSS. | Consolidate one owned selector group at a time, preserving load order until rendered equivalence is verified. Renaming stylesheet files does not remove cascade dependencies. Medium visual regression risk; compare populated desktop/mobile screens and scroll containment. |
| Done | Low / high navigability | `web_adapter.py:354-361` is the active compatibility factory. An unconditional return formerly preceded 127 lines of duplicate HTTP definitions. | Removed only unreachable definitions. Active routers, factory defaults, endpoint mappings and adapter methods remain unchanged. No new abstraction or behavior test was needed for dead-code deletion; existing HTTP tests exercise the active interface. |

### Ownership target

Create modules when a migration slice gives them real behavior. This is an ownership map, not a request to create empty folders.

```text
backend/src/poisontrace/
  domain.py                    benchmark values and policy-neutral contracts
  application/
    credentials.py             credential orchestration, ownership, masked results
    runs.py                    model/gateway/runner composition and run identity
    campaigns.py               selection, claims, execution and recovery
    services.py                temporary compatibility imports during extraction
  scenario_service.py          scenario eligibility and CRUD policy
  scenario_store.py            YAML documents, safe paths and atomic writes
  persistence/                 traces, campaigns, shared schema; ownership migrations
  secrets.py                   encrypted/managed secret adapters
  users.py                     coherent account and authentication module
  interfaces/http/             request translation, identity and error mapping
  web.py                       configuration and concrete composition
  web_adapter.py               retained caller interface until bodies move

frontend/src/
  app/                         composition, identity and shared route layout
  routes/                      URL-specific composition when it owns behavior
  features/{auth,admin,sessions,scenarios,runs,campaigns,credentials}/
                               feature state, presentation and HTTP adapters
  lib/http/                    transport mechanics only
  components/layout/           shared authenticated presentation
  components/common/           product-independent controls
  styles.css, redesign.css     transitional cascade; DESIGN.md is visual authority
  utils/                       compatibility exports until consumers migrate
```

Keep model adapters, gateway and runner filenames stable until a real extraction requires a move. Existing fake/live model and in-memory/SQLite adapters justify those seams. Preserve domain independence and gateway-only tool execution. The deletion test rejects adding a file for every forwarding method: it would increase interface knowledge without hiding implementation.

### Migration order and verification

1. Completed here: remove unreachable HTTP definitions after a green baseline.
2. Next backend structural slice: credential orchestration with an explicit adapter interface and masked results. Keep owner migration a separately tested change, rather than silently changing existing local data semantics.
3. Public correctness slices: saved run ID, atomic campaign claim, ownership schema/backfill decision and cross-user authorization, then usable campaign eligibility. These must precede a public release.
4. Deployment foundation: runtime dependency set, explicit persistent paths, profile settings, curated public library, secure sessions and secret-safe operation. See DEPLOYMENT_REVIEW.md for launch gates and remaining operational decisions.
5. Durable execution and recovery behind one submission/status interface. Retain SQLite on a single host initially if measured load permits; a distributed database is not a prerequisite to fixing identity or job claims.
6. Frontend composition, transport and local configuration ownership can follow independently. CSS consolidation is last unless a current visual defect requires it.

Public BYOK requirements raise the priority of ownership and concurrency over cosmetic folder moves. Existing local behavior must remain usable. No ADR 0001 identity/repair decision or ADR 0002 role permission is reopened by this plan. Public session expiry is an explicit readiness requirement recorded in ADR 0003, not implemented here.

Before and after dead-code removal: Python 76 passed with the existing Starlette/httpx warning; frontend 31 passed and production build passed at baseline. Post-change compilation and final verification are recorded in STATUS.md. No routes or UI behavior changed, so no browser check was required for this slice. The entire e2e suite has not been established as passing; older workspace tests still require migration. Import checks and annotation-presence tests do not prove dynamic contract correctness, ownership or concurrency safety.


## Reorganization progress: credentials, 2026-11-03

The first recommended structural slice is complete. Credential operations and masked serialization moved from services.py and RunWebAdapter to application/credentials.py. Application-owned ports.py now defines the full secrets interface and reference value; concrete adapters remain in secrets.py until the adapter-relocation slice. HTTP composition calls the new credential module directly. Existing RunWebAdapter write methods and old class/type import paths remain compatibility seams.

This resolves credential access through WebOperations.__getattr__, operations.secrets and private _credential_dict. Dynamic delegation still exists for runs/scenarios/campaigns. No owner fields, authorization policy, schema, provider validation, key-retention behavior or cryptographic mechanism changed. The public BYOK blocker remains until owner-aware access is implemented.

The approved backend target uses domain/, application/, adapters/, interfaces/, config.py and bootstrap.py. Create each module as behavior moves into it; avoid empty packages and forwarding-only files. Next extract actual run behavior, then campaign behavior, then composition/configuration and concrete adapters. Keep scenario identity/repair decisions and role restrictions unchanged. Test run-ID correctness and ownership as explicit behavior slices rather than hiding them in path moves.


## Reorganization progress: runs, 2026-11-03

Run creation, list/detail queries, usable-scenario lookup error translation and summaries now live in application/runs.py. Dependencies enter through explicit storage, scenario, model-factory and secret interfaces, rather than WebOperations.__getattr__. HTTP composition uses adapter.runs directly. Existing RunWebAdapter methods, application/services.py class imports and web_adapter.ScenarioNotFound imports remain compatibility seams.

TraceEvent and TraceStore moved to the shared application ports, with persistence/trace exports preserved. ScenarioRunner now imports its model and trace contracts without pulling concrete persistence or the fake model into the run module. A python -S import check confirmed application.runs imports without site packages, SQLite, YAML, FastAPI, Cryptography or vendor SDKs. The application module can therefore be exercised through its own interface without HTTP composition.

Before editing runtime code, an HTTP characterization test passed for summaries/details, saved configuration, trace order and 400/404 rejections. Eight direct application cases then protected clean/poisoned/defended behavior, chosen provider/model/key injection, redaction, mismatched credential rejection and rejection before model construction. Import checks enforce the new dependency direction. AST review confirmed the moved method implementations differ only in dependency names.

The known latest_run_id race was preserved deliberately in this structural slice and now appears in application/runs.py as well as the remaining campaign orchestration. No claim of concurrent correctness or private multi-user storage is made. Next extract campaign behavior and then config/bootstrap; verify saved IDs, atomic claims and ownership in explicit behavior changes.


## Reorganization progress: campaigns, 2026-11-03

Campaign behavior now lives in application/campaigns.py behind explicit campaign/run storage, filename selection/loading, model-factory, summary and secret interfaces. The former forwarding-only CampaignApplicationService is replaced by a compatibility import. HTTP composition passes the constructed application instance directly; RunWebAdapter retains its existing campaign store attribute and delegates its campaign methods. Existing child trace additions are preserved.

CampaignStore moved to application/ports.py with its persistence import retained. CampaignScenarioFiles in scenario_loader.py hides filesystem/YAML mechanics without changing the sorted filename rule or invalid-file failure behavior. Direct application tests use in-memory campaign storage and injected model construction; HTTP tests retain SQLite persistence coverage and characterize errors and ordered traces.

No listed correctness or public-launch blocker is resolved by this extraction. Latest-run correlation and non-atomic claims now reside in application/campaigns.py; selection eligibility remains in CampaignScenarioFiles. Execution remains request-bound and ownership is absent. Next organize validated configuration and explicit bootstrap construction, then relocate concrete adapters, organize domain/account modules and remove compatibility paths only after callers migrate. Keep behavior fixes separately reviewed and tested.


## Reorganization progress: web configuration/bootstrap, 2026-11-03

Web concrete construction moved from web.py, RunWebAdapter and the HTTP app factory into bootstrap.py. WebConfig provides explicit path values, existing environment-key loading and local-key validation without optional dependencies. build_backend constructs shared dependencies and supports injected model construction; build_adapter retains the legacy configured facade and managed-secret client. No-argument compatibility app creation still works without secrets. Relative path defaults are deliberately unchanged.

The HTTP factory receives a single authentication instance for middleware and both account routers. ScenarioService is supplied directly to its router, removing active dynamic scenario forwarding while preserving the old class import. RunWebAdapter and web factory imports remain compatible. Importing bootstrap starts neither HTTP nor storage.

This is the web sub-slice of configuration/bootstrap. CLI construction, account seed environment loading and launcher validation remain in their current modules. Next extract CLI construction while preserving its protected-tool/approval and benchmark policies, then relocate concrete adapters. No owner enforcement, saved-run correlation, atomic claim, usable-campaign eligibility, durable execution or public-profile behavior was added. ADR decisions and all public blockers remain in force.


## Reorganization progress: CLI composition, 2026-11-03

CLI concrete model selection, single-run construction and benchmark factory construction now live in bootstrap.py. cli.py retains parsing, scenario loading, invocation, metrics and text output. Historical imports, PROTECTED_TOOL_NAMES and _model_for remain available. Tests replace concrete constructors at bootstrap and exercise both CLI command output and the explicit construction interfaces.

Single-run protected-tool approval and benchmark empty-high-impact behavior are intentionally distinct and unchanged. Every benchmark trial still receives a new model and in-memory trace store. Trial counts, negative-count rejection, manifest policy, Gemini diagnostics and environment-provider-key fallback are preserved. Web secrets/auth imports became factory-local so sharing bootstrap does not add a web-key or encryption dependency to CLI execution.

The configuration/bootstrap organizational slice now covers web and CLI construction, with account seed configuration explicitly deferred to account separation. Next relocate concrete models, persistence, YAML and secrets into adapters/ in small reviewed moves with compatibility exports. Domain organization and account behavior/persistence separation follow, then compatibility cleanup. Saved IDs, atomic claims, campaign eligibility, recovery and ownership remain separate unresolved behavior work.


## Reorganization progress: model adapter relocation, 2026-11-03

The concrete fake, OpenAI and Gemini implementations moved unchanged into adapters/models/. Bootstrap and facade imports use the canonical modules. Legacy model modules re-export the same classes and provider schema objects. No common model registry, wrapper hierarchy or new orchestration interface was introduced; the existing AgentModel/ModelFactory seam remains sufficient.

All three implementation files match their pre-slice bytes. Provider tests now use canonical imports, compatibility tests verify class/schema identity, and existing execution tests continue covering legacy fake imports. Package initializers avoid eager model imports, and isolated fake imports require no optional packages. Existing provider SDK import behavior and runtime dependency gaps remain unchanged.

Next relocate trace/campaign persistence, then YAML/secrets, preserving old imports and shared database/schema behavior. Domain/account separation and compatibility cleanup follow. This structural relocation does not resolve any saved-ID, campaign-claim, eligibility, recovery, ownership or public-hosting blocker.


## Persistence adapter relocation, 2026-11-03

Concrete trace and campaign stores now live in adapters/persistence/traces.py and campaigns.py. adapters/persistence/support.py owns the unchanged shared schema initializer, including existing account/session tables and additive setup. Storage protocols and TraceEvent remain application-owned. Bootstrap, facade and account setup import canonical adapters; persistence/* and trace.py retain identical class/type/function exports for historical callers.

The moved implementations match .scratch/persistence-adapters-before after only the support import substitution. Tests cover historical export identity, initialization in either store order, reopening persisted results/events/campaign child associations, ordering, account/session retention and existing errors. No schema migration, account separation, run correlation, campaign claiming, eligibility, recovery or ownership behavior changed.


## YAML adapter relocation, 2026-11-03

adapters/scenarios/loader.py owns unchanged YAML parsing and CampaignScenarioFiles filename selection/reload. adapters/scenarios/repository.py owns YAML documents, filesystem lookup, validation, atomic writes and invalid-file representation. application/scenarios.py owns the existing scenario CRUD, identifier allocation, immutable update identity and usable-scenario gate. Its application-owned ScenarioRepository interface hides filesystem paths and serialization; write_document and load are real repository operations. Historical scenario_loader/scenario_store/scenario_service exports retain object identity. Bootstrap and production callers use canonical imports.

The loader matches pre-slice bytes; application bodies match after replacing concrete serialization/loading with injected repository operations. Existing read/write validation differences, draft creation fallback, error behavior and direct campaign YAML eligibility remain unchanged. Tests cover invalid draft repair, stable filenames/IDs, failed replacement preserving the original file, deletion and campaign reload/error behavior. Do not infer that this move implements the ADR 0001 campaign usable-scenario requirement. No routes or UI behavior changed.


## Secrets adapter relocation, 2026-11-03

adapters/secrets/storage.py owns the encrypted SQLite and managed implementations. Keeping both implementations together preserves their existing shared masking behavior without introducing another helper interface. ManagedSecretClient joins CredentialReference and SecretsAdapter in application/ports.py. Credential use cases remain in application/credentials.py. Historical secrets.py exports preserve object identity; bootstrap/facade construction imports canonical storage. CLI factories still defer secret imports.

Both concrete class bodies match the pre-slice ASTs in .scratch/secrets-adapters-before. Encryption, key fallback, retention, replacement/revocation, masks, managed callbacks/client behavior and exception handling are unchanged. Managed reference metadata remains in memory. No ownership or public-profile behavior is added.


## Domain organization, 2026-11-03

Pure benchmark values now live in domain/values.py, marker/redaction rules in domain/rules.py and metric calculations in domain/metrics.py. domain/__init__.py preserves the existing poisontrace.domain interface. metrics.py preserves identical Metrics/calculate_metrics exports. All existing class/function bodies match pre-slice ASTs; metrics changes only its domain-values import.

BenchmarkRunner is execution coordination, so its unchanged implementation moved to application/benchmark.py with a historical benchmark.py export. ScenarioRunner remains application coordination at its existing path for this slice; ToolGateway retains its policy/enforcement role and remains the only tool-execution seam. Neither execution timing, persistence, model construction nor SDKs moved into domain. Bootstrap/CLI use canonical metric and benchmark imports. Domain import checks inspect the whole package, and isolated python -S imports require no optional packages or application/adapters.


## Account separation, 2026-11-03

application/accounts.py owns account values, normalization, scrypt hashing/comparison, authentication, token creation/hashing, current-user checks, logout, analyst creation and lifecycle rules. Its AccountStore/AccountRecords interfaces expose a transaction scope without SQLite types. adapters/persistence/accounts.py implements SQL and existing commit/rollback scopes against the unchanged shared schema. config.py reads the existing seed environment variables into immutable, repr-redacted AccountSeed values; bootstrap.build_accounts constructs storage and applies those seeds. HTTP auth/admin/middleware share the same canonical application instance.

Historical users.AuthUser and AuthenticationError exports retain identity. users.UserSessionService remains a temporary constructor compatibility subclass accepting a database path and delegating construction to bootstrap; canonical application construction takes storage. It retains the historical database attribute. Existing seed order, skip-absent behavior, INSERT OR IGNORE semantics, account fields, password/session hashing, active-status checks, login timestamps and last-active-superadmin guard are preserved. Transaction scoping matches the original sqlite3 context managers; this move adds no stronger concurrency or expiry guarantee.

Characterization tests passed before extraction. Canonical tests cover explicit seeds, repr redaction, rollback and isolated imports. A synthetic pre/post comparison against .scratch/accounts-before matched outcomes/errors, stored hashes, seed records, roles and session rows, excluding cross-database timestamps. Public ownership, finite expiry and account policy are unchanged. Browser investigation configurations remain separate from authentication sessions. Launcher validation is unchanged.


## Current reorganization assessment after caller migration, 2026-11-03

All requested organizational responsibilities now have canonical owners under domain, application, adapters and interfaces, with config/bootstrap composition. ARCHITECTURE.md contains the current ownership table and ARCHITECTURE_RULES.md contains enforceable dependency rules. Execution/gateway coordination moved out of the flat package into application; CLI translation moved into interfaces. Historical modules remain where identity/constructor compatibility still has callers or explicit tests.

Caller migration allowed removal of application/services.py, its dynamic WebOperations/scenario forwarding and four uncalled private RunWebAdapter forwarding methods. Public facade methods and historical import identities remain tested. No wrapper hierarchy, generic repository base class, speculative package or schema migration was added. AccountRecords is an internal transactional seam that keeps policy and password/session behavior in application while preserving the prior SQL commit/rollback scopes. ScenarioRepository hides YAML serialization and path mechanics while keeping repair and eligibility decisions in application.

Reviewed moved implementations against .scratch pre-slice copies. Persistence code differs only in its setup import. YAML loader and benchmark coordination moved byte-for-byte. Secret/domain class and function ASTs match. Scenario use cases and CLI main differ only in injected operations/imports and deletion of a forwarding hop. Account extraction was characterized before edits and compared against the prior implementation using synthetic data; outcomes, errors, hashes and stored session/account records match, excluding cross-database timestamps.

Remaining work is behavioral and operational, not fixed by placement: return the actual saved run ID, make campaign claims atomic, apply the usable-scenario gate to filename-selected campaigns, provide durable execution/recovery and implement backend-resolved owner enforcement with a migration policy. Public profiles, session hardening and clean installation/packaging remain deployment prerequisites under ADR 0003. Scenario validation differences and allocation concurrency remain as documented. Browser investigation configurations remain distinct from auth sessions. Do not delete the remaining compatibility facades without reviewing their callers and tests.


## Backend cleanup assessment after compatibility retirement, 2026-11-03

The user's current priority is a clear backend source tree. Repository consumers have migrated off RunWebAdapter, old root re-export modules, the old persistence package and the database-path users constructor. Those 19 source files are removed. Six files remain directly in the package root: __init__, __main__, config, bootstrap, launcher and web. Canonical modules under domain/application/adapters/interfaces own real responsibilities and remain separate where merging would reduce cohesion.

build_web_backend now returns Backend directly. HTTP composition requires explicit authentication and no longer delegates back into bootstrap. Behavior tests call application interfaces directly; the former facade tests are folded into test_bootstrap.py. Pure compatibility-export tests are retired, and isolated import tests are consolidated. ScenarioStore and the unused repository delete forwarder are removed. Unused error classes, duplicate trace protocols and unconsumed scenario/campaign DTOs are gone, while actual contracts remain.

This is an intentional Python import/factory break. HTTP routes, CLI commands, default paths, key requirements, seed rules and storage behavior are preserved. Compared 22 canonical implementation modules against the pre-cleanup snapshot; class/function definitions match apart from the explicitly removed unused repository delete forwarder. Shared schema bytes are unchanged. No route, UI, schema or account-policy change was made. Earlier compatibility requirements in this review describe completed migration stages and are superseded by the user's cleanup request.

The next structural action is to use the current ownership guide for changes and avoid reintroducing duplicate paths. Remaining saved-run identity, campaign claims/eligibility, ownership and durable execution are separate behavior work. No public deployment readiness is claimed. ARCHITECTURE.md and ARCHITECTURE_RULES.md were rewritten as current guides rather than accumulating more transitional instructions; their pre-cleanup contents are preserved in .scratch/backend-cleanup-docs-before.zip.
