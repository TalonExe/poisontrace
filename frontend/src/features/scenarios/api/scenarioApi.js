const json = (body) => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export function createScenarioApi(http) {
  const fallback = "Scenario API unavailable";
  return {
    listScenarios: () => http.request("/scenarios", { fallback }),
    getScenario: (id) => http.request(`/scenarios/${encodeURIComponent(id)}`, { fallback }),
    createScenario: (document) => http.request("/scenarios", { method: "POST", ...json({ name: document.name, document }), fallback }),
    updateScenario: (id, document) => http.request(`/scenarios/${encodeURIComponent(id)}`, { method: "PUT", ...json({ document }), fallback }),
    deleteScenario: (id) => http.request(`/scenarios/${encodeURIComponent(id)}`, { method: "DELETE", fallback }),
  };
}
