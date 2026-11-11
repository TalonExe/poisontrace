import React, { useState } from "react";
import { Icon } from "../components/common/Ui";

export function LoginPage({ auth, onAuthenticated }) {
  const [username, setUsername] = useState("");
  const [passcode, setPasscode] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setStatus("loading");
    setError("");
    try {
      const session = await auth.signIn(username, passcode);
      onAuthenticated(session);
    } catch (error) {
      setError(error.message || "Unable to sign in. Try again.");
      setStatus("invalid");
    }
  };
  return (
    <main className="login-shell">
      <div className="login-panel">
        <div className="login-brand">
          <span className="logo">P</span>
          <div>
            <strong>PoisonTrace</strong>
            <small>Evidence dashboard</small>
          </div>
        </div>
        <div className="login-copy">
          <h1>Sign in to PoisonTrace</h1>
          <p>Use your local account to access the synthetic research workspace.</p>
        </div>
        <form className="login-form" onSubmit={submit}>
          <label className="field">
            <span>Username</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="analyst"
              required
            />
          </label>
          <label className="field">
            <span>Local passcode</span>
            <input
              type="password"
              autoComplete="current-password"
              value={passcode}
              onChange={(event) => setPasscode(event.target.value)}
              placeholder="Enter your passcode"
              required
            />
          </label>
          {status === "invalid" && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button
            className="run-button login-button"
            disabled={status === "loading"}
          >
            {status === "loading" ? "Checking access…" : "Sign in"}{" "}
            <Icon name="arrow" size={14} />
          </button>
        </form>
        <p className="demo-note">Local synthetic environment. Ask your administrator for account details.</p>
      </div>
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}
