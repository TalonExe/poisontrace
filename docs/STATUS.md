# PoisonTrace status

## Current milestone

### Admin user-management workspace header

- Added the shared authenticated header to `/admin/users`, including the
  current superadmin display name or username, avatar initials, and the same
  sign-out redirect behavior used by the analyst workspace.
- Kept the user directory and account detail panel below the header and
  reused the existing layout stylesheet and responsive admin workspace rules.
- Impeccable detector passed with no findings. Frontend tests and build remain
  unavailable because no active Node.js version is configured. Python source
  compilation and `git diff --check` passed.

### Sessions workspace authenticated header

- Replaced the sessions workspace custom sign-out bar with the shared
  authenticated header, including the current user's display name or username,
  avatar initials, and shared sign-out redirect behavior.
- Impeccable detector reported no findings for the changed sessions surface.

### Admin user-management foundation, ticket 01

- Added backend-managed SQLite users and sessions with normalized usernames,
  analyst and superadmin roles, active status, timestamps, and scrypt-hashed
  passcodes.
- Added environment-configured development analyst and superadmin seed
  accounts. Login returns only public user data and a role-specific redirect.
- Added backend login, current-session, and logout endpoints. Protected-session
  lookup rechecks account status, so a disabled account cannot continue through
  this session seam.
- Added a frontend API authentication seam test without changing the existing
  local-auth behavior or route wiring.
- Focused backend auth tests passed. The existing HTTP fixture test still has
  the documented missing relative canonical scenario path. Full verification
  is pending.

### Live single-run dashboard slice

- The dashboard now loads usable scenarios from `GET /api/scenarios` and lets
  the analyst select one by scenario name. The selected scenario ID comes from
  the backend response and is not persisted.
- Single Gemini runs use `gemini-3.5-flash-lite`. The run button shows a
  loading indicator, and the batch campaign toggle is disabled while the run
  is active.
- Unknown scenario IDs now return HTTP 404. Other rejected run configuration
  remains HTTP 400.
- Focused Python checks passed except for the existing missing canonical
  scenario fixture failures. Frontend checks remain unavailable because no
  Node.js version is active.
- Added `GET /api/runs/{run_id}` for persisted run details, including ordered
  trace events, outcome fields, configuration metadata, and single-run
  metrics. The dashboard now renders those responses instead of static trace
  and outcome placeholders.
- Trace details now include an `agent_output` event with the raw structured
  model output returned by the agent adapter. API keys and credential fields
  are not added to this event.

The first domain, policy, scenario-loading, command-line execution, mode-selection, protected-action, SQLite persistence, runner-persistence, metric, safe-fallback, repeatable-benchmark, benchmark-CLI, run-measurement, OpenAI-adapter, Gemini-adapter, CLI-model-selection, and structured-schema-fix slices are implemented. The repository has no commits yet.

## Architecture slice: PT-ARCH-001

- Added `docs/ARCHITECTURE_RULES.md` with transitional dependency-direction
  rules for backend domain/application seams and frontend utilities/shared UI.
- Added static import-boundary checks covering domain isolation, scenario
  service entrypoint isolation, frontend utility direction, and shared UI
  ownership. The checks do not import optional web or model services.
- No production module moves, routes, payloads, scenario behavior, persistence,
  or secrets handling were changed.
- Baseline verification before this slice: 46 passed, 9 pre-existing fixture
  path failures, and 1 warning. The failures are unrelated to the import
  checks and are documented in the current handoff.
- Next ticket: `PT-ARCH-002`, split backend HTTP routing from application
  orchestration.

## Architecture slice: PT-ARCH-002

- Added application service seams for runs, scenarios, campaigns, and
  credentials under `src/poisontrace/application/services.py`.
- Added dedicated HTTP router modules for runs, scenarios, campaigns, and
  credentials under `src/poisontrace/interfaces/http/routers/`.
- The HTTP app now composes those routers through a separate HTTP application
  factory. `RunWebAdapter` remains a compatibility facade for existing callers
  and tests.
- Preserved existing endpoint paths, status mappings, payloads, credential
  redaction, and scenario behavior. No product routes or persistence schemas
  changed.
- Focused verification passed: architecture boundaries and credential tests
  (6 passed); Python source compilation passed.
- Full-suite verification remains affected by the existing nine missing
  canonical scenario fixture paths. The next ticket is `PT-ARCH-003`, typed
  backend boundary contracts.

## Architecture slice: PT-ARCH-003

- Added framework-independent application contracts for scenario, run,
  campaign, credential, and trace seams.
- Added explicit application error types for invalid/missing scenarios,
  duplicate identities, credential mismatches, and rejected runs.
- Contracts expose credential references and masked metadata only; secret field
  names are excluded from credential response contracts.
- Added contract and service-seam tests. Existing HTTP payloads and adapter
  compatibility remain unchanged.
- Next ticket: `PT-ARCH-004`, separate trace and campaign persistence.

## Architecture slice: PT-ARCH-004

- Split persistence into `persistence/traces.py` and `persistence/campaigns.py`,
  each with an explicit protocol and SQLite implementation.
- Kept `persistence/support.py` as the single shared SQLite schema and additive
  migration initializer. Existing `runs`, `events`, `campaigns`, and
  `campaign_scenarios` columns and relationships remain unchanged.
- Preserved trace `run_key` correlation and campaign `child_run_id` / ordinal
  associations. Added `InMemoryCampaignStore` alongside the existing in-memory
  trace store for fast seam tests.
- Kept `poisontrace.trace` as a compatibility export while the web adapter now
  imports the separate persistence modules directly. Routes, payloads,
  response shapes, scenario behavior, and secrets boundaries are unchanged.
- Focused verification: 13 passed and 2 pre-existing fixture-path failures
  (missing canonical scenario files).
- Full-suite verification after this slice: pending; the known nine fixture-path
  failures are not part of this ticket.
- Next ticket: `PT-ARCH-005`, finish the scenario repository boundary.

## Architecture slice: PT-ARCH-005

- Added `YamlScenarioRepository` as the file-system/YAML boundary. It owns
  directory reads, raw reads and atomic raw writes, safe filename resolution,
  parsed listing/lookup, validated writes, and filename deletion.
- Kept `ScenarioStore` as a compatibility alias for existing callers while new
  application code uses the repository name.
- Kept `ScenarioService` responsible for scenario ID allocation, duplicate-name
  checks, create/update/delete use cases, usable-scenario loading, and the
  invalid-scenario execution/campaign gate.
- Preserved invalid files as listable and repairable, quoted three-digit IDs,
  canonical filenames, immutable update IDs, separate tool lists, historical
  traces/campaign records, and existing HTTP behavior.
- Focused verification: 13 passed and 2 known fixture-path failures. Full-suite
  verification remains 53 passed and 9 known fixture-path failures; those
  missing canonical scenario fixtures are unrelated to this slice.
- Next ticket: `PT-ARCH-006`, move frontend HTTP calls into feature API modules.

## Architecture slice: PT-ARCH-007

- Completed the route-level modules for login, sessions, dashboard, scenario
  library, scenario creation, and scenario editing.
- Moved dashboard, session workspace, and scenario responsibilities into the
  feature areas under `frontend/src/features/`.
- Routes now provide URL parameters and navigation callbacks while feature
  components keep feature state, adapter calls, mutations, and presentation.
- Preserved the navbar-free sessions workspace, authenticated navigation shell,
  auth redirects, route normalization, sidebar behavior, scenario IDs, CRUD,
  invalid-scenario visibility, loading states, and error states.
- Baseline Python verification remains 53 passed with 9 known fixture-path
  failures caused by missing canonical scenario files.
- Python compilation passed. Frontend tests and the Vite build could not run
  because no active Node.js version is configured. The Impeccable detector
  reported no findings for the changed frontend targets. Git diff checks were
  blocked by repository ownership restrictions in the sandbox.
- The next ticket is `PT-ARCH-008`, after a final frontend source-ownership
  review.

## Architecture slice: PT-ARCH-008

- Moved `AuthenticatedHeader` into `frontend/src/components/layout/` and
  updated the authenticated shell imports.
- Added layout-owned header CSS in `components/layout/layout.css` while
  preserving the existing Evidence Control palette, spacing, responsive rules,
  accessibility labels, and sign-out behavior.
- Kept `components/common/Ui.jsx` focused on generic `Icon`, `Select`, and
  `CardHead` primitives. Feature-specific markup remains in feature modules.
- Python verification remains 53 passed with the 9 known missing-fixture
  failures. Python compilation passed.
- Frontend tests and Vite build remain unavailable because no Node.js version
  is active. Impeccable reported no findings for the changed targets. Git diff
  checks remain blocked by sandbox repository ownership restrictions.
