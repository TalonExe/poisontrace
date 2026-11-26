# Working in PoisonTrace

## No comments

Do not add comments under any circumstances in source code, tests, scripts, or configuration files. This includes standalone, inline, block, documentation, TODO/FIXME, and lint or type-check suppression comments. Do not use docstrings or string literals as substitutes for comments. Express intent through clear names and code structure; keep explanations in prose documentation.

Before changing code, read these files in order:

1. `docs/CONTEXT.md` for the current domain boundary.
2. `docs/DOMAIN_GLOSSARY.md` for canonical terms.
3. `docs/ARCHITECTURE.md` for current modules, interfaces and test seams.
4. `docs/STATUS.md` for implementation, verification limits and next eligible work.

For measurement, corpus, attack or matched-comparison changes, read the relevant contracts under `docs/research/` and `docs/SCOPE_REFINEMENT.md`. For runtime, account recovery or hosted HTTP changes, read `CONTAINER.md`. For verification work, read `docs/VERIFICATION.md` and the project verification skill. Read relevant ADRs before changing an accepted decision.

Use a red-green TDD loop for behaviour changes. Test public interfaces at the seams described in `docs/ARCHITECTURE.md`. Keep the domain layer independent of FastAPI, SQLite, Docker, OpenAI SDK types, and MCP transport details.

After each vertical slice:

1. Run `.venv\Scripts\python.exe -m pytest -q`.
2. Update `docs/STATUS.md` with the completed behaviour, verification result, and next slice.
3. Review `git diff` before handing off.

Keep secrets in the environment. Never commit `.env`, API keys, real credentials, production data, or generated database files.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `TalonExe/poisontrace`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository. The glossary is `docs/DOMAIN_GLOSSARY.md` and architecture decisions live in `docs/adr/`. See `docs/agents/domain.md`.
