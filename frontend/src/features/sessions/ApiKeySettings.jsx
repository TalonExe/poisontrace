import React, { useEffect, useRef, useState } from "react";
import { ConfirmationAction } from "../../components/common/ConfirmationAction";
import { PendingButton } from "../../components/common/PendingButton";

export function ApiKeySettings({
  credentials,
  loading,
  loadError,
  onReload,
  onSave,
  onRevoke,
}) {
  const [provider, setProvider] = useState("gemini");
  const [label, setLabel] = useState("");
  const [secret, setSecret] = useState("");
  const [replacement, setReplacement] = useState(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState(null);
  const secretInput = useRef(null);
  const updating = pending || loading;

  useEffect(() => {
    if (replacement) secretInput.current?.focus();
  }, [replacement]);

  const save = async (event) => {
    event.preventDefault();
    if (updating || !secret.trim()) return;
    setPending(true);
    setNotice(null);
    try {
      await onSave({ provider, label, secret }, replacement);
      setNotice({ text: replacement ? "API key replaced." : "API key added." });
      setReplacement(null);
      setLabel("");
      setSecret("");
    } catch {
      setNotice({
        error: true,
        text: "Could not save the API key. Check the details and try again.",
      });
    } finally {
      setPending(false);
    }
  };

  return (
    <section
      className="card api-key-settings"
      aria-labelledby="api-keys-heading"
    >
      <div>
        <h2 id="api-keys-heading">API keys</h2>
        <p>Use your own key to run investigations with Gemini or OpenAI.</p>
        {loading && <p role="status">Loading API keys…</p>}
        {loadError && (
          <p role="alert">
            Could not load API keys.{" "}
            <button className="text-button" type="button" onClick={onReload}>
              Retry
            </button>
          </p>
        )}
        {!loading && !loadError && !credentials.length && (
          <p>No API keys saved.</p>
        )}
        <ul className="api-key-list">
          {credentials.map((credential) => {
            const name = credential.label || credential.provider;
            return (
              <li className="credential-row" key={credential.credential_id}>
                <div>
                  <strong>{name}</strong>
                  <small>
                    {credential.provider === "gemini" ? "Gemini" : "OpenAI"}{" "}
                    {credential.masked}
                  </small>
                </div>
                <div className="settings-actions">
                  <button
                    className="text-button"
                    type="button"
                    disabled={updating || Boolean(replacement)}
                    aria-label={`Replace ${name}`}
                    onClick={() => {
                      setReplacement(credential.credential_id);
                      setProvider(credential.provider);
                      setLabel(credential.label || "");
                      setSecret("");
                      setNotice(null);
                    }}
                  >
                    Replace
                  </button>
                  <ConfirmationAction
                    disabled={updating || Boolean(replacement)}
                    triggerLabel={`Revoke ${name}`}
                    title={`Revoke ${name}?`}
                    description="Saved configurations using this key will need another API key."
                    confirmLabel="Revoke API key"
                    errorMessage="Could not revoke the API key. Try again."
                    onConfirm={() => { setNotice(null); return onRevoke(credential.credential_id); }}
                    onSuccess={() => setNotice({ text: "API key revoked." })}
                  >
                    Revoke
                  </ConfirmationAction>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
      <form className="api-key-form" onSubmit={save}>
        <h3>{replacement ? "Replace a key" : "Add a key"}</h3>
        <label className="field">
          <span>Provider</span>
          <select
            value={provider}
            disabled={pending || Boolean(replacement)}
            onChange={(event) => setProvider(event.target.value)}
          >
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
          </select>
        </label>
        <label className="field">
          <span>Key label</span>
          <input
            value={label}
            disabled={pending}
            onChange={(event) => setLabel(event.target.value)}
          />
        </label>
        <label className="field">
          <span>{replacement ? "New API key" : "API key"}</span>
          <input
            ref={secretInput}
            type="password"
            autoComplete="new-password"
            required
            value={secret}
            disabled={pending}
            onChange={(event) => setSecret(event.target.value)}
          />
        </label>
        <div className="settings-actions">
          <PendingButton
            className="small-button"
            type="submit"
            pending={pending}
            disabled={updating || !secret.trim()}
          >
            {replacement ? "Replace API key" : "Add API key"}
          </PendingButton>
          {replacement && (
            <button
              className="text-button"
              type="button"
              disabled={pending}
              onClick={() => {
                setReplacement(null);
                setLabel("");
                setSecret("");
                setNotice(null);
              }}
            >
              Cancel
            </button>
          )}
        </div>
        {pending && <p role="status">Updating API keys…</p>}
        {notice && (
          <p role={notice.error ? "alert" : "status"}>{notice.text}</p>
        )}
      </form>
    </section>
  );
}
