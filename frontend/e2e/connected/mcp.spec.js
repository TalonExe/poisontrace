import { test, expect } from "@playwright/test";

test.afterAll(async ({ request }) => {
  for (const port of [4175, 4174]) {
    await request.post(`http://127.0.0.1:${port}/__test_shutdown`);
  }
  // Let the owned servers finish their cleanup before Playwright's process hook.
  for (const port of [4175, 4174])
    await expect
      .poll(async () => {
        try {
          await request.get(`http://127.0.0.1:${port}/`, { timeout: 500 });
          return false;
        } catch {
          return true;
        }
      })
      .toBe(true);
});

for (const [family, defended] of [[null,false], ["description-poisoning",false], ["cross-server-shadowing",false], ["description-poisoning",true], ["cross-server-shadowing",true]]) {
test(`real backend and MCP evidence survive browser refresh: ${family || "clean"} ${defended ? "defended" : "unrestricted"}`, async ({
  page,
}) => {
  // Forward HTTP to the isolated backend, without substituting any responses.
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const original = new URL(route.request().url());
      const response = await route.fetch({
        url: `http://127.0.0.1:4175${original.pathname}${original.search}`,
      });
      await route.fulfill({ response });
    },
  );
  const login = await page.request.post(
    "http://127.0.0.1:4175/api/auth/login",
    {
      data: {
        username: "browser-researcher",
        passcode: "synthetic-browser-test",
      },
    },
  );
  expect(login.ok()).toBe(true);
  await page.goto("/dashboard");
  await page
    .getByRole("combobox", { name: "Investigation workflow", exact: true })
    .selectOption(defended ? "Defended MCP investigation" : family ? "Attacked MCP investigation" : "Clean MCP investigation");
  if (family) await page.getByRole("combobox", {name:"Attack family",exact:true}).selectOption(family);
  await page
    .getByRole("button", { name: defended ? "Run defended MCP investigation" : family ? "Run attacked MCP investigation" : "Run clean MCP investigation", exact: true })
    .click();
  await expect(page).toHaveURL(/\/results\/runs\/[1-9]\d*$/, {
    timeout: 30000,
  });
  const savedPath = new URL(page.url()).pathname;
  await expect(page.locator(".outcome")).toContainText("malicious");
  await expect(page.locator(".outcome")).toContainText("P1");
  await expect(
    page.getByRole("region", { name: "Returned evidence" }),
  ).toContainText("unauthorized_access");
  await expect(page.locator(".timeline")).toContainText("model continued");
  await expect(page.locator(".timeline")).toContainText("server_pid");
  await expect(page.locator(".timeline")).toContainText("sdk_version");
  await expect(page.locator(".timeline")).toContainText("controlled-malicious");
  if (family) {
    await expect(page.locator(".outcome")).toContainText(family);
    await expect(page.locator(".outcome")).toContainText(family === "cross-server-shadowing" ? "soc-auth-shadow-v2" : "soc-auth-description-v2");
    await expect(page.locator(".timeline")).toContainText(family === "cross-server-shadowing" ? "do not call get_context" : "Investigation override");
  }
  if (defended) {
    await expect(page.locator(".outcome")).toContainText("Definitions withheld: 1");
    await expect(page.locator(".outcome")).toContainText("Calls rejected: 0");
  }
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`${savedPath}$`));
  await expect(page.locator(".outcome")).toContainText("escalate");
  await expect(
    page.getByRole("region", { name: "Returned evidence" }),
  ).toContainText("context-001");
  await page.screenshot({
    path: `.scratch/bounded-core/mcp-connected-${family || "clean"}-${defended ? "defended" : "unrestricted"}-desktop.png`,
    fullPage: true,
  });
});
}

