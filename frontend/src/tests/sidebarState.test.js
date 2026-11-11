import assert from "node:assert/strict";
import test from "node:test";
import {
  activeSidebarPage,
  activeSidebarRoute,
  closeAfterNavigation,
  defaultSidebarOpen,
  drawerState,
} from "../utils/sidebarState.js";

test("desktop sidebar starts open and preserves the active page", () => {
  assert.equal(defaultSidebarOpen, true);
  assert.equal(activeSidebarPage("dashboard"), "dashboard");
  assert.equal(activeSidebarPage("scenarios"), "scenarios");
});

test("route state highlights only the authenticated workspace destinations", () => {
  assert.equal(activeSidebarRoute("/dashboard"), "dashboard");
  assert.equal(activeSidebarRoute("/scenarios"), "scenarios");
  assert.equal(activeSidebarRoute("/sessions"), "sessions");
  assert.equal(activeSidebarRoute("/unknown"), "sessions");
});

test("drawer actions open it and close it after navigation or dismissal", () => {
  assert.equal(drawerState(false, "open"), true);
  assert.equal(drawerState(true, "backdrop"), false);
  assert.equal(drawerState(true, "close"), false);
  assert.equal(drawerState(true, "navigate"), false);
});

test("navigation closes only the mobile drawer", () => {
  const mobile = { matchMedia: () => ({ matches: true }) };
  const desktop = { matchMedia: () => ({ matches: false }) };
  let closed = 0;
  closeAfterNavigation(() => {
    closed += 1;
  }, mobile);
  closeAfterNavigation(() => {
    closed += 1;
  }, desktop);
  assert.equal(closed, 1);
});
