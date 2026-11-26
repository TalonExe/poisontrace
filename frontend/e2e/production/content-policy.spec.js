import {test, expect} from '../verification-test.js';

test('production content policy retains local authoring and hosted read/run access', async ({page}) => {
  test.setTimeout(90000);
  const hosted = process.env.POISONTRACE_TEST_CONTENT_PROFILE === 'hosted';
  await page.goto('/login');
  expect((await page.request.post('/api/auth/login',{data:{username:'synthetic-operator',passcode:'synthetic-operator-passcode'}})).status()).toBe(200);
  expect((await page.request.post('/api/admin/users',{data:{username:'content-analyst',display_name:'Synthetic content analyst',passcode:'synthetic-content-passcode'}})).status()).toBe(201);
  await page.request.post('/api/auth/logout');
  await page.request.post('/api/auth/login',{data:{username:'content-analyst',passcode:'synthetic-content-passcode'}});
  expect((await (await page.request.get('/api/auth/session')).json()).user.content_read_only).toBe(hosted);
  const scenarios = await (await page.request.get('/api/scenarios')).json();
  const original = await (await page.request.get(`/api/scenarios/${scenarios[0].scenario_id}`)).json();
  const path = '/api/runs/investigation-cases/soc-auth-001';
  const ground = await (await page.request.get(path)).json();
  const payload = {base_version:ground.case_version,expected_decision:ground.expected_decision,dataset_category:ground.dataset_category,attack_targets:ground.attack_targets};
  await page.goto('/scenarios');
  if (hosted) {
    await expect(page.getByText('Curated content is read-only in hosted mode.',{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:/New scenario/})).toHaveCount(0);
    await expect(page.getByRole('checkbox')).toHaveCount(0);
    for (const [method,url,data] of [
      ['POST','/api/scenarios',{name:'Denied synthetic'}],
      ['PUT',`/api/scenarios/${original.scenario_id}`,{document:original.document}],
      ['DELETE',`/api/scenarios/${original.scenario_id}`,undefined],
      ['PUT',path,payload],
    ]) {
      const response = await page.request.fetch(url,{method,data});
      expect(response.status()).toBe(403);
      expect(await response.json()).toEqual({detail:'Curated content is read-only in hosted mode.'});
    }
    await page.goto(`/scenarios/${original.scenario_id}`);
    await expect(page.getByRole('heading',{name:'Scenario details'})).toBeVisible();
    await expect(page.getByLabel('Name',{exact:true}).first()).toHaveAttribute('readonly','');
    await expect(page.getByRole('button',{name:/Save scenario|Delete scenario|Add tool/})).toHaveCount(0);
    await page.screenshot({path:'../.scratch/ticket-42-hosted-scenario-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'../.scratch/ticket-42-hosted-scenario-mobile.png',fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.goto('/scenarios/new');
    await expect(page.getByRole('button',{name:/Save scenario/})).toHaveCount(0);
    await page.goto('/research-cases');
    await page.getByRole('button',{name:'View case ground truth',exact:true}).click();
    await expect(page.getByText('soc-auth-001 · version 1',{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:/Edit case ground truth|Save ground truth/})).toHaveCount(0);
    await page.screenshot({path:'../.scratch/ticket-42-hosted-case-mobile.png',fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await (await page.request.get(path)).json()).toEqual(ground);
    expect(await (await page.request.get(`/api/scenarios/${original.scenario_id}`)).json()).toEqual(original);
  } else {
    await page.getByRole('button',{name:/New scenario/}).click();
    await page.getByLabel('Name',{exact:true}).fill('Synthetic content draft');
    await page.getByRole('button',{name:/Save scenario/}).click();
    await expect(page).toHaveURL(/\/scenarios\/\d+$/);
    const draftId = new URL(page.url()).pathname.split('/').pop();
    expect((await (await page.request.get(`/api/scenarios/${draftId}`)).json()).valid).toBe(false);
    await page.getByLabel('Alert',{exact:true}).fill('Synthetic repair');
    await page.getByRole('button',{name:'+ Add tool',exact:true}).first().click();
    await page.locator('fieldset').first().getByLabel('Name',{exact:true}).fill('lookup');
    await page.locator('fieldset').first().getByLabel('Description',{exact:true}).fill('Synthetic read');
    await page.getByRole('button',{name:/Save scenario/}).click();
    await expect(page.getByRole('status')).toHaveText('Scenario saved.');
    expect((await (await page.request.get(`/api/scenarios/${draftId}`)).json()).valid).toBe(true);
    const deleteScenario = page.getByRole('button',{name:'Delete scenario',exact:true});
    await deleteScenario.click();
    const confirmation = page.getByRole('dialog', {name:'Delete scenario file?'});
    const scenario = await (await page.request.get(`/api/scenarios/${draftId}`)).json();
    await expect(confirmation).toContainText(scenario.filename);
    await expect(confirmation.getByRole('button', {name:'Cancel'})).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(deleteScenario).toBeFocused();
    await deleteScenario.click();
    await confirmation.getByRole('button', {name:'Delete file'}).click();
    await expect(page).toHaveURL(/\/scenarios$/);
    expect((await page.request.get(`/api/scenarios/${draftId}`)).status()).toBe(404);
    await page.goto('/research-cases');
    await page.getByRole('button',{name:'Edit case ground truth',exact:true}).click();
    await page.getByRole('combobox',{name:'Expected priority',exact:true}).selectOption('P2');
    await page.getByRole('button',{name:'Save ground truth as new version',exact:true}).click();
    await expect(page.getByRole('status')).toHaveText('Saved case version 2.');
    expect((await page.request.put(path,{data:payload})).status()).toBe(400);
  }
  await page.goto('/dashboard/single');
  await page.getByRole('button',{name:'Run MCP investigation',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/\d+$/, {timeout:30000});
  await expect(page.locator('.outcome')).toContainText('malicious');
  const resultPath = new URL(page.url()).pathname;
  await page.reload();
  await expect(page.locator('.outcome')).toContainText('escalate');
  const metadata = await page.request.post('/api/investigation-jobs',{
    headers:{"Idempotency-Key":"production-metadata-intent"},
    data:{workflow:'metadata-v1',scenario_id:original.scenario_id,mode:'clean',provider:'fake'},
  });
  expect(metadata.status()).toBe(202);
  const metadataJob = await metadata.json();
  await expect.poll(async () => (await (await page.request.get(`/api/investigation-jobs/${metadataJob.job_id}`)).json()).status).toBe('completed');
  const previousPid = (await (await page.request.post('/__test_pid')).json()).pid;
  await page.request.post('/__test_restart');
  await expect.poll(async()=>{try{return (await (await page.request.post('/__test_pid',{timeout:500})).json()).pid !== previousPid;}catch{return false;}}, {timeout:20000}).toBe(true);
  await expect.poll(async()=>{try{return (await page.request.get('/health/ready',{timeout:500})).status();}catch{return 0;}}).toBe(200);
  await page.goto(resultPath);
  await expect(page.locator('.outcome')).toContainText('malicious');
  expect((await (await page.request.get('/api/auth/session')).json()).user.content_read_only).toBe(hosted);
});
