import React from "react";
import { Link } from "@tanstack/react-router";
import { useContentReadOnly } from "../ContentPolicy";
import { AuthenticatedHeader } from "./AuthenticatedHeader";
import { Icon } from "../common/Ui";

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
  const readOnly = useContentReadOnly();
  if (!visible) return null;
  return (
    <div className="workspace-chrome">
      <AuthenticatedHeader
        user={user}
        auth={auth}
        onSignedOut={onSignedOut}
        subtitle="Synthetic research workspace"
        accountAction={onSessions && (
          <button
            type="button"
            className="profile-settings-button"
            aria-label="Settings"
            aria-current={active === "sessions" ? "page" : undefined}
            title="Settings"
            onClick={onSessions}
          >
            <Icon name="settings" size={19} />
          </button>
        )}
      />
      <nav className="workspace-navigation" aria-label="Workspace navigation">
        <Link to="/activity" activeOptions={{ exact: true }}>Dashboard</Link>
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
            {readOnly ? "MCP research cases" : "MCP research case authoring"}
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