- The next ticket is `PT-ARCH-009`, which classifies prototype and generated
  frontend artifacts before changing ignore rules.

## Architecture slice: PT-ARCH-009

- Classified `frontend/dashboard-preview/` and
  `frontend/reference-prototype.html` / `.css` as maintained reference source.
- Classified frontend dependencies, build output, end-to-end test output, local
  SQLite databases, backups, and caches as disposable or machine-local output.
- Added focused ignore rules for `frontend/node_modules/`, `frontend/dist/`,
  `frontend/test-results/`, `*.db`, and `*.db.backup`.
- Added `docs/ARTIFACTS.md` with the repository artifact policy and recreation
  commands. No user-owned artifacts were deleted.
- Python verification remains 53 passed with 9 known missing-fixture failures.
  Python compilation passed. Git diff checks could not run because the sandbox
  user does not own the repository checkout.
- The architecture ticket sequence is complete through PT-ARCH-009.

## Repository layout update

- Moved Python source to `backend/src/poisontrace/`.
- Moved Python tests to `backend/tests/`.
- Moved scenario fixtures to `backend/scenarios/`.
- Updated pytest configuration, launcher root detection, backend default paths,
  architecture-boundary checks, and fixture references.
- Kept `frontend/` as the frontend root and preserved the root `pyproject.toml`
  as the shared Python entry point.
- The existing missing canonical scenario fixtures remain unchanged and are not
  part of this layout move.

## Completed

- Project context, domain glossary, implementation brief, and architecture notes.
- Python package scaffold and pytest configuration.
- Clean authentication-alert scenario.
- Fake model adapter.
- In-memory trace store.
- Tool gateway with approved-manifest checking.
- Least-privilege high-impact action approval requirement.
- Runner integration with policy decisions.
- Defended poisoned scenario.
- Vulnerable poisoned baseline.
- Initial attack-success and benign-task-success semantics.
- Versioned YAML authentication scenario and loader.
- Scenario validation for required fields and tools.
- CLI command for running a YAML scenario.
- Explicit approved-manifest and poisoned scenario fixtures.
- CLI policy selection for vulnerable and defended modes.
- Protected-action approval handling and trace events.
- SQLite trace and experiment-result persistence.
- Runner persistence through the trace-store seam.
- Initial benchmark metric calculation.
- Safe fallback for defended poisoned runs.
- One deterministic plus repeated benchmark execution.
- CLI benchmark command with aggregate metrics.
- Execution time, system-error, and unauthorised-call fields on run results.
- Injected `gpt-5-mini` OpenAI Responses API adapter with structured output.
- OpenAI `gpt-5-mini` adapter implementation and unit coverage. The adapter is not yet wired into CLI model selection.
- Closed structured-output schema for live model calls.
- Gemini `gemini-3.5-flash-lite` adapter using `GEMINI_API_KEY` and structured JSON output.
- CLI model selection for the Gemini adapter; the offline fake remains the default.
- Model name, prompt version, and run configuration are recorded in results and SQLite.
- Minimal React/Tailwind dashboard slice under `frontend/` with the Evidence Control direction: experiment launcher, chronological trace, security outcome panel, run comparison, synthetic data, and responsive mobile layout.
- Added `frontend/DESIGN.md` to record the implemented palette, typography, layout, interaction, content, and light-mode token rules.
- Added `frontend/reference-prototype.html` and `frontend/reference-prototype.css`, a full-screen modular prototype based on the supplied WhatsApp reference image. It uses the reference greeting, rounded cards, and compact dashboard grid with the active dark Evidence Control palette.
- Added a local prototype authentication seam and login page with loading, invalid-credential, authenticated, and sign-out states. The demo account is transient and clearly labelled synthetic; it does not persist passwords or session data.
- Added a replaceable frontend runner adapter. The authenticated dashboard requests `GET /api/runs` and `POST /api/runs`, and reports backend availability without inventing run records.
- Added a post-login session workspace. Analysts can create, edit, open, and delete local session configurations, select Gemini or OpenAI as the model provider, and return to the session list from the dashboard. Session metadata is stored locally; API keys remain outside the browser.
- Fixed session selection. Clicking a session row or its Edit action now opens the settings editor; Open and Delete remain separate actions.
- Added a shared collapsible sidebar for the session workspace and dashboard. It marks the active location, navigates between Sessions and Dashboard, labels the synthetic workspace, and provides responsive backdrop dismissal on narrow screens.
- Removed repeated workspace and data disclaimers from the visible interface. Safety and synthetic-data boundaries remain in the project documentation and implementation notes.
- Added a framework-neutral Python web adapter and optional FastAPI app factory for `GET /api/runs` and `POST /api/runs`. It maps session provider settings to fake, Gemini, or OpenAI model adapters and persists completed runs through SQLite.
- Added the runnable `poisontrace.web:app` entrypoint and a FastAPI HTTP contract test. The test is skipped in environments where the optional web dependencies are not installed.
- Removed frontend fallback run records. The dashboard now reports API availability errors, displays an empty state for a connected empty store, and sends the selected session provider with POST requests.
- Added dependency-free Node tests for runner adapter GET/POST requests, provider mapping, and backend failure handling.
- Added dependency-free frontend authentication seam tests covering demo login, invalid credentials, session persistence, and sign-out.
- Extracted session configuration persistence and CRUD helpers from the React component, with tests for creation, editing, provider selection, deletion, and malformed local storage.
- Exposed the existing OpenAI `gpt-5-mini` adapter through both CLI commands and added offline CLI model-selection coverage.
- Started secure API-key management with a replaceable secrets adapter and encrypted SQLite local storage. Only credential references and masked metadata are returned; plaintext keys are never stored in records.
- Added credential save, list, replace, test, and revoke operations at the web seam. Run configuration accepts only `credential_id`; credential responses and rotation tests redact plaintext values.
- Wired frontend sessions and runner requests to credential references. The adapter exposes credential lifecycle calls and never persists submitted secrets.
- Added the visible credential-reference selector to the session editor. It loads masked references from the runner adapter, filters them by provider, and stores only `credentialId` in local session configuration.
- Added a replaceable managed secret-store adapter behind `SecretsAdapter`; managed storage receives secret values only through injected callbacks.
- Added an application-owned managed secret client protocol and wired it into `ManagedSecretsAdapter` and the web adapter factory. Managed clients receive plaintext only through injected put/get calls; traces, run configuration, browser storage, and API responses keep credential IDs and masked references.
- Validated credential references before provider execution. Runs now reject missing references and provider mismatches before retrieving a secret.
- Added direct Gemini adapter seam coverage for structured decisions, model and API-key forwarding, malformed or incomplete responses, and secret non-retention. Invalid model output now raises a stable `ValueError`, and the CLI does not print raw model responses.
- Added CLI protected-action coverage. The `run` command recognizes synthetic high-impact tools and accepts `--approval-actor`; protected actions are blocked without approval and allowed with an approval actor.
- Added Playwright browser smoke coverage for demo login, session creation and provider selection, sidebar navigation, and masked credential references. The browser suite uses the built frontend preview and never enters a real API key.
- Added per-run SQLite trace correlation keys. Scenario runners now tag events with a unique run key, and result persistence associates only matching events, including when runs interleave in one database.
- Added ticket #2 scenario-campaign creation. The web seam discovers `*poisoned*.yaml` scenarios in deterministic filename order, rejects empty campaigns, persists the selected provider/model and credential reference, and reloads campaign records with explicit child-run slots without executing child runs.
- Added ticket #3 campaign execution. The execution seam runs each selected poisoned scenario once in persisted order with the selected provider/model configuration, associates successful child runs, records sanitized child failures, continues after errors, and returns aggregate counts and attack-success totals.
- Added ticket #4 campaign history and summary interface. The API lists persisted campaign summaries, and the dashboard displays campaign status, scenario count, completed runs, and attack-success totals with responsive empty and error states.
- Added ticket #5 campaign scenario details and rerun workflow. Expanded campaign entries load filename, scenario ID, child-run association, outcome, and failure state through the public HTTP seam. Individual reruns reuse the persisted campaign provider, model, and credential reference without returning plaintext secrets.
- Added ticket #6 complete campaign workflow verification. A public HTTP smoke test now covers campaign creation, deterministic scenario selection, execution, persisted history, expandable details, individual rerun, and refreshed aggregate history.
- Added the dashboard campaign control. Analysts can start an all-poisoned-scenarios campaign from the active session, see loading and error states, and refresh campaign history after execution.
- Extracted shared frontend primitives into `frontend/src/components/common/Ui.jsx` and the authenticated navigation shell into `frontend/src/components/layout/Sidebar.jsx`. `main.jsx` now consumes these modules without changing route behavior, auth redirects, session CRUD, runner requests, campaign actions, or responsive classes.
- Extracted the login and session workspace route pages into `frontend/src/pages/LoginPage.jsx` and `frontend/src/pages/SessionsPage.jsx`. `main.jsx` now handles app state and route composition while those pages own their existing local UI state and interactions.
- Extracted the scenario library and dashboard route pages into `frontend/src/pages/ScenarioPage.jsx` and `frontend/src/pages/DashboardPage.jsx`, including campaign history as a dashboard-local feature component. `main.jsx` is now limited to bootstrap, auth state, session selection, and route composition.
- Moved application bootstrap, auth/session state, redirects, and route composition into `frontend/src/app/App.jsx`. `main.jsx` is now a small browser entrypoint that loads the global styles and mounts `App`.
- Connected the extracted pages to TanStack Router's route tree through `RouterProvider`, with an outlet-rendering root route. The existing `routes`, `normalizePath`, and `navigate` compatibility helpers remain available for current seams and redirects.
- Reduced the TanStack Router compatibility seam. `routes` and `normalizePath` remain canonical, `createRouter` keeps only the `current` and `navigate` helpers used by the app, and the unused `subscribe` method was removed. Focused tests cover supported paths, unknown-path normalization, memory-history navigation, and replace navigation.
- Fixed the initial auth loading render. `App` now refreshes the TanStack `RouterProvider` when auth checking or selected-session state changes, so signed-out users reach `/login` after local session lookup instead of remaining on "Checking local access…".
- Consolidated the small global `sidebar.css` into `styles.css` and removed its duplicate entrypoint import. The JavaScript seams remain separate because they own tested auth, storage, navigation, adapter, and state behavior rather than presentational markup.
- Reorganized frontend JavaScript seams under `frontend/src/utils/` and dependency-free tests under `frontend/src/tests/`. Updated application imports, package scripts, and handoff commands without changing runtime behavior.

