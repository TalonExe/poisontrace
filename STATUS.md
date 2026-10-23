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
- CLI model selection with offline fake default and live `gpt-5-mini` option.
- Closed structured-output schema for live model calls.
- Gemini `gemini-3.5-flash-lite` adapter using `GEMINI_API_KEY` and structured JSON output.
- CLI model selection for the Gemini adapter; the offline fake remains the default.
- Model name, prompt version, and run configuration are recorded in results and SQLite.

## Verification

The latest test run passed with 21 tests:

```text
.....................                                                    [100%]
21 passed
```

Run the suite with:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Next slice

Next: add the minimal dashboard for inspecting runs, traces, and benchmark metrics.

## Handoff rule

At the start of a new session, read `AGENTS.md` and `STATUS.md`, then run the test suite before changing code. Update this file after each completed slice.
