# Local deployment readiness rehearsal

Issue #49 tests one Linux runtime and its supervised executor. Use five generated analyst accounts, one generated operator, disposable browser profiles, and new application, ledger, archive and restore storage. Keep provider egress disabled at the runtime network boundary. Use Scripted offline for real stdio MCP and the repository's offline SDK test doubles for provider behavior. Keep test doubles out of the release image. The current result and blockers are in [STATUS.md](docs/STATUS.md).

## Build and isolate

From the current checkout run `python scripts/verify_container.py --engine docker` or `python scripts/verify_container.py --engine podman`. This builds a fresh image in a staged context and runs the network-disabled packaging, local persistence and MCP child checks. It cleans up its own image, container and volume. For the load and cutover drill, build operator-owned candidate and rollback images separately with the same explicit build inputs. Use a known prior release source for the rollback image. Record both source identities, architecture, engine version and full image IDs. A second tag for the same image only tests replacement, so record that case separately if no prior compatible image is available.

```sh
docker info --format '{{.OSType}}'
candidate_context=$(mktemp -d)
python -c 'import sys; from pathlib import Path; sys.path.insert(0, "scripts"); from verify_container import stage_build_context; stage_build_context(Path.cwd(), sys.argv[1])' "$candidate_context"
docker build --no-cache -t "$candidate_tag" "$candidate_context"
docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Size}}' "$candidate_tag" "$previous_tag"
candidate=$(docker image inspect --format '{{.Id}}' "$candidate_tag")
previous=$(docker image inspect --format '{{.Id}}' "$previous_tag")
```

Use the runtime limits in [CONTAINER.md](CONTAINER.md). For browser load, bind the engine's port to loopback only and block runtime egress, or put the runtime, local TLS proxy and test browser on an isolated container network. Establish reachability to the test proxy and verify that the runtime egress rules block provider traffic before admitting work. Use the hosted origin and explicitly trusted proxy peers. The proxy must overwrite inbound forwarding headers with its own values. Bootstrap the generated operator before startup, then issue the five analysts through User management. Record the configured limits and the actual CPU quota, memory limit and PID limit from the running container.

For the isolated-network option, set `name` and `rehearsal_network` to unique scratch names. Set `state_dir` and `ledger_dir` to the protected absolute paths described in the recovery section. Export the generated app key, hosted profile, origin and trusted proxy CIDRs in the operator shell. Join the local test proxy and browser to this network using their existing isolated test configuration.

```sh
docker network create --internal "$rehearsal_network"
serving() {
    docker run --init --read-only --cap-drop ALL --security-opt no-new-privileges \
        --pids-limit 64 --memory 1g --cpus 1 --stop-timeout 30 \
        --tmpfs /tmp:rw,noexec,nosuid,size=64m,mode=1777 \
        --mount "type=bind,src=$serve_state,dst=/data" \
        --mount "type=bind,src=$ledger_dir,dst=/ledger" \
        -e POISONTRACE_PROFILE -e POISONTRACE_PUBLIC_ORIGIN -e POISONTRACE_TRUSTED_PROXIES \
        -e POISONTRACE_RECOVERY_LEDGER=/ledger/recovery.db -e POISONTRACE_SECRETS_KEY \
        "$@"
}
serve_state=$state_dir
serving --rm -it --network none "$previous" init-admin
serving -d --name "$name" --network "$rehearsal_network" "$previous"
```

Use the previous image to generate pre-upgrade state for the cutover drill. Use a separate fresh candidate state root and ledger for workload measurements so the upgrade starts with a known previous schema.

## Workload and measurements

Use five independent authenticated browser contexts. Seed one saved Scripted offline result per analyst, one at a time. Run a two-minute browsing baseline and repeat the same actions while executing a Scripted offline matched group. In each context, open Configurations, Experiment and Results in sequence and refresh an owned Results page. Repeat every five seconds while the group is active. Keep all five contexts open and record achieved requests and elapsed overlap with the job. If the job ends before concurrent browsing is observed, extend the workload with additional sequential groups within the existing hosted limits. Use the same case and attempt count for repeat samples. Include at least one clean MCP single, one retained group rerun and one metadata single and campaign using offline substitutes. Report the substitute-based cases separately when they require a repository test process alongside the image.

