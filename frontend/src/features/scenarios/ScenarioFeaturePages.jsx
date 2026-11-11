import React, { useEffect, useState } from "react";

export function ScenarioLibrary({
  adapter,
  onOpen,
  onNew,
  onDashboard,
  onSignOut,
}) {
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
  const removeSelected = async () => {
    const targets = items.filter((item) =>
      selected.includes(item.scenario_id || item.filename),
    );
    const filenames = targets.map((item) => item.filename).join(", ");
    if (
      !targets.length ||
      !window.confirm(
        `Delete scenario file${targets.length === 1 ? "" : "s"} ${filenames}?`,
      )
    )
      return;
    try {
      await Promise.all(
        targets.map((item) =>
          adapter.deleteScenario(item.scenario_id || item.filename),
        ),
      );
      setItems(
        items.filter(
          (item) => !selected.includes(item.scenario_id || item.filename),
        ),
      );
      setSelected([]);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <main className="app-shell">
      <section className="welcome">
        <div>
          <h1>Scenario library</h1>
          <p>Only valid scenarios can be used for runs and campaigns.</p>
        </div>
        <div>
          <button className="run-button" onClick={onNew}>
            New scenario ↗
          </button>
          {selected.length > 0 && (
            <button className="text-button" onClick={removeSelected}>
              Delete selected ({selected.length})
            </button>
          )}
        </div>
      </section>
      <section className="card scenario-library">
        <div className="card-head">
          <div>
            <p className="label">Local definitions</p>
            <h2>{items.length} file{items.length === 1 ? "" : "s"}</h2>
          </div>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {!items.length && !error && (
          <p className="empty-state">No scenarios loaded, make one.</p>
        )}
        {items.map((item) => {
          const id = item.scenario_id || item.filename;
          return (
            <div className="scenario-row" key={item.filename}>
              <input
                type="checkbox"
                aria-label={`Select ${item.filename} for deletion`}
                checked={selected.includes(id)}
                onChange={() => toggle(id)}
              />
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
  const [draft, setDraft] = useState(null);
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
      : adapter.getScenario(scenarioId).then((item) => item.document || item)
    )
      .then(setDraft)
      .catch((err) => setError(err.message));
  }, [adapter, scenarioId, isNew]);
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
    if (saving) return;
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
  const remove = async () => {
    const filename = draft.filename || `${scenarioId}.yaml`;
    if (!window.confirm(`Delete scenario file ${filename}?`)) return;
    try {
      await adapter.deleteScenario(scenarioId);
      onDeleted();
    } catch (err) {
      setError(err.message);
    }
  };
  const toolList = (list, label) => (
    <fieldset className="tool-list">
      <legend>{label}</legend>
      {(draft[list] || []).map((tool, index) => (
        <div className="tool-editor" key={`${list}-${index}`}>
          <label className="field">
            <span>Name</span>
            <input
              value={tool.name || ""}
              onChange={(event) =>
                editTool(list, index, "name", event.target.value)
              }
            />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              rows="3"
              value={tool.description || ""}
              onChange={(event) =>
                editTool(list, index, "description", event.target.value)
              }
            />
          </label>
          <button
            type="button"
            className="text-button"
            onClick={() => removeTool(list, index)}
          >
            Remove tool
          </button>
        </div>
      ))}
      <button
        type="button"
        className="text-button"
        onClick={() => addTool(list)}
      >
        + Add tool
      </button>
    </fieldset>
  );
  return (
    <main className="app-shell">
      <section className="welcome">
        <div>
          <h1>{isNew ? "Create scenario" : "Edit scenario"}</h1>
          <p>
            Edit discovered metadata and the separate trusted manifest used for
            comparison.
          </p>
        </div>
      </section>
      <form className="card scenario-editor" onSubmit={save}>
        <label className="field">
          <span>Name</span>
          <input
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
            rows="3"
            value={draft.alert || ""}
            onChange={(event) => update("alert", event.target.value)}
          />
        </label>
        <label className="field">
          <span>Expected recommendation</span>
          <input
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
        <button className="run-button" type="submit" disabled={saving}>
          Save scenario ↗
        </button>
        {!isNew && (
          <button type="button" className="text-button" onClick={remove}>
            Delete scenario
          </button>
        )}
        <button type="button" className="text-button" onClick={onBack}>
          Back to library
        </button>
      </form>
    </main>
  );
}
