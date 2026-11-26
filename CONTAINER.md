# Local production container

The production runtime packages both editions with operator-issued accounts, analyst-owned credentials/history, hosted read-only content, bounded sessions, account recovery and durable single/group investigations. Ownerless legacy records remain quarantined. Metadata runs and campaigns also use the durable executor. See [data recovery](DATA_RECOVERY.md) for coordinated backup, isolated restore and expiry. Neither profile is ready for public exposure. [STATUS.md](docs/STATUS.md) records exact implementation and verification limits.

## Build and start

Use a Linux Docker engine and Docker Compose v2, or use the standalone Podman verification command below. No existing Python environment or Node installation is required for the image build. The build uses the frontend lockfile, pinned runtime closure and pinned Python/Node base versions. Base tags are versioned, not digest locked. On 18 November, the user-run Podman acceptance check passed a clean Linux build and the offline container checks described below.

Build directly before setting a key, then generate a disposable verification key using the built runtime. Keep the key in your shell for subsequent commands. Compose requires it even for configuration:

```sh
docker build --no-cache -t poisontrace:local .
export POISONTRACE_SECRETS_KEY="$(docker run --rm --network none --entrypoint python poisontrace:local -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
docker compose --profile local run --rm local init-admin
docker compose --profile local up -d local
```

The admin command prompts for username and a hidden passcode. Automation may supply `POISONTRACE_ADMIN_USERNAME` and `POISONTRACE_ADMIN_PASSCODE` only to that one-off command. They are not forwarded by Compose. Run initialization while the server is stopped. It refuses to bootstrap when any account already exists and never resets an existing passcode. Normal container startup ignores development analyst/superadmin seed variables. Sign in at `http://127.0.0.1:8000`, issue an analyst through User management, sign out, and sign in as that analyst. Superadmins cannot use the investigation workspace.

Choose Scripted offline in Experiment, then Single run and Run MCP investigation. No provider key is required. Results opens using the returned saved ID and survives refresh. The default UI remains the existing matched-group workflow; no visual system changes accompany packaging.

`docker compose --profile local restart local` keeps state. `docker compose down` also keeps the named volume. Do not use `down -v` for retained state. Keep the encryption key separately across restarts. Losing or changing it does not rotate existing ciphertext and may make saved provider keys unreadable. Recover the application and archive keys separately using the [data recovery procedure](DATA_RECOVERY.md).

For the hosted packaging profile, replace `local` with `hosted` in both the profile and service arguments. Compose gives each profile a separate named volume. Run only one service/profile at a time on the default host port. The hosted profile enforces read-only curated content in the application services and HTTP API. Local retains YAML creation, repair, updates and deletion, plus versioned research-case ground-truth editing. Login/session responses supply the browser read-only capability; hosted pages offer inspection without editing actions. This does not establish public deployment readiness. Compose binds the host port to loopback in both profiles. No host-directory or Docker-socket mount is used.

## Operator account recovery

`init-admin` is the fresh-installation procedure above. It refuses an installation
with any existing account. Changing development seed values or bootstrap environment
values never resets an existing passcode. Normal production startup ignores them.

For lost administrative access, restrict admission and stop the server before
using the same image, profile, persistent volume and externally retained encryption
key. Only a trusted operator with host/container and volume access may run recovery.
Do not expose this command through HTTP or grant analysts host access. For the local
Compose profile:

```sh
docker compose --profile local stop local
docker compose --profile local run --rm local recover-admin
docker compose --profile local up -d local
```

Use `hosted` for both profile and service when recovering the hosted volume. The
command prompts for the existing superadmin username, then a hidden new passcode
and hidden confirmation. Recovery ignores `POISONTRACE_ADMIN_USERNAME` and
`POISONTRACE_ADMIN_PASSCODE`. Do not put passcodes in command arguments, shell
history, tickets, logs or terminal transcripts. A terminal that cannot hide input
fails closed. New recovery passcodes must contain 1 to 1024 characters. Operators
should generate a unique strong value and use an approved private delivery channel.

Recovery refuses unknown users and analysts. It never creates a replacement account
or promotes an analyst. A disabled superadmin requires deliberate re-enablement:

```sh
docker compose --profile hosted run --rm hosted recover-admin --enable-disabled
```

