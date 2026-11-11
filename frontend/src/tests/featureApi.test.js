import assert from "node:assert/strict";
import test from "node:test";
import { createHttpClient } from "../lib/http/client.js";
import { createScenarioApi } from "../features/scenarios/api/scenarioApi.js";
import { createCredentialApi } from "../features/credentials/api/credentialApi.js";

const response = (body, ok = true) => ({ ok, async json() { return body; } });

test("scenario API preserves HTTP payloads and encoded IDs", async () => {
  const calls = [];
  const http = createHttpClient({
    baseUrl: "/service",
    fetchImpl: async (...args) => { calls.push(args); return response({ scenario_id: "001" }); },
  });
  await createScenarioApi(http).getScenario("case/001");
  assert.equal(calls[0][0], "/service/scenarios/case%2F001");
});

test("credential API sends references and surfaces consistent backend errors", async () => {
  let request;
  const api = createCredentialApi(createHttpClient({
    fetchImpl: async (...args) => { request = args; return response({ detail: "rejected" }, false); },
  }));
  await assert.rejects(() => api.testCredential("cred-1"), /rejected/);
  assert.equal(request[0], "/api/credentials/cred-1/test");
  assert.ok(!JSON.stringify(request).includes("secret"));
});
