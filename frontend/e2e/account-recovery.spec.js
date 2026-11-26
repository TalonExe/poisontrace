import {test, expect} from './verification-test.js';

test('reset failures, cancellation and target changes clear entered passcodes', async ({page}) => {
  const operator = {id:1,username:'operator',display_name:'Operator',role:'superadmin',status:'active'};
  const accounts = [operator,{id:2,username:'first',display_name:'First analyst',role:'analyst',status:'active'},
    {id:3,username:'disabled',display_name:'Disabled analyst',role:'analyst',status:'disabled'}];
  let calls = 0;
  const updates = [];
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/passcode')) {
      calls++;
      return route.fulfill({status:503,json:{detail:'Reset unavailable. Try again later.'}});
    }
    if (path === '/api/admin/users/2' && route.request().method() === 'PATCH') {
      const payload = route.request().postDataJSON();
      updates.push(payload);
      accounts[1] = {...accounts[1], ...payload};
      return route.fulfill({json:accounts[1]});
    }
    return route.fulfill({json:path === '/api/auth/session' ? {user:operator} : accounts});
  });
  await page.goto('/admin/users');
  await page.getByRole('button',{name:/First analyst first/}).click();
  await page.getByRole('button',{name:'Reset analyst passcode',exact:true}).click();
  await page.getByLabel('New passcode',{exact:true}).fill('synthetic-new-passcode');
  await page.getByLabel('Confirm new passcode',{exact:true}).fill('synthetic-new-passcode');
  await page.getByRole('button',{name:'Confirm passcode reset',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Reset unavailable');
  await expect(page.getByLabel('New passcode',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Confirm new passcode',{exact:true})).toHaveValue('');
  await page.getByLabel('New passcode',{exact:true}).fill('synthetic-abandoned-passcode');
  await page.getByRole('button',{name:/Disabled analyst disabled/}).click();
  await page.getByRole('button',{name:'Reset analyst passcode',exact:true}).click();
  await expect(page.getByLabel('New passcode',{exact:true})).toHaveValue('');
  await expect(page.getByText(/This account will stay disabled/)).toBeVisible();
  await page.getByLabel('New passcode',{exact:true}).fill('synthetic-cancelled-passcode');
  await page.getByRole('button',{name:'Cancel reset',exact:true}).click();
  await page.getByRole('button',{name:'Reset analyst passcode',exact:true}).click();
  await expect(page.getByLabel('New passcode',{exact:true})).toHaveValue('');
  expect(calls).toBe(1);
  await page.getByRole('button',{name:/First analyst first/}).click();
  const disable = page.getByRole('button', {name:'Disable account',exact:true});
  await disable.click();
  const confirmation = page.getByRole('dialog', {name:'Disable account: First analyst?'});
  await expect(confirmation.getByRole('button', {name:'Cancel'})).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(disable).toBeFocused();
  expect(updates).toEqual([]);
  await disable.click();
  await confirmation.getByRole('button', {name:'Disable account'}).click();
  await expect(page.getByText('Account updated.')).toBeVisible();
  expect(updates).toEqual([{status:'disabled'}]);
});
