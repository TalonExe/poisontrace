import {notifySessionExpiry, sessionGeneration} from "./sessionExpiry.js";

export function createHttpClient({ fetchImpl = window.fetch.bind(window), baseUrl = "/api" } = {}) {
  async function request(path, { fallback, ...options } = {}) {
    const generation = sessionGeneration();
    const response = await fetchImpl(`${baseUrl}${path}`, options);
    notifySessionExpiry(response, generation);
    if (!response.ok) {
      let message = fallback;
      try { message = (await response.json()).detail || fallback; } catch { /* non-JSON response */ }
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }
  return { request };
}
