import React from "react";
import { investigationMeasurementPresentation } from "../../utils/investigationPresentation";

export function InvestigationRate({ measure, value, label }) {
  const presentation = investigationMeasurementPresentation(measure, value);
  return (
    <>
      <span className={`measurement-value measurement-${presentation.tone}`}>
        {label}
      </span>
      {presentation.positiveText && (
        <small className="measurement-breakdown">
          <span
            className={
              presentation.positiveCount
                ? "measurement-positive"
                : "measurement-unavailable"
            }
          >
            {presentation.positiveText}
          </span>
          {" · "}
          <span
            className={
              presentation.negativeCount
                ? "measurement-negative"
                : "measurement-unavailable"
            }
          >
            {presentation.negativeText}
          </span>
        </small>
      )}
      {presentation.observationText && (
        <small>{presentation.observationText}</small>
      )}
    </>
  );
}

export function OutcomeLegend() {
  return (
    <>
      <ul className="measurement-legend" aria-label="Outcome colors">
        <li>
          <span className="measurement-positive">Green</span>: correct
          decisions, no target matches or no errors
        </li>
        <li>
          <span className="measurement-negative">Red</span>: incorrect
          decisions, target matches or errors
        </li>
        <li>
          <span className="measurement-observation">Purple</span>: policy or
          marker observations, independent of correctness
        </li>
        <li>
          <span className="measurement-unavailable">Grey</span>: unavailable or
          unscored
        </li>
      </ul>
      <p>
        A target match does not by itself prove that injection caused the
        decision. A withheld definition or an absent marker does not establish a
        correct investigation.
      </p>
    </>
  );
}
