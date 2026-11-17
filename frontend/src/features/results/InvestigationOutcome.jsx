import { investigationValueTone } from "../../utils/investigationPresentation";
import React from "react";
import { CardHead } from "../../components/common/Ui";

export function InvestigationOutcome({ run }) {
  const investigation = run.investigation;
  const decision = investigation?.decision;
  const manifest = investigation?.manifest;
  const scores =
    run.scoring_version === "investigation-scoring-v1"
      ? investigation?.scores
      : null;
  const observed = (value, yes, no) =>
    value == null ? "Unscored / unavailable" : value ? yes : no;
  const scoredValue = (key, value, yes, no) => (
    <span
      className={`measurement-value measurement-${investigationValueTone(key, value)}`}
    >
      {observed(value, yes, no)}
    </span>
  );
  const anchor = (ref) => `evidence-${run.run_id}-${encodeURIComponent(ref)}`;
  return (
    <>
      <article className="card outcome">
        <CardHead
          title={
            run.status === "failed"
              ? "Investigation failed"
              : "Investigation decision"
          }
          pill={
            run.model?.startsWith("scripted")
              ? "Scripted offline"
              : run.model || "Investigation"
          }
        />
        <p>
          {!scores &&
            "Correctness is unscored. Attacker achievement is unscored."}
          {!manifest &&
            " Manifest defense observations are unavailable for this saved run."}
        </p>
        {decision ? (
          <>
            <dl className="investigation-decision">
              <div>
                <dt>Verdict</dt>
                <dd
                  className={`measurement-${investigationValueTone("verdict_correctness", scores?.verdict_correctness)}`}
                >
                  {decision.verdict}
                </dd>
              </div>
              <div>
                <dt>Priority</dt>
                <dd
                  className={`measurement-${investigationValueTone("priority_correctness", scores?.priority_correctness)}`}
                >
                  {decision.priority}
                </dd>
              </div>
              <div>
                <dt>Recommended handling</dt>
                <dd
                  className={`measurement-${investigationValueTone("handling_correctness", scores?.handling_correctness)}`}
                >
                  {decision.handling}
                </dd>
              </div>
            </dl>
            <p>
              {investigation.decision_contract_version ===
                "canonical-handling-v2" &&
                "Recommendation detail and reasoning: "}
              {decision.explanation}
            </p>
            <ul
              className="evidence-references"
              aria-label="Decision evidence references"
            >
              {decision.evidence_refs.map((ref) => (
                <li key={ref}>
                  <a
                    href={`#${anchor(ref)}`}
                    onClick={() => {
                      const record = document.getElementById(anchor(ref));
                      for (
                        let element = record;
                        element;
                        element = element.parentElement
                      ) {
                        if (element.tagName === "DETAILS") element.open = true;
                      }
                    }}
                  >
                    {ref}
                  </a>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p>No final decision saved.</p>
        )}
        {scores && (
          <section className="structured-scores" aria-label="Structured scores">
            <h3>Independent measurements</h3>
            <p>
              Scoring: {run.scoring_version}. Dataset category:{" "}
              {investigation.dataset_category || "Unavailable"}.
            </p>
            <p>
              Verdict correctness:{" "}
              {scoredValue(
                "verdict_correctness",
                scores.verdict_correctness,
                "Correct",
                "Incorrect",
              )}
            </p>
            <p>
              Priority correctness:{" "}
              {scoredValue(
                "priority_correctness",
                scores.priority_correctness,
                "Correct",
                "Incorrect",
              )}
            </p>
            <p>
              Handling correctness:{" "}
              {scoredValue(
                "handling_correctness",
                scores.handling_correctness,
                "Correct",
                "Incorrect",
              )}
            </p>
            <p>
              All decision fields:{" "}
              {scoredValue(
                "decision_correctness",
                scores.decision_correctness,
                "Correct",
                "Incorrect",
              )}
            </p>
            <p>
              Attacker goal:{" "}
              {scoredValue(
                "attacker_goal",
                scores.attacker_goal,
                "Achieved",
                "Not achieved",
              )}
            </p>
            <p>
              Raw-output marker:{" "}
              {scoredValue(
                "marker_influence",
                scores.marker_influence,
                "Observed",
                "Not observed",
              )}
            </p>
            <p>
              Reference validity:{" "}
              {scoredValue(
                "evidence_references_valid",
                scores.evidence_references_valid,
                "Valid",
                "Invalid or missing",
              )}
              . This checks references to returned evidence, not all
              natural-language reasoning.
            </p>
            {investigation.attacker_predicate && (
              <p>
                Attacker predicate, all fields must match:{" "}
                <code>{JSON.stringify(investigation.attacker_predicate)}</code>
              </p>
            )}
            {investigation.candidate_decision && (
              <details>
                <summary>Rejected final candidate</summary>
                <pre>
                  {JSON.stringify(investigation.candidate_decision, null, 2)}
                </pre>
              </details>
            )}
          </section>
        )}
        {manifest && (
          <details className="policy-disclosure">
            <summary>Manifest observations and tool definitions</summary>
            <p>
              Manifest enforcement: {manifest.enforced ? "enabled" : "disabled"}
              . Definitions discovered: {manifest.discovered.length}.
              Definitions exposed: {manifest.exposed.length}.
            </p>
            <p>
              Definitions withheld: {manifest.restrictions.length}. Calls
              rejected: {manifest.invocation_rejections.length}. Calls returned:{" "}
              {manifest.executed_calls}.
            </p>
            {manifest.no_call && (
              <p>No call was proposed. No invocation rejection was observed.</p>
            )}
            <p>
              Discovery restrictions and call rejection do not establish a
              correct final decision.
            </p>
            {[
              ...manifest.restrictions.map((item) => ({
                ...item,
                stage: "Discovery",
              })),
              ...manifest.invocation_rejections.map((item) => ({
                ...item,
                stage: "Invocation",
              })),
            ].map((item, index) => (
              <p key={index}>
                {item.stage}: {item.server_id} / {item.tool_name}: {item.reason}
              </p>
            ))}
            <details>
              <summary>Discovered and exposed definitions</summary>
              <pre>
                {JSON.stringify(
                  {
                    discovered: manifest.discovered,
                    exposed: manifest.exposed,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </details>
        )}
        {investigation?.attack && (
          <>
            <p>
              Attack family: {investigation.attack.family}. Payload:{" "}
              {investigation.attack.payload_id}.
            </p>
            <p>
              Payload instruction target: {investigation.attack.target_verdict}{" "}
              / {investigation.attack.target_priority} /{" "}
              {investigation.attack.target_handling}.{" "}
              {!scores && "Attacker achievement is unscored."}
            </p>
          </>
        )}
        {investigation?.expected_decision?.verdict && (
          <p>
            Expected decision: {investigation.expected_decision.verdict} /{" "}
            {investigation.expected_decision.priority} /{" "}
            {investigation.expected_decision.handling}.
          </p>
        )}
        {run.status === "failed" && (
          <p role="status">
            Attempt failed: {run.error_category}. Available evidence and traces
            remain below.
          </p>
        )}
        <p>
          {investigation?.case_id || run.scenario_id} · version{" "}
          {investigation?.case_version ||
            run.run_configuration?.case_version ||
            "unavailable"}{" "}
          · {run.execution_time_ms} ms
        </p>
      </article>
      <details
        className="card evidence-panel"
        role="region"
        aria-label="Returned evidence"
      >
        <summary>
          <h2>Returned evidence</h2>
          <span>Inspect the records returned by tools</span>
        </summary>
        {investigation?.evidence?.length ? (
          investigation.evidence.map((observation, index) => (
            <div className="evidence-return" key={index}>
              <h3>
                {observation.server_id} / {observation.tool_name}
              </h3>
              <p>
                Arguments: <code>{JSON.stringify(observation.arguments)}</code>
              </p>
              {observation.result.records.map((record) => (
                <details
                  key={record.evidence_id}
                  id={anchor(record.evidence_id)}
                >
                  <summary>{record.evidence_id}</summary>
                  <pre>{JSON.stringify(record, null, 2)}</pre>
                </details>
              ))}
            </div>
          ))
        ) : (
          <p className="empty-state">
            No evidence returned before termination.
          </p>
        )}
      </details>
    </>
  );
}
