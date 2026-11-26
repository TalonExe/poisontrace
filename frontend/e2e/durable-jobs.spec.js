import {test, expect} from './verification-test.js';

test('single job reconnects after refresh and opens its attributable result', async ({page}) => {
  let job = null;
  const intents = [];
  let releaseSubmission;
  const submission = new Promise(resolve => { releaseSubmission = resolve; });
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if (path === '/api/auth/session') data = {user: {id: 501, username: 'synthetic', role: 'analyst'}};
    if (path === '/api/runs/investigation-cases') data = [{case_id: 'soc-auth-001', case_version: '1', name: 'Synthetic case', attacks: []}];
    if (path === '/api/investigation-jobs') {
      if (route.request().method() === 'POST') {
        intents.push(route.request().headers()['idempotency-key']);
        await submission;
        job = {job_id: 'synthetic-durable-job', status: 'queued', run_id: null};
        data = job;
      } else data = job ? [job] : [];
    }
    if (path === '/api/runs/93') data = {run_id: 93, id: 'EXP-093', status: 'completed', mode: 'Clean', model: 'scripted-soc-v2', trace: [], run_configuration: {}};
    await route.fulfill({json: data});
  });
  await page.goto('/dashboard/single');
  const launch = page.getByRole('button', {name: /^Run MCP investigation/});
  await expect(launch).toBeEnabled();
  await launch.focus();
  await page.keyboard.press('Enter');
  try {
    await expect(page.getByText('Submitting investigation…')).toBeVisible();
    await expect(launch).toBeFocused();
    await expect(launch).toHaveAttribute('aria-disabled', 'true');
    await page.keyboard.press('Enter');
    expect(intents).toHaveLength(1);
  } finally {
    releaseSubmission();
  }
  await expect(page.getByRole('status', {name: 'Investigation job'})).toContainText('Investigation queued');
  const notification = page.getByRole('region', {name: 'Run notification'});
  await expect(notification).toContainText('Single run queued');
  job = {...job, status: 'active'};
  await page.reload();
  await expect(page.getByRole('status', {name: 'Investigation job'})).toContainText('Investigation running');
  await expect(notification).toContainText('Single run running');
  await expect(page.getByRole('button', {name: 'Running…', exact: true})).toBeDisabled();
  await page.screenshot({path: '../.scratch/ticket-45-active-desktop.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: '../.scratch/ticket-45-active-mobile.png', fullPage: true});
  job = {...job, status: 'completed', run_id: 93};
  await expect(page).toHaveURL(/\/results\/runs\/93$/);
  const seeResults = notification.getByRole('button', {name: 'See the results'});
  await expect(seeResults).toBeVisible();
  await page.screenshot({path: '../.scratch/single-run-notification-mobile.png'});
  await page.getByRole('button', {name: 'Overview', exact: true}).click();
  await expect(page).toHaveURL(/\/results$/);
  await seeResults.click();
  await expect(page).toHaveURL(/\/results\/runs\/93$/);
  await expect(notification).toHaveCount(0);
  expect(intents).toHaveLength(1);
  expect(intents[0]).toMatch(/^[a-z0-9-]{36}$/);
});

test('interrupted job exposes uncertainty and never replays on reload', async ({page}) => {
  let submissions = 0;
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if (path === '/api/auth/session') data = {user: {id: 502, username: 'synthetic', role: 'analyst'}};
    if (path === '/api/runs/investigation-cases') data = [{case_id: 'soc-auth-001', case_version: '1', name: 'Synthetic case', attacks: []}];
    if (path === '/api/investigation-jobs') {
      if (route.request().method() === 'POST') submissions++;
      data = [{job_id: 'uncertain-job', status: 'interrupted', run_id: null, error_category: 'provider_outcome_uncertain'}];
    }
    await route.fulfill({json: data});
  });
  await page.goto('/dashboard/single');
  await expect(page.getByRole('status', {name: 'Investigation job'})).toContainText('provider outcome is uncertain');
  await page.reload();
  await expect(page.getByRole('status', {name: 'Investigation job'})).toContainText('will not replay automatically');
  await page.screenshot({path: '../.scratch/ticket-45-interrupted-desktop.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: '../.scratch/ticket-45-interrupted-mobile.png', fullPage: true});
  expect(submissions).toBe(0);
});

test('uncertain submission keeps the same intent after refresh', async ({page}) => {
  const intents = [];
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if (path === '/api/auth/session') data = {user: {id: 503, username: 'synthetic', role: 'analyst'}};
    if (path === '/api/runs/investigation-cases') data = [{case_id: 'soc-auth-001', case_version: '1', name: 'Synthetic case', attacks: []}];
    if (path === '/api/investigation-jobs' && route.request().method() === 'POST') {
      intents.push(route.request().headers()['idempotency-key']);
      if (intents.length === 1) return route.abort('failed');
      data = {job_id: 'retried-intent', status: 'completed', run_id: 94};
    }
    if (path === '/api/runs/94') data = {run_id: 94, id: 'EXP-094', status: 'completed', mode: 'Clean', model: 'scripted-soc-v2', trace: [], run_configuration: {}};
    await route.fulfill({json: data});
  });
  await page.goto('/dashboard/single');
  await page.getByRole('button', {name: 'Run MCP investigation', exact: true}).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name: 'Run MCP investigation', exact: true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/94$/);
  expect(intents).toHaveLength(2);
  expect(intents[1]).toBe(intents[0]);
});
