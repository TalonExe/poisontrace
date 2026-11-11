import assert from "node:assert/strict";
import test from "node:test";
import {
  executionModes,
  isExecutionMode,
  selectExecutionMode,
} from "../utils/executionMode.js";

test("execution mode seam exposes only the two supported workflows", () => {
  assert.equal(isExecutionMode(executionModes.single), true);
  assert.equal(isExecutionMode(executionModes.campaign), true);
  assert.equal(isExecutionMode("other"), false);
});

test("invalid execution mode selection safely returns single run", () => {
  assert.equal(selectExecutionMode("other"), executionModes.single);
  assert.equal(
    selectExecutionMode(executionModes.campaign),
    executionModes.campaign,
  );
});
