import React, { useEffect, useMemo, useRef, useState } from "react";
import { RouterProvider } from "@tanstack/react-router";
import { createAuthApi } from "../features/auth/api/authApi";
import { createRunnerAdapter } from "../utils/webAdapter";
import { EXECUTION_STORAGE_KEY } from "../utils/executionSelection";
import { loadSessions } from "../utils/sessions";
import { setWorkspaceAccount, workspaceStorage } from "../utils/workspaceStorage";
import { createRouter, routes } from "../utils/router";
import { LoginPage } from "../pages/LoginPage";
import { SessionWorkspace } from "../features/sessions/SessionWorkspace";
import { ResearchCaseAuthoring } from "../features/dashboard/ResearchCaseAuthoring";
import { ExperimentDashboard } from "../features/dashboard/ExperimentDashboard";
import { AnalystDashboard } from "../features/dashboard/AnalystDashboard";
import { RunNotification } from "../features/dashboard/RunNotification";
import { ResultsPage } from "../features/results/ResultsPage";
import { ScenarioLibrary, ScenarioEditor } from "../features/scenarios/ScenarioFeaturePages";
import { Sidebar } from "../components/layout/Sidebar";
import { ContentReadOnlyContext } from "../components/ContentPolicy";
import { AdminUsers } from "../features/admin/AdminUsers";
import { createAdminApi } from "../features/admin/api/adminApi";
import {advanceSessionGeneration, sessionGeneration} from "../lib/http/sessionExpiry.js";

