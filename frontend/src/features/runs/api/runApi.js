export function createRunApi(http) {
  return {
    listRunGroups: () =>
      http.request("/run-groups", { fallback: "Run groups unavailable" }),
    getRunGroup: (id) =>
      http.request(`/run-groups/${encodeURIComponent(id)}`, {
        fallback: "Run group not found",
      }),
    createRunGroup: (payload) =>
      http.request("/run-groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        fallback: "Run group could not complete",
      }),
    executeRunGroup: (id, payload) =>
      http.request(`/run-groups/${encodeURIComponent(id)}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        fallback: "Group rerun could not complete",
      }),
    getInvestigationCase: (id) =>
      http.request(`/runs/investigation-cases/${encodeURIComponent(id)}`, {
        fallback: "Case ground truth unavailable",
      }),
    updateInvestigationCase: (id, payload) =>
      http.request(`/runs/investigation-cases/${encodeURIComponent(id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        fallback: "Case ground truth could not be saved",
      }),
    listInvestigationCases: () =>
      http.request("/runs/investigation-cases", {
        fallback: "Investigation cases unavailable",
      }),
    runInvestigation: ({
      caseId,
      sessionId = "",
      provider = "scripted",
      model,
      credentialId,
      mode = "clean",
      attackFamily,
    }) =>
      http.request("/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow: "mcp-investigation-v1",
          case_id: caseId,
          session_id: sessionId,
          mode,
          ...(attackFamily ? { attack_family: attackFamily } : {}),
          provider,
          ...(["gemini", "openai"].includes(provider)
            ? { model, credential_id: credentialId }
            : {}),
        }),
        fallback: "Investigation API unavailable",
      }),
    getRunSummary: () =>
      http.request("/runs/summary", {
        fallback: "Measurement summary unavailable",
      }),
    listRuns: () =>
      http.request("/runs", { fallback: "Runner API unavailable" }),
    getRun: (id) => http.request(`/runs/${id}`, { fallback: "Run not found" }),
    runExperiment: ({
      scenarioId,
      mode,
      provider = "fake",
      model = "fake",
      sessionId = "",
      credentialId = "",
    }) =>
      http.request("/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario_id: scenarioId,
          mode: mode.toLowerCase(),
          provider,
          model,
          session_id: sessionId,
          credential_id: credentialId,
        }),
        fallback: "Runner API unavailable",
      }),
  };
}
