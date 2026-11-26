import {test, expect} from './verification-test.js';

test('scenario creation and browser back isolate editor drafts and transient state', async ({page}) => {
  let saved;
  let rejectSave = true;
  await page.route('**/api/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === '/api/auth/session')
      return route.fulfill({json: {user: {id: 601, username: 'synthetic-editor', role: 'analyst'}}});
    if (path === '/api/scenarios' && request.method() === 'POST') {
      if (rejectSave) {
        rejectSave = false;
        return route.fulfill({status: 400, json: {detail: 'Synthetic draft rejected'}});
      }
      saved = {...request.postDataJSON().document, scenario_id: '017'};
      return route.fulfill({json: {...saved, document: saved}});
    }
    if (path === '/api/scenarios/017') {
      if (request.method() === 'PUT') saved = {...saved, ...request.postDataJSON().document};
      return route.fulfill({json: {...saved, document: saved}});
    }
    return route.fulfill({json: []});
  });
  await page.goto('/scenarios');
  await page.getByRole('button', {name: /New scenario/}).click();
  await page.getByLabel('Name', {exact: true}).fill('Synthetic editor draft');
  await page.getByLabel('Alert', {exact: true}).fill('Synthetic alert');
  await page.getByRole('button', {name: /Save scenario/}).click();
  await expect(page.getByRole('alert')).toHaveText('Synthetic draft rejected');
  await page.getByRole('button', {name: /Save scenario/}).click();
  await expect(page).toHaveURL(/\/scenarios\/017$/);
  await expect(page.getByRole('heading', {name: 'Edit scenario', exact: true})).toBeVisible();
  await expect(page.getByLabel('Name', {exact: true})).toHaveValue('Synthetic editor draft');
  await expect(page.getByLabel('Scenario ID', {exact: true})).toHaveValue('017');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByRole('status')).toHaveCount(0);
  await page.getByRole('button', {name: /Save scenario/}).click();
  await expect(page.getByRole('status')).toHaveText('Scenario saved.');
  await page.getByLabel('Name', {exact: true}).fill('Unsaved edit');
  await page.goBack();
  await expect(page).toHaveURL(/\/scenarios\/new$/);
  await expect(page.getByRole('heading', {name: 'Create scenario', exact: true})).toBeVisible();
  await expect(page.getByLabel('Name', {exact: true})).toHaveValue('');
  await expect(page.getByLabel('Alert', {exact: true})).toHaveValue('');
  await expect(page.getByLabel('Scenario ID', {exact: true})).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByRole('status')).toHaveCount(0);
  await expect(page.getByRole('button', {name: /Save scenario/})).toBeEnabled();
});
