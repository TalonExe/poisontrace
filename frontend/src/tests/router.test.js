import assert from "node:assert/strict";
import test from "node:test";
import { createRouter, normalizePath, routes } from "../utils/router.js";

test("normalizes supported routes and sends unknown paths to login", () => {
  assert.equal(normalizePath("/dashboard?session=one"), routes.dashboard);
  assert.equal(normalizePath("/"), routes.login);
  assert.equal(normalizePath("/sessions/"), routes.sessions);
  assert.equal(normalizePath("/missing"), routes.login);
  assert.equal(normalizePath("/scenarios/new"), routes.scenarioNew);
  assert.equal(normalizePath("/scenarios/001"), "/scenarios/001");
});

test("TanStack Router exposes the supported route tree for navigation", () => {
  const router = createRouter({ initialEntries: ["/login"] });
  assert.equal(router.current(), routes.login);
  assert.ok(router.tanStackRouter.routesByPath[routes.dashboard]);
  assert.equal(typeof router.tanStackRouter.navigate, "function");
});

test("browser root is replaced with the login route", () => {
  const router = createRouter({ initialEntries: ["/"] });
  assert.equal(router.current(), routes.login);
  assert.equal(router.tanStackRouter.history.location.pathname, routes.login);
});

test("memory history navigation changes the current supported route", async () => {
  const router = createRouter({ initialEntries: ["/login"] });

  await router.navigate(routes.sessions);

  assert.equal(router.current(), routes.sessions);
  assert.equal(
    router.tanStackRouter.history.location.pathname,
    routes.sessions,
  );
});

test("replace navigation does not leave the replaced route in memory history", async () => {
  const router = createRouter({ initialEntries: ["/login"] });

  await router.navigate(routes.sessions);
  await router.navigate(routes.dashboard, { replace: true });
  router.tanStackRouter.history.back();
  await router.tanStackRouter.load();

  assert.equal(router.current(), routes.login);
});
