import test from "node:test";
import assert from "node:assert/strict";
import {
  groupPerformance,
  investigationMeasurementPresentation,
} from "../utils/investigationPresentation.js";

const observed = (numerator, denominator) => ({
  numerator,
  denominator,
  value: denominator ? numerator / denominator : null,
});
test("correctness is green for correct outcomes and red when incorrect outcomes are observed", () => {
  assert.equal(
    investigationMeasurementPresentation("decision_correctness", observed(1, 1))
      .tone,
    "positive",
  );
  const wrong = investigationMeasurementPresentation(
    "verdict_correctness",
    observed(0, 2),
  );
  assert.equal(wrong.tone, "negative");
  assert.equal(wrong.negativeText, "2 incorrect");
  const mixed = investigationMeasurementPresentation(
    "handling_correctness",
    observed(1, 3),
  );
  assert.equal(mixed.positiveText, "1 correct");
  assert.equal(mixed.negativeText, "2 incorrect");
});
test("attacker and error rates have the opposite direction from correctness", () => {
  assert.equal(
    investigationMeasurementPresentation("attacker_goal", observed(1, 1)).tone,
    "negative",
  );
  assert.equal(
    investigationMeasurementPresentation("attacker_goal", observed(0, 1)).tone,
    "positive",
  );
  assert.equal(
    investigationMeasurementPresentation("system_error", observed(2, 3))
      .negativeText,
    "2 with errors",
  );
  assert.equal(
    investigationMeasurementPresentation("system_error", observed(0, 3)).tone,
    "positive",
  );
});
test("missing denominators, policy observations and marker absence never imply a successful investigation", () => {
  assert.equal(
    investigationMeasurementPresentation("decision_correctness", observed(0, 0))
      .tone,
    "unavailable",
  );
  assert.equal(
    investigationMeasurementPresentation("attacker_goal", null).tone,
    "unavailable",
  );
  assert.equal(
    investigationMeasurementPresentation(
      "discovery_restriction",
      observed(3, 3),
    ).tone,
    "observation",
  );
  assert.equal(
    investigationMeasurementPresentation("invocation_rejection", observed(0, 3))
      .tone,
    "observation",
  );
  assert.equal(
    investigationMeasurementPresentation("marker_influence", observed(0, 1))
      .tone,
    "observation",
  );
});

function comparison(correct, scored, completed, failed) {
  const row = {
    attempted: completed + failed,
    completed,
    failed,
    decision_correctness: observed(correct, scored),
  };
  const empty = {
    attempted: 0,
    completed: 0,
    failed: 0,
    decision_correctness: observed(0, 0),
  };
  return {
    scoring_version: "investigation-scoring-v1",
    attempted: completed + failed,
    by_condition: { clean: row, poisoned: empty, defended: empty },
  };
}
test("overall performance counts correct completions across all compatible attempts", () => {
  assert.equal(groupPerformance(comparison(1, 4, 4, 5)).score, 11);
  assert.equal(groupPerformance(comparison(3, 3, 3, 0)).score, 100);
  assert.equal(groupPerformance(comparison(0, 0, 0, 3)).score, 0);
  assert.equal(groupPerformance(comparison(0, 0, 0, 3)).tone, "negative");
  const partial = groupPerformance(comparison(1, 1, 2, 1));
  assert.equal(partial.score, 33);
  assert.equal(partial.unscored, 1);
});
test("empty, missing, unsupported and wholly unscored comparisons are unavailable", () => {
  for (const value of [
    null,
    {},
    comparison(0, 0, 0, 0),
    comparison(0, 0, 2, 0),
    { ...comparison(1, 1, 1, 0), scoring_version: "future" },
    { ...comparison(1, 1, 1, 0), by_condition: {} },
  ]) {
    assert.equal(groupPerformance(value).score, null);
  }
});
test("incompatible and missing slots never inflate the denominator; retained reruns do", () => {
  const first = {
    ...comparison(1, 1, 1, 0),
    excluded_attempts: [2],
    missing_attempts: [3],
  };
  assert.equal(groupPerformance(first).score, 100);
  const rerun = {
    ...comparison(1, 2, 2, 1),
    excluded_attempts: [2],
    missing_attempts: [3],
  };
  rerun.by_condition.clean.discovery_restriction = observed(3, 3);
  rerun.by_condition.clean.marker_influence = observed(0, 3);
  assert.equal(groupPerformance(rerun).score, 33);
  assert.equal(groupPerformance(rerun).attempts, 3);
});

test('reference membership uses membership wording without calling reasoning correct',()=>{
  const presentation=investigationMeasurementPresentation('evidence_references_valid',observed(2,3));
  assert.equal(presentation.positiveText,'2 with references found');
  assert.equal(presentation.negativeText,'1 with invalid or missing references');
  assert.equal(presentation.tone,'negative');
});