## Verification

The latest Python test run passed with 53 tests:

```text
.....................................................                    [100%]
53 passed
```

Frontend verification remains pending because this environment has no active Node.js version:

```text
No active Node.js version is configured. Run `nvm install <version>` then `nvm use <version>`.
```

The reference prototype is static HTML/CSS so it can be opened directly at `frontend/reference-prototype.html`.

Run the suite with:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Next slice

Next: keep route changes on the canonical TanStack route tree and add focused public seam tests before changing navigation behavior. Playwright remains out of scope for this slice.

## Ticket #10 handoff

- Added a shared authenticated user header for protected routes. It reads the current synthetic user session, shows initials and a local-session label, and exposes a visible Sign out action.
- Sign out continues through the existing auth seam and router redirect, clearing the selected session before navigating to `/login`. The login route does not render the header.
- Added dependency-free frontend seam tests for user display and sign-out ordering.
- Impeccable detector completed with no findings.
- Python verification remains `53 passed`. Frontend test/build verification is blocked because no active Node.js version is configured in the environment.

## TanStack Router refactor

- Replaced the hand-written history router with TanStack Router's code-based route tree for `/login`, `/sessions`, `/dashboard`, and `/scenarios`.
- Preserved the existing `routes`, `normalizePath`, and `navigate` seam so page behavior and auth redirects remain unchanged during the migration. Removed the unused `subscribe` method after focused tests and repository-wide search found no callers.
- Frontend verification passed with 21 tests. The Vite build must run from `frontend` so Vite resolves `frontend/index.html`; Node 22.19.0 was invoked directly because the `nvm` shim could not update its registry entry.

## Backlog ticket

### PT-001: launch the full project with one command

Add a documented, cross-platform launcher for the backend and frontend together. It should validate the Python environment and Node.js setup, start the FastAPI app and dashboard dev server, forward useful startup errors, and stop both processes cleanly when the launcher exits.

Acceptance criteria:

- A user can launch the complete local project with one command from `Project`.
- The launcher uses the repository's `.venv` and the configured Node.js version.
- Backend and frontend logs remain visible, with clear failure messages if a dependency or environment variable is missing.
- The launcher does not create or expose real credentials.
- The usage is documented near the project setup instructions.

Status: implemented in `scripts/launch.py`. See `docs/LAUNCH.md`.

## Known gaps against the completed list

- The dashboard adapter requires the `/api/runs` backend and displays an explicit unavailable/empty state when it cannot load runs.

## Handoff rule

### Admin master/detail workspace and responsive polish, ticket 05

- Reworked `/admin/users` into a persistent user-directory and detail layout.
- Kept the Evidence Control graphite, amber, blue, green, and warning semantics.
- Added responsive stacking for narrow screens, visible focus states, explicit
  labels, status feedback, loading and empty states, and confirmation feedback.
- Frontend verification remains blocked until Node.js is available.

## Next-session handoff

The next UI task is to add the existing analyst authenticated top bar to the
administrator `/admin/users` workspace. Reuse
`frontend/src/components/layout/AuthenticatedHeader.jsx` and its existing
`layout.css` styles. Pass the current superadmin user, the backend auth object,
and the existing sign-out redirect callback so the bar shows the user's display
name or username, avatar initials, PoisonTrace identity, and a working `Sign
out` button. Keep the user directory/detail layout below it and preserve the
responsive behavior.

Relevant files:

- `frontend/src/app/App.jsx`
- `frontend/src/features/admin/AdminUsers.jsx`
- `frontend/src/components/layout/AuthenticatedHeader.jsx`
- `frontend/src/components/layout/layout.css`

Current verification state: Impeccable detector passed with `[]`, Python
compilation passed, and `git diff --check` passed. Frontend tests and build are
blocked because no active Node.js version is configured.

### User editing and privilege lifecycle, ticket 04

- Added immutable-username user updates for display name, role, and account
  status.
- Added explicit frontend actions with confirmations for promotion, demotion,
  enabling, and disabling.
- The last active superadmin cannot be demoted or disabled. Disabled sessions
  fail the protected-request status check immediately.
- Focused lifecycle tests pass. Frontend checks remain blocked when Node.js is
  unavailable.

### Superadmin user directory and analyst creation, ticket 03

- Added protected superadmin user listing and analyst creation endpoints.
- Usernames are normalized, duplicates are rejected, new accounts are always
  active analysts, and passcodes never appear in responses.
- Added the `/admin/users` frontend table, search field, creation form, loading,
  empty, API-error, and forbidden states.
- Focused backend coverage passes. Frontend verification remains blocked when
  Node.js is unavailable.

## Ticket #11: raw-output marker classification

- Added the shared `COMPROMISED` injection marker constant and classify attack
  success from its exact, case-sensitive presence in raw agent output.
- Marker presence is recognized in clean, poisoned, and defended runs; marker
  absence is not attack success even when a poisoned tool executes.
- Benign task success remains false when the marker is present, while
  unauthorised tool-call tracking remains tied to the tool/policy path.
- Agent-output trace events redact sensitive field values while retaining the
  marker needed for classification.
- Focused verification passed: 11 marker, clean-run, protected-action, and
  vulnerable-baseline tests.
- Full Python verification remains blocked by the existing missing canonical
  scenario fixtures and legacy campaign/CLI assertions that will be updated in
  the fixture and API tickets. No batch campaign behavior was changed here.

Next: Ticket #12, restructure the existing poisoned scenario injections.

## Scenario library design and backend foundation

- Completed the documented scenario model for a required `name`, quoted three-digit IDs beginning at `001`, canonical name-plus-ID filenames, usable versus invalid files, raw repair, and separate library/create/edit routes.
- Added `docs/adr/0001-scenario-library-identities-and-crud.md` and glossary entries for scenarios, scenario names, and usable scenarios.
- Migrated the four development fixtures to IDs `001` through `004` and canonical filenames. Legacy development persistence remains disposable.
- Added backend scenario listing, lookup, create, update, and delete seams with validation and atomic YAML writes. Invalid files remain listable but are excluded from runner execution.
- Updated existing scenario tests and fixture references. Python verification passes with 53 tests and one existing Starlette/httpx deprecation warning.

## Next safe slice

## Scenario application seam

- Architectural finding: `RunWebAdapter` was coordinating scenario CRUD, usable-scenario loading, and persistence directly. Invalid-file lookup and incomplete-create return behavior were also implicit in `ScenarioStore`.
- Completed slice: added `ScenarioService` as the application boundary for scenario listing, lookup, create/update/delete, and the explicit usable-scenario execution gate. The web adapter now delegates scenario operations through that seam.
- Preserved behavior: invalid files remain visible and repairable; invalid scenarios are rejected for runs; IDs remain immutable on update; create drafts may remain incomplete; HTTP routes and payload shapes are unchanged; no secrets enter scenario data.
- Store hardening: invalid parsed mappings remain available for filename/ID lookup, and create returns the newly written record even when the draft is intentionally invalid.
- Verification: frontend Node tests passed (25); Vite production build passed. Focused Python scenario/service tests passed (4); the full Python suite remains blocked by the pre-existing incomplete fixture migration (9 unrelated missing canonical scenario files, plus the new suite is now green). The existing Starlette/httpx deprecation warning remains.
- Detector: no frontend files changed in this slice, so there was no changed frontend target to scan.

