import React, { useEffect, useMemo, useState } from "react";
import { executionModes, selectExecutionMode } from "../../utils/executionMode";
import { defaultSidebarOpen } from "../../utils/sidebarState";
import { CardHead, Icon, Select } from "../../components/common/Ui";
import { Sidebar } from "../../components/layout/Sidebar";
import { outcomePresentation } from "../../utils/outcomePresentation";

const modelOptions = { gemini: "Gemini API LLM", openai: "OpenAI API LLM" };
function CampaignHistory({ campaigns, error, runner, session, onRefresh, singleRunRunning }) {
  const [details, setDetails] = useState({});
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);
  const [selectedScenarioIndex, setSelectedScenarioIndex] = useState(null);
  const [rerunning, setRerunning] = useState("");
  const [campaignRunning, setCampaignRunning] = useState(false);
  const [campaignRunError, setCampaignRunError] = useState("");
  const runAll = async () => {
    setCampaignRunning(true);
    setCampaignRunError("");
    try {
      const model = session.model === "gemini"
        ? "gemini-3.5-flash-lite"
        : session.model === "openai"
          ? "gpt-5-mini"
          : "fake";
      await runner.runCampaign({
        provider: session.model,
        model,
        credentialId: session.credentialId,
      });
      await onRefresh();
    } catch (runError) {
      setCampaignRunError(runError.message);
    } finally {
      setCampaignRunning(false);
    }
  };
  const selectCampaign = async (campaign) => {
    setSelectedCampaignId(campaign.campaign_id);
    setSelectedScenarioIndex(null);
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
  const selectedCampaign = details[selectedCampaignId];
  const selectedScenario = selectedCampaign?.scenarios?.[selectedScenarioIndex];
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
    <section className="campaign-workspace">
      <div className="campaign-history-panel">
        <CardHead label="Batch campaign" title="Campaign history" />
        <p className="campaign-intro">Select a campaign, then choose a scenario to inspect its result.</p>
        <button className="run-button" onClick={runAll} disabled={campaignRunning || singleRunRunning}>
          {campaignRunning ? "Campaign running…" : "Run all poisoned scenarios"} <Icon name="arrow" size={14} />
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
        {campaigns.length > 0 && <div className="campaign-list">
          {campaigns.map((campaign) => {
            const detail = details[campaign.campaign_id];
            return (
              <div className="campaign-entry" key={campaign.campaign_id}>
                <button
                  className="campaign-row campaign-toggle"
                  onClick={() => selectCampaign(campaign)}
                  aria-pressed={selectedCampaignId === campaign.campaign_id}
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
              </div>
            );
          })}
        </div>
        }
      </div>
      <div className="campaign-breakdown-panel">
        {!selectedCampaignId && <div className="campaign-empty-selection"><span className="campaign-empty-mark">↗</span><h2>Select a scenario</h2><p>Choose a campaign from the history list to load its scenario results.</p></div>}
        {selectedCampaignId && selectedCampaign?.error && <p className="form-error">{selectedCampaign.error}</p>}
        {selectedCampaignId && selectedCampaign && !selectedScenario && !selectedCampaign.error && (
          <div className="campaign-empty-selection"><span className="campaign-empty-mark">○</span><h2>Select a scenario</h2><p>Choose one of this campaign's scenarios to see its breakdown.</p><div className="campaign-scenario-picker">{selectedCampaign.scenarios.map((scenario, index) => <button key={`${scenario.filename}-${index}`} className="scenario-picker-row" onClick={() => setSelectedScenarioIndex(index)}><span>{scenario.filename}</span><small>{scenario.injection_verdict || scenario.outcome || "Pending"}</small></button>)}</div></div>
        )}
        {selectedScenario && <div className="campaign-scenario-breakdown">
          <div className="breakdown-heading"><div><p className="label">Scenario breakdown</p><h2>{selectedScenario.filename}</h2><small>{selectedScenario.scenario_id} · child run {selectedScenario.child_run_id || "not created"}</small></div><button className="small-button" disabled={rerunning === `${selectedCampaignId}:${selectedScenarioIndex}`} onClick={() => rerun(selectedCampaignId, selectedScenarioIndex)}>{rerunning === `${selectedCampaignId}:${selectedScenarioIndex}` ? "Rerunning…" : "Rerun scenario"}</button></div>
          <div className="breakdown-status"><span className={selectedScenario.failure_state ? "red" : selectedScenario.injection_verdict === "Attack success" ? "red" : "green"}>{selectedScenario.failure_state || selectedScenario.injection_verdict || selectedScenario.outcome || "Pending"}</span><small>{selectedScenario.task_outcome || "Task outcome pending"}</small></div>
          <div className="breakdown-grid"><div><small>Injection verdict</small><strong>{selectedScenario.injection_verdict || selectedScenario.outcome || "Pending"}</strong></div><div><small>Task outcome</small><strong>{selectedScenario.task_outcome || "Pending"}</strong></div><div><small>Tool-call status</small><strong>{selectedScenario.tool_call_status || "Pending"}</strong></div><div><small>Failure state</small><strong>{selectedScenario.failure_state || "None"}</strong></div></div>
          <div className="campaign-trace">
            <div className="breakdown-section-heading"><p className="label">Full trace</p><small>{selectedScenario.trace?.length || 0} events</small></div>
            {selectedScenario.trace?.length ? <div className="timeline campaign-timeline">{selectedScenario.trace.map((event, index) => <div key={`${event.kind}-${index}`}><time>{index + 1}</time><i className={event.kind === "policy_decision" ? "red" : "cyan"} /><p><strong>{event.kind.replaceAll("_", " ")}</strong><small>{Object.entries(event.data || {}).map(([key, value]) => `${key}: ${value}`).join(" · ")}</small></p></div>)}</div> : <p className="empty-state">No trace events were persisted for this scenario.</p>}
          </div>
        </div>}
      </div>
    </section>
  );
}

