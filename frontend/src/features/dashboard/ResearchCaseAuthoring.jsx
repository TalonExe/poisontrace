import { useContentReadOnly, readOnlyContentMessage } from "../../components/ContentPolicy";
import React, { useEffect, useState } from "react";
import { Sidebar } from "../../components/layout/Sidebar";
import { CaseGroundTruthEditor } from "./CaseGroundTruthEditor";
import { CaseOptions } from "./CaseOptions";

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
  const readOnly = useContentReadOnly();
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
          <h1>{readOnly ? "MCP research cases" : "MCP research case authoring"}</h1>
          <p>
            {readOnly ? readOnlyContentMessage : "Advanced fixture authoring. Select a research case to revise its expected decision and attacker targets."}
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
        <h2>{readOnly ? "Curated cases" : "MCP research cases"}</h2>
        <p>
          These read-only MCP evidence cases are separate from Metadata
          scenarios (YAML). {readOnly ? "Select a case to inspect its curated ground truth." : "Saving ground truth creates a new case version."}{" "}
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
            <CaseOptions cases={cases} showCaseId />
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
