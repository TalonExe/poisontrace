import React, { useState } from "react";
import { CardHead, Icon } from "../../components/common/Ui";
import { outcomePresentation } from "../../utils/outcomePresentation";
import { InvestigationOutcome } from "./InvestigationOutcome";

export function RunInspection({ selectedRun }) {
  const [traceOpen, setTraceOpen] = useState(false);
  const selectedOutcomes = outcomePresentation(selectedRun);
  const investigation = [
    "investigation-unscored-v1",
    "investigation-scoring-v1",
  ].includes(selectedRun.scoring_version);
  return (
    <>
      {investigation ? (
        <InvestigationOutcome run={selectedRun} />
      ) : (
        <article className="card outcome">
          <CardHead
            label="Security outcome"
            title={selectedRun?.result || "No run yet"}
            pill={selectedRun ? "Recorded" : "Waiting"}
            tone={selectedRun?.tone || "green"}
          />
          <p>
            Recommendation correctness compares exact values only. It does not
            establish evidence-based investigation.
          </p>
          {selectedRun?.status === "failed" && (
            <p role="status">
              Attempt failed: {selectedRun.error_category}. Security and
              recommendation outcomes are unscored.
            </p>
          )}
          <div className="outcome-main">
            <strong>
              {selectedRun?.recommendation || "No outcome recorded"}
            </strong>
            <p>
              {selectedRun
                ? `${selectedRun.execution_time_ms} ms · ${selectedRun.system_error ? "System error" : "No system error"}`
                : "Run a scenario to view the persisted outcome."}
            </p>
          </div>
          <div className="stat-row">
            <div>
              <small>Marker influence</small>
              <strong
                className={
                  selectedRun?.marker_influence ? "text-red" : undefined
                }
              >
                {selectedRun ? selectedOutcomes.injection : "—"}
              </strong>
            </div>
            <div>
              <small>Recommendation correctness</small>
              <strong>{selectedRun ? selectedOutcomes.task : "—"}</strong>
            </div>
            <div>
              <small>Simulated gateway</small>
              <strong>{selectedRun ? selectedOutcomes.defense : "—"}</strong>
            </div>
            <div>
              <small>Attacker goal</small>
              <strong>{selectedRun ? selectedOutcomes.attacker : "—"}</strong>
            </div>
            <div>
              <small>System/model</small>
              <strong>{selectedRun ? selectedOutcomes.system : "—"}</strong>
            </div>
            <div>
              <small>Duration</small>
              <strong>
                {selectedRun ? `${selectedRun.execution_time_ms} ms` : "—"}
              </strong>
            </div>
          </div>
        </article>
      )}
      <details className="card trace">
        <summary>
          <h2>Recorded trace</h2>
          <span>Inspect the ordered events for this attempt</span>
        </summary>
        <div className="timeline">
          {selectedRun?.trace?.length ? (
            selectedRun.trace.map((event, index) => (
              <div key={`${event.kind}-${index}`}>
                <time>{index + 1}</time>
                <i
                  className={event.kind === "policy_decision" ? "red" : "cyan"}
                />
                <p>
                  <strong>{event.kind.replaceAll("_", " ")}</strong>
                  <small>
                    {Object.entries(event.data)
                      .map(
                        ([key, value]) =>
                          `${key}: ${typeof value === "object" ? JSON.stringify(value) : value}`,
                      )
                      .join(" · ")}
                  </small>
                </p>
              </div>
            ))
          ) : (
            <p className="empty-state">No persisted trace events.</p>
          )}
        </div>
        <button className="link-button" onClick={() => setTraceOpen(true)}>
          Open full trace <Icon name="arrow" size={12} />
        </button>
        {traceOpen && (
          <div
            className="trace-placeholder"
            role="region"
            aria-label="Trace inspection"
          >
            <div className="card-head">
              <div>
                <p className="label">Trace inspection</p>
                <h2>{selectedRun?.id || "Selected run"}</h2>
              </div>
              <button
                className="icon-button"
                onClick={() => setTraceOpen(false)}
                aria-label="Close trace"
              >
                <Icon name="close" size={16} />
              </button>
            </div>
            <p>Recorded events for the selected experiment.</p>
            <div className="placeholder-events">
              {selectedRun?.trace?.map((event, index) => (
                <div key={`${event.kind}-full-${index}`}>
                  <i className="cyan" />
                  <span>{event.kind.replaceAll("_", " ")}</span>
                  <small>{JSON.stringify(event.data)}</small>
                </div>
              ))}
            </div>
          </div>
        )}
      </details>
    </>
  );
}
