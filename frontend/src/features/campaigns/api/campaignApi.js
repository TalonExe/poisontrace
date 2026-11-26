const json = (body) => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export function createCampaignApi(http) {
  const fallback = "Campaign API unavailable";
  return {
    listCampaigns: () => http.request("/campaigns", { fallback }),
    getCampaign: (id) => http.request(`/campaigns/${id}`, { fallback }),
    rerunCampaignScenario: (id, ordinal, intent) =>
      http.request(`/campaigns/${id}/scenarios/${ordinal}/rerun`, { method: "POST", headers: { "Idempotency-Key": intent }, fallback }),
    createCampaign: ({ provider = "fake", model = "fake", credentialId = "" } = {}) =>
      http.request("/campaigns", { method: "POST", ...json({ provider, model, credential_id: credentialId || null }), fallback }),
    executeCampaign: (id, intent, excludedFiles) => {
      const request = json({ excluded_files: excludedFiles });
      request.headers["Idempotency-Key"] = intent;
      return http.request(`/campaigns/${id}/execute`, { method: "POST", ...request, fallback });
    },
  };
}
