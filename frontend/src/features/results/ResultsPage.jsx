import { GroupResults } from "./GroupResults";
import { InvestigationMeasurements } from "./InvestigationMeasurements";
import React, { useEffect, useState } from "react";
import { Sidebar } from "../../components/layout/Sidebar";
import { CardHead } from "../../components/common/Ui";
import { outcomePresentation } from "../../utils/outcomePresentation";
import { MeasurementSummary } from "../dashboard/MeasurementSummary";
import { CampaignHistory } from "./CampaignHistory";
import { RunInspection } from "./RunInspection";
import { activityRange, providerLabel, readActivityFilter } from "../dashboard/activityPeriods";

const runPageSize = 10;

export function ResultsPage({
  runner,
  path,
  search = "",
  onNavigate,
  onSessions,
  onDashboard,
  onScenarios,
  user,
  auth,
  onSignOut,
}) {
  const view = path.startsWith("/results/groups")
    ? "groups"
    : path.startsWith("/results/campaigns")
      ? "campaigns"
      : path.startsWith("/results/runs")
        ? "runs"
        : "overview";
  const identifier = path.split("/")[3];
  const runId = view === "runs" && identifier ? Number(identifier) : null;
  const campaignId =
    view === "campaigns" && identifier ? decodeURIComponent(identifier) : null;
  const [runs, setRuns] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [selectedRun, setSelectedRun] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [historyPage, setHistoryPage] = useState(null);
  const [traceOrigin, setTraceOrigin] = useState(null);
  const [attemptFilter, setAttemptFilter] = useState(null);
  const [activityResponse, setActivityResponse] = useState(null);
  const filter = readActivityFilter(search, view);
  const filterStart = filter?.start;
  const filterEnd = filter?.end;
  const activity = activityResponse?.search === search && activityResponse?.attempt === attempt
    ? activityResponse.data : null;
  const activityError = activityResponse?.search === search && activityResponse?.attempt === attempt
    ? activityResponse.error : "";
  useEffect(() => {
    if (filterStart == null) return;
    let active = true;
    runner.getActivity(filterStart, filterEnd).then(
      data => { if (active) setActivityResponse({ search, attempt, data }); },
      error => { if (active) setActivityResponse({ search, attempt, error: error.message }); },
    );
    return () => { active = false; };
  }, [runner, filterStart, filterEnd, search, attempt]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    if (view === "groups") {
      setLoading(false);
      return () => {
        active = false;
      };
    }
    const request =
      view === "overview"
        ? runner.getRunSummary()
        : view === "runs"
          ? runner.listRuns()
          : runner.listCampaigns();
    request
      .then((value) => {
        if (!active) return;
        if (view === "overview") setMetrics(value);
        else if (view === "runs") setRuns(value);
        else setCampaigns(value);
      })
      .catch((error) => {
        if (active) setError(error.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner, view, attempt]);
  useEffect(() => {
    let active = true;
    setSelectedRun(null);
    setDetailError("");
    setDetailLoading(Boolean(runId));
    if (runId)
      runner
        .getRun(runId)
        .then((value) => {
          if (active) setSelectedRun(value);
        })
        .catch((error) => {
          if (active) setDetailError(error.message);
        })
        .finally(() => {
          if (active) setDetailLoading(false);
        });
    return () => {
      active = false;
    };
  }, [runner, runId, detailAttempt]);
  const openRun = (id) => onNavigate(`/results/runs/${id}`);
  const matchingRuns = filter && view === "runs"
    ? new Set(activity?.attempts.filter(record => (
        filter.metric === "provider" ? record.provider === filter.value : !filter.value || record.status === filter.value
      )).map(record => record.run_id))
    : null;
  const matchingGroups = new Map();
  if (filter && view === "groups" && activity) {
    for (const record of activity[filter.metric]) {
      matchingGroups.set(record.group_id, (matchingGroups.get(record.group_id) ?? 0) + 1);
    }
  }
  const filterLabel = filter && {
    attempts: filter.value === "failed" ? "Failed attempts" : filter.value === "completed" ? "Completed attempts" : "Saved attempts",
    provider: `Attempts by ${providerLabel(filter.value)}`,
    groups: "Groups created",
    reruns: "Group reruns submitted",
  }[filter.metric];
  const filteredRuns = runs.filter((run) =>
    (!matchingRuns || matchingRuns.has(run.run_id)) &&
    `${run.id} ${run.mode} ${run.result}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const lastPage = Math.max(0, Math.ceil(filteredRuns.length / runPageSize) - 1);
  const selectedIndex = filteredRuns.findIndex(run => run.run_id === runId);
  const selectedPage = Math.max(0, Math.floor(selectedIndex / runPageSize));
  const page = Math.min(lastPage, historyPage?.search === search ? historyPage.index : selectedPage);
  const pageStart = page * runPageSize;
  const pageEnd = Math.min(pageStart + runPageSize, filteredRuns.length);
  const changePage = index => setHistoryPage({ search, index });
  return (
    <main className="app-shell results-page">
      <Sidebar
        active="results"
        user={user}
        auth={auth}
        onSignedOut={onSignOut}
        onSessions={onSessions}
        onDashboard={onDashboard}
        onResults={() => onNavigate("/results/groups")}
        onScenarios={onScenarios}
      />
      <section className="welcome">
        <div>
          <h1>Results</h1>
          <p>
            Review saved experiments, campaign outcomes and recorded traces.
          </p>
        </div>
      </section>
      <nav className="execution-mode" aria-label="Results views">
        {[
          ["groups", "Groups", "/results/groups"],
          ["overview", "Overview", "/results"],
          ["runs", "Runs", "/results/runs"],
          ["campaigns", "Campaigns", "/results/campaigns"],
        ].map(([id, label, target]) => (
          <button
            key={id}
            aria-current={view === id ? "page" : undefined}
            className={view === id ? "active" : ""}
            onClick={() => onNavigate(target)}
          >
            {label}
          </button>
        ))}
      </nav>
      {filter && <div className="card">
        <strong>{filterLabel}</strong>
        <p>{activityRange(new Date(filter.start * 1000), new Date(filter.end * 1000))}</p>
        {activity && <p>{view === "runs" ? matchingRuns.size : activity[filter.metric].length} matching records</p>}
        {!activity && !activityError && <p role="status">Loading dashboard selection…</p>}
        {activityError && <p role="alert">{activityError} <button className="text-button" onClick={() => setAttempt(value => value + 1)}>Retry selection</button></p>}
        <button className="text-button" onClick={() => onNavigate(`/results/${view}`)}>Clear dashboard filter</button>
      </div>}
      {error && (
        <div className="form-error" role="alert">
          {error}
          <button
            className="text-button"
            onClick={() => setAttempt((value) => value + 1)}
          >
            Retry loading results
          </button>
        </div>
      )}
      {view === "overview" && (
        <section aria-label="Run measurements">
          {loading ? (
            <p role="status">Loading recorded rates…</p>
          ) : (
            !error && (
              <>
                <p>
                  Historical analysis: these pooled rates describe saved attempts across cases and models.
                  They are not matched same-case comparisons.
                </p>
                <InvestigationMeasurements metrics={metrics?.investigations} />
                <p>
                  Recommendation-equality rates below retain the metadata
                  experiment scoring rules. Saved-attempt counts include all
                  workflows.
                </p>
                <MeasurementSummary metrics={metrics} />
              </>
            )
          )}
        </section>
      )}
      {view === "runs" && (
        <section className="results-grid">
          <article className="card activity" id="run-history" tabIndex={-1}>
            <div className="card-head">
              <h2>Recorded experiments</h2>
              <div className="search-field">
                <input
                  aria-label="Filter runs"
                  placeholder="Filter"
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    changePage(0);
                  }}
                />
              </div>
            </div>
            {loading && <p role="status">Loading run history…</p>}
            {!loading && !error && (!filter || activity) && !filteredRuns.length && (
              <p className="empty-state">
                {runs.length
                  ? "No runs match this filter."
                  : "No runs recorded yet. Launch an experiment from Experiment."}
              </p>
            )}
            <div
              className="run-list"
              role="region"
              aria-label="Run history entries"
              tabIndex={0}
            >
              {!loading &&
                !error &&
                filteredRuns.slice(pageStart, pageEnd).map((run) => (
                  <button
                    type="button"
                    className="recorded-run"
                    key={run.run_id}
                    aria-pressed={runId === run.run_id}
                    onClick={() => onNavigate(`/results/runs/${run.run_id}${filter ? search : ""}`)}
                  >
                    <span className={`run-dot ${run.tone}`} />
                    <span>
                      <strong>
                        {run.id} · {run.mode}
                      </strong>
                      <small>
                        {["investigation-scoring-v1", "investigation-unscored-v1"].includes(run.scoring_version)
                          ? `${outcomePresentation(run).task} · ${outcomePresentation(run).attacker} · ${run.status || "Status unavailable"}`
                          : `${outcomePresentation(run).injection} · ${outcomePresentation(run).task}`}
                      </small>
                    </span>
                  </button>
                ))}
            </div>
            {!loading && !error && lastPage > 0 && (
              <nav className="run-history-pages" aria-label="Run history pages">
                <button className="text-button" type="button" aria-disabled={page === 0}
                  onClick={() => page > 0 && changePage(page - 1)}>Previous page</button>
                <span role="status">{pageStart + 1}–{pageEnd} of {filteredRuns.length} runs</span>
                <button className="text-button" type="button" aria-disabled={page === lastPage}
                  onClick={() => page < lastPage && changePage(page + 1)}>Next page</button>
              </nav>
            )}
          </article>
          <div className="result-inspection" aria-busy={detailLoading}>
            {detailLoading && <p role="status">Loading selected run…</p>}
            {detailError && (
              <div className="form-error" role="alert">
                {detailError}
                <button
                  className="text-button"
                  onClick={() => setDetailAttempt((value) => value + 1)}
                >
                  Retry selected run
                </button>
              </div>
            )}
            {!runId && (
              <section className="card">
                <CardHead title="Select a run" />
                <p>
                  Choose a saved experiment to review its outcome and ordered
                  trace.
                </p>
              </section>
            )}
            {selectedRun && (
              <>
                {traceOrigin?.runId === runId ? (
                  <button
                    className="text-button history-return"
                    onClick={() => onNavigate(`/results/groups/${encodeURIComponent(traceOrigin.groupId)}`)}
                  >
                    Back to group
                  </button>
                ) : (
                  <button
                    className="text-button history-return"
                    onClick={() => {
                      const history = document.getElementById("run-history");
                      history?.focus();
                      history?.scrollIntoView({ block: "start" });
                    }}
                  >
                    Back to run history
                  </button>
                )}
                <p className="selected-record">
                  {selectedRun.id} · Case {selectedRun.scenario_id} ·{" "}
                  {selectedRun.mode} ·{" "}
                  {selectedRun.model || "Model unavailable"}
                </p>
                <RunInspection
                  key={selectedRun.run_id}
                  selectedRun={selectedRun}
                  traceOpen={traceOrigin?.runId === runId}
                />
              </>
            )}
          </div>
        </section>
      )}
      {view === "groups" && (
        <GroupResults
          runner={runner}
          groupId={identifier}
          activityMatches={filter ? matchingGroups : null}
          activityLoading={Boolean(filter && !activity && !activityError)}
          showRerunCounts={filter?.metric === "reruns"}
          onNavigate={onNavigate}
          condition={attemptFilter?.groupId === identifier ? attemptFilter?.condition ?? null : null}
          onConditionChange={(condition) => setAttemptFilter({ groupId: identifier, condition })}
          onTrace={(id) => {
            setTraceOrigin({ runId: id, groupId: identifier });
            openRun(id);
          }}
        />
      )}
      {view === "campaigns" && (
        <CampaignHistory
          campaigns={campaigns}
          loading={loading}
          error={error}
          runner={runner}
          campaignId={campaignId}
          onSelect={(id) =>
            onNavigate(`/results/campaigns/${encodeURIComponent(id)}`)
          }
          onRun={openRun}
        />
      )}
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}
