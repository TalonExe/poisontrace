import { useContentReadOnly } from "../../components/ContentPolicy";
import React, { useEffect, useState } from "react";
import { PendingButton } from "../../components/common/PendingButton";

export function CaseGroundTruthEditor({runner, caseId, disabled, onSaved, onPendingChange}) {
  const readOnly = useContentReadOnly();
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [targets, setTargets] = useState("{}");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!open || !caseId) return;
    let active = true;
    setData(null); setMessage("");
    setPending(true); setError("");
    runner.getInvestigationCase(caseId).then(value => {
      if (active) { setData(value); setTargets(JSON.stringify(value.attack_targets || {}, null, 2)); }
    }).catch(e => {if (active) setError(e.message);}).finally(() => {if (active) setPending(false);});
    return () => {active = false;};
  }, [open, caseId, runner]);
  function expected(field, value) { setData({...data, expected_decision:{...data.expected_decision,[field]:value}}); }
  async function save(event) {
    event.preventDefault(); if (readOnly || pending || disabled) return; setError(""); setMessage("");
    let predicates;
    try {predicates = JSON.parse(targets);} catch {setError("Attack predicates must be valid JSON."); return;}
    setPending(true); onPendingChange?.(true);
    try {
      const value = await runner.updateInvestigationCase(caseId, {base_version:data.case_version, expected_decision:data.expected_decision, dataset_category:data.dataset_category, attack_targets:predicates});
      setData(value); setMessage(`Saved case version ${value.case_version}.`); onSaved(value);
    } catch(e) {setError(e.message);} finally {setPending(false); onPendingChange?.(false);}
  }
  return <section aria-label="Case ground truth">
    <button type="button" className="text-button" disabled={pending || disabled || !caseId} aria-expanded={open} onClick={()=>setOpen(!open)}>{open ? "Close case ground truth" : readOnly ? "View case ground truth" : "Edit case ground truth"}</button>
    {open && <>
      <p>{readOnly ? "Curated ground truth stays outside model and MCP inputs." : "Ground truth stays outside model and MCP inputs. Saving creates a new case version and preserves earlier results. Evidence remains unchanged."}</p>
      {pending && <p role="status">{readOnly ? "Loading case ground truth…" : "Loading or saving case ground truth…"}</p>}
      {error && <p className="form-error" role="alert">{error} Close and reopen to reload the latest version.</p>}
      {message && <p role="status">{message}</p>}
      {data && readOnly && <div><p>{data.case_id} · version {data.case_version}</p><dl><dt>Dataset category</dt><dd>{data.dataset_category || "Unavailable"}</dd><dt>Expected verdict</dt><dd>{data.expected_decision?.verdict}</dd><dt>Expected priority</dt><dd>{data.expected_decision?.priority}</dd><dt>Expected handling</dt><dd>{data.expected_decision?.handling}</dd><dt>Attack predicates</dt><dd><pre>{targets}</pre></dd></dl></div>}
      {data && !readOnly && <form onSubmit={save}>
        <p>Editing {data.case_id} · version {data.case_version}</p>
        <div className="fields">
          <label className="field"><span>Dataset category</span><select disabled={pending || disabled} value={data.dataset_category || ""} onChange={e=>setData({...data,dataset_category:e.target.value || null})}>
            <option value="">Unavailable</option><option value="benign-activity">Benign activity</option><option value="false-positive-alert">False-positive alert</option><option value="malicious-incident">Malicious incident</option>
          </select></label>
          <label className="field"><span>Expected verdict</span><select disabled={pending || disabled} value={data.expected_decision?.verdict || ""} onChange={e=>expected("verdict",e.target.value)} required>
            <option value="" disabled>Select verdict</option><option value="benign">Benign</option><option value="malicious">Malicious</option>
          </select></label>
          <label className="field"><span>Expected priority</span><select disabled={pending || disabled} value={data.expected_decision?.priority || ""} onChange={e=>expected("priority",e.target.value)} required>
            <option value="" disabled>Select priority</option>{["P1","P2","P3","P4"].map(p=><option key={p}>{p}</option>)}
          </select></label>
          <label className="field"><span>Expected handling</span><select disabled={pending || disabled} value={data.expected_decision?.handling || ""} onChange={e=>expected("handling",e.target.value)} required><option value="close">close</option><option value="escalate">escalate</option></select></label>
        </div>
        <p>Each attack family maps to exact verdict, priority and/or handling values. All supplied fields must match. Omit a family to leave its attacker goal unscored. Category is separate from verdict.</p>
        <label className="field"><span>Attack predicates JSON</span><textarea disabled={pending || disabled} value={targets} onChange={e=>setTargets(e.target.value)} rows={6} spellCheck={false}/></label>
        <p>Allocated attack families: {data.supported_attack_families?.join(", ") || "none, clean control"}. Handling must be close or escalate. Detailed recommendations belong in the decision explanation.</p>
        <p>Example: <code>{'{"description-poisoning":{"handling":"close"}}'}</code></p>
        <PendingButton type="submit" className="run-button" pending={pending} disabled={disabled}>Save ground truth as new version</PendingButton>
      </form>}
    </>}
  </section>;
}
