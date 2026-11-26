import test from 'node:test';
import assert from 'node:assert/strict';
import {advanceSessionGeneration, sessionGeneration, notifySessionExpiry} from '../lib/http/sessionExpiry.js';

test('only a current protected-request 401 can end the active browser session', () => {
  const events = [];
  const previous = globalThis.window;
  globalThis.window = {dispatchEvent:event=>events.push(event.type)};
  try {
    const first = sessionGeneration();
    notifySessionExpiry({status:403}, first);
    assert.deepEqual(events, []);
    advanceSessionGeneration();
    notifySessionExpiry({status:401}, first);
    assert.deepEqual(events, []);
    notifySessionExpiry({status:401}, sessionGeneration());
    assert.deepEqual(events, ['poisontrace-session-ended']);
  } finally {
    globalThis.window = previous;
  }
});
