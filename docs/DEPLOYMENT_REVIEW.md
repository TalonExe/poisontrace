# Deployment review

Reviewed 2026-11-03. This is a source and documentation review, not a deployment or a security certification. No services were provisioned, credentials transmitted, or environment values inspected. Code references use repository-relative paths and line numbers at review time. Hosting behavior below comes from current first-party documentation. The user selected a publicly hosted demonstration with live models and each visitor's own API key, plus an open-source version for local use. The user also selected operator-issued accounts, private analyst keys and experiment history, a curated read-only public scenario library, and encrypted keys retained until revoked. ADR 0003 records these requirements; enforcement is pending.

## Recommendation by audience

For an FYP demonstration on the author's laptop, keep the existing loopback launcher and use synthetic data. For a small invited group, prefer one server or container host behind HTTPS and an access restriction, with one application instance, persistent local storage, and deliberately serialized experiments. A container would improve repeatability, but this repository currently has no Dockerfile or Compose definition. The implementation brief explicitly calls the product a local research prototype, and forbids connections to production security systems and real cloud infrastructure credentials. Model-provider API keys are a separate configured integration.

For the selected public BYOK demonstration, complete the public-exposure blockers below first. Use the agreed issued accounts, private credentials and private history for the first release. A static frontend plus managed backend is possible, but moving the current files onto a host does not add isolation, durable jobs, or durable storage. Use a same-origin browser entry point even if the frontend and backend run on separate infrastructure. Maintain a separate local distribution with documented setup, fake-model default, optional local provider credentials, and no mandatory hosted account.

| Option | Fit | Required work and tradeoff |
| --- | --- | --- |
| Existing local launcher | Single-machine FYP demo | Lowest change. Both processes bind to loopback. It starts Vite's development server and expects a pre-existing virtual environment and frontend dependencies. |
| One server, optionally containers | Invited remote demonstration | Build static frontend, configure HTTPS reverse proxy, supervise Uvicorn, persist both databases and editable YAML, restrict access, and serialize experiments. Host maintenance and backups remain the operator's responsibility. |
| Managed static frontend and backend | Longer-lived remote service | Add frontend API routing, persistent backend disk or new storage adapters, secure authentication, and reliable execution. Separate browser origins add cookie and CORS work. Horizontal scaling needs a storage and concurrency redesign. |

