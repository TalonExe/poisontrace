# PoisonTrace status

## Current milestone

The first domain, policy, scenario-loading, command-line execution, mode-selection, protected-action, SQLite persistence, runner-persistence, metric, safe-fallback, repeatable-benchmark, benchmark-CLI, run-measurement, OpenAI-adapter, Gemini-adapter, CLI-model-selection, and structured-schema-fix slices are implemented. The repository has no commits yet.

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
- Validated credential references before provider execution. Runs now reject missing references and provider mismatches before retrieving a secret.
- Added direct Gemini adapter seam coverage for structured decisions, model and API-key forwarding, malformed or incomplete responses, and secret non-retention. Invalid model output now raises a stable `ValueError`, and the CLI does not print raw model responses.
- Added CLI protected-action coverage. The `run` command recognizes synthetic high-impact tools and accepts `--approval-actor`; protected actions are blocked without approval and allowed with an approval actor.

## Verification

The latest Python test run passed with 43 tests and 1 skipped optional HTTP test:

```text
...........................................                              [100%]
43 passed, 1 skipped
```

Frontend verification is pending because this environment has no active Node.js version:

```text
No active Node.js version is configured. Run `nvm install <version>` then `nvm use <version>`.
```

The reference prototype is static HTML/CSS so it can be opened directly at `frontend/reference-prototype.html`.

Run the suite with:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Next slice

Next: add browser-level coverage for the login, session workspace, provider selection, sidebar navigation, and credential selector.

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

- Browser-level frontend coverage is still pending for rendered login, session workspace, provider selection, sidebar navigation, and the credential selector.
- The dashboard adapter requires the `/api/runs` backend and displays an explicit unavailable/empty state when it cannot load runs.
- The managed secret-store adapter still needs an application-specific client wiring layer.
- SQLite event association currently assigns all unassigned events to the next saved result, which is unsafe for concurrent runs.

## Handoff rule

At the start of a new session, read `AGENTS.md` and `docs/STATUS.md`, then run the test suite before changing code. Update this file after each completed slice.
