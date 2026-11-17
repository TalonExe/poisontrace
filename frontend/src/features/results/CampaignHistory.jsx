import React, { useEffect, useState } from "react";
import { CardHead } from "../../components/common/Ui";
import { outcomePresentation } from "../../utils/outcomePresentation";
import { MeasurementSummary } from "../dashboard/MeasurementSummary";

export function CampaignHistory({
  campaigns,
  error,
  loading,
  runner,
  campaignId,
  onSelect,
  onRun,
}) {
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [selectedScenarioIndex, setSelectedScenarioIndex] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [rerunning, setRerunning] = useState("");
  const [rerunError, setRerunError] = useState("");
  useEffect(() => {
    let active = true;
    setSelectedCampaign(null);
    setSelectedScenarioIndex(null);
    setDetailError("");
    setRerunError("");
    setDetailLoading(Boolean(campaignId));
    if (campaignId)
      runner
        .getCampaign(campaignId)
        .then((value) => {
          if (active) setSelectedCampaign(value);
        })
        .catch((error) => {
          if (active) setDetailError(error.message);
        })
        .finally(() => {
          if (active) setDetailLoading(false);
        });
    return () => {
      active = false;
    };
  }, [runner, campaignId, attempt]);
  const selectedScenario = selectedCampaign?.scenarios?.[selectedScenarioIndex];
  const rerun = async (id, ordinal) => {
    setRerunning(`${id}:${ordinal}`);
    setRerunError("");
    try {
      setSelectedCampaign(await runner.rerunCampaignScenario(id, ordinal));
    } catch (error) {
      setRerunError(error.message);
    } finally {
      setRerunning("");
    }
  };
  return (
    <section className="campaign-workspace">
      <div className="campaign-history-panel">
        <CardHead label="Batch campaign" title="Campaign history" />
        <p className="campaign-intro">
          Select a campaign, then choose a scenario to inspect its result.
        </p>
        {loading && <p role="status">Loading campaign history…</p>}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {!error && !loading && campaigns.length === 0 && (
          <p className="empty-state campaign-empty">
            No campaigns recorded yet.
          </p>
        )}
        {campaigns.length > 0 && (
          <div
            className="campaign-list"
            role="region"
            aria-label="Campaign history entries"
            tabIndex={0}
          >
            {campaigns.map((campaign) => {
              return (
                <div className="campaign-entry" key={campaign.campaign_id}>
                  <button
                    className="campaign-row campaign-toggle"
                    onClick={() => onSelect(campaign.campaign_id)}
                    aria-pressed={campaignId === campaign.campaign_id}
                  >
                    <div className="campaign-id">
                      <strong>{campaign.campaign_id}</strong>
                      <small>
                        {campaign.provider} · {campaign.model}
                      </small>
                    </div>
                    <div className="campaign-stat">
                      <small>Scenarios</small>
                      <strong>{campaign.scenario_count}</strong>
                    </div>
                    <div className="campaign-stat">
                      <small>Completed</small>
                      <strong className="green">{campaign.completed}</strong>
                    </div>
                    <div className="campaign-stat">
                      <small>Marker observations</small>
                      <strong
                        className={
                          campaign.injection_successes ? "red" : "green"
                        }
                      >
                        {campaign.injection_successes ?? "Unavailable"}
                      </strong>
                    </div>
                    <div className="campaign-stat">
                      <small>Correct recommendations</small>
                      <strong className="green">
                        {campaign.task_successes ?? "—"}
                      </strong>
                    </div>
                    <span className={`campaign-status ${campaign.status}`}>
                      {campaign.status.replaceAll("_", " ")}
                    </span>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
      <div className="campaign-breakdown-panel" aria-busy={detailLoading}>
        {!campaignId && (
          <div className="campaign-empty-selection">
            <h2>Select a campaign</h2>
            <p>
              Choose a campaign from the history list to load its scenario
              results.
            </p>
          </div>
        )}
        {detailLoading && <p role="status">Loading selected campaign…</p>}
        {detailError && (
          <div className="form-error" role="alert">
            {detailError}
            <button
              className="text-button"
              onClick={() => setAttempt((value) => value + 1)}
            >
              Retry selected campaign
            </button>
          </div>
        )}
        {rerunError && (
          <p className="form-error" role="alert">
            {rerunError}
          </p>
        )}
        {selectedCampaign && (
          <div className="selected-campaign">
            <h2>{selectedCampaign.campaign_id}</h2>
            <p>
              {selectedCampaign.status.replaceAll("_", " ")} ·{" "}
              {selectedCampaign.model}
            </p>
          </div>
        )}
        {campaignId &&
          selectedCampaign &&
          !selectedScenario &&
          !detailLoading && (
            <div className="campaign-empty-selection">
              <h2>
                {selectedCampaign.scenarios.length
                  ? "Select a scenario"
                  : "No saved child attempts"}
              </h2>
              <p>
                {selectedCampaign.scenarios.length
                  ? "Choose one of this campaign's scenarios to see its breakdown."
                  : "This campaign has no scenario results to inspect."}
              </p>
              <div className="campaign-scenario-picker">
                {selectedCampaign.scenarios.map((scenario, index) => (
                  <button
                    key={`${scenario.filename}-${index}`}
                    className="scenario-picker-row"
                    onClick={() => setSelectedScenarioIndex(index)}
                  >
                    <span>{scenario.filename}</span>
                    <small>{outcomePresentation(scenario).injection}</small>
                  </button>
                ))}
              </div>
            </div>
          )}
        {selectedCampaign?.metrics && (
          <MeasurementSummary
            metrics={selectedCampaign.metrics}
            label="Campaign attempt rates by condition"
          />
        )}
        {selectedScenario && (
          <div className="campaign-scenario-breakdown">
            <button
              className="text-button"
              disabled={Boolean(rerunning)}
              onClick={() => setSelectedScenarioIndex(null)}
            >
              Choose another scenario
            </button>
            <div className="breakdown-heading">
              <div>
                <p className="label">Scenario breakdown</p>
                <h2>{selectedScenario.filename}</h2>
                <small>
                  {selectedScenario.scenario_id} · child run{" "}
                  {selectedScenario.child_run_id || "not created"}
                </small>
              </div>
              <button
                className="small-button"
                disabled={
                  rerunning === `${campaignId}:${selectedScenarioIndex}`
                }
                onClick={() => rerun(campaignId, selectedScenarioIndex)}
              >
                {rerunning === `${campaignId}:${selectedScenarioIndex}`
                  ? "Rerunning…"
                  : "Rerun scenario"}
              </button>
            </div>
            <div className="breakdown-status">
              <span
                className={
                  selectedScenario.failure_state
                    ? "red"
                    : selectedScenario.marker_influence === true
                      ? "red"
                      : "green"
                }
              >
                {selectedScenario.failure_state ||
                  outcomePresentation(selectedScenario).injection}
              </span>
              <small>{outcomePresentation(selectedScenario).task}</small>
            </div>
            <div className="breakdown-grid">
              <div>
                <small>Marker influence</small>
                <strong>
                  {outcomePresentation(selectedScenario).injection}
                </strong>
              </div>
              <div>
                <small>Recommendation correctness</small>
                <strong>{outcomePresentation(selectedScenario).task}</strong>
              </div>
              <div>
                <small>Attacker goal</small>
                <strong>
                  {outcomePresentation(selectedScenario).attacker}
                </strong>
              </div>
              <div>
                <small>Simulated gateway</small>
                <strong>{outcomePresentation(selectedScenario).defense}</strong>
              </div>
              <div>
                <small>Failure state</small>
                <strong>{selectedScenario.failure_state || "None"}</strong>
              </div>
            </div>
            {selectedScenario.child_run_id && (
              <button
                className="text-button"
                onClick={() => onRun(selectedScenario.child_run_id)}
              >
                Open saved run {selectedScenario.child_run_id}
              </button>
            )}
            <div className="campaign-trace">
              <div className="breakdown-section-heading">
                <p className="label">Full trace</p>
                <small>{selectedScenario.trace?.length || 0} events</small>
              </div>
              {selectedScenario.trace?.length ? (
                <div className="timeline campaign-timeline">
                  {selectedScenario.trace.map((event, index) => (
                    <div key={`${event.kind}-${index}`}>
                      <time>{index + 1}</time>
                      <i
                        className={
                          event.kind === "policy_decision" ? "red" : "cyan"
                        }
                      />
                      <p>
                        <strong>{event.kind.replaceAll("_", " ")}</strong>
                        <small>
                          {Object.entries(event.data || {})
                            .map(
                              ([key, value]) =>
                                `${key}: ${typeof value === "object" ? JSON.stringify(value) : value}`,
                            )
                            .join(" · ")}
                        </small>
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">
                  No trace events were persisted for this scenario.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
