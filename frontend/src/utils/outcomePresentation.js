export function outcomePresentation(run = {}) {
  if (run.scoring_version === "investigation-scoring-v1") {
    const scores = run.investigation?.scores || run.investigation_scores || {};
    const label = (value, yes, no) => value == null ? "Unscored" : value ? yes : no;
    return {injection:label(scores.marker_influence,"Marker observed","Marker not observed"), attacker:label(scores.attacker_goal,"Achieved","Not achieved"),
      task:label(scores.decision_correctness,"Decision fields correct","Decision fields incorrect"), defense:"See recorded manifest observations",
      tool:run.tool_call_status || "Unavailable", system:run.status === "failed" || run.system_error ? "System/model failure" : "No system/model failure"};
  }
  if (run.scoring_version === "investigation-unscored-v1") return {
    injection: run.marker_influence == null ? "Unscored" : run.marker_influence ? "Marker observed" : "Marker not observed",
    attacker: "Not evaluated", task: "Investigation correctness unscored", defense: "Manifest defense not evaluated",
    tool: run.tool_call_status || "Unavailable", system: run.status === "failed" || run.system_error ? "System/model failure" : "No system/model failure",
  };
  const current = run.scoring_version === "recommendation-v1";
  const observed = (value, yes, no) => value == null ? "Unscored" : value ? yes : no;
  return {
    injection: current ? observed(run.marker_influence, "Marker observed", "Marker not observed") : `Legacy: ${run.injection_verdict || "unavailable"}`,
    attacker: current ? observed(run.attacker_goal_achievement, "Achieved", "Not achieved") : "Legacy / unscored",
    task: current ? observed(run.recommendation_correctness, "Correct recommendation", "Incorrect recommendation") : `Legacy: ${run.task_outcome || "unavailable"}`,
    defense: run.defense_evidence_version !== "gateway-v1" ? current ? "Unavailable" : "Legacy / unavailable"
      : run.call_rejected ? `Rejected proposed call: ${run.policy_reason}`
      : run.policy_reason === "no_call_proposed" ? "No call proposed"
      : run.manifest_check_performed ? "Manifest checked; simulated permission allowed"
      : "Manifest policy disabled; simulated permission allowed",
    tool: run.defense_evidence_version === "gateway-v1" ? run.tool_call_status || "Unknown" : `Legacy: ${run.tool_call_status || "unavailable"}`,
    system: run.system_error || run.status === "failed" ? "System/model failure" : "No system/model failure",
  };
}