export function App() {
  const auth = useMemo(() => createAuthApi(), []);
  const runner = useMemo(() => createRunnerAdapter(), []);
  const adminApi = useMemo(() => createAdminApi(), []);
  const routeRenderer = useRef(null);
  const router = useMemo(
    () => createRouter({ renderRoute: () => routeRenderer.current?.() }),
    [],
  );
  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [sessionNotice, setSessionNotice] = useState("");
  const [runNotice, setRunNotice] = useState(null);
  const acceptUser = (value) => {
    advanceSessionGeneration();
    setRunNotice(null);
    setWorkspaceAccount(value);
    setActiveSession(value && [routes.dashboard, routes.single, routes.metadata, routes.metadataCampaign].includes(window.location.pathname)
      ? loadSessions(workspaceStorage(window.localStorage))[0] : null);
    setUser(value);
  };
  const selectExecution = (selection) => {
    workspaceStorage(window.localStorage).setItem(EXECUTION_STORAGE_KEY, selection);
  };
  const [checking, setChecking] = useState(true);
  const [accessError, setAccessError] = useState("");
  const [accessAttempt, setAccessAttempt] = useState(0);

  useEffect(() => {
    const endSession = () => {
      acceptUser(null);
      setSessionNotice("Your session ended. Sign in again to continue.");
      router.navigate(routes.login, {replace:true});
    };
    window.addEventListener('poisontrace-session-ended', endSession);
    return () => window.removeEventListener('poisontrace-session-ended', endSession);
  }, [router]);

  useEffect(() => {
    setAccessError("");
    auth.getSession().then((value) => {
      acceptUser(value);
      setChecking(false);
      if (!value && router.current() !== routes.login)
        router.navigate(routes.login, { replace: true });
      if (value && router.current() === routes.login)
        router.navigate(value.role === "superadmin" ? routes.adminUsers : routes.activity, { replace: true });
    }).catch(() => {
      setAccessError("Unable to check your session. Check that the local API is running, then retry.");
      setChecking(false);
    });
  }, [auth, router, accessAttempt]);

  useEffect(() => {
    let active = true;
    const refreshIdentity = () => {
      const generation = sessionGeneration();
      auth.getSession().then((value) => {
        if (!active || generation !== sessionGeneration()) return;
        if (value?.id !== user?.id || value?.username !== user?.username || value?.role !== user?.role) {
          acceptUser(value);
          if (!value) {
            setSessionNotice("Your session ended. Sign in again to continue.");
            router.navigate(routes.login, { replace: true });
          }
        }
      }).catch(() => {
        if (active) setAccessError("Unable to check your session. Check that the local API is running, then retry.");
      });
    };
    window.addEventListener('focus', refreshIdentity);
    return () => { active = false; window.removeEventListener('focus', refreshIdentity); };
  }, [auth, router, user]);

  const completeSignOut = () => {
    acceptUser(null);
    setSessionNotice("");
    setActiveSession(null);
    router.navigate(routes.login, { replace: true });
  };
  const signOut = async () => {
    await auth.signOut();
    completeSignOut();
  };
  const openSession = (session) => {
    setActiveSession(session);
    selectExecution(`config:${session.id}`);
    router.navigate(routes.dashboard);
  };
  const openSessions = () => {
    setActiveSession(null);
    router.navigate(routes.settings);
  };
  const openDashboard = (target) => router.navigate(typeof target === "string" ? target : routes.dashboard);
  const openScenarios = () => router.navigate(routes.scenarios);
  const openResults = (path = routes.resultGroups) => router.navigate(path);
  const trackRun = (kind) => {
    const generation = sessionGeneration();
    const submission = {};
    setRunNotice({ kind, submission });
    return (job, error) => {
      if (generation !== sessionGeneration()) return;
      setRunNotice((current) => current?.submission === submission
        ? (job || error ? { ...current, job, error } : null)
        : current);
    };
  };

  routeRenderer.current = () => {
    if (accessError) return <main className="login-shell"><section className="login-panel"><h1>Connection unavailable</h1><p role="alert">{accessError}</p><button className="run-button" onClick={() => { setChecking(true); setAccessAttempt((value) => value + 1); }}>Retry connection</button></section></main>;
    if (checking)
      return (
        <main className="login-shell loading-screen">
          <span className="status-dot" />
          Checking local access…
        </main>
      );
    if (!user)
      return (
        <LoginPage
          auth={auth}
          notice={sessionNotice}
          onAuthenticated={(session) => {
            setSessionNotice("");
            acceptUser(session);
            router.navigate(session.role === "superadmin" ? routes.adminUsers : routes.activity, { replace: true });
          }}
        />
      );
    if ((router.current() === routes.admin || router.current() === routes.adminUsers) && user.role !== "superadmin")
      return <ForbiddenState onHome={() => router.navigate(routes.activity)} onSignOut={signOut} />;
    if (user.role === "superadmin" && router.current() === routes.admin)
      return <AdminRedirect onRedirect={() => router.navigate(routes.adminUsers, { replace: true })} />;
    if (user.role === "superadmin" && router.current() !== routes.adminUsers)
      return <ForbiddenState onHome={() => router.navigate(routes.adminUsers)} onSignOut={signOut} />;
    if (router.current() === routes.adminUsers)
      return <AdminUsers api={adminApi} user={user} auth={auth} onSignedOut={completeSignOut} />;
    const path = router.current();
    if (path === routes.activity)
      return <AnalystDashboard runner={runner} user={user} auth={auth} onSignedOut={completeSignOut} onSessions={openSessions} onDashboard={openDashboard} onResults={() => openResults()} onScenarios={openScenarios} onNavigate={openResults} />;
    if (path === routes.results || path.startsWith("/results/"))
      return <ResultsPage path={path} search={router.search()} runner={runner} user={user} auth={auth} onSignOut={completeSignOut} onSessions={openSessions} onDashboard={openDashboard} onScenarios={openScenarios} onNavigate={openResults} />;
    if (path === routes.researchCases)
      return <ResearchCaseAuthoring runner={runner} user={user} auth={auth} onSignOut={completeSignOut} onSessions={openSessions} onDashboard={openDashboard} onResults={() => openResults()} onScenarios={openScenarios} />;
    if (path === routes.scenarios)
      return (
        <>
          <Sidebar
            user={user}
            auth={auth}
            onSignedOut={completeSignOut}
            active="scenarios"
            onSessions={openSessions}
            onDashboard={openDashboard}
            onResults={() => openResults()}
            onScenarios={() => {}}
          />
          <ScenarioLibrary
            adapter={runner}
            onOpen={(id) => router.navigate(`/scenarios/${id}`)}
            onNew={() => router.navigate(routes.scenarioNew)}
            onDashboard={openDashboard}
            onSignOut={signOut}
          />
        </>
      );
    if (path === routes.scenarioNew)
      return (
        <>
          <Sidebar
            user={user}
            auth={auth}
            onSignedOut={completeSignOut}
            active="scenarios"
            onSessions={openSessions}
            onDashboard={openDashboard}
            onResults={() => openResults()}
            onScenarios={openScenarios}
          />
          <ScenarioEditor
            key="scenario-new"
            isNew
            adapter={runner}
            onBack={() => router.navigate(routes.scenarios)}
            onCreated={(id) => router.navigate(`/scenarios/${id}`)}
            onDeleted={() => router.navigate(routes.scenarios)}
            onSignOut={signOut}
          />
        </>
      );
    if (path.startsWith("/scenarios/"))
      return (
        <>
          <Sidebar
            user={user}
            auth={auth}
            onSignedOut={completeSignOut}
            active="scenarios"
            onSessions={openSessions}
            onDashboard={openDashboard}
            onResults={() => openResults()}
            onScenarios={openScenarios}
          />
          <ScenarioEditor
            key="scenario-detail"
            isNew={false}
            scenarioId={path.split("/").pop()}
            adapter={runner}
            onBack={() => router.navigate(routes.scenarios)}
            onCreated={(id) => router.navigate(`/scenarios/${id}`)}
            onDeleted={() => router.navigate(routes.scenarios)}
            onSignOut={signOut}
          />
        </>
      );
    if ([routes.dashboard, routes.single, routes.metadata, routes.metadataCampaign].includes(path) && (activeSession || path === routes.dashboard || path === routes.single))
      return (
          <ExperimentDashboard
          key={path}
          entry={path}
          onDashboard={openDashboard}
          user={user}
          auth={auth}
          onSignOut={completeSignOut}
          session={activeSession}
          runner={runner}
          onSignedOut={openSessions}
          onScenarios={openScenarios}
          onResults={openResults}
          onRunStart={trackRun}
        />
      );
    return (
      <SessionWorkspace
        auth={auth}
        user={user}
        runner={runner}
        onSignOut={completeSignOut}
        onScenarios={openScenarios}
        onResults={() => openResults()}
        onDashboard={openDashboard}
        onOpenSession={openSession}
      />
    );
  };
  useEffect(() => {
    router.tanStackRouter.invalidate();
  }, [router, checking, user, activeSession, accessError]);
  const renderKey = `${checking ? "checking" : user ? `${user.role}:${user.id ?? user.username}` : "signed-out"}:${activeSession?.id || "none"}`;
  return <ContentReadOnlyContext.Provider value={user?.content_read_only === true}>
    <RouterProvider key={renderKey} router={router.tanStackRouter} />
    {!checking && user?.role === "analyst" && <RunNotification
      key={user.id ?? user.username}
      runner={runner}
      notice={runNotice}
      setNotice={setRunNotice}
      onResults={openResults}
    />}
  </ContentReadOnlyContext.Provider>;
}

function ForbiddenState({ onHome, onSignOut }) {
  return <main className="login-shell"><section className="login-panel"><h1>403 Forbidden</h1><p className="login-copy">Your account is authenticated but does not have access to this workspace.</p><button className="run-button" onClick={onHome}>Go to my workspace</button><button className="text-button" onClick={onSignOut}>Sign out</button></section></main>;
}

function AdminRedirect({ onRedirect }) {
  React.useEffect(() => {
    onRedirect();
  }, [onRedirect]);
  return <main className="login-shell loading-screen">Opening user management…</main>;
}
