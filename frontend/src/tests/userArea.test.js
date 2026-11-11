import assert from "node:assert/strict";
import test from "node:test";
import {
  signOutAndRedirect,
  userDisplayName,
  userInitials,
} from "../utils/userArea.js";

test("user area displays the current local user without credentials", () => {
  const user = { username: "analyst", label: "SOC analyst" };

  assert.equal(userDisplayName(user), "SOC analyst");
  assert.equal(userInitials(user), "SA");
  assert.equal(userDisplayName({ username: "analyst" }), "analyst");
});

test("sign out clears auth before handing control to the login redirect", async () => {
  const calls = [];
  const auth = { signOut: async () => calls.push("auth.signOut") };

  await signOutAndRedirect(auth, () => calls.push("redirect"));

  assert.deepEqual(calls, ["auth.signOut", "redirect"]);
});
