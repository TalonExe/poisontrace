# Application backup and recovery

These commands are for one production runtime and one executor. Use the matching
application build and profile for restore. An operator needs filesystem access
to the application root, a separately protected recovery ledger and an
independent encrypted archive destination. Keep each installation's ledger in
its own directory. Grant its runtime account write access to the ledger and its
SQLite sidecars. Keep source, destination and restore parent directories under
exclusive operator control. Use local filesystems with SQLite locking and hard
link support. For containers, mount the independent paths explicitly and run
the operator command with entrypoint `python -m poisontrace.recovery`.
The stock Compose file does not configure these mounts.

Set these environment variables through the operator's secret and configuration
channels:

- `POISONTRACE_RECOVERY_LEDGER` is an absolute SQLite file path outside the state
  root. Configure it before the first eligible backup. Startup creates a new
  ledger only at enrollment. Once enrolled, the application requires that
  installation's ledger. Keep the latest copy available independently of the
  application volume. Preserve its SQLite transactions when replicating it.
- `POISONTRACE_SECRETS_KEY` is the existing application Fernet key. Keep an
  independently recoverable copy. The application uses it to decrypt provider keys.
- `POISONTRACE_BACKUP_KEY` is a different Fernet key supplied to backup and
  restore only. Keep it in separate custody from the archives. Recover both
  keys through the secret channel before rehearsing a restore.

## Drain and create an archive

1. Block incoming traffic at the operator-controlled entry point. Allow
   already admitted work to finish if the maintenance window permits. A
   bounded stop can interrupt current work. Stop the server and wait for
   its supervised worker and MCP children to exit. Stop any other direct
   writers, including account commands and development/CLI processes.
2. Run `python -m poisontrace.recovery backup /backup/snapshot.ptbackup` with
   the original runtime settings and both keys. The parent must already exist
   on independent storage. The command holds the runtime and executor locks,
   snapshots both SQLite databases with SQLite's backup API and copies the
   YAML, JSON, and seed marker. The versioned encrypted archive is published
   under a new name after validation and encryption. The unencrypted SQLite
   snapshots are temporary files under the private data root. If the process
   is killed abruptly, check that private root for abandoned temporary
   snapshots before reopening access. The current tool limits the assembled
   uncompressed snapshot to 64 MiB.
3. Confirm command success and test an isolated restore. Retain the previous
   usable archive when a new backup fails. Restart the original service only
   after maintenance ends. An interrupted claim is reconciled on executor
   startup. A job queued on the original current database can proceed there.

The application database contains users, session hashes, traces and scoring,
actual group and campaign links, pinned plans, retained reruns, and versioned job
snapshots. The second database contains encrypted provider credentials. YAML
and JSON are local content and overrides. Browser-local configurations and
immutable packaged assets are outside the archive. Retain the exact build or
a compatible build independently.

## Restore and reconcile before reopening

1. Keep the source stopped before cutover. Recover the latest authoritative
   independent ledger for this installation. The archive alone cannot prove
   that a ledger copy includes all changes made after the snapshot. If ledger
   freshness is uncertain, keep admission closed until it is established.
   Retain the original state or damaged media for investigation without
   mounting it in the replacement application.
2. Run `python -m poisontrace.recovery restore /backup/snapshot.ptbackup /isolated/state`
   with both recovered keys, the ledger and the original data-root setting.
   Use a new directory on private storage. Authentication of the archive,
   inventory, SQLite checks, installation identity and application key checks
   precede publication. The restored root is marked pending and server startup
   refuses it.
3. Compare the restore point with authoritative account administration records.
   Review account disables, role changes and passcode resets after the snapshot.
   Also review out-of-band content edits or deletions. Use the existing
   operator recovery command for a superadmin passcode where needed. For
   HTTP-only account corrections, perform them during the isolated admission
   check after activation and before opening the entry point. Keep the entry
   point closed until the current account status and role set are confirmed.
   If the account changes cannot be established, leave access restricted.
4. Set `POISONTRACE_DATA_ROOT` to the restored root. Run
   `python -m poisontrace.recovery activate --reviewed`. Activation reapplies
   the current ledger to credentials and YAML, applies linked history
   tombstones, and clears all backed-up sessions. Active jobs become
   interrupted/uncertain and keep saved children. A backed-up queued job may
   have started after the snapshot, so activation marks it interrupted and
   requires an explicit rerun. Unstarted child slots are missing. The executor
   never automatically reruns these jobs.
5. Start on an isolated listener while public traffic stays blocked. Check
   operator login, analyst role and ownership, credential retrieval without a
   provider call, retained history and actual links, pinned comparisons, and
   interrupted job status. Resolve account changes identified in step 3
   before reopening. Switch traffic only after those checks pass.

Credential deletion and replacement record the superseded encrypted value's
digest independently before the active write completes. The restored store
discards matching old values, including values from before a later revocation.
Active retrieval checks the ledger. It cannot recall an in-flight provider
client. Local YAML deletes through the application are recorded by filename and
archive revision. Direct filesystem edits and deletes need the operator's
separate review. The ledger contains deletion IDs and digests, so protect its
access and keep it for the lifetime of the oldest recoverable archive. Avoid
running the original and restored installations against the same ledger.

## Expiry and key custody

Run `python -m poisontrace.recovery expire-history --days DAYS` while stopped.
This uses an inclusive UTC cutoff. It treats a group, campaign or job and its
connected results as one unit. Any pending job, newer record or undated legacy
record protects the linked unit. This keeps retained attempts, actual run links,
scores and provenance intact. Undated standalone history needs a separate
approved disposition. Expiry writes deletion IDs to the independent ledger
before committing the application deletion, so an older archive cannot bring
those records back on activation. If the application write fails, retry expiry
before restarting. Once expired, the old job intent no longer identifies a
retained job. New submissions require a deliberate user action.

Run `python -m poisontrace.recovery expire-backups /backup --days DAYS` on the
dedicated archive store. It removes regular `.ptbackup` files whose recorded
filesystem modification time is at or before the cutoff. Preserve that
timestamp when moving copies. Apply the same policy to independent replicas
and storage snapshots through their storage controls. Credential revocation
and history expiry prevent later use in the application. Encrypted copies
can still contain the old material until archive expiry. File deletion alone
does not guarantee physical erasure from SQLite pages, storage snapshots,
replicas, or filesystem recovery. Disclose the approved expiry window and
any longer-lived copies to users before launch.

A lost archive key makes archives encrypted by that key unrecoverable. To
rotate it, create a new archive with a new key and verify it in isolation.
Keep old keys under separate custody while their archives remain recoverable.
Recover an archive with the application key used for its state. Losing that
key makes its provider ciphertext unreadable and blocks normal activation.
Changing the environment value alone is not rotation. Application-key
rotation in place is outside the tool: a migration must re-encrypt the
credential database and verifier, preserve revocation enforcement, and be
rehearsed separately. Keep any historical application key needed for
unexpired archives or deliberately retire those archives. Never reintroduce
a revoked provider key to recover access.

The 30-day history window, seven days of daily backups, 24-hour RPO and one
working day RTO are proposals. Operators supply positive retention days
explicitly. Approve ownership, cadence, storage custody and retention before
operating the schedule. Measure restore time and archive age with representative
data and the intended storage during a separate operating rehearsal.
