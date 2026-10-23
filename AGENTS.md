# Working in PoisonTrace

Before changing code, read these files in order:

1. `CONTEXT.md` for the current domain boundary.
2. `DOMAIN_GLOSSARY.md` for canonical terms.
3. `IMPLEMENTATION_BRIEF.md` for agreed scope and build order.
4. `ARCHITECTURE.md` for module interfaces and test seams.
5. `STATUS.md` for the current handoff and next slice.

Use a red-green TDD loop for behaviour changes. Test public interfaces at the seams described in `ARCHITECTURE.md`. Keep the domain layer independent of FastAPI, SQLite, Docker, OpenAI SDK types, and MCP transport details.

After each vertical slice:

1. Run `.venv\Scripts\python.exe -m pytest -q`.
2. Update `STATUS.md` with the completed behaviour, verification result, and next slice.
3. Review `git diff` before handing off.

Keep secrets in the environment. Never commit `.env`, API keys, real credentials, production data, or generated database files.