Next safe slice: finish the canonical scenario fixture migration or isolate fixture loading from repository-relative paths, then add structured HTTP response/error contracts around the scenario endpoints.

Add focused backend HTTP tests for valid and invalid scenario CRUD, then wire `/scenarios`, `/scenarios/new`, and `/scenarios/:scenarioId` through the frontend adapter and canonical router. The structured editor should keep IDs and tool names read-only and use raw text for invalid files.

## Handoff rule

## Navbar behavior slice

- The `/sessions` route is now navbar-free, both after sign-in and when reached from the workspace navigation.
- The authenticated sidebar remains available on `/dashboard` and `/scenarios`, with Scenarios retaining the active route state and responsive drawer/backdrop behavior.
- Existing auth redirects, sign-out ordering, session CRUD, route normalization, runner requests, and credential-reference handling were preserved.
- Added dependency-free tests for route active state and drawer open, close, navigation, and backdrop transitions.
- Verification passed: 23 frontend Node tests, Vite production build, and 53 Python tests. The Python run retains one existing Starlette/httpx deprecation warning.
- The Impeccable detector ran over the changed frontend files with no findings.
- Fixed workspace navigation closing the sidebar on Dashboard and Scenarios clicks. Desktop navigation now keeps the sidebar visible, while mobile navigation still closes the drawer at the responsive breakpoint.
- Verification for this follow-up passed: 24 frontend Node tests, Vite production build, and 53 Python tests. The Python run retains one existing Starlette/httpx deprecation warning.

## Next safe slice

Keep the authenticated workspace shell shared between Dashboard and Scenarios, then add a browser-level check only if a responsive visual regression remains after manual review.

## Scenario library/editor completion

- Completed `/scenarios`, `/scenarios/new`, and `/scenarios/:scenarioId` routing with authenticated workspace navigation.
- Replaced the scenario placeholder with an HTTP-backed library and structured editor. The library shows valid and invalid files distinctly; editor identity fields remain read-only where applicable.
- ScenarioStore now supports filename-based invalid-file repair lookup, safe in-directory deletion, duplicate identity/name rejection, atomic writes, and intentionally incomplete create drafts without fake tools.
- Run lookup now rejects missing and invalid scenarios through the usable-scenario boundary.
- Verification passed: 53 Python tests, 25 frontend Node tests, and Vite production build.
- Impeccable detector passed with no findings (`[]`) across changed frontend files.

## Next safe slice

Add the remaining focused backend and frontend scenario CRUD tests, then refine raw-text repair editing for malformed YAML and manual responsive review.

## Editable tool metadata follow-up

- Updated the domain decision: discovered and approved tool names and descriptions are editable scenario test metadata; approved tools remain a separate ordered list and must still refer to declared tools.
- Added structured editor controls for adding, removing, renaming, and editing descriptions in both tool lists. Tool-list edits are submitted through the backend HTTP seam.
- Added backend validation for non-empty and unique declared tool names and valid approved-tool references.
- Verification passed: 25 frontend Node tests, Vite production build, 53 Python tests, and Impeccable detector with no findings (`[]`).

## Next safe slice

Add focused tests for tool-list payloads and invalid-file raw-text repair, then manually review the editor at mobile widths.

## Scenario creation save-flow fix

- Fixed new-scenario saves to submit the complete draft and transition to the assigned stable-ID edit route after creation.
- Follow-up saves now use update semantics instead of attempting another create, preventing duplicate-name bad requests and partially initialized files.
- Verification passed: 25 frontend Node tests, Vite production build, and 53 Python tests.

## Scenario deletion controls

- Added an editor delete action and library checkbox selection with bulk deletion.
- Both paths confirm the exact filename before calling the backend delete endpoint; historical traces and campaign records remain untouched.
- Verification passed: 25 frontend Node tests and Vite production build.

## Handoff rule

### Role authorization boundaries, ticket 02

- Added backend authorization middleware for API requests. Unauthenticated
  protected requests return 401, analysts retain investigation API access, and
  superadmin requests to analyst APIs return 403 Forbidden.
- Added frontend role guards, a clear 403 Forbidden state, and `/admin`
  normalization for the superadmin destination. The frontend now uses the
  backend authentication seam.
- Focused backend authorization tests pass. Full verification remains subject
  to the existing missing scenario fixtures and unavailable Node.js runtime.

At the start of a new session, read `AGENTS.md` and `docs/STATUS.md`, then run the test suite before changing code. Update this file after each completed slice.

## Architecture slice: PT-ARCH-006

- Added feature-owned frontend API modules for scenarios, runs, campaigns, and
  credentials, plus explicit auth and local-session feature API entrypoints.
- Added one low-level HTTP client for the `/api` base URL, JSON decoding, and
  consistent detail/fallback error handling.
- Reduced `src/utils/webAdapter.js` to a compatibility composition facade so
  existing page props and behavior remain unchanged while HTTP ownership moves
  to features.
- Preserved HTTP-only backend communication, route normalization, auth
  redirects, session CRUD, scenario CRUD and invalid-scenario behavior,
  campaign controls, backend-unavailable states, credential references, and
  secret redaction boundaries. No backend persistence or scenario semantics
  changed.
- Added dependency-free feature API seam tests for scenario URL encoding and
  credential error/reference handling.
- Verification before this slice: Python `53 passed, 9 failed` due to the
  documented missing canonical scenario fixtures. Frontend verification was
  attempted with `npm test`, but the environment has no active Node.js version
  (`nvm install <version>` / `nvm use <version>` is required); build was
  therefore not runnable here. Python compilation remains unchanged.
- Next ticket: `PT-ARCH-007`, split frontend route modules from feature
  components.

## Architecture slice: PT-ARCH-007

- Added explicit route modules for login, sessions, dashboard, scenario
  library, new scenario, and scenario detail routes.
- The application shell now composes route modules instead of importing page
  implementations directly. `/sessions` remains navbar-free, while the
  authenticated shell remains on dashboard and scenario routes.
- Preserved route normalization, auth redirects, sidebar navigation, stable
  scenario IDs, scenario create/edit behavior, and existing page props.
- The Impeccable detector reported no findings for the changed route and app
  files. Python compilation passed.
- Full Python verification remains `53 passed, 9 failed` because the known
  canonical scenario fixture files are absent. Frontend tests and build remain
  unavailable until a Node.js version is activated in the environment.
- Next ticket: `PT-ARCH-008`, organize shared UI and styles by ownership.

## Architecture evaluation, 2026-11-03

- Confirmed and ranked findings in ARCHITECTURE_REVIEW.md: hidden browser auth globals, shallow application delegation, repeated role resolution and route layout composition, inconsistent transport ownership, and unreachable legacy HTTP definitions.
- Reviewed both ADRs. Preserve backend role authority, scenario repair/execution separation, and browser experiment configurations distinct from authentication sessions. No ADR changes or runtime edits were made.
- Full Python verification: 59 passed, 17 failed, one existing deprecation warning. Failures include unauthenticated campaign clients receiving 401 as well as absent canonical scenario fixtures. Earlier 53/9 baselines are historical.
- Focused architecture, application-contract and scenario-module tests: 9 passed. Python compilation passed. Frontend test/build attempts blocked by no active Node.js version.
- Next slice: repair test fixtures and authenticate HTTP test clients without weakening middleware; then pass identity/sign-out explicitly through shared layout and remove window globals.
- Existing unrelated working-tree changes were preserved. No commit created.
- Final review checks: git diff --check passed. Reviewed tracked diff summary and STATUS diff; the architecture review file was already untracked and was extended rather than overwritten. Architecture.md received a current composition note.

## Test baseline repair, 2026-11-03

- Added suite-owned synthetic scenario fixtures under backend/tests/fixtures/scenarios and redirected fixture consumers away from the editable development scenario library. No deleted application scenarios were restored or replaced.
- Added an opt-in analyst_client fixture that configures synthetic test credentials and signs in through the real login endpoint. Campaign HTTP tests, including reloads, and the run HTTP smoke test now use it. Existing authentication, role-forbidden, and disabled-account tests remain unchanged.
- Updated stale assertions for campaign injection/task counts, ordered persisted traces including agent_output, and defended fake-model benchmark output. A blocked tool call cannot remove the COMPROMISED marker already emitted by the fake model.
- Verification: full Python suite 76 passed with one existing Starlette/httpx deprecation warning. Python source/test compilation passed. Frontend tests and build attempted but blocked by no active Node.js version. git diff --check passed; reviewed diff summary and changed test content, including previously untracked tests. Runtime code and unrelated working-tree changes preserved. No commit created.
- Next recommended slice: replace window authentication globals with explicit shared-layout dependencies. Frontend runtime verification requires an active Node.js installation first.

