import React, { useEffect, useMemo, useState } from "react";
import { executionModes, selectExecutionMode } from "../../utils/executionMode";
import { defaultSidebarOpen } from "../../utils/sidebarState";
import { CardHead, Icon, Select } from "../../components/common/Ui";
import { Sidebar } from "../../components/layout/Sidebar";
import { outcomePresentation } from "../../utils/outcomePresentation";

const modelOptions = { gemini: "Gemini API LLM", openai: "OpenAI API LLM" };
function CampaignHistory({ campaigns, error, runner, session, onRefresh, singleRunRunning }) {
  const [expanded, setExpanded] = useState(null);
  const [details, setDetails] = useState({});
  const [rerunning, setRerunning] = useState("");
  const [campaignRunning, setCampaignRunning] = useState(false);
  const [campaignRunError, setCampaignRunError] = useState("");
  const runAll = async () => {
    setCampaignRunning(true);
    setCampaignRunError("");
    try {
      await runner.runCampaign({
        provider: session.model,
        model: session.model,
        credentialId: session.credentialId,
      });
      await onRefresh();
    } catch (runError) {
      setCampaignRunError(runError.message);
    } finally {
      setCampaignRunning(false);
    }
  };
  const toggle = async (campaign) => {
    if (expanded === campaign.campaign_id) return setExpanded(null);
    setExpanded(campaign.campaign_id);
    if (!details[campaign.campaign_id]) {
      try {
        const detail = await runner.getCampaign(campaign.campaign_id);
        setDetails((current) => ({
          ...current,
          [campaign.campaign_id]: detail,
        }));
      } catch (loadError) {
        setDetails((current) => ({
          ...current,
          [campaign.campaign_id]: { error: loadError.message },
        }));
      }
    }
  };
  const rerun = async (campaignId, ordinal) => {
    setRerunning(`${campaignId}:${ordinal}`);
    try {
      const detail = await runner.rerunCampaignScenario(campaignId, ordinal);
      setDetails((current) => ({ ...current, [campaignId]: detail }));
    } finally {
      setRerunning("");
    }
  };
  return (
    <article className="card campaign-card">
      <CardHead label="Campaign history" title="Scenario campaigns" />
      <p className="campaign-intro">
        Run every poisoned scenario in filename order with the current session
        provider.
      </p>
      <button
        className="run-button"
        onClick={runAll}
        disabled={campaignRunning || singleRunRunning}
      >
        {campaignRunning ? "Campaign running…" : "Run all poisoned scenarios"}{" "}
        <Icon name="arrow" size={14} />
      </button>
      {campaignRunError && (
        <p className="form-error" role="alert">
          {campaignRunError}
        </p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}. Start the local API and try again.
        </p>
      )}
      {!error && campaigns.length === 0 && (
        <p className="empty-state campaign-empty">No campaigns recorded yet.</p>
      )}
      {campaigns.length > 0 && (
        <div className="campaign-list">
          {campaigns.map((campaign) => {
            const detail = details[campaign.campaign_id];
            return (
              <div className="campaign-entry" key={campaign.campaign_id}>
                <button
                  className="campaign-row campaign-toggle"
                  onClick={() => toggle(campaign)}
                  aria-expanded={expanded === campaign.campaign_id}
                >
                  <div className="campaign-id">
                    <strong>{campaign.campaign_id}</strong>
                    <small>
                      {campaign.provider} · {campaign.model}
                    </small>
                  </div>
                  <div className="campaign-stat">
                    <small>Scenarios</small>
                    <strong>{campaign.scenario_count}</strong>
                  </div>
                  <div className="campaign-stat">
                    <small>Completed</small>
                    <strong className="green">{campaign.completed}</strong>
                  </div>
                  <div className="campaign-stat">
                    <small>Injection successes</small>
                    <strong className={campaign.injection_successes ? "red" : "green"}>
                      {campaign.injection_successes ?? campaign.attack_successes}
                    </strong>
                  </div>
                  <div className="campaign-stat">
                    <small>Task successes</small>
                    <strong className="green">
                      {campaign.task_successes ?? "—"}
                    </strong>
                  </div>
                  <span className={`campaign-status ${campaign.status}`}>
                    {campaign.status.replaceAll("_", " ")}
                  </span>
                </button>
                {expanded === campaign.campaign_id && detail && (
                  <div className="campaign-details">
                    {detail.error ? (
                      <p className="form-error">{detail.error}</p>
                    ) : (
                      detail.scenarios.map((scenario, ordinal) => (
                        <div
                          className="scenario-detail"
                          key={`${scenario.filename}-${ordinal}`}
                        >
                          <div>
                            <strong>{scenario.filename}</strong>
                            <small>
                              {scenario.scenario_id} · child run{" "}
                              {scenario.child_run_id || "not created"}
                            </small>
                          </div>
                          <span
                            className={
                              scenario.failure_state
                                ? "red"
                                : scenario.outcome === "Attack success"
                                  ? "red"
                                  : "green"
                            }
                          >
                            {scenario.failure_state || scenario.injection_verdict || scenario.outcome || "Pending"}
                          </span>
                          {!scenario.failure_state && <small>{scenario.task_outcome || "Task outcome pending"}</small>}
                          <button
                            className="small-button"
                            disabled={
                              rerunning === `${campaign.campaign_id}:${ordinal}`
                            }
                            onClick={() => rerun(campaign.campaign_id, ordinal)}
                          >
                            {rerunning === `${campaign.campaign_id}:${ordinal}`
                              ? "Rerunning…"
                              : "Rerun"}
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}

export function ExperimentDashboard({ session, runner, onSignedOut, onScenarios }) {
  const [mode, setMode] = useState("Defended");
  const [running, setRunning] = useState(false);
  const [query, setQuery] = useState("");
  const [runs, setRuns] = useState([]);
  const [executionMode, setExecutionMode] = useState(executionModes.single);
  const [campaigns, setCampaigns] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(defaultSidebarOpen);
  const [loadError, setLoadError] = useState("");
  const [campaignError, setCampaignError] = useState("");
  const [scenarios, setScenarios] = useState([]);
  const [scenarioError, setScenarioError] = useState("");
  const [selectedScenarioName, setSelectedScenarioName] = useState("");
  const [traceOpen, setTraceOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const selectedScenario = scenarios.find((item) => item.name === selectedScenarioName);
  const selectedOutcomes = outcomePresentation(selectedRun || {});
  useEffect(() => {
    runner
      .listScenarios()
      .then((items) => {
        const usable = items.filter((item) => item.valid);
        setScenarios(usable);
        setSelectedScenarioName((current) => current || usable[0]?.name || "");
      })
      .catch((error) => setScenarioError(error.message));
  }, [runner]);
  useEffect(() => {
    runner
      .listRuns()
      .then((items) => {
        setRuns(items);
        if (items[0]) return runner.getRun(items[0].run_id).then(setSelectedRun);
        return null;
      })
      .catch((error) => setLoadError(error.message));
  }, [runner]);
  const refreshCampaigns = async () => {
    try {
      setCampaigns(await runner.listCampaigns());
      setCampaignError("");
    } catch (error) {
      setCampaignError(error.message);
    }
  };
  useEffect(() => {
    refreshCampaigns();
  }, [runner]);
  const filteredRuns = useMemo(
    () =>
      runs.filter((run) =>
        `${run.id} ${run.mode} ${run.result}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [runs, query],
  );
  const startRun = async () => {
    setRunning(true);
    setLoadError("");
    try {
      const run = await runner.runExperiment({
        sessionId: session.id,
        credentialId: session.credentialId,
        scenarioId: selectedScenario?.scenario_id,
        mode,
        provider: session.model,
        model: session.model === "gemini" ? "gemini-3.5-flash-lite" : session.model,
      });
      setRuns((current) => [run, ...current]);
      setSelectedRun(await runner.getRun(run.run_id));
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setRunning(false);
    }
  };
  return (
    <main className="app-shell">
      <Sidebar
        open={sidebarOpen}
        active="dashboard"
        onClose={() => setSidebarOpen(false)}
        onSessions={onSignedOut}
        onDashboard={() => {}}
        onScenarios={onScenarios}
      />
      <header className="topbar">
        <div className="brand">
          <button
            className="icon-button menu"
            aria-label="Open session workspace"
            onClick={onSignedOut}
          >
            <Icon name="menu" size={18} />
          </button>
          <span className="logo">P</span>
          <div>
            <strong>PoisonTrace</strong>
            <small>{session.name}</small>
          </div>
        </div>
        <div className="profile">
          <span className="avatar">SA</span>
          <div>
            <strong>SOC analyst</strong>
            <small>{modelOptions[session.model]}</small>
          </div>
          <button
            className="icon-button"
            aria-label="Return to sessions"
            onClick={onSignedOut}
          >
            <Icon name="arrow" />
          </button>
        </div>
      </header>
      <section className="welcome">
        <div>
          <h1>
            Ready to investigate? <span>◌</span>
          </h1>
          <p>Configure a run and follow the evidence as it unfolds.</p>
        </div>
        {executionMode === executionModes.single && (
          <button className="run-button" onClick={startRun} disabled={running || !selectedScenario}>
            {running ? <><span className="loading-icon" aria-label="Running" /> Running</> : "Run new experiment"}{" "}
            <Icon name="arrow" size={14} />
          </button>
        )}
      </section>
      <div
        className="execution-mode"
        role="tablist"
        aria-label="Execution workflow"
      >
        <button
          role="tab"
          aria-selected={executionMode === executionModes.single}
          className={executionMode === executionModes.single ? "active" : ""}
          onClick={() =>
            setExecutionMode(selectExecutionMode(executionModes.single))
          }
        >
          Single run
        </button>
        <button
          role="tab"
          aria-selected={executionMode === executionModes.campaign}
          className={executionMode === executionModes.campaign ? "active" : ""}
          onClick={() =>
            setExecutionMode(selectExecutionMode(executionModes.campaign))
          }
          disabled={running}
        >
          Batch campaign
        </button>
      </div>
      <section className="dashboard-grid">
        {executionMode === executionModes.single && (
          <article className="card launcher">
            <CardHead label="Experiment launcher" title="Start a new run" />
            <div className="fields">
              <Select
                label="Scenario"
                value={selectedScenarioName}
                onChange={setSelectedScenarioName}
                options={scenarios.map((scenario) => scenario.name)}
              />
              <Select
                label="Mode"
                value={mode}
                onChange={setMode}
                options={["Defended", "Clean", "Poisoned"]}
              />
            </div>
            {scenarioError && <p className="form-error" role="alert">{scenarioError}</p>}
            {!scenarioError && !scenarios.length && <p className="empty-state">Loading scenarios…</p>}
            <div className="launcher-note">
              <span className="status-dot" />
              <span>Protected actions need approval</span>
              <span className="arrow">↗</span>
            </div>
          </article>
        )}
        <article className="card focus">
          <CardHead label="Current focus" title={selectedRun?.id || "No run yet"} />
          <div className="focus-body">
            <div className="ring">
              <span>{selectedRun ? "100%" : "—"}</span>
              <small>trace</small>
            </div>
            <div>
              <strong>{selectedRun?.scenario_id || "No scenario selected"}</strong>
              <p>
                {selectedRun?.mode || mode} · {selectedRun?.model || modelOptions[session.model]}
              </p>
              <button className="small-button" disabled={!selectedRun} onClick={() => setTraceOpen(true)}>
                Inspect trace <Icon name="arrow" size={12} />
              </button>
            </div>
          </div>
        </article>
        <article className="card outcome">
          <CardHead
            label="Security outcome"
            title={selectedRun?.result || "No run yet"}
            pill={selectedRun ? "Recorded" : "Waiting"}
            tone={selectedRun?.tone || "green"}
          />
          <div className="outcome-main">
            <strong>{selectedRun?.recommendation || "No outcome recorded"}</strong>
            <p>
              {selectedRun
                ? `${selectedRun.execution_time_ms} ms · ${selectedRun.system_error ? "System error" : "No system error"}`
                : "Run a scenario to view the persisted outcome."}
            </p>
          </div>
          <div className="stat-row">
            <div>
              <small>Injection verdict</small>
              <strong className={selectedRun?.attack_success ? "text-red" : "text-green"}>{selectedRun ? selectedOutcomes.injection : "—"}</strong>
            </div>
            <div>
              <small>Task outcome</small>
              <strong>{selectedRun ? selectedOutcomes.task : "—"}</strong>
            </div>
            <div>
              <small>Tool-call status</small>
              <strong>{selectedRun ? selectedOutcomes.tool : "—"}</strong>
            </div>
            <div>
              <small>System/model</small>
              <strong>{selectedRun ? selectedOutcomes.system : "—"}</strong>
            </div>
            <div>
              <small>Duration</small>
              <strong>{selectedRun ? `${selectedRun.execution_time_ms} ms` : "—"}</strong>
            </div>
          </div>
        </article>
        <article className="card trace">
          <CardHead label="Live evidence ledger" title="Trace timeline" />
          <div className="timeline">
            {selectedRun?.trace?.length ? selectedRun.trace.map((event, index) => (
              <div key={`${event.kind}-${index}`}>
                <time>{index + 1}</time>
                <i className={event.kind === "policy_decision" ? "red" : "cyan"} />
                <p>
                  <strong>{event.kind.replaceAll("_", " ")}</strong>
                  <small>{Object.entries(event.data).map(([key, value]) => `${key}: ${value}`).join(" · ")}</small>
                </p>
              </div>
            )) : <p className="empty-state">No persisted trace events.</p>}
          </div>
          <button className="link-button" onClick={() => setTraceOpen(true)}>
            Open full trace <Icon name="arrow" size={12} />
          </button>
          {traceOpen && (
            <div
              className="trace-placeholder"
              role="dialog"
              aria-label="Trace inspection"
            >
              <div className="card-head">
                <div>
                  <p className="label">Trace inspection</p>
                  <h2>{runs[0]?.id || "No run selected"}</h2>
                </div>
                <button
                  className="icon-button"
                  onClick={() => setTraceOpen(false)}
                  aria-label="Close trace"
                >
                  ×
                </button>
              </div>
              <p>
                This inspection surface is ready for the future ordered trace.
              </p>
              <div className="placeholder-events">
                {selectedRun?.trace?.map((event, index) => <div key={`${event.kind}-full-${index}`}><i className="cyan" /><span>{event.kind.replaceAll("_", " ")}</span><small>{JSON.stringify(event.data)}</small></div>)}
              </div>
            </div>
          )}
        </article>
        <article className="card activity">
          <div className="card-head">
            <div>
              <p className="label">Recent runs</p>
              <h2>Compare conditions</h2>
            </div>
            <div className="search-field">
              <Icon name="search" size={13} />
              <input
                aria-label="Filter runs"
                placeholder="Filter"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          </div>
          {loadError && (
            <p className="form-error" role="alert">
              {loadError}. Start the local API and try again.
            </p>
          )}
          <div className="run-list">
            {filteredRuns.length
              ? filteredRuns.map((run) => (
                  <div key={run.id}>
                    <span className={`run-dot ${run.tone}`} />
                    <p>
                      <strong>
                        {run.id} · {run.mode}
                      </strong>
                      <small>
                        {run.injection_verdict || run.result} · {run.task_outcome || "Task outcome unavailable"} · {run.time}
                      </small>
                    </p>
                    <b className={run.tone}>{run.mark}</b>
                  </div>
                ))
              : !loadError && (
                  <p className="empty-state">No runs recorded yet.</p>
                )}
          </div>
          <button className="link-button">
            Open comparison view <Icon name="arrow" size={12} />
          </button>
        </article>
        {executionMode === executionModes.campaign && (
          <CampaignHistory
            campaigns={campaigns}
            error={campaignError}
            runner={runner}
            session={session}
            onRefresh={refreshCampaigns}
            singleRunRunning={running}
          />
        )}
      </section>
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}
