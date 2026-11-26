import { useContentReadOnly, readOnlyContentMessage } from "../../components/ContentPolicy";
import React, { useEffect, useState } from "react";
import { ConfirmationAction } from "../../components/common/ConfirmationAction";
import { PendingButton } from "../../components/common/PendingButton";

export function ScenarioLibrary({
  adapter,
  onOpen,
  onNew,
  onDashboard,
  onSignOut,
}) {
  const readOnly = useContentReadOnly();
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState([]);
  useEffect(() => {
    adapter
      .listScenarios()
      .then(setItems)
      .catch((err) => setError(err.message));
  }, [adapter]);
  const toggle = (id) =>
    setSelected((value) =>
      value.includes(id) ? value.filter((item) => item !== id) : [...value, id],
    );
  const targets = items.filter(item => selected.includes(item.scenario_id || item.filename));
  const removeSelected = async () => {
    const ids = targets.map(item => item.scenario_id || item.filename);
    const outcomes = await Promise.allSettled(ids.map(id => adapter.deleteScenario(id)));
    const deleted = new Set(ids.filter((_, index) => outcomes[index].status === "fulfilled"));
    const failure = outcomes.find(outcome => outcome.status === "rejected");
    setItems(current => current.filter(item => !deleted.has(item.scenario_id || item.filename)));
    setSelected(current => current.filter(id => !deleted.has(id)));
    if (failure) throw failure.reason;
    setError("");
  };
  return (
    <main className="app-shell">
      <section className="welcome">
        <div>
          <h1>Scenario library</h1>
          <p>YAML metadata scenarios for metadata runs and campaigns. Only valid scenarios can be used.</p>
        </div>
        <div>
          {readOnly ? <p>{readOnlyContentMessage}</p> : <button className="run-button" onClick={onNew}>
            New scenario ↗
          </button>}
          {!readOnly && selected.length > 0 && (
            <ConfirmationAction
              title={targets.length === 1 ? "Delete selected scenario file?" : "Delete selected scenario files?"}
              description={targets.map(item => item.filename).join(", ")}
              confirmLabel={targets.length === 1 ? "Delete file" : "Delete files"}
              onConfirm={removeSelected}
            >
              Delete selected ({selected.length})
            </ConfirmationAction>
          )}
        </div>
      </section>
      <section className="card scenario-library">
        <div className="card-head">
          <div>
            <p className="label">{readOnly ? "Curated definitions" : "Local definitions"}</p>
            <h2>{items.length} file{items.length === 1 ? "" : "s"}</h2>
          </div>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {!items.length && !error && (
          <p className="empty-state">{readOnly ? "No curated scenarios available." : "No scenarios loaded, make one."}</p>
        )}
        {items.map((item) => {
          const id = item.scenario_id || item.filename;
          return (
            <div className="scenario-row" key={item.filename}>
              {!readOnly && <input
                type="checkbox"
                aria-label={`Select ${item.filename} for deletion`}
                checked={selected.includes(id)}
                onChange={() => toggle(id)}
              />}
              <button
                className="scenario-row-content"
                onClick={() => onOpen(id)}
              >
                <span className="session-mark">{item.valid ? "✓" : "!"}</span>
                <span>
                  <strong>{item.name}</strong>
                  <small>
                    {item.valid
                      ? "Valid scenario"
                      : `${item.filename} · ${item.error}`}
                  </small>
                </span>
                <b className={item.valid ? "green" : "red"}>
                  {item.valid ? "Valid" : "Invalid"}
                </b>
              </button>
            </div>
          );
        })}
      </section>
      <footer>
        <span>PoisonTrace</span>
      </footer>
    </main>
  );
}

