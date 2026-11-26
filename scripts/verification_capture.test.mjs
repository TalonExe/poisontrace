import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { capturePage, expectedAnonymousSession, navigateForCapture } from './verification_capture.mjs';

test('anonymous readiness waits for the actual sign-in control', async () => {
  const server = createServer((request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html' });
    response.end('<!doctype html><h1>Login</h1><button>Sign in</button>');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch();
    const page = await browser.newPage();
    await navigateForCapture(page, `http://127.0.0.1:${server.address().port}/login`, 'anonymous');
    assert.equal(await page.getByRole('button', { name: 'Sign in', exact: true }).isVisible(), true);
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
});

test('only the unauthenticated session probe has an expected 401 outcome', () => {
  assert.equal(expectedAnonymousSession(401, 'http://127.0.0.1:4176/api/auth/session', false), true);
  assert.equal(expectedAnonymousSession(401, 'http://127.0.0.1:4176/api/auth/session', true), false);
  assert.equal(expectedAnonymousSession(401, 'http://127.0.0.1:4176/api/runs', false), false);
  assert.equal(expectedAnonymousSession(500, 'http://127.0.0.1:4176/api/auth/session', false), false);
});

test('live page capture retains readable UI snapshots and both PNG sizes', async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'poisontrace-visual-'));
  const server = createServer((request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html' });
    response.end('<!doctype html><title>Synthetic visual fixture</title><style>body{margin:0;min-height:1200px}h1{margin:0}</style><main><h1>Visual fixture</h1><button>Inspect synthetic evidence</button></main>');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch();
    for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      const context = await browser.newContext({ viewport: { width, height } });
      const page = await context.newPage();
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      const record = await capturePage(page, directory, name);
      const viewport = await fs.readFile(record.files.viewport);
      const full = await fs.readFile(record.files.fullPage);
      assert.equal(viewport.readUInt32BE(16), width);
      assert.equal(viewport.readUInt32BE(20), height);
      assert.equal(full.readUInt32BE(20), 1200);
      assert.match(await fs.readFile(record.files.snapshot, 'utf8'), /button "Inspect synthetic evidence"/);
      assert.equal(record.layout.horizontalOverflow, false);
      assert.equal(record.title, 'Synthetic visual fixture');
      assert.equal(record.sha256.viewport.length, 64);
      await assert.rejects(capturePage(page, directory, name), { code: 'EEXIST' });
      await context.close();
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    await fs.rm(directory, { recursive: true, force: true });
  }
});