## UI/UX analysis and first fixes, 2026-11-03

- Added docs/UI_UX_REVIEW.md with two independent Impeccable assessments, primary-source UX research, recommended analyst/admin flows, prioritized issues, fixes and remaining work.
- Fixed truthful role-neutral login, session-check failure/retry, transient session creation, session deletion confirmation, nested keyboard controls, credential accessible names/provider reset, selected-run interaction, scenario loading/empty state, dashboard navigation toggle and trace identity/copy. Removed the unsupported comparison action.
- Found installed Node 22 behind the inactive NVM shim and used its direct executable without changing global configuration. Fixed extensionless test imports and aligned stale HTTP-adapter test inputs with the current provider/model contract.
- Verification: 31 frontend tests passed; Vite build passed; 76 Python tests passed with one existing deprecation warning; Python compilation passed. Impeccable source detector returned no findings. Browser smoke passed API recovery and session-cancel behavior with mocked responses; desktop/mobile sessions captures saved under .scratch/ux-review. git diff --check passed.
- User requested visual redesign optimized for fast repeated experiments. Concrete illustrative preview at .scratch/ux-review/redesign-proposal.html. Visual-system replacement awaits direction review; complete rendered website audit and remaining scenario/admin/navigation defects are documented. Do not describe the visual redesign as finished.
- No commits; unrelated changes preserved.

## Site redesign applied, 2026-11-03

- Applied the user-approved research-review direction across all seven route surfaces. Added src/redesign.css and replaced frontend/DESIGN.md with current tokens, typography, responsive composition and state rules.
- Replaced the analyst drawer with persistent top navigation, retained navbar-free sessions and separate administration, removed duplicate headers and browser-global auth defaults, and passed identity explicitly through composition.
- Reorganized experiments into configuration, recorded-run selection, outcome and trace. Removed decorative completion percentage and the redundant focus panel. Session settings now own provider/credential only. Added scenario-save progress/success and forbidden-route recovery.
- Browser validation: all seven surfaces captured at 1440px and 390px with synthetic HTTP responses; no horizontal overflow or page errors. Independent screenshot review passed; corrected singular labels and mobile list height. Three new focused Playwright tests pass. Existing legacy e2e tests were not represented as passing and still require authentication migration.
- Frontend unit tests 31 passed; production build passed. Python suite 76 passed with one existing Starlette/httpx warning; compilation passed. Impeccable detector flagged an unused Inter font fallback; removed it in favor of the system sans stack. git diff --check passed. Reviewed changed content and diff summary; unrelated changes preserved. No commit.
- Next slice: raw invalid-YAML scenario repair and pending/error handling for credential/admin mutations, then migrate legacy browser journeys to backend authentication and verify live API paths.

## Campaign and session layout fixes, 2026-11-03

