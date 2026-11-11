export function createHttpClient({ fetchImpl = window.fetch.bind(window), baseUrl = "/api" } = {}) {
  async function request(path, { fallback, ...options } = {}) {
    const response = await fetchImpl(`${baseUrl}${path}`, options);
    if (!response.ok) {
      let message = fallback;
      try { message = (await response.json()).detail || fallback; } catch { /* non-JSON response */ }
      throw new Error(message);
    }
    return response.json();
  }
  return { request };
}
