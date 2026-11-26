import { ExecutionSelection, useExecutionOptions } from "./ExecutionSelection";
import {
  EXECUTION_STORAGE_KEY,
  resolveExecution,
} from "../../utils/executionSelection";
import { GroupLauncher } from "./GroupLauncher";
import { CaseOptions } from "./CaseOptions";
import { observeInvestigationJobs } from "./investigationJobObserver";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { workspaceStorage } from "../../utils/workspaceStorage";
import { executionModes } from "../../utils/executionMode";
import { CardHead, Icon, Select } from "../../components/common/Ui";
import { Sidebar } from "../../components/layout/Sidebar";
import { PendingButton } from "../../components/common/PendingButton";

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

const sampleCaseId = "soc-backup-002";

export function ExperimentDashboard({
  session,
  entry = "/dashboard",
  onDashboard,
  runner,
  onSignedOut,
  onScenarios,
  onResults,
  onRunStart,
  user,
  auth,
  onSignOut,
}) {
  const storage = useMemo(() => workspaceStorage(window.localStorage), []);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const [executionSelection, setExecutionSelection] = useState(
    () => storage.getItem(EXECUTION_STORAGE_KEY) || "scripted",
  );
  const onExecutionChange = (selection) => {
    setExecutionSelection(selection);
    storage.setItem(EXECUTION_STORAGE_KEY, selection);
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
  const [casesLoading, setCasesLoading] = useState(true);
  const [sampleSelected, setSampleSelected] = useState(false);
  const sampleAvailable = cases.some((item) => item.case_id === sampleCaseId);
  const prepareSample = () => {
    setCaseId(sampleCaseId);
    setCondition("clean");
    setConditionReset(false);
    setExecutionSelection("scripted");
    setSampleSelected(true);
  };
  const defended = condition === "defended";
  const attacked = condition !== "clean";
  const investigation = workflow === "MCP investigation";
  const [attackFamily, setAttackFamily] = useState("description-poisoning");
  const attack = cases
    .find((item) => item.case_id === caseId)
    ?.attacks?.find((item) => item.family === attackFamily);
  const investigationProvider = execution.provider;
  const [submitting, setSubmitting] = useState(false);
  const inFlight = useRef(false);
  const [groupRunning, setGroupRunning] = useState(false);
  const [job, setJob] = useState(null);
  const [sampleResultId, setSampleResultId] = useState(null);
  const savedRunButton = useRef(null);
  useEffect(() => {
    if (sampleResultId && job?.run_id === sampleResultId) savedRunButton.current?.focus();
  }, [sampleResultId, job?.run_id]);
  const running = groupMode ? groupRunning : submitting || job?.status === "queued" || job?.status === "active";
  const jobKind = investigation ? "single" : entry === "/dashboard/campaign" ? "campaign" : "metadata";
  const intentStorageKey = investigation ? "investigation-intent" : `${jobKind}-intent`;
  const [pendingIntent, setPendingIntent] = useState(() => {
    try { return JSON.parse(storage.getItem(intentStorageKey) || 'null'); }
    catch { return null; }
  });
  const sampleRun = sampleSelected && caseId === sampleCaseId &&
    condition === "clean" && execution.provider === "scripted";
  const retainIntent = (value) => {
    setPendingIntent(value);
    storage.setItem(intentStorageKey, JSON.stringify(value));
  };
  const openJobResults = (current) => {
    if (current.campaign_id) onResults(`/results/campaigns/${encodeURIComponent(current.campaign_id)}`);
    else if (current.run_id) onResults(`/results/runs/${current.run_id}`);
  };
  useEffect(() => {
    if (groupMode) return;
    return observeInvestigationJobs({
      runner,
      kind: jobKind,
      jobId: pendingIntent?.jobId,
      onUpdate: ({ job: current, busy }) => {
        setJob(current);
        if (pendingIntent?.jobId === current.job_id && !busy) {
          retainIntent(null);
          if (!pendingIntent.sample) openJobResults(current);
          else if (current.status === "completed") setSampleResultId(current.run_id);
        }
      },
      onError: (error) => setLoadError(error.message),
    });
  }, [runner, jobKind, groupMode, pendingIntent?.jobId]);
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
    if (running || inFlight.current) return;
    if (investigation && (!execution.valid || !caseId || (attacked && !attack)))
      return;
    inFlight.current = true;
    const reportRun = investigation ? onRunStart("single") : null;
    setSubmitting(true);
    setSampleResultId(null);
    setLoadError("");
    try {
      if (executionMode === executionModes.campaign) {
        const model = providerModels[session?.model];
        const campaign = pendingIntent?.campaign || await runner.createCampaign({
          provider: session?.model,
          model,
          credentialId: session.credentialId,
        });
        if (!mounted.current) return;
        const intent = pendingIntent?.intent || crypto.randomUUID();
        const excludedFiles = campaign.excluded_files || [];
        retainIntent({ intent, campaign });
        if (!pendingIntent?.campaign && excludedFiles.length) return;
        const accepted = await runner.executeCampaign(campaign.campaign_id, intent, excludedFiles);
        if (!mounted.current) return;
        retainIntent({ intent, campaign, jobId: accepted.job_id });
        setJob(accepted);
        if (accepted.status !== "queued" && accepted.status !== "active") {
          retainIntent(null);
          openJobResults(accepted);
        }
      } else if (investigation) {
        const currentCases = await runner.listInvestigationCases();
        if (!mounted.current) {
          reportRun(null);
          return;
        }
        const current = currentCases.find(item => item.case_id === caseId);
        const selected = cases.find(item => item.case_id === caseId);
        if (!current || current.case_version !== selected?.case_version) {
          setCases(currentCases);
          if (!current) setCaseId("");
          throw new Error("Research case version changed or is unavailable. Review the refreshed case selection before running again.");
        }
        const request = {
          caseId,
          mode: condition,
          attackFamily: attacked ? attackFamily : undefined,
          sessionId: execution.configuration?.id || "",
          provider: execution.provider,
          model: execution.model,
          credentialId: execution.credentialId,
        };
        const signature = JSON.stringify(request);
        if (pendingIntent && pendingIntent.signature !== signature && !pendingIntent.jobId) throw new Error('A submission has an uncertain response. Restore its selections and retry the same intent before starting different work.');
        const intent = pendingIntent?.signature === signature ? pendingIntent.intent : crypto.randomUUID();
        const sample = sampleRun || (pendingIntent?.signature === signature && pendingIntent.sample);
        retainIntent({intent, signature, sample});
        const accepted = await runner.runInvestigation({...request, intent});
        reportRun(accepted);
        if (!mounted.current) return;
        retainIntent({intent, signature, sample, jobId: accepted.job_id});
        setJob(accepted);
        if (accepted.run_id) {
          retainIntent(null);
          if (!sample) openJobResults(accepted);
          else if (accepted.status === "completed") setSampleResultId(accepted.run_id);
        }
      } else {
        const request = {
          sessionId: session.id,
          credentialId: session.credentialId,
          scenarioId: selectedScenario?.scenario_id,
          mode,
          provider: session?.model,
          model: providerModels[session?.model],
        };
        const signature = JSON.stringify(request);
        if (pendingIntent && pendingIntent.signature !== signature && !pendingIntent.jobId) throw new Error("Restore the previous selections to retry the pending submission.");
        const intent = pendingIntent?.signature === signature ? pendingIntent.intent : crypto.randomUUID();
        retainIntent({ intent, signature });
        const accepted = await runner.runExperiment({ ...request, intent });
        if (!mounted.current) return;
        retainIntent({ intent, signature, jobId: accepted.job_id });
        setJob(accepted);
        if (accepted.run_id) {
          retainIntent(null);
          openJobResults(accepted);
        }
      }
    } catch (error) {
      reportRun?.(null, error.message);
      if (!mounted.current) return;
      setLoadError(error.message);
      if ([400, 404, 409, 422].includes(error.status) &&
          !(error.status === 409 && executionMode === executionModes.campaign)) retainIntent(null);
    } finally {
      inFlight.current = false;
      if (mounted.current) setSubmitting(false);
    }
  };
  const batch = executionMode === executionModes.campaign;
  const LaunchButton = investigation ? PendingButton : "button";
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
                : modelOptions[session?.model]}
          </p>
        </div>
      </section>
      {!groupMode && job && <div className="card investigation-job-status" role="status" aria-label={investigation ? "Investigation job" : "Metadata job"}>
          <div>
            <p>{investigation ? "Investigation" : job.campaign_id ? "Campaign" : "Metadata experiment"} {job.status === "active" ? "running" : job.status}. {sampleResultId ? "" : `Job ${job.job_id}`}</p>
            {['queued', 'active'].includes(job.status) && <p>You can leave this page and return to follow this job.</p>}
            {job.status === 'interrupted' && <p>The provider outcome is uncertain. This job will not replay automatically. Starting another investigation may incur a new provider charge.</p>}
            {job.status === 'failed' && <p>The attempt failed. {job.error_category}</p>}
          </div>
          {job.run_id && <button ref={savedRunButton} className={sampleResultId ? "run-button" : "small-button"} type="button" onClick={() => openJobResults(job)}>{investigation ? "View saved run" : "Open metadata result"}</button>}
          {job.campaign_id && <button type="button" onClick={() => openJobResults(job)}>Open campaign results</button>}
        </div>}
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
      {(groupMode || investigation) && (
        <p className="run-destination">
          Single run investigates one case under one condition. Matched group compares conditions using the same case and model.
        </p>
      )}
      {!groupMode && investigation && (
        <section className="card sample-investigation" aria-label="Sample investigation">
          <div>
            <h2>Start with a sample investigation</h2>
            <p>Investigate one synthetic case with the offline model. No API key required.</p>
            {sampleRun && !sampleResultId && <p role="status">Sample ready to review below.</p>}
            {!casesLoading && !sampleAvailable && <p>The sample case is unavailable. You can choose another available case below.</p>}
          </div>
          <button className={sampleRun ? "small-button" : "run-button"} type="button" disabled={running || !sampleAvailable} onClick={prepareSample}>
            Try a sample investigation
          </button>
        </section>
      )}
      {running && (
        <p role="status">
          {investigation && !groupMode
            ? 'Investigation job in progress. You can return to this page to follow its saved status.'
            : groupMode ? 'Matched group job in progress. You can leave and return to follow its saved progress.' : `${batch ? 'Campaign' : 'Experiment'} running. Results will open when this request finishes.`}
        </p>
      )}
      {loadError && (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      )}
      {groupMode ? (
        <GroupLauncher
          onRunningChange={setGroupRunning}
          runner={runner}
          selection={executionSelection}
          onSelectionChange={onExecutionChange}
          executionOptions={executionOptions}
          onResults={onResults}
          onRunStart={onRunStart}
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
                            <CaseOptions cases={cases} />
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
                {batch && Boolean(pendingIntent?.campaign?.excluded_files?.length) && (
                  <p role="status">Invalid scenario files excluded: {pendingIntent.campaign.excluded_files.join(", ")}.</p>
                )}
                {investigation && !running && (
                  <p className="run-destination">
                    {casesLoading ? "Loading cases…" : !caseId
                      ? "Select an available synthetic case to run an investigation."
                      : !execution.valid
                        ? "Select Scripted offline or choose a configuration with a valid API key."
                        : attacked && !attack
                          ? "Select an available option for this condition."
                          : "When the run finishes, you can open its saved result."}
                  </p>
                )}
                <LaunchButton
                  className="run-button"
                  {...(investigation && { pending: submitting })}
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
                  {running && !(investigation && submitting)
                    ? "Running…"
                    : batch
                      ? pendingIntent?.campaign?.excluded_files?.length
                        ? "Run usable poisoned scenarios"
                        : "Run all poisoned scenarios"
                      : investigation
                        ? sampleRun ? "Run investigation" : "Run MCP investigation"
                        : "Run new experiment"}
                  <Icon name="arrow" size={14} />
                </LaunchButton>
                {investigation && submitting && <p role="status">Submitting investigation…</p>}
                {!investigation && <p className="run-destination">
                  Follow the saved job status here, then open its exact result in Results.
                </p>}
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
