const json = (body) => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export function createCredentialApi(http) {
  return {
    listCredentials: () => http.request("/credentials", { fallback: "Credential API unavailable" }),
    saveCredential: ({ provider, label, secret }) => http.request("/credentials", { method: "POST", ...json({ provider, label, secret }), fallback: "Credential API unavailable" }),
    replaceCredential: (id, { provider, label, secret }) => http.request(`/credentials/${id}`, { method: "PUT", ...json({ provider, label, secret }), fallback: "Credential API unavailable" }),
    testCredential: (id) => http.request(`/credentials/${id}/test`, { method: "POST", fallback: "Credential test failed" }),
    revokeCredential: (id) => http.request(`/credentials/${id}`, { method: "DELETE", fallback: "Credential revoke failed" }),
  };
}
