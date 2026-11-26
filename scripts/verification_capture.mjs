import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from '../frontend/node_modules/playwright/index.mjs';

const sha256 = data => createHash('sha256').update(data).digest('hex');
const sizes = { desktop: { width: 1440, height: 1000 }, mobile: { width: 390, height: 844 } };

export function expectedAnonymousSession(status, url, authenticated) {
  return !authenticated && status === 401 && new URL(url).pathname === '/api/auth/session';
}

export async function navigateForCapture(page, route, role) {
  const response = await page.goto(route, { waitUntil: role === 'anonymous' ? 'domcontentloaded' : 'networkidle' });
  if (!response || response.status() !== 200 ||
      new URL(page.url()).pathname !== new URL(route, page.url()).pathname)
    throw new Error('Requested application route did not load: ' + route);
  if (role === 'anonymous')
    await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor({ state: 'visible' });
  else await page.locator('h1').first().waitFor({ state: 'visible' });
}

export async function capturePage(page, directory, name) {
  if (!/^[a-zA-Z0-9_-]+$/.test(name)) throw new Error('Capture name must be a safe filename');
  const destination = path.join(directory, name);
  await fs.mkdir(destination, { recursive: false });
  await page.locator('body').waitFor({ state: 'visible' });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    window.scrollTo(0, 0);
  });
  const files = {
    viewport: path.join(destination, 'viewport.png'),
    fullPage: path.join(destination, 'full-page.png'),
    snapshot: path.join(destination, 'snapshot.aria.yml'),
    metadata: path.join(destination, 'snapshot.json'),
  };
  const snapshot = await page.locator('body').ariaSnapshot();
  await fs.writeFile(files.snapshot, snapshot, { flag: 'wx' });
  const options = { animations: 'disabled', caret: 'hide', scale: 'css' };
  const viewport = await page.screenshot({ ...options, path: files.viewport, fullPage: false });
  const full = await page.screenshot({ ...options, path: files.fullPage, fullPage: true });
  const layout = await page.evaluate(() => ({
    viewportWidth: innerWidth, viewportHeight: innerHeight,
    documentWidth: document.documentElement.scrollWidth,
    documentHeight: document.documentElement.scrollHeight,
    horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
    headings: [...document.querySelectorAll('h1,h2,h3')].map(node => node.textContent.trim()),
  }));
  const record = { name, capturedAt: new Date().toISOString(), url: page.url(),
    title: await page.title(), layout, files,
    sha256: { viewport: sha256(viewport), fullPage: sha256(full), snapshot: sha256(snapshot) } };
  await fs.writeFile(files.metadata, JSON.stringify(record, null, 2), { flag: 'wx' });
  return record;
}

async function authenticate(page, role, viewport) {
  if (role === 'anonymous') return;
  let account = { username: 'synthetic-operator', passcode: 'synthetic-operator-passcode' };
  if (role === 'analyst') {
    const login = await page.request.post('/api/auth/login', { data: account });
    if (login.status() !== 200) throw new Error('Synthetic operator authentication failed');
    account = { username: 'visual-' + viewport, passcode: 'synthetic-visual-only' };
    const created = await page.request.post('/api/admin/users', { data: { ...account, display_name: 'Visual verification analyst' } });
    if (created.status() !== 201) throw new Error('Synthetic analyst creation failed');
    await page.request.post('/api/auth/logout');
  }
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(account.username);
  await page.getByLabel('Passcode', { exact: true }).fill(account.passcode);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(url => url.pathname !== '/login');
}

async function main() {
  const { values } = parseArgs({ options: {
    origin: { type: 'string' }, output: { type: 'string' }, role: { type: 'string' },
    route: { type: 'string', multiple: true }, viewport: { type: 'string', multiple: true },
  } });
  if (!/^https?:\/\/127\.0\.0\.1:4176$/.test(values.origin || '') ||
      process.env.POISONTRACE_VERIFY_FAMILY !== 'production' ||
      path.resolve(values.output || '') !== path.resolve(process.env.POISONTRACE_VERIFY_ARTIFACT || ''))
    throw new Error('Use verify_ui.py with its owned synthetic production server');
  const output = path.resolve(values.output);
  const manifestPath = path.join(output, 'capture-manifest.json');
  const manifest = { status: 'running', origin: values.origin, role: values.role,
    snapshots: [], consoleErrors: [], requestFailures: [], responseErrors: [], blockedExternalRequests: [] };
  await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2), { flag: 'wx' });
  let browser;
  try {
    browser = await chromium.launch();
    manifest.browser = browser.version();
    for (const viewport of values.viewport) {
      const context = await browser.newContext({ baseURL: values.origin, viewport: sizes[viewport],
        deviceScaleFactor: 1, isMobile: viewport === 'mobile', hasTouch: viewport === 'mobile',
        ignoreHTTPSErrors: values.origin.startsWith('https:'), extraHTTPHeaders: { Origin: values.origin },
        serviceWorkers: 'block', reducedMotion: 'reduce' });
      try {
        await context.route('**/*', async route => {
          if (new URL(route.request().url()).origin !== values.origin) {
            manifest.blockedExternalRequests.push(route.request().url());
            await route.abort();
          } else await route.continue();
        });
        const page = await context.newPage();
        let authenticated = false;
        page.setDefaultTimeout(15000);
        page.on('pageerror', error => manifest.consoleErrors.push({ text: error.message, expected: false }));
        page.on('console', message => {
          if (message.type() === 'error') {
            const url = message.location().url;
            manifest.consoleErrors.push({ text: message.text(), url,
              expected: /^Failed to load resource:.*401/.test(message.text()) && !!url &&
                expectedAnonymousSession(401, url, authenticated) });
          }
        });
        page.on('requestfailed', request => manifest.requestFailures.push({ url: request.url(), error: request.failure()?.errorText }));
        page.on('response', response => {
          if (response.status() >= 400) manifest.responseErrors.push({ url: response.url(), status: response.status(),
            expected: expectedAnonymousSession(response.status(), response.url(), authenticated) });
        });
        await authenticate(page, values.role, viewport);
        authenticated = values.role !== 'anonymous';
        for (const route of values.route) {
          if (!/^\/[A-Za-z0-9/_-]*$/.test(route) || route.startsWith('//') || route.startsWith('/api') || route.startsWith('/__test'))
            throw new Error('Capture route must be a local application path');
          await navigateForCapture(page, route, values.role);
          const name = viewport + '-' + (route.replaceAll('/', '-').replace(/^-/, '') || 'root') + '-' + sha256(route).slice(0, 8);
          const record = await capturePage(page, output, name);
          record.requestedRoute = route;
          record.viewport = viewport;
          manifest.snapshots.push(record);
          await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
        }
      } finally {
        await context.close();
      }
    }
    if (manifest.consoleErrors.some(error => !error.expected) || manifest.requestFailures.length ||
        manifest.responseErrors.some(error => !error.expected) ||
        manifest.snapshots.some(record => record.layout.horizontalOverflow))
      throw new Error('Capture found browser errors, failed requests or horizontal overflow; inspect capture-manifest.json');
    manifest.status = 'passed';
    console.log(`Captured ${manifest.snapshots.length} live UI snapshots with viewport/full-page PNGs`);
  } catch (error) {
    manifest.status = 'failed';
    manifest.error = error.message;
    throw error;
  } finally {
    if (browser) await browser.close();
    await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  await main();
