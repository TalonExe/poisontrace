export function createRunApi(http) {
  return {
    listRuns: () => http.request("/runs", { fallback: "Runner API unavailable" }),
    getRun: (id) => http.request(`/runs/${id}`, { fallback: "Run not found" }),
    runExperiment: ({ scenarioId, mode, provider = "fake", model = "fake", sessionId = "", credentialId = "" }) => http.request("/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenario_id: scenarioId, mode: mode.toLowerCase(), provider, model, session_id: sessionId, credential_id: credentialId }), fallback: "Runner API unavailable" }),
  };
}
