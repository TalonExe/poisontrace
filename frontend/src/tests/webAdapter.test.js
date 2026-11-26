import assert from "node:assert/strict";
import test from "node:test";
import { createRunnerAdapter } from "../utils/webAdapter.js";

function response(body, ok = true) {
  return {
    ok,
    async json() {
      return body;
    },
  };
}

test("lists runs from the backend", async () => {
  const calls = [];
  const adapter = createRunnerAdapter({
    endpoint: "/service",
    fetchImpl: async (...args) => {
      calls.push(args);
      return response([{ id: "EXP-001" }]);
    },
  });

  assert.deepEqual(await adapter.listRuns(), [{ id: "EXP-001" }]);
  assert.deepEqual(calls, [["/service/runs", {}]]);
});

test("uses HTTP seams for scenario CRUD", async () => {
  const calls = [];
  const adapter = createRunnerAdapter({
    endpoint: "/service",
    fetchImpl: async (...args) => {
      calls.push(args);
      return response({ scenario_id: "001", valid: true });
    },
  });
  await adapter.listScenarios();
  await adapter.getScenario("001");
  await adapter.createScenario({ name: "New case" });
  await adapter.updateScenario("001", { scenario_id: "001" });
  await adapter.deleteScenario("001");
  assert.deepEqual(
    calls.map((call) => [call[0], call[1]?.method || "GET"]),
    [
      ["/service/scenarios", "GET"],
      ["/service/scenarios/001", "GET"],
      ["/service/scenarios", "POST"],
      ["/service/scenarios/001", "PUT"],
      ["/service/scenarios/001", "DELETE"],
    ],
  );
});

test("lists campaign history from the backend", async () => {
  const calls = [];
  const adapter = createRunnerAdapter({
    endpoint: "/service",
    fetchImpl: async (...args) => {
      calls.push(args);
      return response([{ campaign_id: "CMP-1", status: "completed" }]);
    },
  });

  assert.deepEqual(await adapter.listCampaigns(), [
    { campaign_id: "CMP-1", status: "completed" },
  ]);
  assert.deepEqual(calls, [["/service/campaigns", {}]]);
});

test("loads and reruns one campaign scenario through the backend", async () => {
  const calls = [];
  const adapter = createRunnerAdapter({
    endpoint: "/service",
    fetchImpl: async (...args) => {
      calls.push(args);
      return response({ campaign_id: "CMP-1", scenarios: [] });
    },
  });

  assert.deepEqual(await adapter.getCampaign("CMP-1"), {
    campaign_id: "CMP-1",
    scenarios: [],
  });
  assert.deepEqual(await adapter.rerunCampaignScenario("CMP-1", 2, "rerun-intent"), {
    campaign_id: "CMP-1",
    scenarios: [],
  });
  assert.deepEqual(calls, [
    ["/service/campaigns/CMP-1", {}],
    ["/service/campaigns/CMP-1/scenarios/2/rerun", { method: "POST", headers: { "Idempotency-Key": "rerun-intent" } }],
  ]);
});

test("creates and executes an all-poisoned-scenarios campaign", async () => {
  const calls = [];
  const adapter = createRunnerAdapter({
    endpoint: "/service",
    fetchImpl: async (...args) => {
      calls.push(args);
      return response({ campaign_id: "CMP-2", status: "completed" });
    },
  });

  assert.deepEqual(
    await adapter.createCampaign({
      provider: "fake",
      model: "workflow-model",
      credentialId: "cred-1",
    }),
    { campaign_id: "CMP-2", status: "completed" },
  );
  await adapter.executeCampaign("CMP-2", "campaign-intent", ["broken.yaml"]);
  assert.deepEqual(calls, [
    [
      "/service/campaigns",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "fake",
          model: "workflow-model",
          credential_id: "cred-1",
        }),
      },
    ],
    ["/service/campaigns/CMP-2/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": "campaign-intent" },
      body: JSON.stringify({ excluded_files: ["broken.yaml"] }),
    }],
  ]);
});

test("posts the selected session runner settings", async () => {
  let request;
  const adapter = createRunnerAdapter({
    fetchImpl: async (...args) => {
      request = args;
      return response({ id: "EXP-002" });
    },
  });

  assert.deepEqual(
    await adapter.runExperiment({
      scenarioId: "authentication-alert",
      mode: "Defended",
      provider: "gemini",
    }),
    { id: "EXP-002" },
  );
  assert.equal(request[0], "/api/investigation-jobs");
  assert.equal(request[1].method, "POST");
  assert.equal(request[1].headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(request[1].body), {
    workflow: "metadata-v1",
    scenario_id: "authentication-alert",
    mode: "defended",
    provider: "gemini",
    model: "fake",
    session_id: "",
    credential_id: "",
  });
});

test("passes a credential reference without retaining a secret", async () => {
  let request;
  const adapter = createRunnerAdapter({
    fetchImpl: async (...args) => {
      request = args;
      return response({ id: "EXP-003" });
    },
  });
  await adapter.runExperiment({
    scenarioId: "x",
    mode: "Clean",
    provider: "openai",
    sessionId: "session-1",
    credentialId: "cred-123",
  });
  assert.deepEqual(JSON.parse(request[1].body), {
    workflow: "metadata-v1",
    scenario_id: "x",
    mode: "clean",
    provider: "openai",
    model: "fake",
    session_id: "session-1",
    credential_id: "cred-123",
  });
  assert.ok(!JSON.stringify(request).includes("secret"));
});

test("surfaces backend failures instead of creating local demo runs", async () => {
  const adapter = createRunnerAdapter({
    fetchImpl: async () => response({}, false),
  });
  await assert.rejects(() => adapter.listRuns(), /Runner API unavailable/);
  await assert.rejects(
    () => adapter.runExperiment({ scenarioId: "x", mode: "Clean" }),
    /Runner API unavailable/,
  );
});

test("MCP investigations forward only the selected provider configuration", async () => {
  const calls = [];
  const adapter = createRunnerAdapter({fetchImpl: async (...args) => { calls.push(args); return response({run_id: 17}); }});
  await adapter.runInvestigation({caseId: "soc-auth-001", provider: "gemini", model: "chosen-gemini", credentialId: "ref-1", intent: 'synthetic-intent-001'});
  assert.equal(calls[0][0], '/api/investigation-jobs');
  assert.equal(calls[0][1].headers['Idempotency-Key'], 'synthetic-intent-001');
  assert.deepEqual(JSON.parse(calls[0][1].body), {workflow: "mcp-investigation-v1", case_id: "soc-auth-001", session_id: "", mode: "clean", provider: "gemini", model: "chosen-gemini", credential_id: "ref-1"});
  await adapter.runInvestigation({caseId: "soc-auth-001", credentialId: "must-not-forward"});
  assert.equal(JSON.parse(calls[1][1].body).credential_id, undefined);
});

test("OpenAI investigation forwards the actual model and credential reference", async () => {
  let sent;
  const adapter = createRunnerAdapter({fetchImpl: async (url, options) => { sent = JSON.parse(options.body); return response({run_id: 19}); }});
  await adapter.runInvestigation({caseId:"soc-auth-001",provider:"openai",model:"gpt-5-mini",credentialId:"test-ref"});
  assert.equal(sent.model,"gpt-5-mini");
  assert.equal(sent.credential_id,"test-ref");
});
