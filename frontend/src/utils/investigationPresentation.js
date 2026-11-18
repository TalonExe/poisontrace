// Presentation direction only. Saved measurements and denominators remain unchanged.
export function investigationMeasurementPresentation(key, rate) {
  if (!rate?.denominator) return { tone: "unavailable" };
  const yes = rate.numerator;
  const no = rate.denominator - yes;
  if (key === "evidence_references_valid") {
    return {
      tone: no ? "negative" : "positive",
      positiveText: `${yes} with references found`,
      negativeText: `${no} with invalid or missing references`,
      positiveCount: yes,
      negativeCount: no,
    };
  }
  if (key.endsWith("_correctness")) {
    return {
      tone: no ? "negative" : "positive",
      positiveText: `${yes} correct`,
      negativeText: `${no} incorrect`,
      positiveCount: yes,
      negativeCount: no,
    };
  }
  if (key === "attacker_goal") {
    return {
      tone: yes ? "negative" : "positive",
      positiveText: `${no} without a target match`,
      negativeText: `${yes} target ${yes === 1 ? "match" : "matches"}`,
      positiveCount: no,
      negativeCount: yes,
    };
  }
  if (key === "system_error") {
    return {
      tone: yes ? "negative" : "positive",
      positiveText: `${no} without errors`,
      negativeText: `${yes} with errors`,
      positiveCount: no,
      negativeCount: yes,
    };
  }
  return {
    tone: "observation",
    observationText: `${yes} observed · ${no} not observed`,
  };
}

export function investigationValueTone(key, value) {
  return investigationMeasurementPresentation(
    key,
    value == null ? null : { numerator: value ? 1 : 0, denominator: 1 },
  ).tone;
}

// Display-only operational indicator. Existing measurement denominators are unchanged.
export function groupPerformance(comparison) {
  const unavailable = {
    score: null,
    tone: "unavailable",
    label: "Unavailable",
  };
  if (comparison?.scoring_version !== "investigation-scoring-v1")
    return unavailable;
  const rows = ["clean", "poisoned", "defended"].map(
    (c) => comparison.by_condition?.[c],
  );
  const count = (n) => Number.isInteger(n) && n >= 0;
  if (
    rows.some(
      (r) =>
        !r ||
        !count(r.attempted) ||
        !count(r.completed) ||
        !count(r.failed) ||
        r.completed + r.failed !== r.attempted ||
        !count(r.decision_correctness?.numerator) ||
        !count(r.decision_correctness?.denominator) ||
        r.decision_correctness.numerator > r.decision_correctness.denominator ||
        r.decision_correctness.denominator > r.completed,
    )
  )
    return unavailable;
  const sum = (f) => rows.reduce((n, r) => n + f(r), 0);
  const attempts = sum((r) => r.attempted);
  const completed = sum((r) => r.completed);
  const failed = sum((r) => r.failed);
  const scored = sum((r) => r.decision_correctness.denominator);
  const correct = sum((r) => r.decision_correctness.numerator);
  const counts = { attempts, correct, failed, unscored: completed - scored };
  if (
    !attempts ||
    comparison.attempted !== attempts ||
    (completed > 0 && scored === 0)
  )
    return { ...unavailable, ...counts };
  return {
    ...counts,
    score: Math.round((correct / attempts) * 100),
    tone: correct === attempts ? "positive" : "negative",
    label:
      correct === attempts
        ? "All attempts correct"
        : "Some attempts not successful",
  };
}
