# Repository artifact policy

The repository keeps maintained frontend source alongside generated local
output. Use this policy when adding or reviewing files.

## Maintained source

- `frontend/dashboard-preview/` is a static dashboard preview used for design
  reference and visual comparison.
- `frontend/reference-prototype.html` and
  `frontend/reference-prototype.css` are maintained reference-prototype source.
- `frontend/src/` is the active React application source.
- `backend/src/` is the Python application source, and `backend/tests/` holds
  its test suite.
- `backend/scenarios/` contains versioned synthetic scenario fixtures.
- `frontend/DESIGN.md`, route notes, package manifests, and lockfiles are
  maintained project documentation or setup source.

These files stay versioned unless a later architecture decision changes their
role.

## Local or generated output

- `frontend/node_modules/` contains installed dependencies. Recreate it with
  `npm install`.
- `frontend/dist/` contains Vite build output. Recreate it with `npm run build`.
- `frontend/test-results/` contains disposable end-to-end test output.
- `*.db` and `*.db.backup` contain local application state or backups. Do not
  commit them, and never use real credentials or production data in them.
- Python caches and pytest caches are disposable local output.

These paths are ignored by the repository rules. Existing local files are not
deleted automatically.

## Repository layout

The root application directories are:

```text
backend/
  src/poisontrace/
  tests/
  scenarios/
frontend/
  src/
```

The root `pyproject.toml` keeps the shared test and packaging commands in one
place and points them at `backend/`.
