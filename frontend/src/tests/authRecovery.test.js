import test from "node:test";
import assert from "node:assert/strict";
import { createApiAuth } from "../utils/auth.js";

test("API auth distinguishes invalid credentials from an unavailable service", async () => {
  for (const [status, code] of [[401, "INVALID_CREDENTIALS"], [503, "AUTH_UNAVAILABLE"]]) {
    const auth = createApiAuth(async () => ({ ok: false, status }));
    await assert.rejects(auth.signIn("analyst", "test"), (error) => error.code === code);
  }
});

test("API auth reports a bounded throttle and does not complete failed logout", async () => {
  const auth = createApiAuth(async () => ({ok: false, status: 429, headers: new Headers({'Retry-After': '120'})}));
  await assert.rejects(auth.signIn('synthetic', 'wrong'), error => error.code === 'LOGIN_THROTTLED' && /120 seconds/.test(error.message));
  await assert.rejects(auth.signOut(), /Unable to sign out/);
});
