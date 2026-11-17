import React, { useState } from 'react';
import { formatRate } from '../../utils/measurementPresentation';

const conditionNames = { clean: 'Clean', poisoned: 'Poisoned', defended: 'Defended' };
const modelMeasures = [
  ['attacker_goal', 'Attacker goal'],
  ['marker_influence', 'Marker influence'],
  ['recommendation_correctness', 'Recommendation correctness'],
];
const gatewayMeasures = [
  ['definition_mismatch_detection', 'Mismatch detection'],
  ['call_rejection', 'Proposed-call rejection'],
];

function RateGroup({ title, measures, condition, note }) {
  return <section className="measurement-group" aria-label={title}>
    <h3>{title}</h3>
    {note && <p className="measurement-group-note">{note}</p>}
    <dl className="measurement-rates">
      {measures.map(([key, name]) => <div key={key}>
        <dt>{name}</dt><dd>{formatRate(condition[key])}</dd>
      </div>)}
    </dl>
  </section>;
}

export function MeasurementSummary({ metrics, label = 'Recorded rates by condition' }) {
  const [selection, setSelection] = useState(null);
  if (!metrics?.by_condition) return <p className="empty-state">Measurement summary unavailable.</p>;
  const conditions = Object.keys(metrics.by_condition).filter(name => metrics.by_condition[name].attempted > 0);
  const active = conditions.includes(selection) ? selection : conditions[0];
  const condition = metrics.by_condition[active];
  return <details className="measurement-summary">
    <summary>{label}</summary>
    <ul className="measurement-totals" aria-label="Run counts">
      <li><strong>{metrics.attempted}</strong> attempts</li>
      <li><strong>{metrics.completed}</strong> completed</li>
      <li><strong>{metrics.failed}</strong> failed</li>
    </ul>
    {condition ? <>
      <div className="measurement-conditions" role="group" aria-label="Measurement condition">
        {conditions.map(name => <button type="button" key={name} aria-pressed={active === name} onClick={() => setSelection(name)}>
          {conditionNames[name] || name}
        </button>)}
      </div>
      <p className="measurement-condition-counts">{condition.attempted} {condition.attempted === 1 ? 'attempt' : 'attempts'} in {conditionNames[active] || active} · {condition.completed} completed · {condition.failed} failed</p>
      <div className="measurement-groups">
        <RateGroup title="Model outcomes" measures={modelMeasures} condition={condition} />
        <RateGroup title="Gateway decisions" condition={condition}
          measures={active === 'clean' ? [...gatewayMeasures, ['inappropriate_clean_block', 'Inappropriate clean blocking']] : gatewayMeasures} />
        <RateGroup title="Reliability" measures={[['system_error', 'System error']]} condition={condition} />
      </div>
    </> : <p>No recorded attempts yet.</p>}
    <div className="measurement-coverage">{metrics.legacy} legacy or other scoring versions · {metrics.unscored} with unavailable outcomes</div>
    <details className="measurement-methods">
      <summary>How to read these rates</summary>
      <ul>
        <li>Counts in parentheses show observed outcomes / eligible trials. Not applicable means no eligible trials.</li>
        <li>Model and gateway rates use completed, compatible records. System error includes all attempts.</li>
        <li>Gateway rates include no-call trials. Clean blocking excludes unknown rejection appropriateness.</li>
        <li>These are pooled history rates, not matched effectiveness comparisons. Correct recommendations do not establish evidence-based investigation.</li>
      </ul>
      {condition && <p>Selected condition: {condition.legacy} records outside metadata scoring; {condition.unscored_attacker_goal} completed attacker goals unscored; {condition.unscored_false_positive} clean-block outcomes unavailable.</p>}
    </details>
  </details>;
}
