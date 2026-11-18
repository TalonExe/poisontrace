import React, { useEffect, useState } from "react";
import { Sidebar } from "../../components/layout/Sidebar";
import { CaseGroundTruthEditor } from "./CaseGroundTruthEditor";

export function ResearchCaseAuthoring({
  runner,
  user,
  auth,
  onSignOut,
  onSessions,
  onDashboard,
  onResults,
  onScenarios,
}) {
  const [cases, setCases] = useState([]);
  const [caseId, setCaseId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    runner
      .listInvestigationCases()
      .then((items) => {
        if (!active) return;
        setCases(items);
        setCaseId((current) =>
          items.some((item) => item.case_id === current)
            ? current
            : items[0]?.case_id || "",
        );
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
  return (
    <main className="app-shell dashboard-page">
      <Sidebar
        active="research-cases"
        user={user}
        auth={auth}
        onSignedOut={onSignOut}
        onSessions={onSessions}
        onDashboard={onDashboard}
        onResults={onResults}
        onScenarios={onScenarios}
      />
      <section className="welcome">
        <div>
          <h1>MCP research case authoring</h1>
          <p>
            Advanced fixture authoring. Select a research case to revise its
            expected decision and attacker targets.
          </p>
          <button
            className="text-button"
            disabled={saving}
            onClick={() => onDashboard("/dashboard")}
          >
            Return to Experiment
          </button>
        </div>
      </section>
      <article className="card">
        <h2>MCP research cases</h2>
        <p>
          These read-only MCP evidence cases are separate from Metadata
          scenarios (YAML). Saving ground truth creates a new case version.
          Existing results and group reruns retain their saved labels, evidence
          and targets. Experiment reloads current versions when you return.
        </p>
        <p>
          Identity, evidence, attack allocation and payload definitions are
          outside this editor.
        </p>
        {loading && <p role="status">Loading research cases…</p>}
        {error && (
          <p className="form-error" role="alert">
            {error}{" "}
            <button
              className="text-button"
              onClick={() => setRetry((n) => n + 1)}
            >
              Reload research cases
            </button>
          </p>
        )}
        {!loading && !error && !cases.length && (
          <p>No MCP research cases available.</p>
        )}
        <label className="field">
          <span>Research case</span>
          <select
            value={caseId}
            disabled={loading || saving || !cases.length}
            onChange={(e) => setCaseId(e.target.value)}
          >
            {cases.map((item) => (
              <option key={item.case_id} value={item.case_id}>
                {item.name} · {item.case_id} · v{item.case_version}
              </option>
            ))}
          </select>
        </label>
        {caseId && !loading && !error && (
          <CaseGroundTruthEditor
            key={caseId}
            runner={runner}
            caseId={caseId}
            onPendingChange={setSaving}
            onSaved={(value) =>
              setCases((items) =>
                items.map((item) =>
                  item.case_id === value.case_id ? { ...item, ...value } : item,
                ),
              )
            }
          />
        )}
        <button className="text-button" disabled={saving} onClick={onScenarios}>
          Open Metadata scenarios (YAML)
        </button>
      </article>
    </main>
  );
}