The launcher commands are in `backend/src/poisontrace/launcher.py:41-44`; environment and dependency checks are at lines 24-38. It sets `PYTHONPATH` and runs from the project directory at lines 68-75. Vite documents building to `dist` and explicitly says `vite preview` is not a production server. Serve the compiled assets with a real static host or reverse proxy. [Vite deployment documentation](https://vite.dev/guide/static-deploy)

## What the running application actually needs

`backend/src/poisontrace/web.py:14-36` creates the app at import time. Its default composition requires `POISONTRACE_SECRETS_KEY`, uses `backend/scenarios`, and opens `poisontrace.db` and `poisontrace-secrets.db` relative to the current working directory. Running from a different directory can select a different database or fail to find scenarios. There are no environment-configured data paths in that entry point. Configure explicit data paths before using a conventional mounted `/data` directory, or deliberately mount the exact existing paths. Merely attaching a disk somewhere else does not persist them.

`pyproject.toml:7-17` has web dependencies in the `web` extra, but YAML and model SDK dependencies in `dev`; it never declares `cryptography`. The app imports `cryptography.fernet` in `secrets.py:10`, and imports the OpenAI adapter through `web_adapter.py:14` even for fake runs. A clean install of only the web extra is therefore insufficient. Define and lock a tested runtime dependency set, confirm the backend import path or package installation in a clean environment, and use the existing frontend lockfile for repeatable builds. Do not copy the existing virtual environment into a Linux image.

The production entry point should run Uvicorn without development reload, with the project source importable. On a container platform it must listen on the container network interface and the platform's configured port; the launcher's `127.0.0.1` binding is intended for local use. Do not expose its development frontend server as the hosted UI. Add a lightweight health endpoint and process supervision before unattended hosting. These are implementation recommendations, not claims that a deployment manifest already exists.

## Storage, backup, and secrets

The durable state has three separate parts:

- `poisontrace.db` contains runs, ordered trace events, campaigns, users, and authentication sessions. See `backend/src/poisontrace/persistence/support.py:7-20` and `interfaces/http/app.py:17`.
- `poisontrace-secrets.db` stores encrypted provider secrets and their metadata. Encryption uses Fernet in `secrets.py:94-132`. Keep the encryption key outside the database, frontend bundle, source tree, and logs. Losing the key makes existing ciphertext unusable; changing the environment key does not rotate existing records. A deliberate re-encryption or MultiFernet migration is required. [Cryptography Fernet documentation](https://cryptography.io/en/latest/fernet/)
- `backend/scenarios` is mutable application state. YAML writes use a temporary file and replacement in `scenario_store.py:31-37` and `75-81`; deletion is at line 103. Atomic replacement protects individual files, but the ID allocation in `scenario_service.py:29-42` is a read-then-write operation and has no cross-request lock. Persist scenario edits across releases and seed an empty data directory explicitly. A volume mounted over packaged scenarios can hide the packaged seed files.

Keep these files on a filesystem owned by the backend account, outside the public static directory. Stop experiments and scenario edits for a coordinated backup of both databases and YAML. Use SQLite's backup API or `.backup` for each live database rather than an uncoordinated file copy. Separate SQLite backups do not make the whole multi-file application state transactional. Retain the encryption key in a separately protected recovery store, and test restoration on an isolated instance. Browser investigation configurations also need a separate export strategy if they matter; `frontend/src/utils/sessions.js:1-16` stores those configurations through browser storage, rather than the backend users/session tables. [SQLite backup API](https://www.sqlite.org/backup.html)

SQLite is suitable for a modest single-host workload, but permits one writer at a time per database. Do not put its files on an arbitrary shared network filesystem or assume multiple replicas each get a coherent copy. A client/server database becomes appropriate when many concurrent writers or distributed application instances are required. Adding a database URL alone cannot change the current direct `sqlite3.connect` adapters. [SQLite appropriate uses](https://www.sqlite.org/whentouse.html)

As a concrete managed-host example, Render documents an ephemeral default filesystem. Only paths under an attached persistent disk survive restarts and releases, and a disk-backed service cannot scale to multiple instances. Its free web services cannot attach persistent disks. This makes a free ephemeral backend unsuitable for the current durable SQLite/YAML design. This example is not a provider selection or price quote. [Render disks](https://render.com/docs/disks), [Render free services](https://render.com/docs/free), [Render scaling](https://render.com/docs/scaling)

`ManagedSecretsAdapter` is an extension seam, not a configured cloud integration. `web.py:15-18` selects it only when a client is injected; module-level startup injects none. Its credential references exist only in `_references` in `secrets.py:49-90`. A restart or another worker loses that reference catalogue even if a cloud service retains the secret. Implement durable metadata and a concrete least-privilege provider client before selecting this adapter for hosting.

## Browser routing, HTTPS, and authentication

Prefer `https://<host>/` for static assets and `https://<host>/api/...` for the backend. Preserve the `/api` prefix upstream because the routers already include it. Configure SPA fallback for routes such as `/sessions` and `/admin/users`, but do not send missing `/api` requests to `index.html`. The current frontend client defaults to `/api` in `frontend/src/lib/http/client.js:1-3`; Vite's `/api` proxy in `frontend/vite.config.js:7-10` applies to development and does not configure a production static host.

Terminate HTTPS at a maintained proxy or platform edge, expose only that edge, and trust forwarded headers only from the actual proxy. FastAPI documents the HTTPS termination pattern and the need to handle forwarded information correctly. [FastAPI HTTPS deployment](https://fastapi.tiangolo.com/deployment/https/)

`interfaces/http/routers/auth.py:15` sets an HttpOnly, SameSite=Lax session cookie without Secure or an expiry. `users.py:70-96` stores a hash of a random token and rechecks active status, but does not enforce a finite server-side session lifetime. A browser session cookie does not supply server-side expiration. ADR 0002 explicitly defers session expiry, passcode reset, and persistent audit history. Add a production Secure-cookie setting, bounded server sessions, login abuse controls, and an explicit CSRF/origin policy for state-changing routes before public exposure. HttpOnly does not itself stop cross-site requests. [MDN Set-Cookie reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)

The seed variables are `POISONTRACE_ANALYST_USERNAME`, `POISONTRACE_ANALYST_PASSCODE`, `POISONTRACE_SUPERADMIN_USERNAME`, and `POISONTRACE_SUPERADMIN_PASSCODE`. `users.py:53-66` skips an account when its passcode variable is absent and uses `INSERT OR IGNORE` when it exists. Changing a seed passcode in the environment therefore does not reset an existing account. Provide a deliberate first-admin and recovery procedure, with strong unique credentials supplied through host secrets. Never publish development credentials.

If the browser calls an independently hosted API origin, the frontend needs an explicit API base URL and `credentials: "include"`; the backend needs credentialed CORS with exact allowed frontend origins. `interfaces/http/app.py:15-42` has no CORS configuration, and the default client supplies no credential override. Cross-origin is different from cross-site. Sibling HTTPS subdomains may be same-site, while unrelated hosting domains generally require SameSite=None and Secure, and can still encounter third-party-cookie restrictions. A same-origin proxy avoids this extra failure mode. Never use wildcard allowed origins for credentialed CORS. [FastAPI CORS documentation](https://fastapi.tiangolo.com/tutorial/cors/), [MDN Set-Cookie reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)

## Execution time and concurrency

`interfaces/http/routers/campaigns.py:27-30` calls campaign execution inside the HTTP request. `web_adapter.py:225-285` loads each selected scenario and calls the model sequentially before returning. The frontend waits for that execute response in `frontend/src/features/campaigns/api/campaignApi.js:9-10`. Single runs likewise execute in the POST handler. There is no durable background queue, job lease, cancellation protocol, or recovery for a process that dies after setting a campaign to `running`.

The model adapters make synchronous provider calls in `openai_model.py:31-57` and `gemini_model.py:33-61`. They do not explicitly configure application request deadlines or retry budgets; SDK defaults may still apply. Measure real campaign durations before configuring proxy and hosting timeouts. Increasing an HTTP timeout does not create restart recovery, prevent duplicate executions, or make a client retry safe. Provider rate limits, cost caps, and outbound HTTPS access also need an operational policy before public users can initiate paid runs.

One Uvicorn worker does not serialize these operations. FastAPI runs ordinary `def` endpoints in a thread pool, so requests can overlap within one process. The async role middleware also calls synchronous SQLite lookups in `interfaces/http/app.py:20-26`. [FastAPI concurrency documentation](https://fastapi.tiangolo.com/async/)

Specific correctness blockers are visible in the source:

- `web_adapter.py:138`, `265`, and `318` use `latest_run_id()` after a run finishes. Another overlapping run can change the latest ID before lookup and associate a response or campaign with the wrong run. Return the saved ID directly through the runner boundary.
- `web_adapter.py:226-240` checks `created` and sets `running` as separate database operations. Concurrent execute requests can both pass the check. Use an atomic conditional state transition and reject duplicate execution.
- Scenario creation allocates IDs outside a transaction or lock, and concurrent edits can overwrite each other. Serialize mutations for the demonstration or introduce conflict detection and durable ID allocation.
- Campaign creation scans `*poisoned*.yaml` directly in `web_adapter.py:159-162`. It can fail on malformed YAML instead of applying the library's usable-scenario filter. Verify this path against ADR 0001 before relying on unattended campaigns.

For an invited FYP demo, permit one active experiment or campaign at a time and freeze scenario editing during execution. Enforce that policy in the backend if more than one client can connect. For a public service, use persisted queued jobs, explicit run IDs, atomic job claims, bounded provider timeouts, status polling, restart recovery, and idempotent submission. Those changes are required work, not functionality supplied by deploying with extra workers.

## Public-exposure blockers and a reviewable next step

Backend role enforcement exists in `interfaces/http/app.py:25-34`: analysts can use the investigation API, and superadmins can use the admin API. However, data ownership is absent. Runs and campaigns have no user owner in `persistence/support.py:9-12`; credentials have no owner in `secrets.py:105-109`. Every authenticated analyst reaches the same services. Treat this as a shared trusted research workspace until a deliberate ownership and authorization policy is implemented. Role checks alone do not provide separate user workspaces or separate provider-key budgets.

Public BYOK makes this a launch blocker. Associate credentials, runs, campaigns, and their trace/history records with the authenticated backend user. Enforce ownership on listing, lookup, replacement, revocation, testing, and execution, including campaign reruns and child-run detail access. Never accept a browser-supplied owner as authoritative. Add cross-user authorization tests through these HTTP seams. The user selected a curated read-only public library. Enforce that profile in backend mutation routes, not only hidden frontend controls, while retaining local CRUD and invalid-file repair under ADR 0001.

BYOK means the backend receives the visitor's key, decrypts it when needed, and uses it for outbound provider requests. The current flow is visible in `web_adapter.py:109-119` and `232-239`; it is not browser-only provider access. Explain this to visitors. Keys will remain encrypted across logins until their owner revokes them. Implement owner-authorized revocation and define deletion behavior and backup-expiry policy before launch. Deleting an active database row does not erase older backups. The current encrypted store is useful, but encryption does not replace user isolation. BYOK also does not prevent application abuse or unexpected charges on a visitor's provider account. Apply per-user concurrency and request limits, provider usage controls, and secret-safe logs.

Before invited remote access, resolve clean installation and data-path configuration; build the static frontend; establish HTTPS and restricted access; set secure unique accounts; persist and restore the data; and enforce experiment serialization. Verify login, role rejection, logout, deep-link refresh, scenario edits, a fake run, campaign status, restart persistence, and a full isolated restore. Paid provider tests require separately authorized keys and an explicit spend limit.

Before unrestricted internet access, also resolve ownership and credential permissions, session security and abuse controls, concurrency correctness, durable execution, recovery, request/input limits, and operational logging that excludes secrets. Decide whether API documentation should remain public; `/docs` and `/openapi...` currently bypass authentication in `interfaces/http/app.py:21`. Review the intentional benchmark attack inputs as untrusted data and preserve the synthetic-data boundary from the implementation brief.

The next implementation should produce two documented profiles: the public authenticated BYOK service and the open-source local application. Admission, privacy, scenario editing policy and active-key retention are settled in ADR 0003. Host, expected simultaneous users, operational budget, historical backup erasure and recovery targets remain open before final deployment configuration. No particular cloud account, domain, region, or paid plan is assumed by this review.


## Recommended first public topology and readiness checklist

Use one server with a maintained HTTPS reverse proxy serving the compiled frontend and forwarding /api to one backend instance, with local persistent storage and a supervised durable executor. Containers are optional packaging for the same topology, not a substitute for the missing execution and ownership behavior. This is the lowest-change recommendation for the current SQLite/YAML implementation, not a selected cloud vendor. Use admission limits until measured workload establishes capacity. Keep the local edition available with fake models by default and optional live provider keys.

- [x] Audience and behavior agreed in ADR 0003: public issued accounts, live BYOK, private keys/history, curated scenarios, encrypted keys until revoked; local scenario CRUD retained.
- [ ] Clean runtime install, declared cryptography/YAML/model dependencies, deterministic package/import setup, and a tested container or documented server installation.
- [ ] Explicit database/scenario paths, profile configuration, first-admin setup and account recovery. Confirm an open-source license and sanitized example configuration before publication; no license audit was performed here.
- [ ] Backend owner enforcement and cross-user denial tests for credentials, run history, campaign details, execution and child traces. Partition or clear browser configurations on account changes as well.
- [ ] Public scenario mutations rejected while local repair and CRUD continue to pass ADR 0001 tests.
- [ ] Correct run-ID return, atomic campaign claims, usable-scenario eligibility and durable execution/restart recovery.
- [ ] HTTPS, Secure cookies, finite server-side sessions, login/request limits, explicit origin/CSRF policy and input bounds. Keep both role restrictions from ADR 0002.
- [ ] Key-handling disclosure, verified revocation, no keys in responses/traces/logs, encrypted backups and separate key recovery. Set a backup retention/expiry policy consistent with revoked keys.
- [ ] Same-origin routing and SPA deep links verified against the real backend, plus live-provider tests with authorized disposable credentials and bounded spend.
- [ ] Persistence across restart/release and isolated restore drill, provider failure/timeout tests and concurrent-user tests. Measure duration and load before choosing a host plan.

No item above is satisfied by the existing mocked browser captures or the passing unit suite alone. Host, budget and capacity preferences can be decided after these code slices are concrete; no resources need to be provisioned during architecture review.


## Path update after organization, 2026-11-03

The historical source paths/line numbers above predate the completed organization. Current concrete storage is in adapters/persistence and adapters/secrets/storage.py; YAML files are handled by adapters/scenarios; accounts/authentication are in application/accounts.py with SQL in adapters/persistence/accounts.py; execution is in application/execution.py and campaigns.py; seed environment reads are in config.py and construction is in bootstrap.py. Historical imports remain where compatibility is tested. These relocations do not resolve any listed public-exposure blocker. Relative paths, dependency declarations, ownership, session lifetime, campaign eligibility/claims, saved-run correlation and request-bound execution behavior remain unchanged. No deployment, clean-install, live-provider, recovery or concurrency verification was performed.


## Compatibility retirement note, 2026-11-03

Historical Python compatibility modules and RunWebAdapter have now been retired after consumer migration. Configured web startup uses bootstrap.build_web_backend returning Backend, followed by bootstrap.create_app. The documented Uvicorn entrypoint remains poisontrace.web:app; HTTP routes, CLI commands and storage behavior are unchanged. ARCHITECTURE.md is the current path guide. No deployment blocker above was resolved by this source cleanup.
