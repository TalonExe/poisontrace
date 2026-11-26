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

test('new configurations omit unused scenario defaults and stored configurations retain extra fields',()=>{
  assert.equal(Object.hasOwn(defaultSession,'scenario'),false);
  assert.equal(Object.hasOwn(createSession(456),'scenario'),false);
  const legacy={id:'stored-old',name:'Legacy configuration',model:'openai',credentialId:'synthetic-reference',scenario:'preserved legacy selection',extra:{retained:true}};
  const serialized=JSON.stringify([legacy]);
  const storage={getItem:()=>serialized,setItem:()=>assert.fail('loading must not rewrite browser data')};
  const loaded=loadSessions(storage);
  assert.deepEqual(loaded,[legacy]);
  const saved=saveSession(loaded,{...loaded[0],name:'Updated name'});
  assert.equal(saved[0].scenario,'preserved legacy selection');
  assert.deepEqual(saved[0].extra,{retained:true});
});
