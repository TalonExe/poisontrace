import { test, expect } from "../verification-test.js";

test('two analysts keep group plans, retained reruns, campaigns and child Results private', async ({page}) => {
  test.setTimeout(120000);
  const alice = {username:'private-plan-alice', passcode:'synthetic-plan-alice'};
  const bob = {username:'private-plan-bob', passcode:'synthetic-plan-bob'};
  const login = async (account) => {
    await page.request.post('/api/auth/logout');
    expect((await page.request.post('/api/auth/login', {data:account})).ok()).toBe(true);
  };
  await login({username:'synthetic-operator',passcode:'synthetic-operator-passcode'});
  for (const account of [alice,bob])
    expect((await page.request.post('/api/admin/users', {data:{...account,display_name:account.username}})).status()).toBe(201);
  await login(alice);
  await page.goto('/dashboard');
  await page.getByLabel('Group case', {exact:true}).selectOption('soc-backup-002');
  await page.getByRole('button',{name:'Run matched group',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/groups\/[^/]+$/, {timeout:30000});
  const groupPath = new URL(page.url()).pathname;
  const gid = groupPath.split('/').pop();
  await expect(page.getByRole('link',{name:/View trace · Attempt/})).toHaveCount(1, {timeout:30000});
  const notification = page.getByRole('region', {name:'Run notification'});
  await expect(notification).toContainText('Matched group complete');
  await page.getByRole('button', {name:'Overview', exact:true}).click();
  await notification.getByRole('button', {name:'See the results'}).click();
  await expect(page).toHaveURL((url) => url.pathname === groupPath);
  const original = await (await page.request.get(`/api/run-groups/${gid}`)).json();
  const firstLink = await page.getByRole('link',{name:/View trace · Attempt 1 ·/}).getAttribute('href');
  await page.getByRole('link',{name:/View trace · Attempt 1 ·/}).click();
  await expect(page.locator('.outcome')).toContainText('All decision fields: Correct');
  await expect(page.getByRole('region',{name:'Returned evidence'})).toContainText('backup');
  await page.goto('/dashboard');
  await page.getByLabel('Group source').selectOption(gid);
  await page.getByRole('button',{name:'Rerun matched group',exact:true}).click();
  await expect(page.getByRole('link',{name:/View trace · Attempt/})).toHaveCount(2, {timeout:30000});
  await expect(page.getByRole('link',{name:/View trace · Attempt 1 ·/})).toHaveAttribute('href',firstLink);
  const retained = await (await page.request.get(`/api/run-groups/${gid}`)).json();
  expect(retained.plan).toEqual(original.plan);
  expect(retained.attempts[0]).toEqual(original.attempts[0]);
  await page.reload();
  await expect(page.getByRole('region',{name:'Overall experiment performance'})).toContainText('2 correct results from 2 attempts');
  const campaign = await (await page.request.post('/api/campaigns', {data:{provider:'fake'}})).json();
  const cid = campaign.campaign_id;
  const response = await page.request.post(`/api/campaigns/${cid}/execute`, {headers:{"Idempotency-Key":"production-campaign-intent"}});
  expect(response.status()).toBe(202);
  const campaignJob = await response.json();
  await expect.poll(async () => (await (await page.request.get(`/api/investigation-jobs/${campaignJob.job_id}`)).json()).status).toBe('completed');
  const executed = await (await page.request.get(`/api/campaigns/${cid}`)).json();
  const child = executed.scenarios[0].child_run_id;
  const campaignPath = `/results/campaigns/${cid}`;
  await page.goto(campaignPath);
  await page.locator('.scenario-picker-row').first().click();
  await expect(page.locator('.campaign-trace')).toContainText('recommendation created');
  await page.getByRole('button',{name:`Open saved run ${child}`,exact:true}).click();
  await expect(page.locator('.outcome')).toBeVisible();
  await page.goto(campaignPath);
  await page.locator('.scenario-picker-row').first().click();
  await page.getByRole('button',{name:'Rerun scenario',exact:true}).click();
  await expect.poll(async () => (await (await page.request.get(`/api/campaigns/${cid}`)).json()).metrics.attempted).toBe(executed.scenarios.length+1);
  const latest = await (await page.request.get(`/api/campaigns/${cid}`)).json();
  expect(latest.scenarios[0].child_run_id).not.toBe(child);
  expect((await page.request.get(`/api/runs/${child}`)).ok()).toBe(true);
  // A genuine process restart retains ownership, the pinned plan and old attempts.
  const previousPid = (await (await page.request.post('/__test_pid')).json()).pid;
  await page.request.post('/__test_restart');
  await expect.poll(async () => {
    try { return (await (await page.request.post('/__test_pid',{timeout:500})).json()).pid !== previousPid; }
    catch { return false; }
  }, {timeout:20000}).toBe(true);
  await page.goto(groupPath);
  await expect(page.getByRole('link',{name:/View trace · Attempt/})).toHaveCount(2);
  expect(await (await page.request.get(`/api/run-groups/${gid}`)).json()).toEqual(retained);
  // Account switching on an open plan must remove its cached comparison and links.
  await login(bob);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('alert')).toContainText('group or case not found');
  await expect(page.locator('.group-comparison')).toHaveCount(0);
  await expect(page.getByRole('link',{name:/View trace · Attempt/})).toHaveCount(0);
  expect(await (await page.request.get('/api/run-groups')).json()).toEqual([]);
  expect(await (await page.request.get('/api/campaigns')).json()).toEqual([]);
  expect((await (await page.request.get('/api/runs/summary')).json()).attempted).toBe(0);
  await page.goto('/results/groups');
  await expect(page.getByText('No matched groups yet. Configure one on Experiment.',{exact:true})).toBeVisible();
  await page.goto('/results/campaigns');
  await expect(page.getByText('No campaigns recorded yet.',{exact:true})).toBeVisible();
  for (const path of [campaignPath,'/results/campaigns/unknown']) {
    await page.goto(path);
    await expect(page.getByRole('alert')).toContainText('campaign not found');
    await expect(page.locator('.selected-campaign')).toHaveCount(0);
  }
  for (const id of [cid,'unknown']) {
    expect((await page.request.post(`/api/campaigns/${id}/execute`)).status()).toBe(404);
    expect((await page.request.post(`/api/campaigns/${id}/scenarios/0/rerun`)).status()).toBe(404);
  }
  for (const id of [gid,'unknown'])
    expect((await page.request.post(`/api/run-groups/${id}/execute`,{data:{}})).status()).toBe(404);
  for (const path of [firstLink,`/results/runs/${child}`]) {
    await page.goto(path);
    await expect(page.getByRole('alert')).toContainText('run not found');
    await expect(page.locator('.outcome')).toHaveCount(0);
  }
  await page.goto('/dashboard');
  await expect(page.getByLabel('Group source').locator('option')).toHaveCount(1);
  await page.getByLabel('Group case',{exact:true}).selectOption('soc-backup-002');
  await page.getByRole('button',{name:'Run matched group',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/groups\/[^/]+$/, {timeout:30000});
  const bobPath = new URL(page.url()).pathname;
  expect(bobPath).not.toBe(groupPath);
  await expect(notification).toContainText('Matched group complete', {timeout:30000});
  const bobJobs = await (await page.request.get('/api/investigation-jobs')).json();
  expect(bobJobs.find(job => job.group_id === bobPath.split('/').pop())?.status).toBe('completed');
  await login(alice);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('alert')).toContainText('group or case not found');
  await page.goto(campaignPath);
  await page.locator('.scenario-picker-row').first().click();
  await expect(page.locator('.campaign-trace')).toBeVisible();
  await login(bob);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('alert')).toContainText('campaign not found');
  await expect(page.locator('.campaign-trace')).toHaveCount(0);
  await login(alice);
  await page.goto(groupPath);
  await expect(page.getByRole('link',{name:/View trace · Attempt/})).toHaveCount(2);
  await page.screenshot({path:'../.scratch/production-browser/private-plans.png',fullPage:true});
});

