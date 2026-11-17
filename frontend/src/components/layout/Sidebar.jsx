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
        <button
          aria-current={active === "scenarios" ? "page" : undefined}
          onClick={onScenarios}
        >
          Scenarios
        </button>
      </nav>
    </div>
  );
}