Keep the server stopped for that command too. Recovery preserves the account ID,
username, display name and role, replaces only the salted one-way scrypt passcode
hash, and deletes all affected sessions in the same SQLite transaction. Other
accounts and sessions remain unchanged. Without the explicit enable option a
disabled administrator remains disabled. Success prints a fixed confirmation;
failure exits nonzero with safe text and no passcode. Confirm fresh authentication
after restart. No admin recovery HTTP endpoint exists. The last-active-superadmin
disable/demotion guard remains in force.

An authenticated active superadmin can select an analyst in User management, choose
Reset analyst passcode, enter and confirm a new value, and submit. Success revokes
every session for that analyst, including other browsers, without changing identity,
role or status. Disabled analysts remain disabled; enabling later requires a fresh
login and old tokens never revive. The browser clears reset values after success,
server failure, cancellation or account selection changes. Superadmins require the
restricted operator recovery command above. Analysts cannot reset themselves or
others. There is no self-service email or public registration flow.

The backend endpoint is `POST /api/admin/users/{id}/passcode` with a `passcode`
JSON field. It authenticates the current superadmin again inside the account-write
transaction. It returns a fixed success response, 401 for absent/revoked sessions,
403 for other roles or an invalid hosted Origin, 404 for unknown users, and 400 for
an invalid passcode or superadmin target. Malformed requests return safe 422 text
without echoing the body. Passcodes never enter URLs or successful responses.

Reset/recovery preserves private encrypted provider credentials, saved history,
retained reruns, scores, provenance and account-scoped browser preferences. It does
not grant superadmins analyst-workspace access or decrypt credentials. It does not
cancel already admitted execution. Hosted login throttle windows remain in effect
after recovery, so wait for Retry-After rather than deleting counters. This account
procedure does not replace coordinated backup/restore or key recovery. Durable
job interruption handling is described below. The [data recovery runbook](DATA_RECOVERY.md) covers archive restoration.

## Configuration and state

| Setting | Container default | Meaning |
| --- | --- | --- |
| `POISONTRACE_PROFILE` | `local` | Exactly `local` or `hosted` |
| `POISONTRACE_PUBLIC_ORIGIN` | Required for hosted | Canonical HTTPS origin, such as `https://demo.example.org`, without path or trailing slash |
| `POISONTRACE_TRUSTED_PROXIES` | Empty | Comma-separated explicit proxy IPs/CIDRs; never all-address networks |
| `POISONTRACE_DATA_ROOT` | `/data` | Absolute persistent root, separate from frontend assets |
| `POISONTRACE_FRONTEND_ROOT` | `/opt/poisontrace/frontend` | Absolute built asset root with index.html |
| `POISONTRACE_SECRETS_KEY` | Required | External Fernet key, never copied into the image |
| `POISONTRACE_BIND` | `0.0.0.0` | Uvicorn interface |
| `PORT` | `8000` | Uvicorn port, 1 through 65535 |
| `POISONTRACE_LOCAL_PORT` | `8000` | Compose host loopback port |

`/data/poisontrace.db` contains accounts/sessions, runs/traces, campaigns, matched groups/attempts and execution jobs. `/data/poisontrace-secrets.db` contains encrypted credentials. `/data/scenarios/` contains curated YAML, and `/data/investigation-cases/` contains JSON ground-truth overrides. These are writable through local authoring only; hosted mutation requests return 403. Operators can curate a stopped local volume before selecting hosted mode. Switching profiles never resets existing overrides, seeds, saved group snapshots or retained attempts. Browser configurations remain browser-local storage.

Bundled corpus, manifest and YAML seeds are installed as immutable package assets outside `/data`. First initialization copies missing YAML seeds and writes `.scenario-seeds-v1`. Subsequent restarts preserve edits and deletions. This is initialization, not a migration of existing working-directory databases. The container never opens the repository's historical databases. New seed releases require an explicit migration decision.

Settings and built assets are validated before directory or database creation. Missing/invalid keys or invalid paths/profile/port stop startup. An unusable data root stops startup with a storage error. `/health/live` reports a running process. `/health/ready` checks writable state directories, existing main/credential schemas, SQLite writer acquisition and index.html. Storage loss returns JSON 503 without raw paths or credentials; readiness does not recreate a missing database. These probes do not claim provider availability, key decryption, owner isolation or interrupted-job recovery.

The production entrypoint is `python -m poisontrace.production serve`. It uses one Uvicorn worker without reload. Uvicorn proxy-header rewriting stays disabled; the hosted HTTP policy handles only explicitly trusted peers as described below. FastAPI serves built assets and `/api` on the same origin. Configurations, Experiment, Results and admin deep links receive the SPA shell. Missing asset/API requests retain errors rather than successful HTML. Existing authentication and role middleware remain authoritative for API access.

