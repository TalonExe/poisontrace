import assert from 'node:assert/strict';
import test from 'node:test';
import { workspaceStorage, setWorkspaceAccount } from '../utils/workspaceStorage.js';

test('authenticated workspaces partition configurations and execution without changing local edition data', () => {
  const data = new Map([['poisontrace.synthetic.sessions', 'legacy local configuration']]);
  const storage = { getItem: k => data.get(k) ?? null, setItem: (k,v) => data.set(k,v) };
  setWorkspaceAccount(null);
  assert.equal(workspaceStorage(storage).getItem('poisontrace.synthetic.sessions'), 'legacy local configuration');
  setWorkspaceAccount({id: 1, role: 'analyst'});
  const alice = workspaceStorage(storage);
  assert.equal(alice.getItem('poisontrace.synthetic.sessions'), null);
  alice.setItem('poisontrace.synthetic.sessions', 'Alice private configuration');
  alice.setItem('poisontrace.synthetic.execution', 'config:alice');
  setWorkspaceAccount({id: 2, role: 'analyst'});
  const bob = workspaceStorage(storage);
  assert.equal(bob.getItem('poisontrace.synthetic.sessions'), null);
  assert.equal(bob.getItem('poisontrace.synthetic.execution'), null);
  bob.setItem('poisontrace.synthetic.sessions', 'Bob configuration');
  // A late write from an old component remains bound to its original account.
  alice.setItem('poisontrace.synthetic.execution', 'scripted');
  assert.equal(bob.getItem('poisontrace.synthetic.execution'), null);
  setWorkspaceAccount({id: 1, role: 'analyst'});
  assert.equal(workspaceStorage(storage).getItem('poisontrace.synthetic.sessions'), 'Alice private configuration');
  setWorkspaceAccount(null);
  assert.equal(data.get('poisontrace.synthetic.sessions'), 'legacy local configuration');
});
