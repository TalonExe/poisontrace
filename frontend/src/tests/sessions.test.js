import assert from "node:assert/strict";
import test from "node:test";
import {
  createSession,
  defaultSession,
  deleteSession,
  loadSessions,
  saveSession,
} from "../utils/sessions.js";

test("session CRUD helpers create, update, and delete configurations", () => {
  const created = createSession(123);
  let sessions = [defaultSession, created];
  sessions = saveSession(sessions, {
    ...created,
    name: "  OpenAI study  ",
    model: "openai",
  });
  assert.equal(sessions[1].name, "OpenAI study");
  assert.equal(sessions[1].model, "openai");
  assert.deepEqual(deleteSession(sessions, created.id), [defaultSession]);
  assert.deepEqual(deleteSession([created], created.id), [defaultSession]);
});

test("session loader handles missing and malformed local storage", () => {
  const empty = { getItem: () => null };
  const malformed = { getItem: () => "{bad json" };
  assert.deepEqual(loadSessions(empty), [defaultSession]);
  assert.deepEqual(loadSessions(malformed), [defaultSession]);
});