| Measure | Collection |
| --- | --- |
| CPU, memory and PIDs | Sample `docker stats --no-stream --format '{{json .}}' "$name"` from the host throughout baseline and load. Record timestamps and the actual sampling intervals. Include peaks, limits, and the sample count. Record cgroup CPU throttling and memory OOM counter deltas where available. |
| Disk | At fresh start, before workload, after workload and after backup, record `docker exec "$name" du -sk /data`, `docker exec "$name" df -Pk /data`, and backup and ledger sizes from their independent stores. Include SQLite sidecars in data-root totals and record image size separately. |
| Execution | Time each HTTP admission response and the interval from HTTP 202 until terminal status using a monotonic clock. Poll `/api/investigation-jobs/{id}` at one-second intervals and report that timing resolution. Record terminal outcome and actual saved child count for each workload. |
| SQLite | On scratch only, measure an independent read transaction and a `BEGIN IMMEDIATE` followed by `ROLLBACK` against the application database every two seconds. Open the existing file with SQLite URI `mode=rw`, set a 200 ms busy timeout and record timings and busy failures separately. Run the probes in one persistent process and report its PID and overhead. Never query private rows for measurements. |
| Health | Once per second probe both `/health/live` and `/health/ready` with a two-second timeout. Report p50, p95, maximum, timeouts and non-200 counts separately. Record expected probe failures during intentionally stopped or failed phases. |

Save only command names and safe arguments, image IDs, elapsed times, counts and statuses. Record the host and engine configuration, wall clock, sample count, job overlap and any processes included in the measurements. Use the same conditions for a second load sample before drawing sizing conclusions.

In a dedicated terminal, record the engine resource samples until the browser load ends. Use a new file under the scratch evidence directory for each phase. Ctrl+C stops this collector without stopping the runtime.

```sh
while docker stats --no-stream --format "$(date -u +%FT%TZ) {{json .}}" "$name"; do
    sleep 1
done > "$resource_samples"
```

For cgroup v2, collect these counters before and after load. Interpret `usage_usec` as cumulative CPU time and `nr_throttled` as throttled CPU periods. The PID counter includes threads. When cgroup counters are unavailable, record the engine statistics and their limits as the available source.

```sh
docker exec "$name" sh -c 'cd /sys/fs/cgroup && cat cpu.max cpu.stat memory.max memory.events pids.max pids.events'
```

## Execution and access checks

While each execution kind is active, submit another kind as a different analyst and expect busy rejection. Cover MCP singles, matched groups, metadata singles and campaigns as the active kind at least once. Repeat an accepted intent as its owner and confirm the same durable ID. Confirm that a second analyst cannot read the ID, use a foreign credential, or execute a foreign group or campaign. Confirm same-owner reconnect after refresh and that a deliberate rerun appends a correctly linked child. Use the `test_durable_*`, `test_group_job_limits.py`, ownership and hosted-session tests as assertion references. An offline substitute run and a current-image run each need their own result.

Record rejection outcomes for missing idempotency keys, overlong request fields, oversized bodies, excess hosted group repeats, duplicate conditions, campaign size and oversized metadata snapshots. Check malformed YAML exclusion and the required acknowledgement when a saved campaign input becomes unusable. Use offline failure controls to check the 20-second transport timeout and 45-second attempt watchdog. Record whether a controlled failure saved an unscored result or left an interrupted job. Verify the existing MCP call, output and time limits against the packaged executor and leave the fixtures and scoring contract intact.

In the isolated Linux namespace, record the two MCP child PIDs and UID during execution by using synthetic evidence identifiers and process metadata without arguments or environments. Force a controlled failure and interrupt an active attempt. Confirm both children are gone after normal completion, failure and interruption. Restart and check the saved child links, terminal states, missing unstarted slots and absence of replay. For provider timeout and validation failure use generated marker values in synthetic credentials and request bodies. Scan only the new rehearsal's diagnostics for marker presence and record pass/fail and counts. Include application, worker, engine and proxy logging in that scan.

