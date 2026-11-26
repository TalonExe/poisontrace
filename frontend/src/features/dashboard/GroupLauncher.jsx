import { ExecutionSelection } from "./ExecutionSelection";
import { CaseOptions } from "./CaseOptions";
import { observeInvestigationJobs } from "./investigationJobObserver";
import {
  executionModels as models,
  resolveExecution,
} from "../../utils/executionSelection";
import React, { useEffect, useMemo, useRef, useState } from "react";

import { workspaceStorage } from "../../utils/workspaceStorage";
import { useContentReadOnly } from "../../components/ContentPolicy";
import { PendingButton } from "../../components/common/PendingButton";

const conditions = ["clean", "poisoned", "defended"];

export function GroupLauncher({
  runner,
  selection,
  onSelectionChange,
  executionOptions,
  onResults,
  onRunningChange,
  onRunStart,
}) {
  const storage = useMemo(() => workspaceStorage(window.localStorage), []);
  const mounted = useRef(true);
  const inFlight = useRef(false);
  const readOnly = useContentReadOnly();
  const [pending, setPending] = useState(() => {
    try { return JSON.parse(storage.getItem('group-intent') || 'null'); }
    catch { return null; }
  });
  const [submission, setSubmission] = useState(null);
  const [job, setJob] = useState(null);
  const [progress, setProgress] = useState(null);
  const retain = (value) => {
    storage.setItem('group-intent', JSON.stringify(value));
    setPending(value);
  };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => observeInvestigationJobs({
    runner,
    kind: "group",
    onUpdate: ({ job: current, busy, progress: currentProgress }) => {
      setJob(current);
      setProgress(currentProgress);
      setRunning(busy);
      onRunningChange(busy);
    },
    onError: (error) => setError(error.message),
  }), [runner, onRunningChange]);
  const [cases, setCases] = useState([]);
  const [groups, setGroups] = useState([]);
  const [caseId, setCaseId] = useState("");
  const [family, setFamily] = useState("cross-server-shadowing");
  const [schedule, setSchedule] = useState(conditions);
  const [repeats, setRepeats] = useState("1");
  const [groupId, setGroupId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([runner.listInvestigationCases(), runner.listRunGroups()])
      .then(([items, saved]) => {
        if (!active) return;
        setCases(items);
        setCaseId(items[0]?.case_id || "");
        setGroups(saved);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner, retry]);
  const saved = groups.find((g) => g.group_id === groupId);
  const selected = cases.find((c) => c.case_id === caseId);
  const allocated = Boolean(selected?.attacks?.length);
  const execution = resolveExecution(
    selection,
    executionOptions.configurations,
    executionOptions.credentials,
    saved?.plan,
  );
  const provider = execution.provider;
  const actualProvider = provider;
  const validCredential = execution.valid;
  const count = saved
    ? saved.plan.repeats * saved.plan.conditions.length
    : Number(repeats) * schedule.length;
  const valid =
    saved ||
    (selected &&
      schedule.length &&
      Number.isInteger(Number(repeats)) &&
      Number(repeats) > 0 &&
      (!schedule.some((c) => c !== "clean") || allocated));
  async function submit(value, source) {
    if (inFlight.current) return;
    inFlight.current = true;
    const reportRun = onRunStart("group");
    retain(value);
    setSubmission(source);
    setRunning(true);
    onRunningChange(true);
    setError("");
    try {
      const accepted = value.groupId
        ? await runner.executeRunGroup(value.groupId, value.payload, value.intent)
        : await runner.createRunGroup(value.payload, value.intent);
      reportRun(accepted);
      if (!mounted.current) return;
      retain(null);
      setJob(accepted);
      onResults(`/results/groups/${accepted.group_id}`);
    } catch (e) {
      reportRun(null, e.message);
      if (!mounted.current) return;
      setError(e.message);
      if ([400, 404, 409, 422].includes(e.status)) retain(null);
    } finally {
      inFlight.current = false;
      if (mounted.current) {
        setSubmission(null);
        setRunning(false);
        onRunningChange(false);
      }
    }
  }
  async function launch(event) {
    event.preventDefault();
    if (running || loading || pending || !valid || !validCredential) return;
    const credential = actualProvider === "scripted" ? {} : { credential_id: execution.credentialId };
    const payload = saved ? credential : {
      case_id: caseId,
      case_version: selected.case_version,
      provider,
      ...(provider === "scripted" ? {} : { model: execution.model }),
      ...credential,
      conditions: schedule,
      repeats: Number(repeats),
      ...(schedule.some(c => c !== "clean") ? { attack_family: family } : {}),
    };
    await submit({intent: crypto.randomUUID(), groupId: saved ? groupId : null, payload}, "launch");
  }
  return (
    <form className="group-launcher" onSubmit={launch}>
      {((pending && submission !== "launch") || job) && <article className="card group-job-status" aria-label="Matched group job" role="status">
        {job && <>
          <p><strong>Matched group {job.status}.</strong> <span className="group-job-id">Job {job.job_id}</span></p>
          {progress && <p><strong>{progress.completed} completed</strong>, {progress.failed} failed, {progress.interrupted} interrupted, {progress.missing} missing, {progress.queued} queued, {progress.active} active.</p>}
          <button className="small-button" type="button" onClick={() => onResults(`/results/groups/${job.group_id}`)}>Open group progress and Results</button>
          {job.status === 'interrupted' && <p>The provider outcome is uncertain. No attempt will replay automatically. An explicit rerun adds new attempts and may incur new provider charges.</p>}
        </>}
        {pending && submission !== "launch" && <>
          <p>{submission === "retry" ? "Retrying the saved submission…" : "The submission response is uncertain. Retry the saved submission intent to recover its job before starting different work."}</p>
          <PendingButton className="small-button" type="button" pending={submission === "retry"} onPress={() => submit(pending, "retry")}>Retry group submission</PendingButton>
        </>}
      </article>}
      <article className="card">
        <h2>Matched group setup</h2>
        <p>
          Keep one case and model fixed across the selected conditions. Each
          repeat uses fresh MCP processes.
        </p>
        {loading && <p role="status">Loading cases and saved groups…</p>}
        {error && (
          <div className="form-error" role="alert">
            {error}{" "}
            <button
              type="button"
              className="text-button"
              onClick={() => setRetry((n) => n + 1)}
            >
              Reload group setup
            </button>
          </div>
        )}
        {readOnly && <p>Hosted groups allow one repeat and up to three unique conditions. Larger saved local schedules cannot run here.</p>}
        <fieldset disabled={running || loading || Boolean(pending)} className="group-fields">
          <legend>Group inputs</legend>
          <label className="field">
            Group source
            <select
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
            >
              <option value="">New matched group</option>
              {groups.map((g) => (
                <option key={g.group_id} value={g.group_id}>
                  Rerun {g.plan.case.name} · v{g.plan.case.case_version} ·{" "}
                  {g.plan.model} · {g.group_id}
                </option>
              ))}
            </select>
          </label>
          <ExecutionSelection
            selection={selection}
            onChange={onSelectionChange}
            options={executionOptions}
            required={saved?.plan}
            disabled={running || loading || Boolean(pending)}
          />
          {!saved && (
            <>
              <label className="field">
                Group case
                <select
                  value={caseId}
                  onChange={(e) => {
                    const next = cases.find(
                      (c) => c.case_id === e.target.value,
                    );
                    setCaseId(e.target.value);
                    setSchedule(next?.attacks?.length ? conditions : ["clean"]);
                  }}
                >
                  <CaseOptions cases={cases} />
                </select>
              </label>
              {!loading && !cases.length && <p>No research cases available.</p>}
              <fieldset className="condition-schedule">
                <legend>Condition schedule</legend>
                <p>Execution order follows the list below, once per repeat.</p>
                {conditions.map((c) => (
                  <label key={c}>
                    <input
                      type="checkbox"
                      checked={schedule.includes(c)}
                      disabled={c !== "clean" && !allocated}
                      onChange={(e) =>
                        setSchedule(
                          conditions.filter((value) =>
                            value === c
                              ? e.target.checked
                              : schedule.includes(value),
                          ),
                        )
                      }
                    />
                    {c}
                  </label>
                ))}
              </fieldset>
              {!allocated && selected && (
                <p>
                  This case is a clean control. No attacked or defended trials
                  are allocated.
                </p>
              )}
              {schedule.some((c) => c !== "clean") && (
                <label className="field">
                  Group attack family
                  <select
                    value={family}
                    onChange={(e) => setFamily(e.target.value)}
                  >
                    {(selected?.attacks || []).map((a) => (
                      <option key={a.family} value={a.family}>
                        {a.family} · {a.payload_id}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="field">
                Group repeats
                <input
                  type="number"
                  min="1"
                  max={readOnly ? "1" : undefined}
                  step="1"
                  required
                  value={repeats}
                  onChange={(e) => setRepeats(e.target.value)}
                />
              </label>
            </>
          )}
        </fieldset>
      </article>
      <aside
        className="card group-specification"
        aria-label="Group specification"
      >
        <h2>{saved ? "Rerun saved group" : "This group"}</h2>
        <dl>
          <dt>Case</dt>
          <dd>
            {saved?.plan.case.name || selected?.name || "Select a case"} · v
            {saved?.plan.case.case_version ||
              selected?.case_version ||
              "unavailable"}
          </dd>
          <dt>Model</dt>
          <dd>{saved?.plan.model || models[provider]}</dd>
          <dt>Schedule</dt>
          <dd>
            {(saved?.plan.conditions || schedule).join(" → ") ||
              "Select at least one condition"}
          </dd>
          <dt>Repeats</dt>
          <dd>{saved?.plan.repeats || repeats || "Required"}</dd>
          <dt>Attempts to run</dt>
          <dd>
            {Number.isInteger(count) && count > 0 ? count : "Unavailable"}
          </dd>
          <dt>Payload</dt>
          <dd>
            {saved
              ? saved.plan.attack?.payload_id || "None, clean control"
              : schedule.some((c) => c !== "clean")
                ? selected?.attacks?.find((a) => a.family === family)
                    ?.payload_id || "Unavailable"
                : "None, clean-only"}
          </dd>
          <dt>Credential</dt>
          <dd>
            {actualProvider === "scripted"
              ? "No key used"
              : validCredential
                ? "Selected execution's private reference"
                : "Matching provider credential required"}
          </dd>
        </dl>
        {saved && (
          <p>
            The saved evidence, labels and targets will be reused. Earlier
            attempts remain available. Changed runtime settings require a new
            group.
          </p>
        )}
        {!validCredential && (
          <p role="status">
            Select a matching configuration above or reload execution options
            before running.
          </p>
        )}
        <PendingButton
          className="run-button"
          type="submit"
          pending={submission === "launch"}
          disabled={running || loading || Boolean(pending) || !valid || !validCredential}
        >
          {running && !submission
            ? "Group running…"
            : saved
              ? "Rerun matched group"
              : "Run matched group"}
        </PendingButton>
        {submission === "launch" && (
          <p role="status">
            Submitting a durable schedule of {count} attempts. Progress is saved and can be reopened after leaving this page.
          </p>
        )}
        {running && !submission && <p>Follow the accepted job in progress or Results.</p>}
      </aside>
    </form>
  );
}
