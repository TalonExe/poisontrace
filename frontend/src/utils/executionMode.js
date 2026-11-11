export const executionModes = Object.freeze({
  single: "single",
  campaign: "campaign",
});

export function isExecutionMode(value) {
  return Object.values(executionModes).includes(value);
}

export function selectExecutionMode(value) {
  return isExecutionMode(value) ? value : executionModes.single;
}
