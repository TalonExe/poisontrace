# Architecture tickets

These tickets turn `docs/ARCHITECTURE_REVIEW.md` into an incremental plan. They
are local planning tickets; they do not create or update GitHub Issues.

## PT-ARCH-001: Add import-boundary rules and architecture checks

Status: ready

Goal: Make dependency direction explicit before moving production files.

Acceptance criteria:

- Document the allowed dependency direction for frontend and backend modules.
- Add focused tests or static checks for the most important forbidden imports.
- Preserve all existing routes, HTTP payloads, scenario behavior, and secrets
  boundaries.
- Record the result in `docs/STATUS.md`.

Dependencies: none.

## PT-ARCH-002: Split backend HTTP routing from application orchestration

Status: ready

Goal: Make HTTP routers thin and move run, campaign, scenario, and credential
use cases out of `web_adapter.py`.

Acceptance criteria:

- Add `interfaces/http/routers/` modules for scenarios, runs, campaigns, and
  credentials.
- Add application services or use-case modules for those operations.
- Keep HTTP request validation and error-to-status mapping in the HTTP layer.
- Keep model selection, credential lookup, and runner construction out of route
  functions.
- Preserve every existing endpoint, status code, response field, and rejection
  behavior.
- Keep `RunWebAdapter` as a temporary compatibility facade if needed while
  tests move to the new seams.

Dependencies: PT-ARCH-001.

## PT-ARCH-003: Establish typed backend boundary contracts

Status: ready

Goal: Replace unstructured dictionaries at module boundaries with explicit
request, response, and error contracts.

Acceptance criteria:

- Add domain/application contracts for scenario, run, campaign, credential,
  and trace operations.
- Keep domain contracts independent of FastAPI, SQLite, Docker, and vendor SDKs.
- Make invalid scenario, missing scenario, duplicate name/ID, credential
  mismatch, and run rejection errors explicit.
- Ensure secrets never appear in contracts, traces, logs, or responses.
- Add seam tests for each public contract.

Dependencies: PT-ARCH-002.

## PT-ARCH-004: Separate trace and campaign persistence

Status: ready

Goal: Remove the combined persistence responsibility from `trace.py`.

Acceptance criteria:

- Move trace persistence behind a trace-store module/protocol.
- Move campaign persistence behind a campaign-store module/protocol.
- Keep shared database setup/migrations in one persistence support module.
- Preserve run correlation keys and campaign child-run associations.
- Keep in-memory stores available for fast tests.
- Preserve SQLite schema behavior unless a migration is explicitly added.

Dependencies: PT-ARCH-002, PT-ARCH-003.

## PT-ARCH-005: Finish the scenario repository boundary

Status: ready

Goal: Separate YAML persistence from scenario validation and application policy.

Acceptance criteria:

- Give the YAML repository responsibility for reading, atomic writing, raw
  repair, filename safety, and deletion.
- Give the scenario application service responsibility for CRUD, usable lookup,
  ID allocation, duplicate detection, and run/campaign eligibility.
- Keep invalid files listable and repairable.
- Keep invalid files excluded from runs and campaigns.
- Preserve quoted three-digit IDs, canonical filenames, immutable IDs, separate
  tool lists, exact delete confirmation filenames, and historical records.
- Add focused tests for raw repair, failed writes, invalid lookups, and empty
  usable-scenario states.

Dependencies: PT-ARCH-003.

## PT-ARCH-006: Move frontend HTTP calls into feature API modules

Status: ready

Goal: Replace the broad `src/utils/webAdapter.js` ownership with feature-owned
HTTP adapters.

Acceptance criteria:

- Add feature API modules for auth, sessions, scenarios, runs, campaigns, and
  credentials where each feature needs them.
- Keep one low-level HTTP client responsible for base URL, JSON parsing, and
  consistent error handling.
- Keep secrets and plaintext credentials out of frontend state and storage.
- Preserve HTTP-only frontend/backend communication.
- Keep dependency-free tests for each adapter seam.

Dependencies: PT-ARCH-001, PT-ARCH-003.

## PT-ARCH-007: Split frontend route modules from feature components

Status: ready

Goal: Make routes responsible for URL composition and make feature components
responsible for feature behavior and presentation.

Acceptance criteria:

- Add route modules for `/login`, `/sessions`, `/dashboard`, `/scenarios`,
  `/scenarios/new`, and `/scenarios/:scenarioId`.
- Split `DashboardPage`, `SessionsPage`, and `ScenarioPage` into route-level
  containers and smaller feature components.
- Keep `/sessions` navbar-free.
- Keep the authenticated shell on `/dashboard` and every scenario route.
- Preserve auth redirects, route normalization, sidebar behavior, and existing
  interaction states.
- Add or update focused route and component seam tests.

Dependencies: PT-ARCH-006.

## PT-ARCH-008: Organize frontend shared UI and styles by ownership

Status: ready

Goal: Make shared UI and CSS ownership visible without changing the visual
system.

Acceptance criteria:

- Move the authenticated header into the layout shell.
- Split generic UI primitives from feature-specific components.
- Separate global tokens, global resets, layout styles, and feature styles.
- Preserve the existing Evidence Control palette, responsive behavior, and
  dark-first design.
- Run Prettier over all frontend source and configuration files.
- Run frontend tests and the Vite production build.

Dependencies: PT-ARCH-007.

## PT-ARCH-009: Classify generated and disposable artifacts

Status: ready

Goal: Make repository contents predictable for contributors and agents.

Acceptance criteria:

- Decide whether `frontend/dashboard-preview/` and
  `frontend/reference-prototype.*` are maintained source, documentation
  examples, or disposable artifacts.
- Keep generated `dist/`, dependency folders, local databases, and backups out
  of version control unless a documented exception exists.
- Add or update ignore rules and setup documentation.
- Do not delete user-owned artifacts without confirming their classification.

Dependencies: none, but coordinate with all frontend tickets.

## Recommended implementation order

`PT-ARCH-001 → PT-ARCH-002 → PT-ARCH-003 → PT-ARCH-004 → PT-ARCH-005`

Then:

`PT-ARCH-006 → PT-ARCH-007 → PT-ARCH-008 → PT-ARCH-009`
