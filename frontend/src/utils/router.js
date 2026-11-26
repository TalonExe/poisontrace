import {
  createBrowserHistory,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter as createTanStackRouter,
  useRouterState,
} from "@tanstack/react-router";
import { createElement } from "react";
import { Outlet } from "@tanstack/react-router";

export const routes = Object.freeze({
  login: "/login",
  activity: "/activity",
  dashboard: "/dashboard",
  researchCases: "/research-cases",
  single: "/dashboard/single",
  metadata: "/dashboard/metadata",
  metadataCampaign: "/dashboard/campaign",
  results: "/results",
  resultRuns: "/results/runs",
  resultGroups: "/results/groups",
  resultCampaigns: "/results/campaigns",
  sessions: "/sessions",
  settings: "/settings",
  scenarios: "/scenarios",
  scenarioNew: "/scenarios/new",
  admin: "/admin",
  adminUsers: "/admin/users",
});

export function normalizePath(pathname = "/") {
  const path = pathname.split("?")[0].replace(/\/+$/, "") || "/";
  if (Object.values(routes).includes(path)) return path;
  if (/^\/scenarios\/[^/]+$/.test(path)) return path;
  if (/^\/results\/runs\/[1-9]\d*$/.test(path)) return path;
  if (/^\/results\/groups\/[^/]+$/.test(path)) return path;
  if (/^\/results\/campaigns\/[^/]+$/.test(path)) return path;
  return routes.login;
}

export function createRouter({
  windowRef = globalThis.window,
  initialEntries,
  renderRoute,
} = {}) {
  function RouteContent() {
    // Parameter-only navigation must refresh the selected persisted record too.
    useRouterState({ select: (state) => state.location.href });
    return renderRoute?.() || null;
  }
  const rootRoute = createRootRoute({
    component: () => createElement(Outlet),
    notFoundComponent: () => null,
  });
  const routePaths = [
    ...Object.values(routes),
    "/scenarios/$scenarioId",
    "/results/runs/$runId",
    "/results/campaigns/$campaignId",
    "/results/groups/$groupId",
  ];
  const routeTree = rootRoute.addChildren(
    routePaths.map((path) =>
      createRoute({
        getParentRoute: () => rootRoute,
        path,
        component: RouteContent,
      }),
    ),
  );
  const history = initialEntries
    ? createMemoryHistory({ initialEntries })
    : createBrowserHistory({ window: windowRef });
  if (history.location.pathname === "/") history.replace(routes.login);
  const tanStackRouter = createTanStackRouter({ routeTree, history });
  const ready = tanStackRouter.load();

  return {
    current: () => normalizePath(tanStackRouter.state.location.pathname),
    search: () => tanStackRouter.state.location.searchStr,
    navigate(path, { replace = false } = {}) {
      const next = normalizePath(path);
      const query = path.indexOf("?");
      return ready.then(() => {
        const location = tanStackRouter.buildLocation({ to: next });
        const href = location.pathname + (query === -1 ? "" : path.slice(query));
        if (replace) history.replace(href);
        else history.push(href);
        return tanStackRouter.load();
      });
    },
    tanStackRouter,
  };
}