test('real case ground-truth revision drives saved scores and rates without changing evidence',async ({page})=>{
  await page.route(url=>url.pathname.startsWith('/api/'),async route=>{
    const original=new URL(route.request().url());
    const response=await route.fetch({url:`http://127.0.0.1:4175${original.pathname}${original.search}`});
    await route.fulfill({response});
  });
  const login=await page.request.post('http://127.0.0.1:4175/api/auth/login',{data:{username:'browser-researcher',passcode:'synthetic-browser-test'}});
  expect(login.ok()).toBe(true);
  await page.goto('/dashboard');
  await page.getByRole('combobox',{name:'Investigation workflow',exact:true}).selectOption('Clean MCP investigation');
  await page.getByRole('button',{name:'Edit case ground truth',exact:true}).click();
  await page.getByRole('combobox',{name:'Expected priority',exact:true}).selectOption('P2');
  await page.getByRole('button',{name:'Save ground truth as new version',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Saved case version 2');
  await page.getByRole('button',{name:'Run clean MCP investigation',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/[1-9]\d*$/,{timeout:30000});
  await expect(page.locator('.outcome')).toContainText('Verdict correctness: Correct');
  await expect(page.locator('.outcome')).toContainText('Priority correctness: Incorrect');
  await expect(page.locator('.outcome')).toContainText('Handling correctness: Correct');
  await expect(page.locator('.outcome')).toContainText('Raw-output marker: Unscored / unavailable');
  await page.reload();
  await expect(page.locator('.outcome')).toContainText('Reference validity: Valid');
  await page.screenshot({path:'.scratch/bounded-core/scoring-connected-results-desktop.png',fullPage:true});
  await page.goto('/results');
  await page.getByText('MCP investigation rates',{exact:true}).click();
  await expect(page.getByRole('region',{name:'MCP scoring rates'})).toContainText('Priority correctness');
  await page.screenshot({path:'.scratch/bounded-core/scoring-connected-rates-desktop.png',fullPage:true});
});

test('fifteen-case catalog selects controls and P2 incident with saved independent scores', async ({page}) => {
  test.setTimeout(60000);
  await page.route(url => url.pathname.startsWith('/api/'),async route => {
    const original=new URL(route.request().url());
    const response=await route.fetch({url:`http://127.0.0.1:4175${original.pathname}${original.search}`});
    await route.fulfill({response});
  });
  const login=await page.request.post('http://127.0.0.1:4175/api/auth/login',{data:{username:'browser-researcher',passcode:'synthetic-browser-test'}});
  expect(login.ok()).toBe(true);
  for (const [identifier,category,verdict,priority] of [
    ['soc-backup-002','benign-activity','benign','P4'],
    ['soc-beacon-009','false-positive-alert','benign','P3'],
    ['soc-c2-013','malicious-incident','malicious','P2'],
  ]) {
    await page.goto('/dashboard');
    await page.getByRole('combobox',{name:'Investigation workflow',exact:true}).selectOption('Clean MCP investigation');
    const select=page.getByRole('combobox',{name:'Synthetic case',exact:true});
    await expect(select.locator('option')).toHaveCount(15);
    await select.selectOption(identifier);
    if (identifier==='soc-backup-002') {
      await page.getByRole('combobox',{name:'Investigation workflow',exact:true}).selectOption('Attacked MCP investigation');
      await expect(page.getByRole('button',{name:'Run attacked MCP investigation',exact:true})).toBeDisabled();
      await expect(page.getByRole('status')).toContainText('clean control');
      await page.getByRole('combobox',{name:'Investigation workflow',exact:true}).selectOption('Clean MCP investigation');
    }
    await page.getByRole('button',{name:'Edit case ground truth',exact:true}).click();
    await expect(page.getByRole('combobox',{name:'Expected handling',exact:true})).toHaveValue(verdict==='malicious' ? 'escalate' : 'close');
    if (identifier==='soc-c2-013') {
      await page.screenshot({path:'.scratch/bounded-core/corpus-dashboard-desktop.png',fullPage:true});
      await page.setViewportSize({width:390,height:844});
      await page.screenshot({path:'.scratch/bounded-core/corpus-dashboard-mobile.png',fullPage:true});
      await page.setViewportSize({width:1280,height:900});
    }
    await page.getByRole('button',{name:'Run clean MCP investigation',exact:true}).click();
    await expect(page).toHaveURL(/\/results\/runs\/[1-9]\d*$/,{timeout:30000});
    await expect(page.locator('.outcome')).toContainText(`Dataset category: ${category}`);
    await expect(page.locator('.outcome')).toContainText('All decision fields: Correct');
    await expect(page.locator('.investigation-decision')).toContainText(verdict);
    await expect(page.locator('.investigation-decision')).toContainText(priority);
    await page.reload();
    await expect(page.locator('.outcome')).toContainText('Reference validity: Valid');
    if (identifier==='soc-c2-013') {
      await page.screenshot({path:'.scratch/bounded-core/corpus-results-desktop.png',fullPage:true});
      await page.setViewportSize({width:390,height:844});
      await expect(page.locator('.outcome')).toContainText('Recommendation detail and reasoning');
      await page.screenshot({path:'.scratch/bounded-core/corpus-results-mobile.png',fullPage:true});
    }
  }
});

test('matched groups retain six attempts, reopen and link real MCP evidence', async ({page}) => {
  test.setTimeout(90000);
  await page.route(url=>url.pathname.startsWith('/api/'),async route=>{
    const url=new URL(route.request().url());
    const response=await route.fetch({url:`http://127.0.0.1:4175${url.pathname}${url.search}`,timeout:80000});
    await route.fulfill({response});
  });
  expect((await page.request.post('http://127.0.0.1:4175/api/auth/login',{data:{username:'browser-researcher',passcode:'synthetic-browser-test'}})).ok()).toBe(true);
  await page.goto('/dashboard');
  await page.getByRole('button',{name:'Matched group',exact:true}).click();
  await page.getByLabel('Group repeats').fill('2');
  await page.getByRole('button',{name:'Run matched group',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/groups\/[^/]+$/,{timeout:80000});
  await expect(page.getByRole('heading',{name:'Matched comparison',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:/Inspect attempt/})).toHaveCount(6);
  await expect(page.getByText('No missing conditions.')).toBeVisible();
  await expect(page.getByRole('region',{name:'Overall experiment performance'})).toContainText('6 correct results from 6 attempts; 0 failed.');
  const path=new URL(page.url()).pathname;
  await page.reload();
  await expect(page.getByRole('link',{name:/Inspect attempt/})).toHaveCount(6);
  for (const [width,height,name] of [[1440,1000,'desktop'],[390,844,'mobile']]) {
    await page.setViewportSize({width,height});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:`../.impeccable/review/matched-group-${name}.png`,fullPage:true});
  }
  await page.getByRole('link',{name:/Inspect attempt 1 /}).click();
  await expect(page.locator('.outcome')).toContainText('escalate');
  await expect(page.getByRole('region',{name:'Returned evidence'})).toContainText('unauthorized_access');
  await page.goto(path);
  await expect(page.getByRole('link',{name:/Inspect attempt/})).toHaveCount(6);
});

test('clean-control group can be rerun from Experiment without replacing prior evidence', async ({page})=>{
  test.setTimeout(60000);
  await page.route(url=>url.pathname.startsWith('/api/'),async route=>{
    const url=new URL(route.request().url());
    await route.fulfill({response:await route.fetch({url:`http://127.0.0.1:4175${url.pathname}${url.search}`,timeout:50000})});
  });
  await page.request.post('http://127.0.0.1:4175/api/auth/login',{data:{username:'browser-researcher',passcode:'synthetic-browser-test'}});
  await page.goto('/dashboard');
  await page.getByRole('button',{name:'Matched group',exact:true}).click();
  await page.getByLabel('Group case').selectOption('soc-backup-002');
  await expect(page.getByRole('checkbox',{name:'poisoned',exact:true})).toBeDisabled();
  await expect(page.getByRole('checkbox',{name:'defended',exact:true})).toBeDisabled();
  for (const [width,height,name] of [[1440,1000,'desktop'],[390,844,'mobile']]) {
    await page.setViewportSize({width,height});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:`../.impeccable/review/group-setup-${name}.png`,fullPage:true});
  }
  await page.getByRole('button',{name:'Run matched group',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/groups\/[^/]+$/,{timeout:30000});
  await expect(page.getByText('Not scheduled for this group: poisoned, defended.')).toBeVisible();
  const groupId=new URL(page.url()).pathname.split('/').pop();
  const first=await page.getByRole('link',{name:/Inspect attempt 1 /}).getAttribute('href');
  await page.getByRole('button',{name:'Configure a group or rerun',exact:true}).click();
  await page.getByRole('button',{name:'Matched group',exact:true}).click();
  await page.getByLabel('Group source').selectOption(groupId);
  await page.getByRole('button',{name:'Rerun matched group',exact:true}).click();
  await expect(page.getByRole('link',{name:/Inspect attempt/})).toHaveCount(2,{timeout:30000});
  await expect(page.getByRole('link',{name:/Inspect attempt 1 /})).toHaveAttribute('href',first);
  await page.reload();
  await expect(page.getByRole('link',{name:/Inspect attempt/})).toHaveCount(2);
  await expect(page.getByRole('region',{name:'Overall experiment performance'})).toContainText('2 correct results from 2 attempts; 0 failed.');
});
