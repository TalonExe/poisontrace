import assert from "node:assert/strict";
import { setImmediate } from "node:timers/promises";
import test from "node:test";
import { observeInvestigationJobs } from "../features/dashboard/investigationJobObserver.js";

test("prefers an outstanding job of the selected kind and falls back in collection order", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const completed = { job_id: "completed", status: "completed" };
  const active = { job_id: "active", status: "active" };
  const group = { job_id: "group", group_id: "group-id", status: "queued" };
  let jobs = [group, completed, active];
  const updates = [];
  const stop = observeInvestigationJobs({
    runner: { listInvestigationJobs: async () => jobs },
    kind: "single",
    onUpdate: (update) => updates.push(update),
    onError: assert.fail,
  });
  t.after(stop);

  await setImmediate();
  assert.deepEqual(updates, [{ job: active, busy: true }]);

  jobs = [completed, { job_id: "older", status: "interrupted" }, group];
  t.mock.timers.tick(1000);
  await setImmediate();
  assert.deepEqual(updates[1], { job: completed, busy: false });
});

test("reports a polling error and retries after one second", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const failure = new Error("Jobs unavailable");
  const errors = [];
  const updates = [];
  const job = { job_id: "single", status: "queued" };
  let requests = 0;
  const stop = observeInvestigationJobs({
    runner: {
      async listInvestigationJobs() {
        if (++requests === 1) throw failure;
        return [job];
      },
    },
    kind: "single",
    onUpdate: (update) => updates.push(update),
    onError: (error) => errors.push(error),
  });
  t.after(stop);

  await setImmediate();
  assert.deepEqual(errors, [failure]);
  t.mock.timers.tick(999);
  assert.equal(requests, 1);
  t.mock.timers.tick(1);
  await setImmediate();
  assert.deepEqual(updates, [{ job, busy: true }]);
});

test("stopping during collection loading prevents an update and a group detail request", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const collection = Promise.withResolvers();
  let requests = 0;
  const stop = observeInvestigationJobs({
    runner: {
      listInvestigationJobs() {
        requests++;
        return collection.promise;
      },
      getRunGroup: () => assert.fail("A stopped observer must not fetch group progress"),
    },
    kind: "group",
    onUpdate: assert.fail,
    onError: assert.fail,
  });

  stop();
  collection.resolve([{ group_id: "group-id", status: "active" }]);
  await setImmediate();
  t.mock.timers.tick(1000);
  assert.equal(requests, 1);
});

test("group polling waits for progress and ignores a late response after cleanup", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const progress = { completed: 1 };
  const job = { job_id: "group", group_id: "group-id", status: "active" };
  const secondDetail = Promise.withResolvers();
  const updates = [];
  const detailRequests = [];
  let requests = 0;
  const stop = observeInvestigationJobs({
    runner: {
      async listInvestigationJobs() {
        requests++;
        return [{ job_id: "single", status: "active" }, job];
      },
      getRunGroup(id) {
        detailRequests.push(id);
        return detailRequests.length === 1 ? Promise.resolve({ progress }) : secondDetail.promise;
      },
    },
    kind: "group",
    onUpdate: (update) => updates.push(update),
    onError: assert.fail,
  });
  t.after(stop);

  await setImmediate();
  assert.deepEqual(updates, [{ job, busy: true, progress }]);
  t.mock.timers.tick(1000);
  await setImmediate();
  assert.deepEqual(detailRequests, ["group-id", "group-id"]);
  t.mock.timers.tick(5000);
  assert.equal(requests, 2);

  stop();
  secondDetail.resolve({ progress: { completed: 2 } });
  await setImmediate();
  t.mock.timers.tick(1000);
  assert.equal(updates.length, 1);
  assert.equal(requests, 2);
});
