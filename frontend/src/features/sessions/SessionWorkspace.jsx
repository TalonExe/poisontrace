import React, { useEffect, useState } from "react";
import {
  createSession,
  deleteSession,
  loadSessions,
  saveSession,
} from "../../utils/sessions";
import { Icon } from "../../components/common/Ui";
import { Sidebar } from "../../components/layout/Sidebar";
import "../../components/layout/layout.css";

const modelOptions = { gemini: "Gemini API LLM", openai: "OpenAI API LLM" };

export function SessionWorkspace({
  onOpenSession,
  onSignOut,
  onScenarios,
  onResults,
  onDashboard,
  auth,
  user,
  runner = { listCredentials: async () => [] },
}) {
  const [sessions, setSessions] = useState(() =>
    loadSessions(window.localStorage),
  );
  const [credentials, setCredentials] = useState([]);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState(null);
  const [credentialDraft, setCredentialDraft] = useState({
    provider: "gemini",
    label: "",
    secret: "",
  });
  const [credentialStatus, setCredentialStatus] = useState("");
  useEffect(() => {
    window.localStorage.setItem(
      "poisontrace.synthetic.sessions",
      JSON.stringify(sessions),
    );
  }, [sessions]);
  useEffect(() => {
    runner
      .listCredentials()
      .then(setCredentials)
      .catch(() => setCredentials([]));
  }, [runner]);
  const beginCreate = () => {
    const next = createSession();
    setEditing(next.id);
    setDraft(next);
  };
  const beginEdit = (session) => {
    setEditing(session.id);
    setDraft({ ...session });
  };
  const saveDraft = (event) => {
    event.preventDefault();
    if (!draft.name.trim()) return;
    setSessions((current) =>
      current.some((session) => session.id === draft.id)
        ? saveSession(current, draft)
        : [{ ...draft, name: draft.name.trim() }, ...current],
    );
    if (draft.name.trim()) {
      setEditing(null);
      setDraft(null);
    }
  };
  const removeSession = (id) => {
    const session = sessions.find((item) => item.id === id);
    if (
      !window.confirm(
        `Delete configuration "${session?.name}"? Its configuration will be removed from this browser.`,
      )
    )
      return;
    setSessions((current) => deleteSession(current, id));
    if (editing === id) {
      setEditing(null);
      setDraft(null);
    }
  };
  const addCredential = async (event) => {
    event.preventDefault();
    if (!credentialDraft.secret.trim()) return;
    setCredentialStatus("Saving…");
    try {
      const credential = await runner.saveCredential(credentialDraft);
      setCredentials((current) => [...current, credential]);
      setDraft((current) => ({
        ...current,
        credentialId: credential.credential_id,
        model: credential.provider,
      }));
      setCredentialDraft({
        provider: credentialDraft.provider,
        label: "",
        secret: "",
      });
      setCredentialStatus(
        "Credential saved. The secret was not stored in the browser.",
      );
    } catch (error) {
      setCredentialStatus(error.message);
    }
  };
  const revokeCredential = async (credentialId) => {
    setCredentialStatus("Revoking…");
    try {
      await runner.revokeCredential(credentialId);
      setCredentials((current) =>
        current.filter((item) => item.credential_id !== credentialId),
      );
      setDraft((current) =>
        current && current.credentialId === credentialId
          ? { ...current, credentialId: "" }
          : current,
      );
      setCredentialStatus("Credential revoked.");
    } catch (error) {
      setCredentialStatus(error.message);
    }
  };
  return (
    <main className="session-shell">
      <Sidebar
        active="sessions"
        user={user}
        auth={auth}
        onSignedOut={onSignOut}
        onSessions={() => {}}
        onDashboard={onDashboard}
        onResults={onResults}
        onScenarios={onScenarios}
      />
      <section className="session-heading">
        <div>
          <h1>Configurations</h1>
          <p>
            Reusable provider settings for your experiments. Select the case and
            condition in Experiment; revisit saved attempts in Results.
          </p>
        </div>
        <button className="run-button" onClick={beginCreate}>
          New configuration <Icon name="arrow" size={14} />
        </button>
      </section>
      <section className="session-layout">
        <div className="session-list">
          <div className="list-heading">
            <div>
              <p className="label">Saved configurations</p>
              <h2>
                {sessions.length} saved configuration
                {sessions.length === 1 ? "" : "s"}
              </h2>
            </div>
          </div>
          {sessions.map((session) => (
            <article
              className={`session-row ${editing === session.id ? "selected" : ""}`}
              key={session.id}
            >
              <div className="session-mark">
                {session.model === "gemini" ? "G" : "O"}
              </div>
              <div className="session-summary">
                <strong>{session.name}</strong>
                <small>{modelOptions[session.model]}</small>
                <small>Updated {session.updated}</small>
              </div>
              <button
                className="text-button"
                onClick={(event) => {
                  event.stopPropagation();
                  onOpenSession(session);
                }}
              >
                Open
              </button>
              <button
                className="text-button"
                onClick={(event) => {
                  event.stopPropagation();
                  beginEdit(session);
                }}
              >
                Edit
              </button>
              <button
                className="icon-button danger-button"
                aria-label={`Delete ${session.name}`}
                onClick={(event) => {
                  event.stopPropagation();
                  removeSession(session.id);
                }}
              >
                <Icon name="trash" size={16} />
              </button>
            </article>
          ))}
        </div>
        {draft ? (
          <form className="card session-editor" onSubmit={saveDraft}>
            <div className="card-head">
              <div>
                <p className="label">Provider settings</p>
                <h2>
                  {editing && sessions.some((session) => session.id === editing)
                    ? "Edit configuration"
                    : "New configuration"}
                </h2>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="Close editor"
                onClick={() => {
                  setEditing(null);
                  setDraft(null);
                }}
              >
                <Icon name="close" size={16} />
              </button>
            </div>
            <label className="field">
              <span>Configuration name</span>
              <input
                value={draft.name}
                onChange={(event) =>
                  setDraft({ ...draft, name: event.target.value })
                }
                maxLength="60"
                required
              />
            </label>
            <fieldset className="field provider-field">
              <legend>Model provider</legend>
              <div className="model-options">
                {Object.entries(modelOptions).map(([value, label]) => (
                  <button
                    type="button"
                    key={value}
                    className={`model-option ${draft.model === value ? "active" : ""}`}
                    aria-pressed={draft.model === value}
                    onClick={() =>
                      setDraft({ ...draft, model: value, credentialId: "" })
                    }
                  >
                    <strong>{value === "gemini" ? "G" : "O"}</strong>
                    <span>{label}</span>
                    <small>
                      {value === "gemini"
                        ? "gemini-3.5-flash-lite"
                        : "gpt-5-mini"}
                    </small>
                  </button>
                ))}
              </div>
            </fieldset>
            <label className="field">
              <span>API credential reference</span>
              <div className="select-wrap">
                <select
                  value={draft.credentialId || ""}
                  onChange={(event) =>
                    setDraft({ ...draft, credentialId: event.target.value })
                  }
                >
                  <option value="">No credential selected</option>
                  {credentials
                    .filter((item) => item.provider === draft.model)
                    .map((item) => (
                      <option
                        key={item.credential_id}
                        value={item.credential_id}
                      >
                        {item.label || item.provider} · {item.masked}
                      </option>
                    ))}
                </select>
                <Icon name="chevron" size={14} />
              </div>
            </label>
            <div className="credential-form">
              <p className="label">Add credential</p>
              <div className="credential-fields">
                <select
                  aria-label="Credential provider"
                  value={credentialDraft.provider}
                  onChange={(event) =>
                    setCredentialDraft({
                      ...credentialDraft,
                      provider: event.target.value,
                    })
                  }
                >
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                </select>
                <input
                  value={credentialDraft.label}
                  onChange={(event) =>
                    setCredentialDraft({
                      ...credentialDraft,
                      label: event.target.value,
                    })
                  }
                  aria-label="Credential label"
                  placeholder="Label"
                />
                <input
                  type="password"
                  value={credentialDraft.secret}
                  onChange={(event) =>
                    setCredentialDraft({
                      ...credentialDraft,
                      secret: event.target.value,
                    })
                  }
                  aria-label="API key"
                  placeholder="API key"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="small-button"
                  onClick={addCredential}
                >
                  Save
                </button>
              </div>
              {credentials
                .filter((item) => item.provider === draft.model)
                .map((item) => (
                  <div className="credential-row" key={item.credential_id}>
                    <span>
                      {item.label || item.provider} · {item.masked}
                    </span>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => revokeCredential(item.credential_id)}
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              {credentialStatus && (
                <p className="editor-note" role="status">
                  {credentialStatus}
                </p>
              )}
            </div>
            <p className="editor-note">
              <span className="status-dot" />
              Secrets are sent directly to the local API and are never stored in
              browser session data.
            </p>
            <button className="run-button save-session">
              Save configuration <Icon name="arrow" size={14} />
            </button>
          </form>
        ) : (
          <div className="session-empty">
            <span className="logo">P</span>
            <h2>Choose settings for your next experiment</h2>
            <p>
              Open a saved configuration or create one. Your experiment history
              is available in Results independently of these settings.
            </p>
            <button className="small-button" onClick={beginCreate}>
              Create a configuration <Icon name="arrow" size={12} />
            </button>
          </div>
        )}
      </section>
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}
