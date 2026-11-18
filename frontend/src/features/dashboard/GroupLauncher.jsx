import { ExecutionSelection } from "./ExecutionSelection";
import {
  executionModels as models,
  resolveExecution,
} from "../../utils/executionSelection";
import React, { useEffect, useState } from "react";

const conditions = ["clean", "poisoned", "defended"];

export function GroupLauncher({
  runner,
  selection,
  onSelectionChange,
  executionOptions,
  onResults,
  onRunningChange,
}) {
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
  async function launch(event) {
    event.preventDefault();
    if (!valid || !validCredential) return;
    setRunning(true);
    onRunningChange(true);
    setError("");
    try {
      const credential =
        actualProvider === "scripted"
          ? {}
          : { credential_id: execution.credentialId };
      const group = saved
        ? await runner.executeRunGroup(groupId, credential)
        : await runner.createRunGroup({
            case_id: caseId,
            case_version: selected.case_version,
            provider,
            ...(provider === "scripted" ? {} : { model: execution.model }),
            ...credential,
            conditions: schedule,
            repeats: Number(repeats),
            ...(schedule.some((c) => c !== "clean")
              ? { attack_family: family }
              : {}),
          });
      onResults(`/results/groups/${group.group_id}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
      onRunningChange(false);
    }
  }
  return (
    <form className="group-launcher" onSubmit={launch}>
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
        <fieldset disabled={running || loading} className="group-fields">
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
            disabled={running || loading}
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
                  {cases.map((c) => (
                    <option key={c.case_id} value={c.case_id}>
                      {c.name} · v{c.case_version} · {c.dataset_category}
                    </option>
                  ))}
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
        <button
          className="run-button"
          disabled={running || loading || !valid || !validCredential}
        >
          {running
            ? "Group running…"
            : saved
              ? "Rerun matched group"
              : "Run matched group"}
        </button>
        {running && (
          <p role="status">
            Running {count} attempts. Results opens when this request finishes.
            Do not submit another group while waiting.
          </p>
        )}
      </aside>
    </form>
  );
}
