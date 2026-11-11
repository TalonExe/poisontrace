export function createAdminApi(fetchImpl = fetch) {
  async function request(url, options) {
    const response = await fetchImpl(url, { ...options, headers: { "Content-Type": "application/json", ...(options?.headers || {}) } });
    const body = await response.json().catch(() => null);
    if (!response.ok) { const error = new Error(body?.detail || "Request failed."); error.status = response.status; throw error; }
    return body;
  }
  return {
    listUsers: (search = "") => request(`/api/admin/users?search=${encodeURIComponent(search)}`),
    createUser: (payload) => request("/api/admin/users", { method: "POST", body: JSON.stringify(payload) }),
    updateUser: (id, payload) => request(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  };
}
