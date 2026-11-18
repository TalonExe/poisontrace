import test from "node:test";
import assert from "node:assert/strict";
import { resolveExecution } from "../utils/executionSelection.js";

const configs = [
  {
    id: "old-g",
    name: "Existing Gemini",
    model: "gemini",
    credentialId: "g-ref",
    scenario: "retained",
  },
  {
    id: "old-o",
    name: "Existing OpenAI",
    model: "openai",
    credentialId: "o-ref",
  },
  { id: "wrong", name: "Mismatched", model: "gemini", credentialId: "o-ref" },
];
const credentials = [
  { credential_id: "g-ref", provider: "gemini" },
  { credential_id: "o-ref", provider: "openai" },
];
test("execution selection pairs existing configurations with matching credentials", () => {
  assert.equal(
    resolveExecution("config:old-g", configs, credentials).model,
    "gemini-3.5-flash-lite",
  );
  assert.equal(
    resolveExecution("config:old-o", configs, credentials).model,
    "gpt-5-mini",
  );
  assert.equal(
    resolveExecution("config:old-o", configs, credentials).credentialId,
    "o-ref",
  );
  assert.equal(configs[0].scenario, "retained");
});
test("offline clears credentials and does not require configurations or credential availability", () => {
  assert.deepEqual(resolveExecution("scripted", [], []), {
    provider: "scripted",
    model: "scripted-soc-v2",
    credentialId: undefined,
    configuration: undefined,
    valid: true,
  });
});
test("mismatched, missing and revoked references cannot be forwarded", () => {
  for (const [id, refs] of [
    ["config:wrong", credentials],
    ["config:missing", credentials],
    ["config:old-g", []],
  ]) {
    const execution = resolveExecution(id, configs, refs);
    assert.equal(execution.valid, false);
    assert.equal(execution.credentialId, undefined);
  }
});
test("reruns retain the saved model and require a current matching credential", () => {
  const saved = { provider: "openai", model: "saved-model-version" };
  assert.equal(
    resolveExecution("config:old-g", configs, credentials, saved).valid,
    false,
  );
  const execution = resolveExecution(
    "config:old-o",
    configs,
    credentials,
    saved,
  );
  assert.equal(execution.model, "saved-model-version");
  assert.equal(execution.credentialId, "o-ref");
  assert.equal(
    resolveExecution("config:old-g", configs, credentials, {
      provider: "scripted",
      model: "saved-scripted",
    }).credentialId,
    undefined,
  );
});
