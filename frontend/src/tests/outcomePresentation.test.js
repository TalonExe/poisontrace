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
      injection: "Blocked",
      task: "Benign success",
      tool: "Executed",
      system: "No system/model failure",
    },
  );
});
