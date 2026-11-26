import {test, expect} from './verification-test.js';

test('expired protected requests clear the workspace and allow a different analyst to sign in', async ({page}) => {
  let user = {id: 43, username: 'first', display_name: 'First analyst', role: 'analyst'};
  let expired = false;
  let throttled = true;
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/auth/login') {
      if (throttled) return route.fulfill({status:429, headers:{'Retry-After':'60'}, json:{detail:'Too many sign-in attempts'}});
      user = {id:44, username:'second', display_name:'Second analyst', role:'analyst'};
      expired = false;
      return route.fulfill({json:{user, redirect:'/sessions'}});
    }
    if (expired) return route.fulfill({status:401, json:{detail:'Authentication required'}});
    return route.fulfill({json:path === '/api/auth/session' ? {user} : []});
  });
  await page.goto('/sessions');
  await expect(page.getByRole('heading',{name:'Settings'})).toBeVisible();
  await page.waitForLoadState('networkidle');
  expired = true;
  await page.getByRole('button',{name:'Results',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Sign in to PoisonTrace'})).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Your session ended');
  await expect(page.getByText('First analyst',{exact:true})).toHaveCount(0);
  await page.getByLabel('Username',{exact:true}).fill('second');
  await page.getByLabel('Passcode',{exact:true}).fill('synthetic-passcode');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('60 seconds');
  throttled = false;
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Analyst dashboard'})).toBeVisible();
  await expect(page.getByText('second',{exact:true})).toBeVisible();
  await expect(page.getByText('First analyst',{exact:true})).toHaveCount(0);
});
