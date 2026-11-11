import React from "react";
import { AuthenticatedHeader } from "./AuthenticatedHeader";

export function Sidebar({ active, onSessions, onDashboard, onScenarios, visible = true, user, auth, onSignedOut }) {
  if (!visible || active === "sessions") return null;
  return <div className="workspace-chrome">
    <AuthenticatedHeader user={user} auth={auth} onSignedOut={onSignedOut} subtitle="Synthetic research workspace" />
    <nav className="workspace-navigation" aria-label="Workspace navigation">
      <button onClick={onSessions}>Sessions</button>
      <button aria-current={active === "dashboard" ? "page" : undefined} onClick={onDashboard}>Experiments</button>
      <button aria-current={active === "scenarios" ? "page" : undefined} onClick={onScenarios}>Scenarios</button>
    </nav>
  </div>;
}
