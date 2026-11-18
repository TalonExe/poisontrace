import React, { useEffect, useState } from "react";
import { loadSessions } from "../../utils/sessions";
import {
  executionModels,
  resolveExecution,
} from "../../utils/executionSelection";

export function useExecutionOptions(runner) {
  const [configurations, setConfigurations] = useState(() =>
    loadSessions(window.localStorage),
  );
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setConfigurations(loadSessions(window.localStorage));
    setCredentials([]);
    setLoading(true);
    setError("");
    runner
      .listCredentials()
      .then((items) => {
        if (active) setCredentials(items);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runner, revision]);
  return {
    configurations,
    credentials,
    loading,
    error,
    reload: () => setRevision((n) => n + 1),
  };
}

export function ExecutionSelection({
  selection,
  onChange,
  options,
  required,
  disabled = false,
}) {
  const execution = resolveExecution(
    selection,
    options.configurations,
    options.credentials,
    required,
  );
  const credential = options.credentials.find(
    (c) => c.credential_id === execution.credentialId,
  );
  const offlineOnly = required?.provider === "scripted";
  const value = offlineOnly ? "scripted" : selection;
  return (
    <section className="execution-selection" aria-label="Execution selection">
      {required && (
        <p>
          Saved group model: {required.provider} · {required.model}. The rerun
          keeps this model.
        </p>
      )}
      <label className="field">
        <span>Execution model and credential</span>
        <select
          value={value}
          disabled={disabled || offlineOnly}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="scripted" disabled={Boolean(required && !offlineOnly)}>
            Scripted offline · no key
          </option>
          {!offlineOnly &&
            options.configurations.map((c) => (
              <option
                key={c.id}
                value={`config:${c.id}`}
                disabled={Boolean(required && c.model !== required.provider)}
              >
                {c.name} ·{" "}
                {required?.provider === c.model
                  ? required.model
                  : executionModels[c.model] || c.model}{" "}
                · {c.credentialId ? "saved credential" : "no credential"}
              </option>
            ))}
          {!offlineOnly &&
            selection !== "scripted" &&
            !options.configurations.some(
              (c) => `config:${c.id}` === selection,
            ) && (
              <option value={selection}>
                Configuration no longer available
              </option>
            )}
        </select>
      </label>
      <p>
        {execution.provider === "scripted"
          ? "No API key used."
          : execution.valid
            ? `${execution.model} · Credential: ${credential?.label || "Saved reference"}${credential?.masked ? ` · ${credential.masked}` : ""}`
            : options.loading
              ? "Loading saved credential references…"
              : `Matching ${required?.provider || execution.provider || "provider"} credential required. Select a configuration with a current matching credential.`}
      </p>
      {options.error && execution.provider !== "scripted" && (
        <p role="alert">{options.error}</p>
      )}
      <div className="execution-recovery">
        <button
          type="button"
          className="text-button"
          disabled={disabled || options.loading}
          onClick={options.reload}
        >
          Reload execution options
        </button>
        <a href="/sessions" target="_blank" rel="noreferrer">
          Manage configurations and credentials (opens a new tab)
        </a>
      </div>
    </section>
  );
}