Compose runs UID/GID 10001, read-only root, a named data volume, 64 MiB temporary filesystem, no capabilities, no new privileges, one CPU, 1 GiB memory and 64 PIDs, with an init process and 30-second stop grace. These are local verification bounds, not measured capacity or application admission limits. The fixed MCP transport launches two Python stdio children per investigation. It needs neither Docker nor provider credentials inside the runtime.

## Verification

On a machine with a reachable Linux Docker engine:

```sh
python scripts/verify_container.py
```

For Podman, run this from a terminal that can access your running Podman machine:

```powershell
Set-Location C:\Users\TalonExe\Documents\FYP-implementation\Project
.venv\Scripts\python.exe scripts/verify_container.py --engine podman
```

The runner invokes Podman directly and needs no Docker socket or Compose provider. It stages only explicit build inputs into a temporary directory outside the project, so remote clients never enumerate local scratch data, databases, logs or agent/tool folders. Its Podman build requests Docker image format so the healthcheck is retained, and the Dockerfile uses fully qualified image names. On 18 November, Podman 5.8.1 was present, but the agent sandbox could not read the configured Podman SSH identity and failed before contacting the engine. Starting the machine does not grant that sandbox access. Do not copy the identity into the repository or loosen its permissions. This runner uses only generated application credentials and its own disposable state.

This builds without cache, generates disposable accounts/key, creates a uniquely named scratch volume, runs without a network, checks installed corpus/manifest, non-root execution, deep links/API status, real two-child MCP normal/error/cancellation cleanup, saved Results after restart, missing-key startup and unavailable-storage readiness. It removes only its own named container/volume/image. It does not touch Compose state. Build failures include the last 16,000 characters of build output. Runtime/application diagnostics remain suppressed to avoid exposing generated credentials. The user supplied a successful Podman acceptance result on 18 November; it is historical evidence and does not verify later source changes. The agent sandbox itself cannot use the Podman connection identity.

Production browser verification, after building `frontend/dist` and installing the repository's test dependencies:

```sh
cd frontend
node node_modules/@playwright/test/cli.js test --config playwright.production.config.js
```

The browser check uses an isolated synthetic supervisor, built assets and the production app, without Vite or API interception. It checks admin/analyst login, issued accounts, role denial, deep-link refresh, real offline MCP and saved Results across server process restart. Its shutdown/restart routes exist only in the test harness and are excluded from the image. Set `POISONTRACE_TEST_PYTHON` to an absolute test Python executable if necessary. Browser automation was run on Windows against the production app. Linux container behavior was verified through HTTP by the user-run acceptance script; browser automation was not run inside the Linux image.


## Analyst provider credentials

HTTP establishes a trusted `Principal(account_id, role)` from the authenticated
backend session. The browser cannot choose credential ownership. The encrypted
SQLite store adds nullable `credentials.owner_id` and an owner index at startup.
All reads, masked metadata, replacement, retrieval checks, deletion and execution
resolution filter by the current analyst account ID before decrypting. A
superadmin has no analyst credential access. Unknown and foreign references
return the same `404 credential not found` response.

Keys remain encrypted on disk until their owning analyst revokes them. The
backend decrypts BYOK keys into memory to construct the selected provider client;
this is server-side BYOK, not end-to-end encryption from the operator. The master
Fernet key must remain separate from data, images and logs. Key values do not
enter saved run configurations, traces, MCP child environments or responses.
Credential `POST /api/credentials/{id}/test` checks authorized stored-key retrieval
and decryption only. It does not contact a provider, validate billing/access or
prove that the key is accepted by a live model. Verification uses generated keys
and offline substitutes. Application provider runs and campaigns require an
owned reference and cannot fall back to server environment provider keys. The
separate local CLI retains its explicitly configured environment-key behavior.

Revocation removes the active encrypted record and prevents subsequent retrieval,
including each new campaign child or group attempt. It cannot recall a key
already supplied to an in-flight provider client or cancel a request already
sent. The independent ledger reconciles revoked credentials on restore. Archive expiry requires an approved operating policy. See [data recovery](DATA_RECOVERY.md).

### Ownerless legacy quarantine

