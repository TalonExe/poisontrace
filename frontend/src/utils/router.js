import {
  createBrowserHistory,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter as createTanStackRouter,
} from "@tanstack/react-router";
import { createElement } from "react";
import { Outlet } from "@tanstack/react-router";

export const routes = Object.freeze({
  login: "/login",
  dashboard: "/dashboard",
  sessions: "/sessions",
  scenarios: "/scenarios",
  scenarioNew: "/scenarios/new",
  admin: "/admin",
  adminUsers: "/admin/users",
});

export function normalizePath(pathname = "/") {
  const path = pathname.split("?")[0].replace(/\/+$/, "") || "/";
  if (Object.values(routes).includes(path)) return path;
  if (/^\/scenarios\/[^/]+$/.test(path)) return path;
  return routes.login;
}

export function createRouter({
  windowRef = globalThis.window,
  initialEntries,
  renderRoute,
} = {}) {
  const rootRoute = createRootRoute({
    component: () => createElement(Outlet),
    notFoundComponent: () => null,
  });
  const routePaths = [...Object.values(routes), "/scenarios/$scenarioId"];
  const routeTree = rootRoute.addChildren(
    routePaths.map((path) =>
      createRoute({
        getParentRoute: () => rootRoute,
        path,
        component: () => renderRoute?.() || null,
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
    navigate(path, { replace = false } = {}) {
      const next = normalizePath(path);
      return ready.then(() => {
        const location = tanStackRouter.buildLocation({ to: next });
        if (replace) history.replace(location.href);
        else history.push(location.href);
        return tanStackRouter.load();
      });
    },
    tanStackRouter,
  };
}
