import { ExecutionSelection, useExecutionOptions } from "./ExecutionSelection";
import {
  EXECUTION_STORAGE_KEY,
  resolveExecution,
} from "../../utils/executionSelection";
import { GroupLauncher } from "./GroupLauncher";
import React, { useEffect, useState } from "react";
import { executionModes } from "../../utils/executionMode";
import { CardHead, Icon, Select } from "../../components/common/Ui";
import { Sidebar } from "../../components/layout/Sidebar";

const modelOptions = {
  gemini: "Gemini API LLM",
  openai: "OpenAI API LLM",
  fake: "Offline model substitute",
};

const providerModels = {
  gemini: "gemini-3.5-flash-lite",
  openai: "gpt-5-mini",
  fake: "fake",
};

export function ExperimentDashboard({
  session,
  entry = "/dashboard",
  onDashboard,
  runner,
  onSignedOut,
  onScenarios,
  onResults,
  user,
  auth,
  onSignOut,
}) {
  const [executionSelection, setExecutionSelection] = useState(
    () => window.localStorage.getItem(EXECUTION_STORAGE_KEY) || "scripted",
  );
  const onExecutionChange = (selection) => {
    setExecutionSelection(selection);
    window.localStorage.setItem(EXECUTION_STORAGE_KEY, selection);
  };
  const executionOptions = useExecutionOptions(runner);
  const execution = resolveExecution(
    executionSelection,
    executionOptions.configurations,
    executionOptions.credentials,
  );
  const groupMode = entry === "/dashboard";
  const [mode, setMode] = useState("Defended");
  const workflow =
    entry === "/dashboard/metadata" || entry === "/dashboard/campaign"
      ? "Metadata experiment"
      : "MCP investigation";
  const [condition, setCondition] = useState("clean");
  const [conditionReset, setConditionReset] = useState(false);
  const [cases, setCases] = useState([]);
  const [caseId, setCaseId] = useState("");
  const [caseError, setCaseError] = useState("");
  const [casesLoading, setCasesLoading] = useState(false);
  const defended = condition === "defended";
  const attacked = condition !== "clean";
  const investigation = workflow === "MCP investigation";
  const [attackFamily, setAttackFamily] = useState("description-poisoning");
  const attack = cases
    .find((item) => item.case_id === caseId)
    ?.attacks?.find((item) => item.family === attackFamily);
  const investigationProvider = execution.provider;
  const [running, setRunning] = useState(false);
  const executionMode =
    entry === "/dashboard/campaign"
      ? executionModes.campaign
      : executionModes.single;
  const [scenarios, setScenarios] = useState([]);
  const [scenarioError, setScenarioError] = useState("");
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [selectedScenarioName, setSelectedScenarioName] = useState("");
  const [runs, setRuns] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [activityError, setActivityError] = useState("");
  const [activityLoading, setActivityLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const selectedScenario = scenarios.find(
    (item) => item.name === selectedScenarioName,
  );
  useEffect(() => {
    if (!investigation) return;
    let active = true;
    setCasesLoading(true);
    setCaseError("");
    runner
      .listInvestigationCases()
      .then((items) => {
        if (!active) return;
        setCases(items);
        setCaseId(items[0]?.case_id || "");
      })
      .catch((error) => {
        if (active) setCaseError(error.message);
      })
      .finally(() => {
        if (active) setCasesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner, investigation]);
  useEffect(() => {
    let active = true;
    runner
      .listScenarios()
      .then((items) => {
        if (!active) return;
        const usable = items.filter((item) => item.valid);
        setScenarios(usable);
        setSelectedScenarioName((current) => current || usable[0]?.name || "");
      })
      .catch((error) => {
        if (active) setScenarioError(error.message);
      })
      .finally(() => {
        if (active) setScenariosLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner]);
  useEffect(() => {
    let active = true;
    setActivityLoading(true);
    setActivityError("");
    const request =
      executionMode === executionModes.single
        ? runner.listRuns()
        : runner.listCampaigns();
    request
      .then((items) => {
        if (!active) return;
        if (executionMode === executionModes.single) setRuns(items.slice(0, 3));
        else setCampaigns(items.slice(0, 3));
      })
      .catch((error) => {
        if (active) setActivityError(error.message);
      })
      .finally(() => {
        if (active) setActivityLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner, executionMode]);
  const startRun = async () => {
    if (investigation && (!execution.valid || !caseId || (attacked && !attack)))
      return;
    setRunning(true);
    setLoadError("");
    try {
      if (executionMode === executionModes.campaign) {
        const model = providerModels[session?.model];
        const campaign = await runner.runCampaign({
          provider: session?.model,
          model,
          credentialId: session.credentialId,
        });
        onResults(
          `/results/campaigns/${encodeURIComponent(campaign.campaign_id)}`,
        );
      } else if (investigation) {
        const currentCases = await runner.listInvestigationCases();
        const current = currentCases.find(item => item.case_id === caseId);
        const selected = cases.find(item => item.case_id === caseId);
        if (!current || current.case_version !== selected?.case_version) {
          setCases(currentCases);
          if (!current) setCaseId("");
          throw new Error("Research case version changed or is unavailable. Review the refreshed case selection before running again.");
        }
        const run = await runner.runInvestigation({
          caseId,
          mode: condition,
          attackFamily: attacked ? attackFamily : undefined,
          sessionId: execution.configuration?.id || "",
          provider: execution.provider,
          model: execution.model,
          credentialId: execution.credentialId,
        });
        onResults(`/results/runs/${run.run_id}`);
      } else {
        const run = await runner.runExperiment({
          sessionId: session.id,
          credentialId: session.credentialId,
          scenarioId: selectedScenario?.scenario_id,
          mode,
          provider: session?.model,
          model: providerModels[session?.model],
        });
        onResults(`/results/runs/${run.run_id}`);
      }
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setRunning(false);
    }
  };
  const batch = executionMode === executionModes.campaign;
  return (
    <main className="app-shell dashboard-page">
      <Sidebar
        user={user}
        auth={auth}
        onSignedOut={onSignOut}
        active="dashboard"
        onSessions={onSignedOut}
        onDashboard={onDashboard}
        onResults={() => onResults("/results/groups")}
        onScenarios={onScenarios}
      />
      <section className="welcome">
        <div>
          <h1>Set up an experiment</h1>
          <p>
            {groupMode || investigation ? "MCP execution" : session.name} ·{" "}
            {groupMode
              ? "Matched investigations"
              : investigation && executionMode === executionModes.single
                ? investigationProvider === "scripted"
                  ? "Scripted offline model"
                  : modelOptions[investigationProvider]
                : modelOptions[session?.model]}{" "}
            · Configure an experiment, then review saved evidence on Results.
          </p>
        </div>
      </section>
      <div
        className="execution-mode"
        role="group"
        aria-label="Execution workflow"
      >
        <button
          aria-pressed={groupMode}
          className={groupMode ? "active" : ""}
          disabled={running}
          onClick={() => {
            onDashboard("/dashboard");
          }}
        >
          Matched group
        </button>
        <button
          aria-pressed={!batch && !groupMode && investigation}
          className={!batch && !groupMode && investigation ? "active" : ""}
          disabled={running}
          onClick={() => {
            onDashboard("/dashboard/single");
          }}
        >
          Single run
        </button>
      </div>
      {running && (
        <p role="status">
          {batch ? "Campaign" : "Experiment"} running. Results will open when
          this request finishes.
        </p>
      )}
      {loadError && (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      )}
      {groupMode ? (
        <GroupLauncher
          onRunningChange={setRunning}
          runner={runner}
          selection={executionSelection}
          onSelectionChange={onExecutionChange}
          executionOptions={executionOptions}
          onResults={onResults}
        />
      ) : (
        <>
          <section className="dashboard-execution">
            {!investigation && (
              <p className="launcher-note">
                Advanced metadata scenarios. These experiments do not retrieve
                MCP evidence.
              </p>
            )}
            <div className="dashboard-setup">
              {!batch && (
                <article className="card launcher">
                  <CardHead
                    title={
                      investigation ? "MCP investigation" : "Experiment setup"
                    }
                  />
                  <div className="fields">
                    {!investigation && (
                      <Select
                        label="Investigation workflow"
                        value={workflow}
                        onChange={() => {}}
                        disabled={running}
                        options={["Metadata experiment"]}
                      />
                    )}
                    {investigation ? (
                      <>
                        <label className="field">
                          <span>Synthetic case</span>
                          <select
                            value={caseId}
                            disabled={running || casesLoading}
                            onChange={(event) => {
                              const next = cases.find(
                                (item) => item.case_id === event.target.value,
                              );
                              setCaseId(event.target.value);
                              setConditionReset(
                                !next?.attacks?.length && condition !== "clean",
                              );
                              if (!next?.attacks?.length) setCondition("clean");
                            }}
                          >
                            {cases.map((item) => (
                              <option key={item.case_id} value={item.case_id}>
                                {item.name} · v{item.case_version}
                                {item.dataset_category
                                  ? ` · ${item.dataset_category.replaceAll("-", " ")}`
                                  : ""}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field">
                          <span>Condition</span>
                          <select
                            value={condition}
                            disabled={running || casesLoading || !caseId}
                            onChange={(event) => {
                              setCondition(event.target.value);
                              setConditionReset(false);
                            }}
                          >
                            <option value="clean">
                              Clean · trusted metadata
                            </option>
                            {Boolean(
                              cases.find((item) => item.case_id === caseId)
                                ?.attacks?.length,
                            ) && (
                              <>
                                <option value="poisoned">
                                  Poisoned · attack exposed
                                </option>
                                <option value="defended">
                                  Defended · manifest enforced
                                </option>
                              </>
                            )}
                          </select>
                        </label>
                        <ExecutionSelection
                          selection={executionSelection}
                          onChange={onExecutionChange}
                          options={executionOptions}
                          disabled={running}
                        />
                        {attacked && (
                          <label className="field">
                            <span>Attack family</span>
                            <select
                              value={attack ? attackFamily : ""}
                              disabled={
                                running ||
                                !cases.find((item) => item.case_id === caseId)
                                  ?.attacks?.length
                              }
                              onChange={(event) =>
                                setAttackFamily(event.target.value)
                              }
                            >
                              {!attack && (
                                <option value="">
                                  No attack allocated to this case
                                </option>
                              )}
                              <option
                                value="description-poisoning"
                                disabled={
                                  !cases
                                    .find((item) => item.case_id === caseId)
                                    ?.attacks?.some(
                                      (item) =>
                                        item.family === "description-poisoning",
                                    )
                                }
                              >
                                Description poisoning
                              </option>
                              <option
                                value="cross-server-shadowing"
                                disabled={
                                  !cases
                                    .find((item) => item.case_id === caseId)
                                    ?.attacks?.some(
                                      (item) =>
                                        item.family ===
                                        "cross-server-shadowing",
                                    )
                                }
                              >
                                Cross-server shadowing
                              </option>
                            </select>
                          </label>
                        )}
                      </>
                    ) : (
                      <>
                        <Select
                          label="Scenario"
                          value={selectedScenarioName}
                          onChange={setSelectedScenarioName}
                          disabled={running}
                          options={scenarios.map((scenario) => scenario.name)}
                        />
                        <Select
                          label="Mode"
                          value={mode}
                          onChange={setMode}
                          disabled={running}
                          options={["Defended", "Clean", "Poisoned"]}
                        />
                      </>
                    )}
                  </div>
                  {investigation && (
                    <div className="launcher-note investigation-note">
                      <details className="method-disclosure">
                        <summary>Investigation method and limits</summary>
                        <p>
                          Read-only investigation through two local synthetic
                          MCP servers. Verdict, priority, handling and evidence
                          references are saved on Results. Scripted offline
                          verifies mechanics and does not establish live-model
                          effectiveness.
                        </p>
                      </details>
                      {caseId &&
                        !cases.find((item) => item.case_id === caseId)?.attacks
                          ?.length && (
                          <p role="status">
                            This case is a clean control. Only Clean is
                            available.
                            {conditionReset &&
                              " Condition reset to Clean for this control."}
                          </p>
                        )}
                      {attacked && (
                        <details className="method-disclosure">
                          <summary>Attack payload and exposure</summary>
                          <p>
                            Payload:{" "}
                            {attack?.payload_id || "Loading payload identity"}.{" "}
                            {defended
                              ? "Manifest policy withholds changed or unapproved definitions before model exposure and checks calls before invocation."
                              : "Malicious metadata is exposed to the model without manifest enforcement."}{" "}
                            Scripted offline normally ignores it; this selection
                            does not establish live-model vulnerability.
                          </p>
                        </details>
                      )}
                    </div>
                  )}
                  {investigation && casesLoading && (
                    <p role="status">Loading investigation cases…</p>
                  )}
                  {investigation && caseError && (
                    <p className="form-error" role="alert">
                      {caseError}
                    </p>
                  )}
                  {investigation &&
                    !casesLoading &&
                    !caseError &&
                    !cases.length && (
                      <p className="empty-state">
                        No investigation cases are available.
                      </p>
                    )}
                  {!investigation && scenarioError && (
                    <p className="form-error" role="alert">
                      {scenarioError}
                    </p>
                  )}
                  {!investigation && scenariosLoading && (
                    <p role="status">Loading scenarios…</p>
                  )}
                  {!investigation &&
                    !scenariosLoading &&
                    !scenarioError &&
                    !scenarios.length && (
                      <div className="empty-state">
                        <p>
                          No valid scenarios are available. Create or repair a
                          scenario before running an experiment.
                        </p>
                        <button className="text-button" onClick={onScenarios}>
                          Open scenario library
                        </button>
                      </div>
                    )}
                  {!investigation && (
                    <div className="launcher-note">
                      <span className="status-dot" />
                      <span>
                        Gateway decisions are simulated and occur after the
                        model completion.
                      </span>
                    </div>
                  )}
                </article>
              )}
              {batch && (
                <article className="card">
                  <CardHead title="Run a campaign" />
                  <p>
                    Run every scenario selected by the existing
                    poisoned-filename rule, using {modelOptions[session?.model]}{" "}
                    and this session's credential reference.
                  </p>
                  <p>
                    Campaign status, individual attempts and traces will be
                    available on Results.
                  </p>
                </article>
              )}
              <section
                className="card run-specification"
                aria-label="This experiment"
              >
                <h2>This experiment</h2>
                <p className="specification-intro">
                  Review the input, model and policy before you run.
                </p>
                <dl className="specification-list">
                  <div>
                    <dt>Configuration</dt>
                    <dd>
                      {investigation
                        ? execution.configuration?.name || "Scripted offline"
                        : session.name}
                    </dd>
                  </div>
                  <div>
                    <dt>Workflow</dt>
                    <dd>
                      {batch
                        ? "Batch campaign"
                        : investigation
                          ? "Read-only MCP investigation"
                          : "Metadata experiment"}
                    </dd>
                  </div>
                  <div>
                    <dt>{batch ? "Inputs" : "Input"}</dt>
                    <dd>
                      {batch
                        ? "All scenarios selected by the poisoned-filename rule"
                        : investigation
                          ? cases.find((item) => item.case_id === caseId)
                              ?.name || "No case selected"
                          : selectedScenario?.name || "No scenario selected"}
                    </dd>
                  </div>
                  {investigation && !batch && (
                    <div>
                      <dt>Case version</dt>
                      <dd>
                        {caseId || "Unavailable"} · v
                        {cases.find((item) => item.case_id === caseId)
                          ?.case_version || "Unavailable"}
                      </dd>
                    </div>
                  )}
                  <div>
                    <dt>Condition</dt>
                    <dd>
                      {batch
                        ? "Poisoned scenarios"
                        : investigation
                          ? defended
                            ? "Defended"
                            : attacked
                              ? "Poisoned"
                              : "Clean"
                          : mode}
                    </dd>
                  </div>
                  <div>
                    <dt>Model</dt>
                    <dd>
                      {investigation && !batch
                        ? investigationProvider === "scripted"
                          ? `Scripted offline · ${execution.model}`
                          : execution.model || "Select execution"
                        : `${modelOptions[session?.model]} · ${providerModels[session?.model]}`}
                    </dd>
                  </div>
                  <div>
                    <dt>Credential</dt>
                    <dd>
                      {investigation && !batch
                        ? execution.provider === "scripted"
                          ? "No API key used"
                          : execution.credentialId
                            ? `Reference: ${execution.credentialId}`
                            : "Matching credential required"
                        : session.credentialId
                          ? `Reference: ${session.credentialId}`
                          : "No credential selected"}
                    </dd>
                  </div>
                  {attacked && !batch && (
                    <div>
                      <dt>Attack payload</dt>
                      <dd>{attack?.payload_id || "No attack allocated"}</dd>
                    </div>
                  )}
                  {!batch && (
                    <div>
                      <dt>Manifest policy</dt>
                      <dd>
                        {investigation
                          ? defended || !attacked
                            ? "Enabled before exposure and invocation"
                            : "Disabled"
                          : mode === "Poisoned"
                            ? "Disabled · simulated gateway"
                            : "Simulated after model completion"}
                      </dd>
                    </div>
                  )}
                </dl>
                <p className="specification-note">
                  {batch
                    ? "Existing campaign selection and model settings apply. Inspect each saved attempt on Results."
                    : investigation
                      ? "Synthetic evidence only. Recommendations do not change incident state."
                      : "This workflow retrieves no evidence and executes no external MCP tool."}
                </p>
                <button
                  className="run-button"
                  onClick={startRun}
                  disabled={
                    running ||
                    (!batch &&
                      (investigation
                        ? !caseId ||
                          casesLoading ||
                          (attacked && !attack) ||
                          !execution.valid
                        : !selectedScenario))
                  }
                >
                  {running
                    ? "Running…"
                    : batch
                      ? "Run all poisoned scenarios"
                      : investigation
                        ? "Run MCP investigation"
                        : "Run new experiment"}
                  <Icon name="arrow" size={14} />
                </button>
                <p className="run-destination">
                  The exact saved result opens when this request finishes.
                </p>
              </section>
            </div>
            <article className="card recent-activity">
              <div className="card-head">
                <h2>Recent activity</h2>
                <button
                  className="text-button"
                  disabled={running}
                  onClick={() =>
                    onResults(batch ? "/results/campaigns" : "/results/runs")
                  }
                >
                  View all {batch ? "campaigns" : "runs"}
                </button>
              </div>
              {activityLoading && <p role="status">Loading recent activity…</p>}
              {activityError && (
                <p className="form-error" role="alert">
                  {activityError}
                </p>
              )}
              {!activityLoading && !activityError && (
                <div className="run-list">
                  {(batch ? campaigns : runs).map((item) => (
                    <button
                      type="button"
                      className="recorded-run"
                      disabled={running}
                      key={batch ? item.campaign_id : item.run_id}
                      onClick={() =>
                        onResults(
                          batch
                            ? `/results/campaigns/${encodeURIComponent(item.campaign_id)}`
                            : `/results/runs/${item.run_id}`,
                        )
                      }
                    >
                      <span>
                        <strong>{batch ? item.campaign_id : item.id}</strong>
                        <small>
                          {batch
                            ? item.status?.replaceAll("_", " ")
                            : item.result}{" "}
                          · {batch ? item.model : item.mode}
                        </small>
                      </span>
                      <Icon name="arrow" size={14} />
                    </button>
                  ))}
                  {!(batch ? campaigns : runs).length && (
                    <p className="empty-state">
                      No {batch ? "campaigns" : "runs"} recorded yet.
                    </p>
                  )}
                </div>
              )}
            </article>
          </section>
        </>
      )}
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}
