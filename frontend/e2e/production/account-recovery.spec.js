import {test, expect} from '../verification-test.js';
import {randomBytes} from 'node:crypto';

test('admin resets an issued analyst while revoked browser sessions clear private work', async ({page, browser, baseURL}) => {
  test.setTimeout(90000);
  const hosted = process.env.POISONTRACE_TEST_CONTENT_PROFILE === 'hosted';
  const passcode = randomBytes(24).toString('hex');
  const replacement = randomBytes(24).toString('hex');
  const account = {username:'recovery-analyst',display_name:'Recovery analyst',passcode};
  await page.goto('/login');
  expect((await page.request.post('/api/auth/login',{data:{username:'synthetic-operator',passcode:'synthetic-operator-passcode'}})).status()).toBe(200);
  const created = await page.request.post('/api/admin/users',{data:account});
  expect(created.status()).toBe(201);
  const id = (await created.json()).id;
  const analystContext = await browser.newContext({baseURL,ignoreHTTPSErrors:hosted,extraHTTPHeaders:{Origin:baseURL}});
  try {
    const analyst = await analystContext.newPage();
    expect((await analyst.request.post('/api/auth/login',{data:{username:account.username,passcode}})).status()).toBe(200);
    await analyst.goto('/sessions');
    await expect(analyst.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
    expect((await analyst.request.post(`/api/admin/users/${id}/passcode`,{data:{passcode:replacement}})).status()).toBe(403);
    await page.goto('/admin/users');
    await page.getByRole('button',{name:/Recovery analyst recovery-analyst/}).click();
    await page.getByRole('button',{name:'Reset analyst passcode',exact:true}).click();
    await page.getByLabel('New passcode',{exact:true}).fill(replacement);
    await page.getByLabel('Confirm new passcode',{exact:true}).fill(replacement+'mismatch');
    await page.getByRole('button',{name:'Confirm passcode reset',exact:true}).click();
    await expect(page.getByRole('alert')).toContainText('Passcodes do not match');
    expect((await analyst.request.get('/api/auth/session')).status()).toBe(200);
    await page.getByLabel('Confirm new passcode',{exact:true}).fill(replacement);
    await page.getByRole('button',{name:'Confirm passcode reset',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('Passcode reset. All sessions for this analyst were revoked.');
    await expect(page.getByLabel('New passcode',{exact:true})).toHaveCount(0);
    await analyst.evaluate(()=>window.dispatchEvent(new Event('focus')));
    await expect(analyst.getByRole('heading',{name:'Sign in to PoisonTrace'})).toBeVisible();
    await expect(analyst.getByRole('heading',{name:'Settings',exact:true})).toHaveCount(0);
    expect((await analyst.request.post('/api/auth/login',{data:{username:account.username,passcode}})).status()).toBe(401);
    await analyst.getByLabel('Username',{exact:true}).fill(account.username);
    await analyst.getByLabel('Passcode',{exact:true}).fill(replacement);
    await analyst.getByRole('button',{name:'Sign in',exact:true}).click();
    await expect(analyst).toHaveURL(/\/activity$/);
    expect((await page.request.get('/api/runs')).status()).toBe(403);
    expect((await analyst.request.get('/api/admin/users')).status()).toBe(403);
    await page.getByRole('button',{name:'Reset analyst passcode',exact:true}).click();
    await page.getByLabel('New passcode',{exact:true}).fill(replacement);
    await page.getByLabel('Confirm new passcode',{exact:true}).fill(replacement);
    await page.screenshot({path:`../.scratch/ticket-44-${hosted?'hosted':'local'}-reset-desktop.png`,fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:`../.scratch/ticket-44-${hosted?'hosted':'local'}-reset-mobile.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('button',{name:'Cancel reset',exact:true}).click();
    await expect(page.getByLabel('New passcode',{exact:true})).toHaveCount(0);
    await page.getByRole('button',{name:/Development superadmin synthetic-operator/}).click();
    await expect(page.getByRole('button',{name:'Reset analyst passcode',exact:true})).toHaveCount(0);
    await expect(page.getByText(/Superadmin recovery requires/)).toBeVisible();
  } finally {
    await analystContext.close();
  }
});
