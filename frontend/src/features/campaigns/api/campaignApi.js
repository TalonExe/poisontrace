const json = (body) => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export function createCampaignApi(http) {
  const fallback = "Campaign API unavailable";
  return {
    listCampaigns: () => http.request("/campaigns", { fallback }),
    getCampaign: (id) => http.request(`/campaigns/${id}`, { fallback }),
    rerunCampaignScenario: (id, ordinal) => http.request(`/campaigns/${id}/scenarios/${ordinal}/rerun`, { method: "POST", fallback }),
    async runCampaign({ provider = "fake", model = "fake", credentialId = "" } = {}) {
      const created = await http.request("/campaigns", { method: "POST", ...json({ provider, model, credential_id: credentialId || null }), fallback });
      return http.request(`/campaigns/${created.campaign_id}/execute`, { method: "POST", fallback });
    },
  };
}