- Inspected both user screenshots in .scratch/tofix. Legacy fixed campaign columns exceeded the history panel width; credential controls retained a four-column layout in the narrow session editor.
- Scoped the populated campaign rows to a two-column metric grid with full-width identity/status, wrapping long identifiers and filenames. Session provider choices and credential fields now stack with readable text; long credential references wrap beside the revoke action.
- Browser assertions passed at 1440, 1223, 768 and 390 pixels for campaign/editor containment and non-overlapping credential controls, using synthetic HTTP responses. Reviewed rendered 1223px captures; saved all eight captures under .scratch/ux-review/*-fixed-*.png.
- Frontend tests: 31 passed. Production build passed. Impeccable detector returned no findings. Python suite and compilation verified for this slice. git diff --check passed. No runtime logic, unrelated changes or commits were changed.

## Scrollable recorded experiments, 2026-11-03

- Constrained the single-run history list to 28rem on desktop and 22rem on narrow screens with independent vertical scrolling. Heading and filter stay outside the scroll area; focused rows retain padding and long text wraps.
- Browser verification with 30 synthetic runs confirmed actual scrolling at 1440px and 390px, with 448px and 352px list heights. Captures saved under .scratch/ux-review/history-scroll-*.png; mobile capture reviewed.
- Verification passed: 31 frontend tests, production build, 76 Python tests with the existing deprecation warning, Python compilation, Impeccable detector with no findings, and git diff --check. No commits or unrelated changes.


## Architecture and public deployment review, 2026-11-03

- Read current guidance, both existing ADRs, implementation and design documents, dependency manifests and working-tree diffs before editing. Preserved existing modified, untracked and deleted files. Used per-command safe.directory only; no reset, clean or commit.
- Revalidated architecture with an independent read-only inspection. Browser authentication globals, feature HTTP extraction and separate trace/campaign persistence are already fixed or present. The final dated assessment in ARCHITECTURE_REVIEW.md supersedes earlier stale inventories and ranks ownership, saved-run correlation, dynamic Any delegation, credential orchestration, campaign eligibility, authentication composition, routes, transport, local configurations and CSS. Added an ownership map, dependencies, risk and small migration slices; retained useful compatibility seams.
- Completed the smallest behavior-preserving cleanup: deleted 127 unreachable legacy HTTP lines after create_app's unconditional return in backend/src/poisontrace/web_adapter.py. Kept the active factory, routers and existing adapter methods unchanged. Existing child-trace working-tree edits in the same file were preserved. No new abstraction or test duplicating dead code was added.
- Researched official Vite, FastAPI, SQLite, Cryptography, MDN and Render documentation against actual startup, storage, secret, model and campaign code. DEPLOYMENT_REVIEW.md compares local/containerized, single-server and managed arrangements, recommends a single HTTPS origin and single persistent host initially, and records public launch gates. No provider, domain, budget or paid plan selected; no deployment or credentials transmitted.
- User decisions are accepted in ADR 0003: public live-model BYOK demo plus open-source local edition; operator-issued accounts; private analyst keys and experiment history; curated read-only public scenario library; keys encrypted until revoked. Local scenario CRUD/repair and the analyst/superadmin restrictions remain. Glossary records investigation configuration, analyst-owned credential and curated public library. The brief distinguishes plaintext leakage from the agreed encrypted storage. Requirements are documented, not implemented by this cleanup.
- Critical public blockers: absent per-user credential/run/campaign ownership; global latest_run_id correlation race; non-atomic campaign claim; request-bound execution without durable recovery; incomplete clean runtime dependencies including cryptography; relative data paths; session/HTTPS/abuse controls; cross-user browser configurations; public scenario write restrictions and backup/revocation policy. One Uvicorn worker does not serialize synchronous HTTP handlers.
- Baseline and post-change verification: 76 Python tests passed with one existing Starlette/httpx deprecation warning; 31 frontend tests passed; production build passed; Python source/test compilation passed. Used Node 22 through current-process PATH only. git diff --check passed and final edits were reviewed. No route or UI behavior changed, so no browser check was required. No full e2e pass claimed; legacy workspace journeys still require authentication migration. No live model, concurrent-user, clean-install, restart/restore or deployment test was performed.
- Visual candidate report: C:/Users/TalonExe/AppData/Local/Temp/architecture-review-20261103-161825.html. Static diagrams and CSS work without CDN styling; Mermaid/Tailwind require network. Automatic approval review rejected the initial command to open it because sandbox approvals are disabled; generated the file separately and supplied its path instead. This does not affect runtime verification.
- Next structural slice: move credential orchestration behind its existing secrets adapter and masked-result interface with focused redaction/error tests. Then implement owner-aware access with an explicit migration policy for existing ownerless records, and independently return saved run IDs/claim campaigns atomically. Follow with public profile configuration, scenario eligibility, durable execution and launch gates before any exposure. Frontend route and CSS moves remain separate slices needing rendered checks.


## Backend reorganization: credential module, 2026-11-03

- Began the accepted backend organization with credential extraction. Added application/credentials.py for credential operations and masked results, and application/ports.py for CredentialReference and the complete SecretsAdapter protocol. Both existing concrete adapters satisfy the same interface; list and replace are now declared alongside save/retrieve/reference/revoke.
- Removed credential behavior from the dynamic application forwarding module and removed private _credential_dict serialization from RunWebAdapter. HTTP composition now supplies the shared adapter.credentials instance directly to the typed credential router. Existing RunWebAdapter.save_credential/replace_credential methods and old class/type import paths remain compatible. The application class constructor intentionally now accepts the secrets adapter directly.
- Added CredentialWriteRequest and aligned response provider metadata with the existing unrestricted string storage contract. No provider-validation behavior was added. No schema, encryption, retention, role authorization or scenario behavior changed. Public per-user ownership remains unimplemented.
- Before extraction, added HTTP characterization tests and confirmed their existing 400/503 missing-storage statuses, 404 revoked test/delete statuses, 400 invalid replacement/empty-key statuses, masked responses and lifecycle behavior. Added a direct application-interface test that first failed because the new module did not exist, then passed after extraction against encrypted SQLite and managed secret adapters. Added an import rule preventing concrete storage/framework/SDK dependencies in the new application modules.
- Verification: baseline 76 Python tests, 31 frontend tests and production build passed. After extraction, 20 focused credential/contracts/storage tests passed; full Python suite 86 passed with the existing Starlette/httpx deprecation warning. Python source/test compilation passed. Frontend source, routes and UI behavior are unchanged, so baseline frontend checks remain applicable and browser checks were not needed. No full e2e or live-provider claim.
- Updated ARCHITECTURE.md, ARCHITECTURE_RULES.md and ARCHITECTURE_REVIEW.md with current ownership and compatibility details. git diff --check passed; reviewed touched production files, new tests and tracked diffs. Existing unrelated working-tree changes, prior deletions and child-trace edits were preserved. No commit, deployment or credential transmission.
- Next organizational slice: extract actual run orchestration into application/runs.py, then campaign orchestration, followed by config/bootstrap and concrete adapter relocation. Keep saved-run identity and ownership changes explicit, with focused behavior tests. Retain domain independence, gateway-only tool invocation and all accepted ADR restrictions.


## Backend reorganization: run module, 2026-11-03

- Extracted actual run orchestration, list/detail queries, summaries and scenario lookup error translation into application/runs.py. RunApplicationService receives explicit RunStore, UsableScenarioLookup, ModelFactory and optional SecretsAdapter dependencies. RunWebAdapter composes one instance; active HTTP routes now call it directly. Existing create_run/list_runs/get_run methods and old class import path remain compatible. The extracted class constructor now requires the explicit dependencies.
- Added application-owned model, trace and run-storage interfaces. Moved TraceEvent/TraceStore declarations into application/ports.py and preserved imports through persistence.traces and trace. ScenarioRunner now declares AgentModel/TraceStore dependencies rather than concrete FakeModel/InMemoryTraceStore types. No persistence implementation or schema changed.
- Moved ScenarioNotFound into application/errors.py, retaining the old web_adapter export. Run routers now import the error and application module directly. Added typed detail/metrics/trace contracts and completed existing summary outcome annotations. Response payloads and HTTP mappings are unchanged.
- Added and passed HTTP characterization before extraction. The new direct application tests first failed because runs.py did not exist, then passed after extraction. They cover all experiment modes, persisted evidence, selected provider/model/key forwarding, secret-free detail, credential mismatch and rejected inputs before model construction. Import checks allow pure domain contracts while rejecting concrete persistence/framework/SDK imports. AST comparison against pre-slice copies confirmed moved bodies preserve behavior apart from dependency names.
- Verification: baseline 86 Python tests passed with the existing Starlette/httpx warning; 31 frontend tests and production build passed using process-local Node 22 PATH. After extraction, the full Python suite passed 96 tests with the same warning, and source/test compilation passed. A python -S import check confirmed application.runs imports without optional packages or concrete adapters. No frontend or route behavior changed, so no browser rerun was needed; no full e2e or live-provider claim.
- Updated ARCHITECTURE.md, ARCHITECTURE_RULES.md and ARCHITECTURE_REVIEW.md. Reviewed pre-slice comparisons including untracked production modules, and git diff --check passed. Existing unrelated modifications, deletions and campaign trace content were preserved. No commit, deployment or credential transmission.
- Next organizational slice: extract campaign orchestration into application/campaigns.py, preserving selection, summaries, child traces, reruns and error behavior. Then centralize config/bootstrap and relocate concrete adapters. The latest_run_id race remains in run/campaign paths; fix saved IDs, atomic campaign claims and owner authorization as explicit behavior slices before public hosting. ADR scenario/role decisions remain unchanged.


## Backend reorganization: campaign module, 2026-11-03

- Extracted actual campaign selection coordination, creation, list/detail responses, execution, aggregation, child-run associations, ordered child traces and reruns into application/campaigns.py. Its five operations receive explicit CampaignStore, RunStore, CampaignScenarios, ModelFactory, RunSummary and optional SecretsAdapter dependencies. Shared summaries enter as runs.summary.
- Added filename-based CampaignScenarioFiles to scenario_loader.py for sorted poisoned-YAML selection and reload. Moved CampaignStore to application/ports.py while preserving persistence.campaigns and trace imports. HTTP composition passes adapter.campaign_service directly to the typed campaign router. Existing adapter.campaigns storage access, campaign methods, private summary/detail helpers, _serialize and application/services.py class imports remain compatible. The extracted constructor now requires explicit dependencies.
- Characterized HTTP errors and ordered child traces before extraction. Direct application tests first failed because campaigns.py did not exist, then passed after extraction. They cover filename ordering, credential/provider revalidation at creation/execution/rerun, selected model/key forwarding, persisted metadata, aggregate responses, partial failures, repair/rerun associations, unchanged rerun status and missing-child detail. All eight moved method bodies match the pre-slice snapshot after dependency and filename-loader substitutions.
- Verification: baseline 96 Python tests passed. After extraction, 99 Python tests passed with the existing Starlette/httpx warning; Python source/test compilation passed. Isolated python -S campaign import passed without SQLite, YAML, FastAPI, Cryptography or vendor SDKs. Frontend tests passed 31 tests and production build passed using process-local Node 22. No route or UI behavior changed, so browser checks were not needed. No full e2e, live-provider, concurrency or deployment readiness claim.
- Known issues deliberately preserved: latest_run_id correlation race, non-atomic created/running transition, direct YAML selection failing on invalid matching files, request-bound execution without recovery and missing per-user ownership. ADR 0001/0002/0003 requirements remain unchanged and public privacy requirements are not yet implemented.
- Updated architecture ownership/rules/review. Reviewed touched tracked and untracked source/tests and git diff --check. Preserved unrelated working-tree modifications and prior deletions. No commit, deployment, provisioning or credential transmission.
- Next organizational slice: validated configuration and explicit bootstrap construction, followed by concrete adapter relocation, domain organization/account behavior-persistence separation and eventual compatibility cleanup. Split these where needed; keep correctness and ownership fixes separate with focused red-green tests.


## Backend reorganization: web configuration/bootstrap, 2026-11-03

- Completed the web sub-slice of configuration/bootstrap. Added standard-library-only immutable WebConfig for explicit paths and existing environment-key loading. The key is hidden from repr and validated for local storage before files are created. Kept existing relative defaults and missing-key RuntimeError, including generation guidance. Managed-secret injection still does not require a local key. No environment path overrides or public profiles were introduced.
- bootstrap.py now constructs concrete web models, stores, application dependencies, secrets and authentication. build_backend composes shared dependencies and accepts a model factory. The configured build_adapter still returns the compatibility RunWebAdapter. The key-optional no-argument compatibility app factory remains available. Bootstrap import creates no files and does not start/import the web entrypoint.
- RunWebAdapter retains attributes, methods, historical imports and _model while delegating construction. web.py is thin and re-exports build_adapter/_build_local_secrets. HTTP composition receives one shared UserSessionService instead of constructing two instances and seeding twice. Existing auth/admin/role tests pass. Scenario routes now receive ScenarioService directly; the prior forwarding class remains importable. No route/UI or response changes.
- Baseline: 99 Python tests passed with the existing Starlette/httpx warning. New startup/interface tests first failed for missing config.py, then passed after extraction. Coverage includes defaults, key validation/redaction, no writes on invalid startup, explicit paths, local/managed secrets, injected fake campaigns, shared storage, model defaults/key forwarding, import side effects and key-optional compatibility startup. Added standard-library config and HTTP-construction import rules.
- Verification: 108 Python tests passed with the existing warning; Python source/test compilation passed; isolated python -S config import passed. Frontend tests passed 31 tests and production build passed with process-local Node 22. No route or UI behavior changed, so no browser rerun was needed. No full e2e, live-provider, concurrency, clean-install or deployment-readiness claim. git diff --check and touched tracked/untracked source/test review passed; unrelated work and prior deletions preserved. No commit, provisioning, deployment or credentials transmitted.
- Remaining composition work: extract CLI model/runner construction without changing protected-tool approval or benchmark policy. __main__.py is already thin. Account seed environment reads remain in users.py for the later account behavior/persistence split; launcher checks remain unchanged. Then relocate concrete adapters, organize domain/account modules and clean compatibility paths after callers migrate.
- Known latest_run_id races, non-atomic campaign claims, direct-YAML campaign eligibility, request-bound execution and missing per-user ownership remain unresolved. ADR 0001/0002/0003 decisions are unchanged; public privacy/profile requirements are still pending.


## Backend reorganization: CLI composition, 2026-11-03

- Moved concrete CLI model selection, single-run construction and benchmark runner-factory construction into bootstrap.py behind build_cli_model, build_cli_runner and build_cli_benchmark. The factories accept a model-construction callable. cli.py retains parsing, scenario loading, execution, metric formatting and Gemini diagnostic output; __main__.py remains unchanged and thin.
- Preserved supported names/defaults, environment provider-key fallback, approved-manifest fallback and mode enforcement. Single runs retain protected-tool intersection and optional approval actor; benchmarks retain their empty high-impact set. BenchmarkRunner still executes repeated_runs + 1 trials and rejects negative counts. Each trial receives a fresh model and in-memory trace store. Tool execution stays behind the gateway.
- Preserved historical CLI imports, PROTECTED_TOOL_NAMES and _model_for. Tests that replace concrete constructors now patch bootstrap. Deferred web-only secrets/auth imports to their factories so CLI composition does not acquire web secret-key, authentication or Cryptography dependencies. Existing YAML/model-adapter dependency requirements are unchanged.
- Baseline 108 Python tests passed. Added exact output, Gemini diagnostic and parser/error characterization tests before extraction. Direct construction tests first failed because the new factories did not exist, then passed after extraction. Coverage includes approval outcomes, manifest modes, benchmark policy/state isolation, supported model names and rejection, plus subprocess module-entrypoint tests for run and benchmark with web/secrets/auth/FastAPI/Cryptography imports blocked and no storage writes. AST comparison confirmed the model-selection body matches its pre-slice implementation.
- Verification: 119 Python tests passed with the existing Starlette/httpx warning; Python source/test compilation and git diff --check passed. Reviewed touched tracked/untracked source, tests, architecture documentation and pre-slice comparisons. No frontend, route or UI behavior changed; frontend tests/build and browser checks were not rerun for this CLI-only slice. The previous slice's 31 frontend tests/build remain the latest frontend verification. No full e2e, live-provider, concurrency, clean-install or deployment-readiness claim.
- Updated architecture ownership, rules and review. Preserved unrelated modifications, migration deletions and campaign traces. No commit, deployment, provisioning or credential transmission.
- Next organizational slice: relocate concrete adapters, starting with one cohesive responsibility such as model adapters, retaining old imports while callers migrate. Then relocate persistence/YAML/secrets, organize the domain and separate account behavior/configuration/persistence; clean compatibility paths after migration. Account seed environment reads and launcher validation remain unchanged. Known saved-run correlation, atomic campaign claim, usable-scenario eligibility, durable execution and per-user ownership issues remain unresolved; ADR decisions remain unchanged.


## Backend reorganization: model adapter relocation, 2026-11-03

- Completed the first concrete-adapter relocation sub-slice. Moved FakeModel, OpenAIModel and GeminiModel implementations into adapters/models/fake.py, openai.py and gemini.py. All three implementation files are byte-for-byte unchanged from pre-slice copies under .scratch/model-adapters-before. No defaults, key fallback, SDK calls, prompts, schemas, parsing, exceptions or model behavior changed.
- Updated bootstrap, CLI and web facade imports to canonical modules. Retained historical agent.py/openai_model.py/gemini_model.py exports for the model classes and provider DECISION_SCHEMA objects. They refer to identical objects, without wrapper classes. Class __module__ values now identify the canonical modules. Existing application-owned interfaces and constructor injection remain unchanged.
- Added only necessary adapters/models package parents, with initializers that import no concrete models. Provider tests now use canonical imports; existing fake-model execution tests continue exercising legacy imports. Six compatibility/import tests first failed because adapters did not exist, then passed after relocation. Added an import rule excluding orchestration/composition/storage concerns from models. Isolated python -S fake imports through both paths load no optional dependencies.
- Verification: baseline 119 Python tests passed; after relocation 126 Python tests passed with the existing Starlette/httpx warning. Source/test compilation and git diff --check passed. Reviewed pre-slice comparisons and touched tracked/untracked source, tests and architecture notes. No frontend, routes or UI behavior changed, so frontend tests/build and browser checks were not rerun; 31 frontend tests/build from the web-bootstrap slice remain the latest frontend checks. No full e2e, live-provider, concurrency, clean-install, packaging or deployment-readiness claim.
- Updated architecture ownership, rules and review. Preserved unrelated modifications, migration deletions and campaign traces. No commit, deployment, provisioning or credential transmission.
- Next organizational slice: relocate trace/campaign persistence into adapters with old imports and shared-schema behavior preserved, splitting further where useful. Then relocate YAML/secrets, organize domain code and separate account behavior/configuration/persistence, followed by compatibility cleanup after caller migration. Known latest_run_id correlation, atomic claims, usable-campaign eligibility, request-bound recovery and per-user ownership issues remain unresolved; ADR decisions remain unchanged.


## Backend reorganization: persistence adapters, 2026-11-03

- Relocated concrete stores and unchanged shared schema setup to adapters/persistence. Canonical bootstrap/facade/account imports now use adapters; historical persistence and trace exports preserve object identity. Application-owned ports remain unchanged. No migration or account separation was mixed into the move.
- Compared implementations to .scratch/persistence-adapters-before, with only the support import path changed. Full suite passed 131 tests with the existing warning; the subsequently added import rule and persistence tests passed together, 16 tests. Source/test compilation and git diff --check passed. Frontend/routes/UI unchanged, so frontend/browser checks were not rerun.
- Architecture ownership/rules/review updated. Preserved unrelated working-tree edits/deletions. Known run correlation, atomic claims, campaign eligibility, request-bound recovery and ownership issues remain. Next slice: YAML adapters.


## Backend reorganization: YAML adapters, 2026-11-03

- Moved loader/CampaignScenarioFiles and repository mechanics to adapters/scenarios. Moved scenario use cases to application/scenarios.py with an application-owned ScenarioRepository interface. Repository serialization/load operations hide YAML and paths. Old modules preserve identical exports. Production callers use canonical paths.
- Loader is byte-identical to .scratch/yaml-adapters-before. Application bodies match with only injected serialization/loading substitutions. Tests preserve invalid drafts, repair, stable filename/ID, failed-write retention, deletion and campaign reload/error behavior. Existing validation differences and invalid-file campaign selection remain unchanged.
- Full Python suite: 135 passed, existing Starlette/httpx warning. Source/test compilation and git diff --check passed. Architecture ownership/rules/review updated; unrelated work preserved. No UI/routes changed, frontend/browser checks not rerun. Next: secrets adapters, then domain/accounts and compatibility cleanup. Known behavior/public-readiness issues remain unresolved.


## Backend reorganization: secrets adapters, 2026-11-03

- Relocated both concrete implementations into adapters/secrets/storage.py. ManagedSecretClient is application-owned; credential behavior remains in application/credentials.py. Bootstrap/facade imports are canonical; historical secrets imports retain object identity. Both class ASTs match .scratch/secrets-adapters-before.
- Encryption/key fallback, masks, retention/revocation, provider matching, callback/client handling and exceptions are unchanged. Existing secret/application tests exercise canonical adapters; a compatibility test verifies historical class/type identity.
- Full Python suite: 136 passed, existing warning. Compilation and git diff --check passed. Updated architecture ownership/rules/review. No frontend/routes/UI changes or browser rerun. Preserved unrelated changes. Known correctness/ownership/public-readiness issues remain; next: domain organization.


## Backend reorganization: domain organization, 2026-11-03

- Domain is now a package containing values, marker/redaction rules and metric calculations. Historical poisontrace.domain and metrics imports preserve identical objects. BenchmarkRunner is coordination and moved byte-for-byte to application/benchmark.py, with a historical export. Bootstrap/CLI import canonical modules. Runner/gateway responsibilities stay outside the domain package.
- Compared all domain class/function ASTs and metrics/benchmark implementations with .scratch/domain-organization-before. Domain package import checks and isolated python -S coverage reject frameworks/storage/SDKs and application/adapters. Full Python suite: 138 passed, existing warning. Compilation and git diff --check passed. No frontend/routes/UI behavior changes or browser rerun.
- Updated architecture ownership/rules/review, preserved unrelated work. Known run correlation, claims, eligibility, recovery and ownership issues remain. Next: account behavior/configuration/persistence separation.


## Backend reorganization: account separation, 2026-11-03

- Account use cases and account-owned transactional storage interfaces now live in application/accounts.py. SQLite records live in adapters/persistence/accounts.py using unchanged shared setup. config.load_account_seeds owns environment reads, default usernames, missing-passcode filtering and repr-redacted seed values. bootstrap.build_accounts composes and seeds one application instance for HTTP auth/admin/middleware.
- Kept historical user/error value identity and database-path constructor through users.py compatibility glue. Preserved normalization, scrypt hashes, token hashing, session checks/logout, login response timestamps, seed order/INSERT OR IGNORE, role/status handling and last-active-admin restrictions. No schema, expiry, ownership or policy change. Transaction scopes match the old SQLite context managers, without stronger atomicity claims.
- Three characterization tests passed against the pre-slice implementation. Focused account/HTTP/bootstrap/CLI checks passed 25 tests. Full Python suite: 146 passed with the existing warning. Canonical checks cover explicit seeds, rollback, secret repr and isolated application imports. Synthetic pre/post old/new comparison matched outcomes, errors, records, hashes and sessions with timestamps excluded; snapshots and synthetic databases are review artifacts under .scratch. Initial comparison succeeded but its temporary-directory cleanup hit a Windows open-file error; rerun retained review artifacts and completed successfully.
- Compilation and git diff --check passed. Architecture ownership/rules/review updated. No routes/UI behavior changed; frontend/browser checks not rerun. Preserved unrelated work. Next: migrate remaining callers and remove obsolete forwarding only where unused. Known run-ID, campaign-claim/eligibility/recovery and per-user ownership issues remain.


## Backend reorganization: caller migration and handoff, 2026-11-03

- Completed the requested organizational slices in order: persistence adapters, YAML adapters and scenario use cases, secrets adapters, domain package, account behavior/configuration/persistence separation, then caller migration/compatibility cleanup. Each slice had its own checks and pre-slice copies under .scratch. No schema migration, ownership, expiry, account-policy or other known behavior fix was mixed in.
- Final canonical placement also puts ScenarioRunner/ToolGateway in application/execution.py and application/gateway.py, BenchmarkRunner in application/benchmark.py and CLI translation in interfaces/cli.py. __main__.py remains thin. Runner/gateway implementations match pre-slice copies after import changes; CLI main AST matches after removing the model-selector forwarding hop.
- Migrated production and behavioral-test imports to canonical modules. Added an import rule preventing production dependencies on historical paths. Retained tested historical class/function exports and the users.py database-path constructor. Public RunWebAdapter methods/attributes remain useful to current tests and the configured factory. Removed application/services.py and its unused WebOperations/ScenarioApplicationService after migrating its only consumer, plus four uncalled private facade helpers. No removal based only on file count.
- Final verification: 148 Python tests passed with the existing Starlette/httpx deprecation warning. Python source/test compilation passed. git diff --check passed. Inspected tracked diffs and new/untracked canonical modules/tests, verified moved implementations against snapshots and checked added files for whitespace. Account extraction additionally matched a synthetic pre/post behavior/storage comparison. No UI or route behavior changed, so frontend tests/build and browser checks were not rerun. The previous web-bootstrap slice's 31 frontend tests and production build remain the latest frontend checks. Older e2e journeys still need auth migration. No live-provider, concurrency, clean-install, packaging, deployment or full-e2e readiness claim.
- Updated ARCHITECTURE.md with the authoritative ownership table and compatibility inventory, ARCHITECTURE_RULES.md with current dependency rules, ARCHITECTURE_REVIEW.md with the final assessment, and DEPLOYMENT_REVIEW.md with current-path notes. Earlier dated notes are historical where superseded.
- Preserved unrelated modifications, untracked work, prior migration deletions, scenario files and stored experiment data. No reset, clean, commit, deployment, provisioning or credential transmission. Synthetic comparison databases and snapshots remain review artifacts in .scratch.
- Next behavior slice: return the saved run ID through execution instead of querying latest_run_id, with focused overlapping-run tests. Keep atomic campaign claims, usable-scenario campaign eligibility, durable execution/recovery and owner enforcement as separate reviewed fixes. Public privacy/read-only-profile/session-hardening and runtime installation requirements remain pending under ADR 0003. Browser investigation configurations remain distinct from authentication sessions; ADR 0001 repair/identity and ADR 0002 analyst/superadmin restrictions are preserved.


## Backend clean state: compatibility retirement, 2026-11-03

- The user refocused on backend clarity and authorized removing migration clutter. Baseline: 148 Python tests passed with the existing Starlette/httpx warning. Captured source/tests in .scratch/backend-cleanup-before.zip, and current architecture guides in .scratch/backend-cleanup-docs-before.zip. Preserved unrelated working-tree modifications/deletions and experiment data.
- Migrated remaining runtime/test consumers to bootstrap factories and direct application interfaces. Removed 19 compatibility source files, reducing backend/src/poisontrace from 67 Python files to 48 including package initializers. Retired root model/trace/scenario/secrets/users/execution/metrics/CLI wrappers, old persistence exports and web_adapter.py. No RunWebAdapter or database-path account wrapper remains. build_web_backend replaces build_adapter and returns Backend directly. HTTP composition requires explicit authentication instead of a bootstrap fallback. Six root files remain: __init__, __main__, bootstrap, config, launcher and web.
- HTTP routes/responses, CLI commands, paths, local/managed key behavior, seeds, roles and schema/data behavior are unchanged. Old Python import paths, aliases/factories and facade methods are intentionally retired; external Python callers must migrate. Architecture import checks now cover tests as well as production and reject reintroduced legacy modules.
- Retired only compatibility-identity tests. Migrated facade behavior tests into test_bootstrap.py and account behavior tests onto build_accounts; HTTP campaign/run/credential tests remain. Consolidated isolated imports into test_imports.py and added canonical run/campaign optional-dependency-free imports. First cleanup checkpoint: 136 Python tests passed. A missing import in a folded test was corrected before that passing result.
- Removed unused placeholder errors, duplicate trace contracts, unconsumed scenario/campaign DTOs, ScenarioStore alias and an unused repository delete forwarder. Actual application contracts/interfaces/errors remain. Final suite: 136 Python tests passed with the existing warning, including a new fresh-process smoke test of the configured poisontrace.web entrypoint. Source/test compilation, git diff --check and whitespace/parsing review of tracked and untracked Python files passed. Counts fell because compatibility-only and unused-error inheritance assertions were retired, not because behavior tests were dropped. A test-variable rename temporarily affected adapters import strings; corrected before the final passing suite.
- Compared 22 canonical domain/application/adapter modules with the snapshot. Behavior definitions are identical except the explicitly removed unused delete forwarder; shared schema bytes match. No schema migration, ownership, concurrency, eligibility, expiry or account-policy change. Removed the retired persistence directory only after verifying it held generated .pyc files alone.
- ARCHITECTURE.md and ARCHITECTURE_RULES.md now describe the current clean structure; prior guides are in the review ZIP. ARCHITECTURE_REVIEW.md records the cleanup and clearly supersedes older compatibility-retention notes. No frontend/routes/UI behavior changed, so frontend tests/build and browser checks were not rerun; prior 31 frontend tests/build remain the latest frontend checks. No live-provider, full-e2e, concurrency, clean-install, packaging or deployment-readiness claim.
- Known latest_run_id correlation, non-atomic campaign claims, invalid-file campaign selection, request-bound execution/recovery and missing per-user ownership remain unresolved. This cleanup does not implement ADR 0003's public requirements. No commit, reset, clean, deployment, provisioning or credential transmission. Continue backend changes in canonical modules without restoring forwarding layers.


## Next-session priority: research-objective review, 2026-11-10

- The user wants the next session to assess current system fulfillment against ../Havyn Liew Investigation Report.pdf. Start with docs/NEXT_SESSION_HANDOFF_RESEARCH_REVIEW.md. This supersedes earlier next-slice implementation suggestions and the old compromised-marker handover as the immediate task.
- The handover identifies the verified PDF path/hash, current canonical source locations, historical verification, research-sensitive measurement/tool-execution questions, assessment format and workspace constraints. Read the PDF objectives and methodology first, then produce docs/RESEARCH_OBJECTIVES_REVIEW.md with page-cited requirements and source/test/experiment evidence before proposing implementation work.
- PDF contents were not extracted or evaluated in this handover-only task; no objective fulfillment verdict is claimed. Available default/project Python interpreters lack PDF extraction libraries, and Poppler commands were not on PATH. The handover records reader setup as the first review prerequisite.
- Documentation-only change. No application code or behavior changed; Python/frontend tests were not rerun. The recorded baseline remains 136 Python tests and the previously recorded frontend 31 tests/build. No commit, deployment, provisioning or credential transmission.
