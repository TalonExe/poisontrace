import assert from "node:assert/strict";
import test from "node:test";
import { createApiAuth, createLocalAuth, localDemoCredentials } from "../utils/auth.js";

function installWindow() {
  globalThis.window = { setTimeout: (callback) => callback() };
}

test("local auth starts signed out and accepts the demo account", async () => {
  installWindow();
  const auth = createLocalAuth();
  assert.equal(await auth.getSession(), null);
  const session = await auth.signIn(
    localDemoCredentials.username,
    localDemoCredentials.passcode,
  );
  assert.deepEqual(session, { username: "analyst", label: "SOC analyst" });
  assert.deepEqual(await auth.getSession(), session);
});

test("local auth rejects invalid credentials and preserves signed-out state", async () => {
  installWindow();
  const auth = createLocalAuth();
  await assert.rejects(
    () => auth.signIn("analyst", "wrong"),
    (error) => error.code === "INVALID_CREDENTIALS",
  );
  assert.equal(await auth.getSession(), null);
});

test("local auth clears the session on sign out", async () => {
  installWindow();
  const auth = createLocalAuth();
  await auth.signIn("analyst", "synthetic-only");
  await auth.signOut();
  assert.equal(await auth.getSession(), null);
});

test("API auth preserves the backend role and login destination", async () => {
  const calls = [];
  const auth = createApiAuth(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, status: 200, async json() { return { user: { username: "superadmin", role: "superadmin" }, redirect: "/admin/users" }; } };
  });
  assert.deepEqual(await auth.signIn("admin", "secret"), { username: "superadmin", role: "superadmin", redirect: "/admin/users" });
  assert.equal(calls[0][0], "/api/auth/login");
  assert.equal((await auth.getSession()).role, "superadmin");
});
