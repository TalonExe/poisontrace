import { InvestigationRate, OutcomeLegend } from "./InvestigationRate";
import { groupPerformance } from "../../utils/investigationPresentation";
import React, { useEffect, useState } from "react";

const metrics = [
  ["verdict_correctness", "Verdict correct"],
  ["priority_correctness", "Priority correct"],
  ["handling_correctness", "Handling correct"],
  ["decision_correctness", "All decision fields correct"],
  ["attacker_goal", "Attacker goal achieved"],
  ["discovery_restriction", "Discovery restriction observed"],
  ["invocation_rejection", "Invocation rejection observed"],
  ["marker_influence", "Raw marker observed"],
  ["system_error", "System error, compatible attempts"],
];
function rate(value) {
  return value?.denominator
    ? `${value.numerator}/${value.denominator} (${Math.round(value.value * 100)}%)`
    : "Unavailable · 0 eligible";
}

export function GroupResults({ runner, groupId, onNavigate, onDashboard }) {
  const [groups, setGroups] = useState([]);
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setGroup(null);
    Promise.all([
      runner.listRunGroups(),
      groupId ? runner.getRunGroup(groupId) : Promise.resolve(null),
    ])
      .then(([list, selected]) => {
        if (active) {
          setGroups(list);
          setGroup(selected);
        }
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
  }, [runner, groupId, retry]);
  const comparison = group?.comparison;
  const performance = groupPerformance(comparison);
  const modes = ["clean", "poisoned", "defended"];
  return (
    <section className="group-results">
      <article className="card">
        <h2>Saved groups</h2>
        {loading && <p role="status">Loading saved groups…</p>}
        {error && (
          <p className="form-error" role="alert">
            {error}{" "}
            <button
              className="text-button"
              onClick={() => setRetry((n) => n + 1)}
            >
              Retry groups
            </button>
          </p>
        )}
        {!loading && !error && !groups.length && (
          <p>No matched groups yet. Configure one on Experiment.</p>
        )}
        <div className="run-list">
          {groups.map((g) => (
            <button
              className="recorded-run"
              key={g.group_id}
              aria-pressed={g.group_id === groupId}
              onClick={() => onNavigate(`/results/groups/${g.group_id}`)}
            >
              <span>
                <strong>
                  {g.plan.case.name} · v{g.plan.case.case_version}
                </strong>
                <small>
                  {g.plan.model} · {g.plan.conditions.join(" / ")} ·{" "}
                  {g.plan.repeats} repeats · {g.status}
                </small>
                <small>{g.group_id}</small>
              </span>
            </button>
          ))}
        </div>
      </article>
      {!groupId && !loading && (
        <article className="card">
          <h2>Select a group</h2>
          <p>
            Matched comparisons use only the selected group's saved inputs and
            linked attempts.
          </p>
        </article>
      )}
      {group && (
        <article className="card group-comparison">
          <section
            className="group-performance"
            aria-label="Overall experiment performance"
          >
            <h2>Overall experiment performance</h2>
            <strong
              className={`group-performance-score measurement-${performance.tone}`}
            >
              {performance.score == null
                ? "Unavailable"
                : `${performance.score}/100`}
            </strong>
            {performance.score != null && <p>{performance.label}</p>}
            {performance.attempts != null && (
              <p>
                {performance.correct} correct{" "}
                {performance.correct === 1 ? "result" : "results"} from{" "}
                {performance.attempts} attempts; {performance.failed} failed.{" "}
                {performance.unscored} completed but unscored.
              </p>
            )}
            <p>
              Successful-attempt percentage for this matched group, including
              execution reliability.
            </p>
            <details>
              <summary>How this indicator works</summary>
              <p>
                Correct completed decisions / compatible saved attempts × 100,
                rounded to the nearest whole number. Verdict, priority and
                handling must all match.
              </p>
              <p>
                Failed and completed but unscored attempts stay in the
                denominator without adding a correct result. Failed correctness
                scores remain null. Every retained rerun attempt counts once.
                Incompatible records and missing saved results are excluded and
                reported below.
              </p>
              <p>
                Empty or unsupported data, including completed records with no
                available correctness observations, shows unavailable. Partial
                missing or unscored observations remain visible and limit
                interpretation.
              </p>
              <p>
                This describes overall experiment performance. It is not
                accuracy among completed decisions or a validated security
                benchmark. Policy restrictions, attacker outcomes and marker
                presence do not contribute.
              </p>
              <p>
                Green means every compatible attempt was correct; red means at
                least one was not a confirmed correct completion; grey means
                unavailable. These are presentation conventions, not research
                findings.
              </p>
            </details>
          </section>
          <h2>Matched comparison</h2>
          <p>
            {group.plan.case.name} · v{group.plan.case.case_version} ·{" "}
            {group.plan.model} ·{" "}
            {group.plan.attack?.payload_id || "Clean control"}
          </p>
          <p>
            {group.plan.conditions.join(" → ")} · {group.plan.repeats} requested
            repeats · {group.status}
          </p>
          <p>
            Finished means the schedule ended; failed attempts are still
            failures.
          </p>
          <p>
            {comparison.attempted} compatible saved attempts.{" "}
            {comparison.excluded_attempts.length} incompatible.{" "}
            {comparison.missing_attempts.length} scheduled attempts without a
            saved result.
          </p>
          <p>
            {comparison.missing_conditions.length
              ? `Missing compatible conditions: ${comparison.missing_conditions.join(", ")}.`
              : "No missing conditions."}
          </p>
          {comparison.not_requested_conditions?.length > 0 && (
            <p>
              Not scheduled for this group:{" "}
              {comparison.not_requested_conditions.join(", ")}.
            </p>
          )}
          <p>
            Rates show observed positives / eligible attempts. Failed decisions
            stay unavailable. Policy rates use actual checks, including checks
            before a failure. No-check and disabled enforcement are unavailable.
          </p>
          <OutcomeLegend />
          <p className="group-scroll-hint">
            Scroll the table horizontally to review all conditions on a narrow
            screen. Keyboard users can focus the table and use the arrow keys.
          </p>
          <div
            className="group-table-scroll"
            role="region"
            aria-label="Condition comparison"
            tabIndex={0}
          >
            <table className="group-table">
              <thead>
                <tr>
                  <th scope="col">Measurement</th>
                  {modes.map((c) => (
                    <th scope="col" key={c}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Requested per execution", (row) => row.requested],
                  ["Scheduled, including reruns", (row) => row.scheduled],
                  ["Saved attempts", (row) => row.saved],
                  ["Compatible completed attempts", (row) => row.completed],
                  ["Failed saved attempts", (row) => row.saved_failed],
                  ["Missing saved results", (row) => row.missing],
                  ["Incompatible attempts", (row) => row.excluded],
                ].map(([label, value]) => (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    {modes.map((c) => (
                      <td key={c}>{value(comparison.by_condition[c])}</td>
                    ))}
                  </tr>
                ))}
                {metrics.map(([key, label]) => (
                  <tr key={key}>
                    <th scope="row">{label}</th>
                    {modes.map((c) => {
                      const row = comparison.by_condition[c];
                      return (
                        <td key={c}>
                          <InvestigationRate
                            measure={key}
                            value={row[key]}
                            label={rate(row[key])}
                          />
                          <small>{row.unavailable[key]} unavailable</small>
                        </td>
                      );
                    })}
                  </tr>
                ))}
                <tr>
                  <th scope="row">Mean duration, compatible attempts</th>
                  {modes.map((c) => {
                    const d = comparison.by_condition[c].duration;
                    return (
                      <td key={c}>
                        {d.count
                          ? `${Math.round(d.mean_ms)} ms`
                          : "Unavailable"}
                        <small>{d.count} attempts</small>
                      </td>
                    );
                  })}
                </tr>
                <tr>
                  <th scope="row">System error, all saved attempts</th>
                  {modes.map((c) => (
                    <td key={c}>
                      <InvestigationRate
                        measure="system_error"
                        value={comparison.by_condition[c].all_saved_error_rate}
                        label={rate(
                          comparison.by_condition[c].all_saved_error_rate,
                        )}
                      />
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
          {comparison.excluded_attempts.length > 0 && (
            <section aria-label="Incompatible attempts">
              <h3>Excluded from matched rates</h3>
              {comparison.excluded_attempts.map((a) => (
                <p key={a.attempt}>
                  Attempt {a.attempt}: {a.reasons.join("; ")}
                </p>
              ))}
            </section>
          )}
          <h3>Retained attempts</h3>
          <ol className="group-attempts">
            {group.attempts.map((a) => (
              <li key={a.attempt}>
                <span
                  className={
                    a.status === "failed" ? "measurement-negative" : undefined
                  }
                >
                  Repeat {a.repeat} · {a.condition} ·{" "}
                  {a.status || "No saved result"}
                  {a.execution_time_ms != null
                    ? ` · ${Math.round(a.execution_time_ms)} ms`
                    : ""}
                  {a.error_category ? ` · ${a.error_category}` : ""}
                </span>
                {a.run_id && (
                  <a
                    href={`/results/runs/${a.run_id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      onNavigate(`/results/runs/${a.run_id}`);
                    }}
                  >
                    Inspect attempt {a.attempt} · EXP-
                    {String(a.run_id).padStart(3, "0")}
                  </a>
                )}
              </li>
            ))}
          </ol>
          <details>
            <summary>Saved group inputs and compatibility contract</summary>
            <pre>{JSON.stringify(group.plan, null, 2)}</pre>
          </details>
          <p>
            Reruns retain earlier attempts and reuse the saved case, labels and
            targets. Configure execution on Experiment.
          </p>
          <button className="text-button" onClick={onDashboard}>
            Configure a group or rerun
          </button>
        </article>
      )}
    </section>
  );
}