Verify analyst denial at User management and superadmin denial at investigation and credential endpoints. Confirm Secure, HttpOnly and SameSite cookies over local HTTPS, revocation, invalid Origin rejection and rejection of direct HTTP with forged forwarding headers. Send a controlled request through the configured trusted peer, then check rejection of missing or malformed forwarded values there. Confirm hosted YAML and ground-truth writes fail and the corresponding reads remain stable. Exercise expected 401, 403, 404 and busy responses without exposing submitted values.

## Restart, replacement and rollback

Before draining, save a comparison of the synthetic IDs and selected invariant fields through the owned HTTP routes. Include actual child IDs for matched groups and campaigns, retained reruns, pinned inputs, historical scores and provenance. Keep exact image IDs and schema-only fingerprints with the record. Fingerprint SQLite schema from `sqlite_schema` with stable ordering while stopped. Run `PRAGMA quick_check` on each stopped synthetic database. Compare results as well as schema after restart and release replacement.

1. Block incoming traffic at the local proxy. Let admitted work reach a terminal state, or record the intent to interrupt it. Stop the runtime with `docker stop --time 30 "$name"` and confirm it exited. Stop every other writer. Copy the stopped state to scratch for the release drill and archive the pre-upgrade state with the previous image and the [recovery procedure](DATA_RECOVERY.md). Retain the previous image, current ledger and separately recoverable keys. During a separate interruption drill, create a snapshot with backed-up queued or active jobs and record their IDs.
2. Remove the stopped container with `docker rm "$name"`. Keep its scratch state and ledger. Create the replacement using `serving -d --name "$name" --network "$rehearsal_network" "$candidate"` with the same `serve_state`. Start with admission closed. Verify readiness, inspect the schema and compare the owned history. Repeat a restart with `docker restart --time 30 "$name"` and verify persistence again.
3. For rollback, stop and remove the candidate container with the same stop and remove commands. Preserve candidate state for diagnosis. Use the previous image ID and the matching pre-upgrade archive to restore to a new root. Keep the independent ledger current through the drill. Use `python -m poisontrace.recovery restore /backup/pre-upgrade.ptbackup /restore/state`, then set `POISONTRACE_DATA_ROOT=/restore/state` and run `python -m poisontrace.recovery activate --reviewed`. Invoke these via the previous image's `python -m poisontrace.recovery` entrypoint with explicit mounts and recovery settings. Validate account changes since backup and check that synthetic credential revocations and content/history deletions still apply. Verify backed-up active and queued jobs are interrupted and stay interrupted across restart. Confirm saved results and link integrity through HTTP. Do not point the previous image at the upgraded schema unless compatibility has been independently demonstrated.
4. Set `serve_state="$restore_parent/state"` and start the previous image using `serving -d --name "$name" --network "$rehearsal_network" "$previous"`. Compare its schema and the retained history to pre-upgrade expectations. Record restored data age, reconcile any writes between the archive and rollback, and rehearse allowing traffic only after an operator verifies readiness, authentication, ownership, content policy, revocations, interrupted jobs and retained history. Record time from drain to eligibility to reopen. Keep the test listener isolated throughout.

For the recovery steps, set `state_dir`, `ledger_dir`, `archive_dir` and `restore_parent` to newly prepared absolute paths. Use separate protective permissions and make the intended paths writable by UID 10001. Set the app key, archive key and profile as environment variables in the operator's shell and use the same ledger mount for each phase. The original root maps to `/data`, and the restore target starts absent under the mounted `/restore` parent. Use a protected environment channel and disable shell tracing.

```sh
recovery() {
    image=$1
    state_root=$2
    shift 2
    docker run --rm --network none --read-only --cap-drop ALL \
        --security-opt no-new-privileges --pids-limit 64 --memory 1g --cpus 1 \
        --tmpfs /tmp:rw,noexec,nosuid,size=64m,mode=1777 \
        --mount "type=bind,src=$state_dir,dst=/data" \
        --mount "type=bind,src=$ledger_dir,dst=/ledger" \
        --mount "type=bind,src=$archive_dir,dst=/backup" \
        --mount "type=bind,src=$restore_parent,dst=/restore" \
        -e "POISONTRACE_DATA_ROOT=$state_root" -e POISONTRACE_PROFILE \
        -e POISONTRACE_PUBLIC_ORIGIN -e POISONTRACE_TRUSTED_PROXIES \
        -e POISONTRACE_RECOVERY_LEDGER=/ledger/recovery.db \
        -e POISONTRACE_SECRETS_KEY -e POISONTRACE_BACKUP_KEY \
        --entrypoint python "$image" -m poisontrace.recovery "$@"
}
recovery "$previous" /data backup /backup/pre-upgrade.ptbackup
```

