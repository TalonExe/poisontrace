import {test, expect} from '../verification-test.js';

test('production expiry, revocation and hosted HTTPS protections preserve private workspaces', async ({page}) => {
  test.setTimeout(60000);
  const hosted = process.env.POISONTRACE_TEST_CONTENT_PROFILE === 'hosted';
  await page.goto('/login');
  const operator = {username:'synthetic-operator',passcode:'synthetic-operator-passcode'};
  expect((await page.request.post('/api/auth/login',{data:operator})).status()).toBe(200);
  for (const username of ['session-first','session-second']) {
    expect((await page.request.post('/api/admin/users',{data:{username,display_name:username,passcode:'synthetic-session-passcode'}})).status()).toBe(201);
  }
  const users = await (await page.request.get('/api/admin/users')).json();
  const first = users.find(user=>user.username === 'session-first');
  await page.request.post('/api/auth/logout');
  const login = await page.request.post('/api/auth/login',{data:{username:'session-first',passcode:'synthetic-session-passcode'}});
  expect(login.status()).toBe(200);
  const cookie = (await page.context().cookies()).find(cookie=>cookie.name === 'poisontrace_session');
  expect(cookie.httpOnly).toBe(true);
  expect(cookie.secure).toBe(hosted);
  expect(cookie.sameSite).toBe('Lax');
  expect(cookie.expires).toBeGreaterThan(Date.now()/1000);
  const stale = cookie.value;
  await page.goto('/sessions');
  await expect(page.getByRole('heading',{name:'Settings'})).toBeVisible();
  await page.waitForLoadState('networkidle');
  expect((await page.request.post('/__test_advance')).status()).toBe(200);
  await page.getByRole('button',{name:'Results',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Sign in to PoisonTrace'})).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Your session ended');
  await page.screenshot({path:`../.scratch/ticket-43-${hosted?'hosted':'local'}-expired-desktop.png`,fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:`../.scratch/ticket-43-${hosted?'hosted':'local'}-expired-mobile.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.setViewportSize({width:1280,height:720});
  await page.getByLabel('Username',{exact:true}).fill('session-second');
  await page.getByLabel('Passcode',{exact:true}).fill('wrong');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Invalid username or passcode');
  await page.getByLabel('Passcode',{exact:true}).fill('synthetic-session-passcode');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page).toHaveURL(/\/activity$/);
  await expect(page.getByText('session-first',{exact:true})).toHaveCount(0);
  if (hosted) {
    for (const origin of ['null','https://evil.invalid']) {
      expect((await page.request.post('/api/auth/logout',{headers:{Origin:origin}})).status()).toBe(403);
    }
    expect((await page.request.get('/api/auth/session')).status()).toBe(200);
    for (const path of ['/docs','/redoc','/openapi.json']) expect((await page.request.get(path)).status()).toBe(404);
    for (let index=0;index<10;index++) expect((await page.request.post('/api/auth/login',{data:{username:'missing-session',passcode:'wrong'}})).status()).toBe(401);
    const throttled = await page.request.post('/api/auth/login',{data:{username:'missing-session',passcode:'wrong'}});
    expect(throttled.status()).toBe(429);
    expect(Number(throttled.headers()['retry-after'])).toBeGreaterThan(0);
  }
  await page.request.post('/api/auth/logout');
  await page.request.post('/api/auth/login',{data:{username:'session-first',passcode:'synthetic-session-passcode'}});
  const beforeDisable = (await page.context().cookies()).find(cookie=>cookie.name === 'poisontrace_session').value;
  await page.request.post('/api/auth/login',{data:operator});
  expect((await page.request.patch(`/api/admin/users/${first.id}`,{data:{status:'disabled'}})).status()).toBe(200);
  expect((await page.request.post('/api/auth/login',{data:{username:'session-first',passcode:'synthetic-session-passcode'}})).status()).toBe(401);
  expect((await page.request.patch(`/api/admin/users/${first.id}`,{data:{status:'active'}})).status()).toBe(200);
  expect((await page.request.get('/api/auth/session',{headers:{Cookie:`poisontrace_session=${beforeDisable}`}})).status()).toBe(401);
  expect((await page.request.get('/api/auth/session',{headers:{Cookie:`poisontrace_session=${stale}`}})).status()).toBe(401);
  expect((await page.request.post('/api/auth/login',{data:{username:'session-first',passcode:'synthetic-session-passcode'}})).status()).toBe(200);
  await page.request.post('/api/auth/logout');
  await page.goto('/login');
  await expect(page.getByRole('heading',{name:'Sign in to PoisonTrace'})).toBeVisible();
});
