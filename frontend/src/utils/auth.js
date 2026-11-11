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
      if (response.status === 401) return null;
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
        const error = new Error(invalid ? "Invalid username or passcode. Check your details and try again." : "Unable to reach the sign-in service. Try again shortly.");
        error.code = invalid ? "INVALID_CREDENTIALS" : "AUTH_UNAVAILABLE";
        throw error;
      }
      const payload = await response.json();
      session = payload.user;
      return { ...session, redirect: payload.redirect };
    },
    async signOut() {
      await fetchImpl("/api/auth/logout", { method: "POST" });
      session = null;
    },
  };
}
