import React, { lazy, Suspense, useEffect, useState } from "react";
import { Sidebar } from "../../components/layout/Sidebar";
import { activityLink, activityPeriod, activityRange, localDate, providerLabel } from "./activityPeriods";
import "./analystDashboard.css";

const SavedAttemptsPlot = lazy(() => import("./SavedAttemptsPlot"));

function ActivityChart({ title, description, buckets, series, onNavigate }) {
  const maximum = Math.max(1, ...buckets.map(bucket => series.reduce((sum, item) => sum + bucket[item.metric], 0)));
  return (
    <article className="card activity-chart">
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="activity-legend">
        {series.map(item => <span key={item.metric}><i className={item.color} />{item.label}</span>)}
      </div>
      <div className="activity-plot">
        {buckets.map(bucket => (
          <div className="activity-column" key={+bucket.start}>
            <div className="activity-stack">
              {series.map(item => {
                const count = bucket[item.metric];
                const label = `${activityRange(bucket.start, bucket.end)} · ${count} ${item.label.toLowerCase()}`;
                return count > 0 && (
                  <button key={item.metric} className={item.color} style={{ height: `${count / maximum * 100}%` }}
                    title={label} aria-label={label}
                    onClick={() => onNavigate(activityLink(item.view, bucket.start, bucket.end, item.filter, item.value))}>
                    {count}
                  </button>
                );
              })}
            </div>
            <span>{bucket.label}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

const attemptSeries = [
  { metric: "failed", label: "Failed", fill: "var(--ec-danger)" },
  { metric: "completed", label: "Completed", fill: "var(--ec-success)" },
];
const groupSeries = [
  { metric: "groups", label: "Groups created", color: "activity-completed", view: "groups", filter: "groups" },
  { metric: "reruns", label: "Reruns submitted", color: "activity-rerun", view: "groups", filter: "reruns" },
];

function SavedAttemptsChart({ buckets, completed, failed, onNavigate }) {
  const chartBuckets = buckets.map(bucket => ({
    ...bucket,
    results: Object.fromEntries(attemptSeries.filter(({ metric }) => bucket[metric] > 0).map(({ metric }) => [
      metric,
      {
        href: activityLink("runs", bucket.start, bucket.end, "attempts", metric),
        label: `${activityRange(bucket.start, bucket.end)} · ${bucket[metric]} ${metric}`,
      },
    ])),
  }));
  const entries = chartBuckets.flatMap(bucket => Object.values(bucket.results));

  return (
    <article className="card activity-chart" aria-labelledby="saved-attempts-title" aria-describedby="saved-attempts-summary">
      <h2 id="saved-attempts-title">Saved attempts over time</h2>
      <p id="saved-attempts-summary">Standalone and matched-group investigations. {completed} completed, {failed} failed.</p>
      {entries.length === 0 ? <p>No saved attempts in this period.</p> : <>
        <div className="activity-legend" aria-hidden="true">
          {attemptSeries.map(({ metric, label, fill }) => <span key={metric}><i style={{ background: fill }} />{label}</span>)}
        </div>
        <div className="activity-attempts-plot" aria-hidden="true">
          <Suspense fallback={null}>
            <SavedAttemptsPlot buckets={chartBuckets} series={attemptSeries} onNavigate={onNavigate} />
          </Suspense>
        </div>
        <ul className="activity-results" aria-label="Saved attempts by date and status">
          {entries.map(({ href, label }) => (
            <li key={href}>
              <a href={href} onClick={event => {
                if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                onNavigate(href);
              }}>{label}</a>
            </li>
          ))}
        </ul>
      </>}
    </article>
  );
}

export function AnalystDashboard({ runner, onNavigate, ...navigation }) {
  const [mode, setMode] = useState("week");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [response, setResponse] = useState(null);
  const { start, end } = activityPeriod(new Date(), mode, offset);
  const from = +start / 1000;
  const until = +end / 1000;
  const key = `${from}:${until}:${retry}`;
  useEffect(() => {
    let active = true;
    runner.getActivity(from, until).then(
      data => { if (active) setResponse({ key, data }); },
      error => { if (active) setResponse({ key, error: error.message }); },
    );
    return () => { active = false; };
  }, [runner, key, from, until]);
  const current = response?.key === key ? response : null;
  const data = current?.data;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const buckets = [];
  const providers = new Map();
  if (data) {
    const format = new Intl.DateTimeFormat(undefined, mode === "week" ? { weekday: "short" } : { month: "short", day: "numeric" });
    for (let date = start; date < end; date = localDate(date, mode === "week" ? 1 : 7)) {
      buckets.push({
        start: date, end: new Date(Math.min(+end, +localDate(date, mode === "week" ? 1 : 7))),
        label: format.format(date), completed: 0, failed: 0, groups: 0, reruns: 0,
      });
    }
    for (const attempt of data.attempts) {
      const bucket = buckets.find(item => attempt.at * 1000 < +item.end);
      bucket[attempt.status]++;
      providers.set(attempt.provider, (providers.get(attempt.provider) ?? 0) + 1);
    }
    for (const metric of ["groups", "reruns"]) {
      for (const record of data[metric]) {
        buckets.find(item => record.at * 1000 < +item.end)[metric]++;
      }
    }
  }
  const failed = data?.attempts.filter(attempt => attempt.status === "failed").length ?? 0;
  return (
    <main className="app-shell analyst-dashboard">
      <Sidebar active="activity" {...navigation} />
      <section className="welcome activity-heading">
        <div><h1>Analyst dashboard</h1><p>Your investigation activity · {timezone}</p></div>
        <div className="activity-controls" aria-label="Reporting period">
          {["week", "month"].map(option => (
            <button key={option} type="button" aria-pressed={mode === option} onClick={() => { setMode(option); setOffset(0); }}>
              {option === "week" ? "Week" : "Month"}
            </button>
          ))}
          <div className="activity-period-nav">
            <button type="button" aria-label="Previous period" onClick={() => setOffset(value => value - 1)}>‹</button>
            <span aria-live="polite">{activityRange(start, end)}{offset === 0 && <small>In progress</small>}</span>
            <button type="button" aria-label="Next period" disabled={offset === 0} onClick={() => setOffset(value => value + 1)}>›</button>
          </div>
        </div>
      </section>
      {!current && <p role="status">Loading dashboard activity…</p>}
      {current?.error && <p role="alert">{current.error} <button className="text-button" onClick={() => setRetry(value => value + 1)}>Retry dashboard</button></p>}
      {data && <>
        <section className="activity-totals" aria-label="Period totals">
          {[
            ["Saved attempts", data.attempts.length, `${data.attempts.length - failed} completed · ${failed} failed`],
            ["Groups created", data.groups.length, "New matched plans"],
            ["Group reruns", data.reruns.length, "Submitted against saved plans"],
            ["Interrupted jobs", data.interrupted, "Provider outcome may be unknown"],
          ].map(([label, count, detail]) => (
            <article className="card" key={label}><h2>{label}</h2><strong>{count}</strong><p>{detail}</p></article>
          ))}
        </section>
        <section className="activity-charts" aria-label="Period charts">
          <SavedAttemptsChart buckets={buckets} completed={data.attempts.length - failed} failed={failed} onNavigate={onNavigate} />
          <article className="card activity-chart">
            <h2>Attempts by provider</h2><p>Saved attempts, including failures</p>
            {providers.size === 0 && <p>No saved attempts in this period.</p>}
            {[...providers].sort(([left], [right]) => left.localeCompare(right)).map(([provider, count]) => (
              <button className="activity-provider" type="button" key={provider}
                onClick={() => onNavigate(activityLink("runs", start, end, "provider", provider))}>
                <span>{providerLabel(provider)}</span>
                <span aria-hidden="true"><i style={{ width: `${count / Math.max(...providers.values()) * 100}%` }} /></span>
                <strong>{count}</strong>
              </button>
            ))}
            <p className="activity-note">Token usage is unavailable in saved records.</p>
          </article>
          <div className="activity-wide">
            <ActivityChart title="Matched-group activity" description="New plans and explicit reruns submitted in the period"
              buckets={buckets} series={groupSeries} onNavigate={onNavigate} />
          </div>
        </section>
      </>}
    </main>
  );
}
