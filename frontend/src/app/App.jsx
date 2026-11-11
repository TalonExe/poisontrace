import React, { useEffect, useMemo, useRef, useState } from "react";
import { RouterProvider } from "@tanstack/react-router";
import { createAuthApi } from "../features/auth/api/authApi";
import { createRunnerAdapter } from "../utils/webAdapter";
import { loadSessions } from "../utils/sessions";
import { createRouter, routes } from "../utils/router";
import { LoginRoute } from "../routes/login";
import { SessionsRoute } from "../routes/sessions/index";
import { DashboardRoute } from "../routes/dashboard";
import { ScenarioLibraryRoute } from "../routes/scenarios/index";
import { NewScenarioRoute } from "../routes/scenarios/new";
import { ScenarioDetailRoute } from "../routes/scenarios/$scenarioId";
import { Sidebar } from "../components/layout/Sidebar";
import { AdminUsers } from "../features/admin/AdminUsers";
import { createAdminApi } from "../features/admin/api/adminApi";

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
  const [activeSession, setActiveSession] = useState(() =>
    window.location.pathname === routes.dashboard
      ? loadSessions(window.localStorage)[0]
      : null,
  );
  const [checking, setChecking] = useState(true);
  const [accessError, setAccessError] = useState("");
  const [accessAttempt, setAccessAttempt] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    setAccessError("");
    auth.getSession().then((value) => {
      setUser(value);
      setChecking(false);
      if (!value && router.current() !== routes.login)
        router.navigate(routes.login, { replace: true });
      if (value && router.current() === routes.login)
        router.navigate(value.redirect || (value.role === "superadmin" ? routes.adminUsers : routes.sessions), { replace: true });
    }).catch(() => {
      setAccessError("Unable to check your session. Check that the local API is running, then retry.");
      setChecking(false);
    });
  }, [auth, router, accessAttempt]);

  const completeSignOut = () => {
    setUser(null);
    setActiveSession(null);
    router.navigate(routes.login, { replace: true });
  };
  const signOut = async () => {
    await auth.signOut();
    completeSignOut();
  };
  const openSession = (session) => {
    setActiveSession(session);
    router.navigate(routes.dashboard);
  };
  const openSessions = () => {
    setActiveSession(null);
    router.navigate(routes.sessions);
  };
  const openScenarios = () => router.navigate(routes.scenarios);

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
        <LoginRoute
          auth={auth}
          onAuthenticated={(session) => {
            setUser(session);
            router.navigate(session.redirect || (session.role === "superadmin" ? routes.adminUsers : routes.sessions), { replace: true });
          }}
        />
      );
    if ((router.current() === routes.admin || router.current() === routes.adminUsers) && user.role !== "superadmin")
      return <ForbiddenState onHome={() => router.navigate(user.role === "superadmin" ? routes.adminUsers : routes.sessions)} onSignOut={signOut} />;
    if (user.role === "superadmin" && router.current() === routes.admin)
      return <AdminRedirect onRedirect={() => router.navigate(routes.adminUsers, { replace: true })} />;
    if (user.role === "superadmin" && router.current() !== routes.adminUsers)
      return <ForbiddenState onHome={() => router.navigate(user.role === "superadmin" ? routes.adminUsers : routes.sessions)} onSignOut={signOut} />;
    if (router.current() === routes.adminUsers)
      return <AdminUsers api={adminApi} user={user} auth={auth} onSignedOut={completeSignOut} />;
    const path = router.current();
    if (path === routes.scenarios)
      return (
        <>
          <Sidebar
            user={user}
            auth={auth}
            onSignedOut={completeSignOut}
            open={sidebarOpen}
            active="scenarios"
            onClose={() => setSidebarOpen(false)}
            onSessions={openSessions}
            onDashboard={() => router.navigate(routes.dashboard)}
            onScenarios={() => {}}
          />
          <ScenarioLibraryRoute
            adapter={runner}
            onOpen={(id) => router.navigate(`/scenarios/${id}`)}
            onNew={() => router.navigate(routes.scenarioNew)}
            onDashboard={() => router.navigate(routes.dashboard)}
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
            open={sidebarOpen}
            active="scenarios"
            onClose={() => setSidebarOpen(false)}
            onSessions={openSessions}
            onDashboard={() => router.navigate(routes.dashboard)}
            onScenarios={openScenarios}
          />
          <NewScenarioRoute
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
            open={sidebarOpen}
            active="scenarios"
            onClose={() => setSidebarOpen(false)}
            onSessions={openSessions}
            onDashboard={() => router.navigate(routes.dashboard)}
            onScenarios={openScenarios}
          />
          <ScenarioDetailRoute
            scenarioId={path.split("/").pop()}
            adapter={runner}
            onBack={() => router.navigate(routes.scenarios)}
            onCreated={(id) => router.navigate(`/scenarios/${id}`)}
            onDeleted={() => router.navigate(routes.scenarios)}
            onSignOut={signOut}
          />
        </>
      );
    if (path === routes.dashboard && activeSession)
      return (
          <DashboardRoute
          user={user}
          auth={auth}
          onSignOut={completeSignOut}
          session={activeSession}
          runner={runner}
          onSignedOut={openSessions}
          onScenarios={openScenarios}
        />
      );
    return (
      <SessionsRoute
        auth={auth}
        user={user}
        runner={runner}
        onSignOut={completeSignOut}
        onScenarios={openScenarios}
        onOpenSession={openSession}
      />
    );
  };
  useEffect(() => {
    router.tanStackRouter.invalidate();
  }, [router, checking, user, activeSession, accessError]);
  const renderKey = `${checking ? "checking" : user ? "authenticated" : "signed-out"}:${activeSession?.id || "none"}`;
  return <RouterProvider key={renderKey} router={router.tanStackRouter} />;
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