Existing records migrate with `owner_id = NULL`. They remain encrypted and are
inaccessible to every analyst and superadmin, including listing, testing and
execution. Login never claims them. The migration reads schema metadata only;
it does not enumerate, decrypt, relabel or reassign legacy keys. Historical runs,
groups and credential references are retained without fabricated ownership.
Analysts must save a fresh key under their issued account and select that new
reference for future runs. Existing campaign configurations with a quarantined
reference cannot execute or rerun; create a new campaign with an owned key.
Owned groups may explicitly rerun with a current owned reference. Ownerless legacy
groups and campaigns cannot be opened or rerun by any viewer.

No legacy ownership-assignment command is provided. Any future attribution or
purge is a separate operator-controlled, explicitly authorized migration with a
coordinated backup, verified account mapping and maintenance window. Do not inspect
private records to guess ownership. Keep quarantined ciphertext until that
separate decision. Do not roll back to an application version that ignores owner
checks while allowing traffic. Account IDs refer to the paired main database;
restore main and credential databases together rather than attaching one analyst
store to unrelated accounts.

Backend ownership covers run/history, traces, metrics, group/campaign plans and
reruns. Browser configurations/execution are account-scoped; existing unscoped
records remain preserved without guessed ownership. Hosted content is read-only.
Single/group execution uses the shared durable admission contract below.
Metadata and campaigns use the same admission slot. Operating release gates remain open.

## Hosted login and sessions

Both editions issue random server-side sessions with a fixed eight-hour deadline.
Requests never extend the deadline. SQLite retains only the token hash and expiry;
restarting preserves the deadline. Existing sessions without expiry fail closed
and require a fresh login. No account, key, run, group, campaign or score is
reassigned or rewritten. The application accepts an injected clock for offline
verification; the shipped runtime uses system UTC time. Keep the system clock
correct. There is no sliding idle timeout or automatic background execution logout.

The host-only `poisontrace_session` cookie has Path=/, HttpOnly, SameSite=Lax and
Max-Age=28800. Hosted always sets Secure, independently of forwarded headers.
Local keeps HTTP loopback compatibility without Secure. Lax permits top-level
navigation from external links; it is supplementary to the origin check below.
Logout deletes the server record and cookie. Disable and role changes revoke all
sessions atomically with the account update. Re-enable never restores old tokens;
the user must authenticate again. Display-name edits retain sessions. Every
protected request still checks the current account and role. Revocation/expiry
does not cancel work already admitted by a request.

