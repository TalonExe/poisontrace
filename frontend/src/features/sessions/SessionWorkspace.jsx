import React, { useEffect, useMemo, useState } from "react";
import { workspaceStorage } from "../../utils/workspaceStorage";
import {
  createSession,
  deleteSession,
  loadSessions,
  saveSession,
} from "../../utils/sessions";
import { Icon } from "../../components/common/Ui";
import { ApiKeySettings } from "./ApiKeySettings";
import { Sidebar } from "../../components/layout/Sidebar";
import { ConfirmationAction } from "../../components/common/ConfirmationAction";
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
  const storage = useMemo(() => workspaceStorage(window.localStorage), []);
  const [sessions, setSessions] = useState(() => loadSessions(storage));
  const [credentials, setCredentials] = useState([]);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState(null);
  const [credentialsLoading, setCredentialsLoading] = useState(true);
  const [credentialsError, setCredentialsError] = useState(false);
  const [credentialAttempt, setCredentialAttempt] = useState(0);
  useEffect(() => {
    storage.setItem("poisontrace.synthetic.sessions", JSON.stringify(sessions));
  }, [sessions, storage]);
  useEffect(() => {
    let active = true;
    setCredentialsLoading(true);
    setCredentialsError(false);
    runner
      .listCredentials()
      .then((items) => {
        if (active) setCredentials(items);
      })
      .catch(() => {
        if (active) setCredentialsError(true);
      })
      .finally(() => {
        if (active) setCredentialsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner, credentialAttempt]);
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
    setSessions((current) => deleteSession(current, id));
    if (editing === id) {
      setEditing(null);
      setDraft(null);
    }
  };
  const saveCredential = async (values, replacement) => {
    const saved = replacement
      ? await runner.replaceCredential(replacement, values)
      : await runner.saveCredential(values);
    setCredentials((current) =>
      replacement
        ? current.map((item) =>
            item.credential_id === replacement ? saved : item,
          )
        : [...current, saved],
    );
  };
  const revokeCredential = async (credentialId) => {
    await runner.revokeCredential(credentialId);
    setCredentials((current) =>
      current.filter((item) => item.credential_id !== credentialId),
    );
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
          <h1>Settings</h1>
          <p>Manage API keys and reusable settings for your investigations.</p>
        </div>
      </section>
      <ApiKeySettings
        credentials={credentials}
        loading={credentialsLoading}
        loadError={credentialsError}
        onReload={() => setCredentialAttempt((attempt) => attempt + 1)}
        onSave={saveCredential}
        onRevoke={revokeCredential}
      />
      <section
        className="settings-configurations"
        aria-labelledby="saved-configurations-heading"
      >
        <div className="card-head">
          <h2 id="saved-configurations-heading">Saved configurations</h2>
          <button className="small-button" onClick={beginCreate}>
            New configuration
          </button>
        </div>
        <div
          className={
            draft ? "session-layout" : "session-layout settings-list-only"
          }
        >
          <div className="session-list">
            {sessions.length === 0 && <p>No saved configurations.</p>}
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
                <ConfirmationAction
                  className="icon-button danger-button"
                  triggerLabel={`Delete ${session.name}`}
                  title={`Delete configuration "${session.name}"?`}
                  description="This removes the saved configuration from this browser."
                  confirmLabel="Delete configuration"
                  onConfirm={() => removeSession(session.id)}
                >
                  <Icon name="trash" size={16} />
                </ConfirmationAction>
              </article>
            ))}
          </div>
          {draft ? (
            <form className="card session-editor" onSubmit={saveDraft}>
              <div className="card-head">
                <div>
                  <p className="label">Provider settings</p>
                  <h2>
                    {editing &&
                    sessions.some((session) => session.id === editing)
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
                    {draft.credentialId &&
                      !credentials.some(
                        (item) => item.credential_id === draft.credentialId,
                      ) && (
                        <option value={draft.credentialId}>
                          API key unavailable
                        </option>
                      )}
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
              <p className="editor-note">
                Add or replace keys in the API keys section above.
              </p>
              <button className="run-button save-session">
                Save configuration <Icon name="arrow" size={14} />
              </button>
            </form>
          ) : null}
        </div>
      </section>
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}
