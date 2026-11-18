import { InvestigationRate } from "./InvestigationRate";
import React, { useState } from "react";
import { formatRate } from "../../utils/measurementPresentation";

export function InvestigationMeasurements({ metrics }) {
  const [selected, setSelected] = useState(null);
  if (!metrics) return null;
  const names = Object.keys(metrics.by_condition).filter(
    (key) => metrics.by_condition[key].attempted > 0,
  );
  const active = names.includes(selected) ? selected : names[0];
  const condition = metrics.by_condition[active];
  const groups = [
    [
      "Structured decisions",
      [
        ["verdict_correctness", "Verdict correctness"],
        ["priority_correctness", "Priority correctness"],
        ["handling_correctness", "Handling correctness"],
        ["decision_correctness", "All decision fields"],
        ["attacker_goal", "Attacker-target matches"],
      ],
    ],
    [
      "Policy, marker and reference observations",
      [
        ["evidence_references_valid", "Evidence-reference membership"],
        ["marker_influence", "Raw-output marker"],
        ["discovery_restriction", "Discovery restriction"],
        ["invocation_rejection", "Invocation rejection"],
      ],
    ],
    ["Reliability", [["system_error", "System error"]]],
  ];
  return (
    <details className="measurement-summary">
      <summary>MCP investigation rates</summary>
      <section role="region" aria-label="MCP scoring rates">
        <p>
          {metrics.attempted} attempts · {metrics.completed} completed ·{" "}
          {metrics.failed} failed · {metrics.historical_unscored} historical
          unscored
        </p>
        {condition ? (
          <>
            <div
              className="measurement-conditions"
              role="group"
              aria-label="MCP measurement condition"
            >
              {names.map((name) => (
                <button
                  type="button"
                  key={name}
                  aria-pressed={name === active}
                  onClick={() => setSelected(name)}
                >
                  {name}
                </button>
              ))}
            </div>
            <div className="measurement-groups">
              {groups.map(([title, measures]) => (
                <section className="measurement-group" key={title}>
                  <h3>{title}</h3>
                  <dl className="measurement-rates">
                    {measures.map(([key, label]) => (
                      <div key={key}>
                        <dt>{label}</dt>
                        <dd>
                          <InvestigationRate
                            measure={key}
                            value={condition[key]}
                            label={formatRate(condition[key])}
                          />
                        </dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ))}
            </div>
          </>
        ) : (
          <p>No MCP attempts recorded yet.</p>
        )}
        <p>
          Decision and marker rates use completed investigation-scoring-v1
          records with available outcomes. Clean or missing attacker targets are
          not applicable. Evidence-reference membership includes observed final candidates
          with rejected references. Membership in returned evidence does not establish that the explanation is true. Target matches do not establish injection causation.
        </p>
        <p>
          Policy rates include failed attempts only where the corresponding
          manifest stage was observed. Withheld definitions and rejected calls
          are separate. Reliability includes all saved MCP attempts; invalid
          configuration is not an attempt. These are pooled history rates, not
          matched comparisons.
        </p>
      </section>
    </details>
  );
}
