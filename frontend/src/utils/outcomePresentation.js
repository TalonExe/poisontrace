export function outcomePresentation(run = {}) {
  return {
    injection: run.injection_verdict || (run.attack_success ? "Attack success" : "Blocked"),
    task: run.task_outcome || (run.benign_task_success ? "Benign success" : "Failed"),
    tool: run.tool_call_status || "Unknown",
    system: run.system_error ? "System/model failure" : "No system/model failure",
  };
}