test("built frontend, operator-issued analyst, offline MCP Results and process restart", async ({ page }) => {
  await page.goto("/admin/users");
  await page.getByLabel("Username").fill("synthetic-operator");
  await page.getByLabel("Passcode").fill("synthetic-operator-passcode");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/users$/);
  await page.reload();
  await expect(page.getByRole("heading", { name: "User management", exact: true })).toBeVisible();
  expect((await page.request.get("/api/runs")).status()).toBe(403);
  expect((await page.request.get("/api/runs/summary")).status()).toBe(403);
  await page.goto('/results/runs/1');
  await expect(page.getByRole('heading', {name:'403 Forbidden', exact:true})).toBeVisible();
  await page.goto('/admin/users');
  expect((await page.request.post("/api/admin/users", {data: {
    username: "synthetic-browser-analyst", display_name: "Synthetic analyst", passcode: "synthetic-browser-passcode",
  }})).status()).toBe(201);
  expect((await page.request.post("/api/admin/users", {data: {
    username: "synthetic-browser-bob", display_name: "Synthetic Bob", passcode: "synthetic-bob-passcode",
  }})).status()).toBe(201);
  await page.request.post("/api/auth/logout");
  await page.goto("/login");
  await page.getByLabel("Username").fill("synthetic-browser-analyst");
  await page.getByLabel("Passcode").fill("synthetic-browser-passcode");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/activity$/);
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  expect((await page.request.get("/api/admin/users")).status()).toBe(403);
  const generatedKey = `generated-${Date.now()}-offline-only-key`;
  const credential = await (await page.request.post("/api/credentials", { data: {
    provider: "gemini", label: "Alice private credential", secret: generatedKey, owner_id: 3,
  }})).json();
  await page.reload();
  await page.getByRole("button", { name: "New configuration" }).click();
  await expect(page.locator(".credential-row")).toContainText("Alice private credential");
  await expect(page.locator(".credential-row")).not.toContainText(generatedKey);
  await page.request.post("/api/auth/logout");
  await page.request.post("/api/auth/login", { data: { username: "synthetic-browser-bob", passcode: "synthetic-bob-passcode" } });
  await page.reload();
  await page.getByRole("button", { name: "New configuration" }).click();
  await expect(page.locator(".credential-row")).toHaveCount(0);
  expect(await (await page.request.get("/api/credentials")).json()).toEqual([]);
  for (const reference of [credential.credential_id, "unknown"])
    expect((await page.request.post(`/api/credentials/${reference}/test`)).status()).toBe(404);
  await page.request.post("/api/auth/logout");
  await page.request.post("/api/auth/login", { data: { username: "synthetic-browser-analyst", passcode: "synthetic-browser-passcode" } });
  await page.reload();
  await page.getByRole("button", { name: "New configuration" }).click();
  await expect(page.locator(".credential-row")).toContainText("Alice private credential");
  expect((await page.request.delete(`/api/credentials/${credential.credential_id}`)).status()).toBe(200);
  await page.reload();
  await page.getByRole("button", { name: "New configuration" }).click();
  await expect(page.locator(".credential-row")).toHaveCount(0);

  const missing = await page.request.get("/api/missing");
  expect(missing.status()).toBe(404);
  expect(missing.headers()["content-type"]).toContain("application/json");
  await page.goto("/dashboard/single");
  await page.reload();
  await page.getByRole("button", { name: "Run MCP investigation", exact: true }).click();
  await expect(page.getByRole("status", { name: "Investigation job" }).or(
    page.getByRole("heading", { name: "Results", exact: true }),
  )).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/results\/runs\/[1-9]\d*$/, { timeout: 30000 });
  const path = new URL(page.url()).pathname;
  await expect(page.locator(".outcome")).toContainText("malicious");
  await page.reload();
  await expect(page.locator(".outcome")).toContainText("escalate");
  const saved = await (await page.request.get(`/api/runs/${path.split("/").pop()}`)).json();
  expect(JSON.parse(saved.run_configuration.transport_identity).servers).toHaveLength(2);
  const previousPid = (await (await page.request.post("/__test_pid")).json()).pid;
  await page.request.post("/__test_restart");
  await expect.poll(async () => {
    try { return (await (await page.request.post("/__test_pid", { timeout: 500 })).json()).pid !== previousPid; }
    catch { return false; }
  }, {timeout:20000}).toBe(true);
  await expect.poll(async () => {
    try { return (await page.request.get("/health/ready", { timeout: 500 })).status(); }
    catch { return 0; }
  }).toBe(200);
  await page.goto(path);
  await expect(page.locator(".outcome")).toContainText("malicious");
  expect(await (await page.request.get(`/api/runs/${saved.run_id}`)).json()).toEqual(saved);
  // Account-scoped configuration, selection, direct links and cached Results.
  await page.goto('/sessions');
  await page.getByRole('button', {name:'New configuration'}).click();
  await page.getByLabel('Configuration name').fill('Alice private study');
  await page.getByRole('button', {name:'Save configuration'}).click();
  await page.locator('.session-row').filter({hasText:'Alice private study'}).getByRole('button', {name:'Open', exact:true}).click();
  await expect(page.locator('.execution-selection select')).toHaveValue(/config:/);
  await page.goto(path);
  await expect(page.locator('.outcome')).toContainText('malicious');
  await page.getByRole('button', {name:'Sign out', exact:true}).click();
  await page.getByLabel('Username').fill('synthetic-browser-bob');
  await page.getByLabel('Passcode').fill('synthetic-bob-passcode');
  await page.getByRole('button', {name:'Sign in', exact:true}).click();
  await page.getByRole('button', {name:'Settings', exact:true}).click();
  await expect(page.getByRole('heading', {name:'Settings', exact:true})).toBeVisible();
  await expect(page.locator('.session-row')).not.toContainText('Alice private study');
  expect(await (await page.request.get('/api/runs')).json()).toEqual([]);
  const emptyMetrics = await (await page.request.get('/api/runs/summary')).json();
  expect(emptyMetrics.attempted).toBe(0);
  expect(emptyMetrics.system_error_rate).toBeNull();
  await page.goto('/results/runs');
  await expect(page.locator('.empty-state')).toContainText('No runs recorded yet.');
  await page.goto('/results');
  await page.getByText('Recorded rates by condition', {exact:true}).click();
  await expect(page.getByLabel('Run counts')).toContainText('0 attempts');
  await expect(page.getByText('No recorded attempts yet.', {exact:true})).toBeVisible();
  await page.goto(path);
  await expect(page.getByRole('alert')).toContainText('run not found');
  await expect(page.locator('.outcome')).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('run not found');
  await page.goto('/dashboard/single');
  await expect(page.locator('.execution-selection select')).toHaveValue('scripted');
  await page.getByRole('button', {name:'Run MCP investigation', exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/[1-9]\d*$/, {timeout:30000});
  const bobPath = new URL(page.url()).pathname;
  expect(bobPath).not.toBe(path);
  await page.reload();
  await expect(page.locator('.outcome')).toContainText('malicious');
  expect((await (await page.request.get('/api/runs/summary')).json()).attempted).toBe(1);
  await page.request.post('/api/auth/logout');
  await page.request.post('/api/auth/login', {data:{username:'synthetic-browser-analyst',passcode:'synthetic-browser-passcode'}});
  await page.goto('/sessions');
  await expect(page.locator('.session-row').filter({hasText:'Alice private study'})).toHaveCount(1);
  await page.goto('/dashboard/single');
  await expect(page.locator('.execution-selection select')).toHaveValue(/config:/);
  await page.goto(bobPath);
  await expect(page.getByRole('alert')).toContainText('run not found');
  await page.goto('/results');
  expect((await (await page.request.get('/api/runs/summary')).json()).attempted).toBe(1);
  await page.getByText('MCP investigation rates', {exact:true}).click();
  await expect(page.getByRole('region', {name:'MCP scoring rates'})).toContainText('1 attempts · 1 completed · 0 failed');
  await page.goto(path);
  await expect(page.locator('.outcome')).toContainText('malicious');
  // A cookie changed in another tab is rechecked on focus, clearing old Results.
  await page.request.post('/api/auth/logout');
  await page.request.post('/api/auth/login', {data:{username:'synthetic-browser-bob',passcode:'synthetic-bob-passcode'}});
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByRole('alert')).toContainText('run not found');
  await expect(page.locator('.outcome')).toHaveCount(0);
  await page.request.post('/api/auth/logout');
  await page.request.post('/api/auth/login', {data:{username:'synthetic-browser-analyst',passcode:'synthetic-browser-passcode'}});
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.locator('.outcome')).toContainText('malicious');
  await page.screenshot({ path: "../.scratch/production-browser/results.png", fullPage: true });
});
