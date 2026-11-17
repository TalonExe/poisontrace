import assert from "node:assert/strict";
import test from "node:test";
import { outcomePresentation } from "../utils/outcomePresentation.js";

test("presents injection, task, tool, and system outcomes independently", () => {
  assert.deepEqual(
    outcomePresentation({
      injection_verdict: "Blocked",
      task_outcome: "Benign success",
      tool_call_status: "Executed",
      system_error: false,
    }),
    {
      injection: "Legacy: Blocked",
      attacker: "Legacy / unscored",
      task: "Legacy: Benign success",
      tool: "Legacy: Executed",
      defense: "Legacy / unavailable",
      system: "No system/model failure",
    },
  );
});

test('separates marker influence, attacker goal and recommendation correctness', () => {
  const output = outcomePresentation({ scoring_version: 'recommendation-v1', marker_influence: true, attacker_goal_achievement: false, recommendation_correctness: true });
  assert.equal(output.injection, 'Marker observed');
  assert.equal(output.attacker, 'Not achieved');
  assert.equal(output.task, 'Correct recommendation');
  assert.equal(outcomePresentation({scoring_version: 'recommendation-v1', attacker_goal_achievement: null}).attacker, 'Unscored');
});

test('never infers rejection from marker absence and identifies simulated permissions', () => {
  assert.equal(outcomePresentation({scoring_version: 'recommendation-v1', defense_evidence_version: 'gateway-v1', marker_influence: false, call_rejected: false, policy_reason: 'no_call_proposed'}).defense, 'No call proposed');
  assert.equal(outcomePresentation({scoring_version: 'recommendation-v1', defense_evidence_version: 'gateway-v1', marker_influence: true, call_rejected: true, policy_reason: 'tool_definition_mismatch'}).defense, 'Rejected proposed call: tool_definition_mismatch');
  assert.equal(outcomePresentation({defense_evidence_version: 'gateway-v1', call_rejected: false, manifest_check_performed: false, proposed_tool_name: 'evidence'}).defense, 'Manifest policy disabled; simulated permission allowed');
  assert.equal(outcomePresentation({}).defense, 'Legacy / unavailable');
});
