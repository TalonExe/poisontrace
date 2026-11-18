import React from "react";
import { AuthenticatedHeader } from "./AuthenticatedHeader";

export function Sidebar({
  active,
  onSessions,
  onDashboard,
  onResults,
  onScenarios,
  visible = true,
  user,
  auth,
  onSignedOut,
}) {
  if (!visible) return null;
  return (
    <div className="workspace-chrome">
      <AuthenticatedHeader
        user={user}
        auth={auth}
        onSignedOut={onSignedOut}
        subtitle="Synthetic research workspace"
      />
      <nav className="workspace-navigation" aria-label="Workspace navigation">
        <button
          aria-current={active === "sessions" ? "page" : undefined}
          onClick={onSessions}
        >
          Configurations
        </button>
        <button
          aria-current={active === "dashboard" ? "page" : undefined}
          onClick={onDashboard}
        >
          Experiment
        </button>
        <button
          aria-current={active === "results" ? "page" : undefined}
          onClick={onResults}
        >
          Results
        </button>
        <details className="advanced-navigation">
          <summary>Advanced</summary>
          <button aria-current={active === "research-cases" ? "page" : undefined} onClick={() => onDashboard("/research-cases")}>
            MCP research case authoring
          </button>
          <button onClick={() => onDashboard("/dashboard/metadata")}>
            Metadata experiments
          </button>
          <button onClick={() => onDashboard("/dashboard/campaign")}>
            Metadata campaigns
          </button>
          <button
            aria-current={active === "scenarios" ? "page" : undefined}
            onClick={onScenarios}
          >
            Metadata scenarios (YAML)
          </button>
        </details>
      </nav>
    </div>
  );
}
