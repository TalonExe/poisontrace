const DEMO_ACCOUNT = { username: "analyst", passcode: "synthetic-only" };

export function createLocalAuth() {
  let session = null;

  return {
    async getSession() {
      return session;
    },
    async signIn(username, passcode) {
      await new Promise((resolve) => window.setTimeout(resolve, 450));
      if (
        username.trim().toLowerCase() !== DEMO_ACCOUNT.username ||
        passcode !== DEMO_ACCOUNT.passcode
      ) {
        const error = new Error("Invalid local demo credentials.");
        error.code = "INVALID_CREDENTIALS";
        throw error;
      }
      session = { username: DEMO_ACCOUNT.username, label: "SOC analyst" };
      return session;
    },
    async signOut() {
      session = null;
    },
  };
}

export const localDemoCredentials = DEMO_ACCOUNT;

export function createApiAuth(fetchImpl = fetch) {
  let session = null;
  return {
    async getSession() {
      const response = await fetchImpl("/api/auth/session");
      if (response.status === 401) { session = null; return null; }
      if (!response.ok) throw new Error("Unable to load authentication session.");
      session = (await response.json()).user;
      return session;
    },
    async signIn(username, passcode) {
      const response = await fetchImpl("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, passcode }),
      });
      if (!response.ok) {
        const invalid = response.status === 401;
        const throttled = response.status === 429;
        const seconds = Number(response.headers?.get('Retry-After'));
        const delay = Number.isFinite(seconds) && seconds > 0 ? ` Try again in ${Math.ceil(seconds)} seconds.` : " Try again shortly.";
        const error = new Error(throttled ? `Too many sign-in attempts.${delay}` : invalid ? "Invalid username or passcode. Check your details and try again." : "Unable to reach the sign-in service. Try again shortly.");
        error.code = throttled ? "LOGIN_THROTTLED" : invalid ? "INVALID_CREDENTIALS" : "AUTH_UNAVAILABLE";
        throw error;
      }
      const payload = await response.json();
      session = payload.user;
      return { ...session, redirect: payload.redirect };
    },
    async signOut() {
      const response = await fetchImpl("/api/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("Unable to sign out. Check your connection and try again.");
      session = null;
    },
  };
}
