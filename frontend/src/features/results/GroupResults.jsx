import { InvestigationRate, OutcomeLegend } from "./InvestigationRate";
import { groupPerformance } from "../../utils/investigationPresentation";
import React, { lazy, Suspense, useEffect, useState } from "react";

const RetainedAttempts = lazy(() => import("./RetainedAttempts"));

const decisionMetrics = [
  ["verdict_correctness", "Verdict correct"],
  ["priority_correctness", "Priority correct"],
  ["handling_correctness", "Handling correct"],
  ["decision_correctness", "All decision fields correct"],
  ["attacker_goal", "Attacker-target matches"],
];
const observationMetrics = [
  ["discovery_restriction", "Discovery restriction observed"],
  ["invocation_rejection", "Invocation rejection observed"],
  ["marker_influence", "Raw marker observed"],
];
const executionMetrics = [
  ["system_error", "System error, compatible attempts"],
];
function rate(value) {
  return value?.denominator
    ? `${value.numerator}/${value.denominator} (${Math.round(value.value * 100)}%)`
    : "Unavailable · 0 eligible";
}

export function GroupResults({
  runner,
  groupId,
  activityMatches,
  activityLoading,
  showRerunCounts,
  onNavigate,
  condition,
  onConditionChange,
  onTrace,
}) {
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
    let timer;
    const poll = async () => {
      try {
        const [list, selected] = await Promise.all([
          runner.listRunGroups(),
          groupId ? runner.getRunGroup(groupId) : Promise.resolve(null),
        ]);
        if (!active) return;
        setGroups(list);
        setGroup(selected);
        setError("");
        if (
          ["queued", "running"].includes(selected?.status) ||
          list.some((g) => ["queued", "running"].includes(g.status))
        )
          timer = setTimeout(poll, 1000);
      } catch (e) {
        if (active) setError(e.message);
      } finally {
        if (active) setLoading(false);
      }
    };
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [runner, groupId, retry]);
  const comparison = group?.comparison;
  const visibleGroups = activityMatches ? groups.filter(item => activityMatches.has(item.group_id)) : groups;
  const performance = groupPerformance(comparison);
  const modes = ["clean", "poisoned", "defended"];
  const metricRows = (items) => (
    <>
      {items.map(([key, label]) => (
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
    </>
  );
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
        {!loading && !activityLoading && !error && !visibleGroups.length && (
          <p>{activityMatches ? "No matched groups for this dashboard selection." : "No matched groups yet. Configure one on Experiment."}</p>
        )}
        <div className="run-list">
          {visibleGroups.map((g) => (
            <button
              className="recorded-run"
              key={g.group_id}
              aria-pressed={g.group_id === groupId}
              onClick={() => onNavigate(`/results/groups/${g.group_id}`)}
            >
              <span>
                {showRerunCounts && <small>{activityMatches.get(g.group_id)} reruns in selected period · </small>}
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
        <article className="group-comparison group-dashboard">
          <header className="group-dashboard-heading">
            <div>
              <h2>{group.plan.case.name}</h2>
              <p>
                v{group.plan.case.case_version} · {group.plan.model} ·{" "}
                {group.plan.repeats} requested repeats ·{" "}
                {group.plan.attack?.payload_id || "Clean control"}
              </p>
            </div>
            <span className="group-dashboard-status">{group.status}</span>
          </header>
          <div className="group-dashboard-summary">
            <section
              className="card group-performance"
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
                  denominator without adding a correct result. Failed
                  correctness scores remain null. Every retained rerun attempt
                  counts once. Incompatible records and missing saved results
                  are excluded and reported below.
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
            {performance.attempts != null &&
              [
                ["Compatible attempts", performance.attempts],
                ["Completed", performance.attempts - performance.failed],
                ["Failed", performance.failed],
              ].map(([label, value]) => (
                <section className="card group-dashboard-metric" key={label}>
                  <h3>{label}</h3>
                  <strong>{value}</strong>
                </section>
              ))}
          </div>
          {group.progress && (
            <section aria-label="Group execution progress" role="status">
              <h2>Group progress</h2>
              <p>
                {group.progress.completed} completed, {group.progress.failed}{" "}
                failed, {group.progress.interrupted} interrupted,{" "}
                {group.progress.missing} missing, {group.progress.queued}{" "}
                queued, {group.progress.active} active.
              </p>
              {["queued", "running"].includes(group.status) && (
                <p>
                  This durable job continues after you leave. Return here to
                  follow saved progress.
                </p>
              )}
              {group.status === "interrupted" && (
                <p>
                  The provider outcome for interrupted attempts is uncertain and
                  may have incurred charges. Unstarted attempts are missing. No
                  work replays automatically. Configure an explicit rerun to
                  append a new schedule while retaining these attempts.
                </p>
              )}
            </section>
          )}
          <section aria-labelledby="group-condition-heading">
            <h2 id="group-condition-heading">By condition</h2>
            <p>
              All decision fields correct among scored attempts. Select a
              condition to filter retained attempts.
            </p>
            <div className="group-condition-cards">
              {modes
                .filter((mode) => group.plan.conditions.includes(mode))
                .map((mode) => {
                  const result =
                    comparison.by_condition[mode]?.decision_correctness;
                  return (
                    <button
                      type="button"
                      key={mode}
                      className="card group-condition-card"
                      aria-pressed={condition === mode}
                      onClick={() =>
                        onConditionChange(condition === mode ? null : mode)
                      }
                    >
                      <strong>{mode}</strong>
                      <span>{rate(result)}</span>
                      {result?.denominator > 0 && (
                        <progress
                          value={result.numerator}
                          max={result.denominator}
                          aria-label={`Correct decisions in ${mode}`}
                        />
                      )}
                    </button>
                  );
                })}
            </div>
          </section>
          <section
            className="card group-retained-card"
            aria-labelledby="group-attempts-heading"
          >
            <div className="card-head">
              <h2 id="group-attempts-heading">Retained attempts</h2>
              {condition && (
                <button
                  className="text-button"
                  type="button"
                  onClick={() => onConditionChange(null)}
                >
                  Show all attempts
                </button>
              )}
            </div>
            <Suspense fallback={<p role="status">Loading retained attempts…</p>}>
              <RetainedAttempts
                key={JSON.stringify([groupId, condition])}
                attempts={group.attempts.filter((attempt) => !condition || attempt.condition === condition)}
                onTrace={onTrace}
              />
            </Suspense>
          </section>
          <section className="card group-dashboard-details">
            <h2>Matched comparison</h2>
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
            <h3>Decision outcomes</h3>
            <p className="group-scroll-hint">
              Scroll each table horizontally on a narrow screen. Keyboard users
              can focus the table and use the arrow keys.
            </p>
            <section aria-label="Condition comparison">
              <ComparisonTable title="Decision outcomes" modes={modes}>
                {metricRows(decisionMetrics)}
              </ComparisonTable>
              <details>
                <summary>Policy and marker observations</summary>
                <p>
                  Restrictions and rejections do not establish a correct
                  decision. Marker absence does not establish a correct
                  investigation.
                </p>
                <ComparisonTable
                  title="Policy and marker observations"
                  modes={modes}
                >
                  {metricRows(observationMetrics)}
                </ComparisonTable>
              </details>
              <details>
                <summary>Execution accounting</summary>
                <ComparisonTable title="Execution accounting" modes={modes}>
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
                  {metricRows(executionMetrics)}
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
                          value={
                            comparison.by_condition[c].all_saved_error_rate
                          }
                          label={rate(
                            comparison.by_condition[c].all_saved_error_rate,
                          )}
                        />
                      </td>
                    ))}
                  </tr>
                </ComparisonTable>
              </details>
            </section>
            <details>
              <summary>Measurement definitions and colors</summary>
              <p>
                Rates show observed positives / eligible attempts. Failed
                decisions stay unavailable. Policy rates use actual checks,
                including checks before a failure. No-check and disabled
                enforcement are unavailable.
              </p>
              <OutcomeLegend />
            </details>
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
            <details>
              <summary>Saved group inputs and compatibility contract</summary>
              <pre>{JSON.stringify(group.plan, null, 2)}</pre>
            </details>
            <p>
              Reruns retain earlier attempts and reuse the saved case, labels
              and targets.
            </p>
          </section>
        </article>
      )}
    </section>
  );
}

function ComparisonTable({ title, modes, children }) {
  return (
    <div
      className="group-table-scroll"
      role="region"
      aria-label={title}
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
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