After the candidate stops and the operator reviews the current ledger and account changes, run the restore and activation separately. Use the restored directory and the ledger in the replacement runtime mounts. Keep the archive key out of the serving container.

```sh
recovery "$previous" /data restore /backup/pre-upgrade.ptbackup /restore/state
recovery "$previous" /restore/state activate --reviewed
```

## Proposed operator alerts

Tune these initial thresholds using the measured load. Page the assigned operator for any critical alert and leave admission closed while required checks fail.

| Trigger | Operator check and action |
| --- | --- |
| CPU over 85% of quota for five minutes or sustained throttling | Check cgroup throttling and the active job duration. Pause new admission if health degrades. Resume when the job clears and health and latency recover. Review host CPU headroom before changing limits. |
| Memory above 80% or PIDs above 75% of limit for five minutes, or any OOM event | Check cgroup memory events, process counts and executor/MCP cleanup. Drain and stop the runtime if pressure persists or a child remains. Check interrupted job reconciliation before reopening. |
| Data or backup filesystem above 75%, or projected to fill in seven days | Check image, log, archive, data and SQLite sidecar growth independently. Verify the last usable archive. Expand storage or expire data only under an approved policy. Close admission if capacity threatens writes. |
| Three consecutive readiness failures or SQLite writer acquisition above 200 ms in three consecutive probes | Compare liveness and readiness. Check space, volume permissions, lock contention and extra writers. Keep admission closed until storage and readiness recover. |
| Unexpected restart, repeated executor failures or three unexpected HTTP 5xx in five minutes | Check the restart count, job terminal counts and readiness. Check for OOM, watchdog timeout or disk errors. Verify interrupted IDs and saved child links. Reopen only after a successful isolated smoke check. Never automatically replay interrupted work. |
| Backup failure or last recoverable archive older than the approved RPO | Verify independent archive availability, key custody and ledger freshness. Retain the last usable archive, fix the failed prerequisite and verify a new isolated restore. |

Log route templates, status classes, durations, aggregate resource readings and fixed error categories. Suppress raw URLs, query strings, headers, bodies, provider exceptions and record payloads in the proxy, runtime and collection pipeline. The current production command inherits Uvicorn access logging. Verify engine and proxy output directly before approving a pilot logging configuration. Scrubbing output after collection leaves the original logs on disk. Limit access to diagnostics and verify the synthetic marker scan before collecting pilot data.

## Pilot decisions pending

The initial topology is one persistent Linux host and one HTTPS origin. DigitalOcean Singapore SGP1 is a candidate. Published rates put a 1-vCPU, 2-GiB, 50-GiB Droplet plus independent Spaces Standard storage at USD 17/month. A 2-vCPU, 4-GiB, 80-GiB Droplet plus the same storage comes to USD 29/month. These are list-price estimates before tax, overages, domain and operator costs. A 1-GiB application limit leaves at most 1 GiB on the smaller host for the OS, engine, cache and proxy. Compare measured app peaks, host overhead, disk growth and archive volume before choosing either size. [Droplet pricing](https://www.digitalocean.com/pricing/droplets) · [Region availability](https://docs.digitalocean.com/platform/regional-availability/) · [Spaces pricing](https://docs.digitalocean.com/products/spaces/details/pricing/) · [Spaces availability](https://docs.digitalocean.com/products/spaces/details/availability/)

Obtain a region-specific written quote or reproducible checkout estimate including taxes, egress and storage. Decide where the independent ledger and archive copies reside and how keys are recovered separately. Assign a primary and backup operator with escalation, restore and account-recovery duties. Confirm who approves expiry, restore and reopening. The 30-day history window, seven days of daily backups, 24-hour RPO and one working day RTO remain proposals from #48. Record representative archive age and measured restore time before seeking approval.