export function ExperimentDashboard({ session, runner, onSignedOut, onScenarios, user, auth, onSignOut }) {
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
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
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
      .catch((error) => setScenarioError(error.message))
      .finally(() => setScenariosLoading(false));
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
  const selectRun = async (run) => {
    setRunLoading(true);
    setLoadError("");
    try { setSelectedRun(await runner.getRun(run.run_id)); }
    catch (error) { setLoadError(error.message); }
    finally { setRunLoading(false); }
  };
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
        user={user} auth={auth} onSignedOut={onSignOut}
        open={sidebarOpen}
        active="dashboard"
        onClose={() => setSidebarOpen(false)}
        onSessions={onSignedOut}
        onDashboard={() => {}}
        onScenarios={onScenarios}
      />
      <section className="welcome">
        <div>
          <h1>
            {session.name}
          </h1>
          <p>{modelOptions[session.model]} · Select a scenario, run an experiment, and inspect the recorded evidence.</p>
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
        role="group"
        aria-label="Execution workflow"
      >
        <button
          aria-pressed={executionMode === executionModes.single}
          className={executionMode === executionModes.single ? "active" : ""}
          onClick={() =>
            setExecutionMode(selectExecutionMode(executionModes.single))
          }
        >
          Single run
        </button>
        <button
          aria-pressed={executionMode === executionModes.campaign}
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
            {scenariosLoading && <p role="status">Loading scenarios…</p>}
            {!scenariosLoading && !scenarioError && !scenarios.length && <div className="empty-state"><p>No valid scenarios are available. Create or repair a scenario before running an experiment.</p><button className="text-button" onClick={onScenarios}>Open scenario library</button></div>}
            <div className="launcher-note">
              <span className="status-dot" />
              <span>Protected actions need approval</span>
              <span className="arrow">↗</span>
            </div>
          </article>
        )}
        {executionMode === executionModes.single && <>
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
          <CardHead label="Recorded evidence" title="Recorded trace" />
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
              role="region"
              aria-label="Trace inspection"
            >
              <div className="card-head">
                <div>
                  <p className="label">Trace inspection</p>
                  <h2>{selectedRun?.id || "Selected run"}</h2>
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
                Recorded events for the selected experiment.
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
              <h2>Recorded experiments</h2>
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
          {runLoading && <p role="status">Loading selected run…</p>}
          <div className="run-list">
            {filteredRuns.length
              ? filteredRuns.map((run) => (
                  <button type="button" className="recorded-run" key={run.id} disabled={runLoading || running} aria-pressed={selectedRun?.run_id === run.run_id} onClick={() => selectRun(run)}>
                    <span className={`run-dot ${run.tone}`} />
                    <span>
                      <strong>
                        {run.id} · {run.mode}
                      </strong>
                      <small>
                        {run.injection_verdict || run.result} · {run.task_outcome || "Task outcome unavailable"} · {run.time}
                      </small>
                    </span>
                    <b className={run.tone}>{run.mark}</b>
                  </button>
                ))
              : !loadError && (
                  <p className="empty-state">No runs recorded yet.</p>
                )}
          </div>

        </article>
        </>}
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
