import { GroupResults } from "./GroupResults";
import { InvestigationMeasurements } from "./InvestigationMeasurements";
import React, { useEffect, useState } from "react";
import { Sidebar } from "../../components/layout/Sidebar";
import { CardHead } from "../../components/common/Ui";
import { outcomePresentation } from "../../utils/outcomePresentation";
import { MeasurementSummary } from "../dashboard/MeasurementSummary";
import { CampaignHistory } from "./CampaignHistory";
import { RunInspection } from "./RunInspection";

export function ResultsPage({
  runner,
  path,
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
  const filteredRuns = runs.filter((run) =>
    `${run.id} ${run.mode} ${run.result}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
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
        <button className="text-button" onClick={onDashboard}>
          Configure an experiment
        </button>
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
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
            </div>
            {loading && <p role="status">Loading run history…</p>}
            {!loading && !error && !filteredRuns.length && (
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
                filteredRuns.map((run) => (
                  <button
                    type="button"
                    className="recorded-run"
                    key={run.run_id}
                    aria-pressed={runId === run.run_id}
                    onClick={() => openRun(run.run_id)}
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
                <p className="selected-record">
                  {selectedRun.id} · Case {selectedRun.scenario_id} ·{" "}
                  {selectedRun.mode} ·{" "}
                  {selectedRun.model || "Model unavailable"}
                </p>
                <RunInspection
                  key={selectedRun.run_id}
                  selectedRun={selectedRun}
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
          onNavigate={onNavigate}
          onDashboard={onDashboard}
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