Hosted requires an exact configured Origin on every method other than GET, HEAD
and OPTIONS, including login and logout. Missing, null, foreign, duplicate and
cross-site origins fail before route execution. Non-browser clients must send
the configured Origin as well as authenticate. Referer alone is not accepted.
No credentialed cross-origin CORS policy is enabled. All API responses use
Cache-Control: no-store. Hosted /docs, /redoc and /openapi.json return JSON 404
for anonymous and authenticated visitors; local documentation stays available.
The fixed origin follows [OWASP's origin-validation guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

Terminate TLS at an operator-controlled proxy and restrict backend ingress to
that proxy. Set POISONTRACE_PUBLIC_ORIGIN before hosted initialization or startup.
Configure POISONTRACE_TRUSTED_PROXIES to the actual immediate peer IPs or bounded
networks. The proxy must preserve the public Host and overwrite client-supplied
X-Forwarded-Proto with a single `https` value and X-Forwarded-For with one valid
client IP. Chains, empty values and malformed addresses fail closed for trusted
peers. Forwarded and X-Forwarded-Host never determine the origin or host.
Untrusted peers' forwarded values are ignored, so direct HTTP cannot claim TLS
or rotate its login identity through those headers. Direct TLS is also supported.
Health probes remain available over the internal HTTP connection without proxy
headers or authentication. Keep Uvicorn's own proxy rewriting disabled when using
an alternative launch command. Do not trust `*`, 0.0.0.0/0 or ::/0. A real vendor's
ingress/overwrite contract must be verified during the separately authorized pilot;
no Render address ranges or real deployment are asserted by these local tests.

Hosted login reserves each attempt before passcode hashing in a SQLite transaction.
Five-minute fixed windows allow 10 attempts per normalized account, 60 per client
IP and 200 globally. Success counts too; restarting or rotating usernames/IPs does
not reset the other limits. The first reservation starts each window. Rejections
return 429 with Retry-After seconds and do not extend the window. Only hashed
bucket identifiers, counters and deadlines persist. Expired buckets are removed;
the table also has a 4096-bucket fail-closed bound. These conservative limits may
temporarily deny legitimate sign-ins and are not a distributed denial-of-service
defense. Local login keeps its separate loopback behavior without these hosted
throttles. Browser recovery distinguishes invalid credentials, throttling and
service failure. A protected-request 401 or focus-time session loss unmounts the
workspace, clears the active account/configuration and cached Results, and asks
for login. Account-scoped saved preferences remain private to that account.

For local HTTPS browser verification set POISONTRACE_TEST_CONTENT_PROFILE=hosted
before the production Playwright command above. The isolated supervisor generates
a disposable localhost certificate and test-only controllable clock. It does not
change the shipped TLS configuration, reuse private accounts or contact providers.


## Single-investigation jobs

Run one application instance with one Uvicorn worker on the persistent local
volume. The application supervises its single-investigation executor automatically;
do not launch an additional external job service. The database-adjacent executor
lock is an OS lock, not a stale PID file to delete while the service runs.

Single MCP submissions use POST /api/investigation-jobs and an explicit
Idempotency-Key. Keep that key when retrying an uncertain HTTP response. Poll the
returned job ID or reopen the Experiment single-run page. Queued and active jobs
occupy the sole durable admission slot. Excess work receives an explicit busy
response and is not queued. Completed and ordinary failed jobs link their actual
saved Results runs. After executor termination, active jobs become interrupted
with a provider-outcome uncertainty warning; restarting never replays them.
A deliberate new attempt needs a new intent and may incur another provider charge.

Admission accepts at most 4096 body bytes and 200 UTF-8 bytes per selection field.
The evidence loop retains its four-call, 16384-byte-output and 20-second limits;
a 45-second watchdog terminates a stuck worker and its MCP descendants. A storage
busy response is safe to retry with the same intent. Provider diagnostics and
private request bodies are not returned as errors. Credential revocation before
worker retrieval prevents use; it cannot recall a key already passed to a provider.

Matched groups share this admission contract as described below.
Metadata runs and campaigns share the same admission slot.
Do not treat these single-job controls as public deployment readiness. Linux
container lifecycle verification remains a separate required operating check.


## Matched-group jobs

POST /api/run-groups and POST /api/run-groups/{group_id}/execute now require an
Idempotency-Key and return HTTP 202 with job_id and group_id before execution.
Poll /api/investigation-jobs/{job_id} and reopen /results/groups/{group_id}.
Retry an uncertain response with the same intent and inputs. An explicit rerun
needs a new intent and appends the entire saved schedule, retaining earlier slots.

Single and group jobs share one outstanding queued/active slot, the same SQLite
admission transaction/index, the same supervised worker and the same OS lock.
There is no independent group queue or capacity. Hosted submissions and reruns
allow one repeat and one to three unique clean/poisoned/defended conditions.
Larger local schedules remain supported; switching to hosted never rewrites
saved local plans and cannot execute their larger schedules. The 4096-byte body
and 200-byte UTF-8 selection limits also cover group submission/rerun endpoints.

The job, pinned plan and complete attempt allocation commit together. Each result,
returned run ID, trace association and owning attempt link commit together. The
last result also finishes the schedule/job in that transaction. A schedule can
finish with ordinary failed runs, whose scores remain unavailable. Every attempt
renews the finite 60-second lease and gets its own 45-second process watchdog,
while retaining the investigation's 20-second/four-call/output bounds.

After worker loss, active slots become interrupted with uncertain provider outcome;
unstarted slots become missing. Saved children remain linked. Unresolved slots
never acquire invented scores or provider retries. Queued jobs that have not
started may execute after restart. Polling survives browser refresh; Experiment
retains uncertain submission intents within the authenticated account workspace.
Results shows completed/failed/interrupted/missing/queued/active counts and links
only actual saved attempts. Existing comparison denominators are unchanged.

Metadata runs and campaigns share the same durable admission and supervised
executor. The Windows scratch rehearsal exercises application recovery.
Linux container lifecycle, actual-host proxy behavior, capacity, recovery
on the intended storage, live-provider effectiveness and release readiness
remain separate operating checks.

An older request-bound group may retain a running label without a durable job.
An explicit owner-authorized rerun can append a new schedule when shared admission
is free. Older unlinked slots remain missing, with no invented execution status or
score. The global outstanding-job check still rejects every concurrent durable
single/group submission before any allocation. No automatic legacy rerun occurs.
