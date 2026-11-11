import { createHttpClient } from "../lib/http/client.js";
import { createScenarioApi } from "../features/scenarios/api/scenarioApi.js";
import { createRunApi } from "../features/runs/api/runApi.js";
import { createCampaignApi } from "../features/campaigns/api/campaignApi.js";
import { createCredentialApi } from "../features/credentials/api/credentialApi.js";

// Compatibility facade while pages still receive one runner prop.
export function createRunnerAdapter({ fetchImpl, endpoint } = {}) {
  const http = createHttpClient({ fetchImpl, baseUrl: endpoint });
  return {
    ...createScenarioApi(http),
    ...createRunApi(http),
    ...createCampaignApi(http),
    ...createCredentialApi(http),
  };
}