export function ScenarioEditor({
  adapter,
  scenarioId,
  isNew,
  onBack,
  onCreated,
  onDeleted,
  onSignOut,
}) {
  const readOnly = useContentReadOnly();
  const [draft, setDraft] = useState(null);
  const [filename, setFilename] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    (isNew
      ? Promise.resolve({
          name: "",
          scenario_id: "",
          alert: "",
          expected_recommendation: "escalate",
          tools: [],
          approved_tools: [],
        })
      : adapter.getScenario(scenarioId).then(item => {
          setFilename(item.filename || "");
          return item.document || item;
        })
    )
      .then(setDraft)
      .catch((err) => setError(err.message));
  }, [adapter, scenarioId, isNew]);
  if (readOnly && isNew) return <main className="app-shell"><section className="card"><h1>Scenario library</h1><p>{readOnlyContentMessage}</p><button className="text-button" onClick={onBack}>Back to library</button></section></main>;
  if (!draft)
    return (
      <main className="app-shell">
        <p className="empty-state">{error || "Loading scenario…"}</p>
      </main>
    );
  const update = (key, value) => setDraft({ ...draft, [key]: value });
  const editTool = (list, index, key, value) =>
    update(
      list,
      draft[list].map((tool, toolIndex) =>
        toolIndex === index ? { ...tool, [key]: value } : tool,
      ),
    );
  const addTool = (list) =>
    update(list, [...(draft[list] || []), { name: "", description: "" }]);
  const removeTool = (list, index) =>
    update(
      list,
      draft[list].filter((_, toolIndex) => toolIndex !== index),
    );
  const save = async (event) => {
    event.preventDefault();
    if (readOnly || saving) return;
    setSaving(true);
    setNotice("");
    try {
      const result = isNew
        ? await adapter.createScenario(draft)
        : await adapter.updateScenario(scenarioId, draft);
      setDraft(result.document || result);
      setError("");
      setNotice("Scenario saved.");
      if (isNew) onCreated(result.scenario_id);
    } catch (err) {
      setError(err.message);
    } finally { setSaving(false); }
  };
  const toolList = (list, label) => (
    <fieldset className="tool-list">
      <legend>{label}</legend>
      {(draft[list] || []).map((tool, index) => (
        <div className="tool-editor" key={`${list}-${index}`}>
          <label className="field">
            <span>Name</span>
            <input
              readOnly={readOnly}
              value={tool.name || ""}
              onChange={(event) =>
                editTool(list, index, "name", event.target.value)
              }
            />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              readOnly={readOnly}
              rows="3"
              value={tool.description || ""}
              onChange={(event) =>
                editTool(list, index, "description", event.target.value)
              }
            />
          </label>
          {!readOnly && <button
            type="button"
            className="text-button"
            onClick={() => removeTool(list, index)}
          >
            Remove tool
          </button>}
        </div>
      ))}
      {!readOnly && <button
        type="button"
        className="text-button"
        onClick={() => addTool(list)}
      >
        + Add tool
      </button>}
    </fieldset>
  );
  return (
    <main className="app-shell">
      <section className="welcome">
        <div>
          <h1>{readOnly ? "Scenario details" : isNew ? "Create scenario" : "Edit scenario"}</h1>
          <p>
            {readOnly ? readOnlyContentMessage : "Edit discovered metadata and the separate trusted manifest used for comparison."}
          </p>
        </div>
      </section>
      <form className="card scenario-editor" onSubmit={save}>
        <label className="field">
          <span>Name</span>
          <input
            readOnly={readOnly}
            required
            value={draft.name || ""}
            onChange={(event) => update("name", event.target.value)}
          />
        </label>
        {!isNew && (
          <label className="field">
            <span>Scenario ID</span>
            <input readOnly value={draft.scenario_id || scenarioId} />
          </label>
        )}
        <label className="field">
          <span>Alert</span>
          <textarea
            readOnly={readOnly}
            rows="3"
            value={draft.alert || ""}
            onChange={(event) => update("alert", event.target.value)}
          />
        </label>
        <label className="field">
          <span>Attacker target recommendation (optional)</span>
          <input readOnly={readOnly} value={draft.attacker_target_recommendation ?? ""} onChange={(event) => update("attacker_target_recommendation", event.target.value || null)} />
          <small>Exact structured value, distinct from the expected recommendation. Leave empty for marker-only smoke cases; attacker goal remains unscored.</small>
        </label>
        <label className="field">
          <span>Expected recommendation</span>
          <input
            readOnly={readOnly}
            value={draft.expected_recommendation || ""}
            onChange={(event) =>
              update("expected_recommendation", event.target.value)
            }
          />
        </label>
        {toolList("tools", "Discovered tools")}
        {toolList("approved_tools", "Approved tools")}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {notice && <p role="status">{notice}</p>}
        {!readOnly && <PendingButton className="run-button" type="submit" pending={saving}>
          Save scenario ↗
        </PendingButton>}
        {saving && <p role="status">Saving scenario…</p>}
        {!readOnly && !isNew && (
          <ConfirmationAction
            disabled={saving}
            title="Delete scenario file?"
            description={filename || draft.filename || `${scenarioId}.yaml`}
            confirmLabel="Delete file"
            onConfirm={() => adapter.deleteScenario(scenarioId)}
            onSuccess={onDeleted}
          >
            Delete scenario
          </ConfirmationAction>
        )}
        <button type="button" className="text-button" onClick={onBack}>
          Back to library
        </button>
      </form>
    </main>
  );
}
