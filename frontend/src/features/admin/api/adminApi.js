import {notifySessionExpiry, sessionGeneration} from "../../../lib/http/sessionExpiry.js";

export function createAdminApi(fetchImpl = fetch) {
  async function request(url, options) {
    const generation = sessionGeneration();
    const response = await fetchImpl(url, { ...options, headers: { "Content-Type": "application/json", ...(options?.headers || {}) } });
    notifySessionExpiry(response, generation);
    const body = await response.json().catch(() => null);
    if (!response.ok) { const error = new Error(body?.detail || "Request failed."); error.status = response.status; throw error; }
    return body;
  }
  return {
    listUsers: (search = "") => request(`/api/admin/users?search=${encodeURIComponent(search)}`),
    createUser: (payload) => request("/api/admin/users", { method: "POST", body: JSON.stringify(payload) }),
    updateUser: (id, payload) => request(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    resetPasscode: (id, passcode) => request(`/api/admin/users/${id}/passcode`, { method: "POST", body: JSON.stringify({passcode}) }),
  };
}
