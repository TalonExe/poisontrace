import { test, expect } from './verification-test.js';

test('hosted library and direct authoring links offer read-only content', async ({page}) => {
  const document = {scenario_id:'001',name:'Curated synthetic case',alert:'Synthetic alert',tools:[],approved_tools:[]};
  await page.route(url => url.pathname.startsWith('/api/'), route => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({json: path === '/api/auth/session'
      ? {user:{id:1,username:'synthetic',role:'analyst',content_read_only:true}}
      : path === '/api/scenarios' ? [{...document,filename:'synthetic.yaml',valid:true}]
      : path === '/api/scenarios/001' ? {document}
      : path === '/api/runs/investigation-cases' ? [{case_id:'synthetic',case_version:'1',name:'Curated case'}]
      : path === '/api/runs/investigation-cases/synthetic' ? {case_id:'synthetic',case_version:'1',expected_decision:{verdict:'benign',priority:'P4',handling:'close'},attack_targets:{}}
      : []});
  });
  await page.goto('/scenarios');
  await expect(page.getByText('Curated content is read-only in hosted mode.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:/New scenario/})).toHaveCount(0);
  await expect(page.getByRole('checkbox')).toHaveCount(0);
  await page.getByRole('button',{name:/Curated synthetic case/}).click();
  await expect(page.getByRole('heading',{name:'Scenario details'})).toBeVisible();
  await expect(page.getByRole('button',{name:/Save scenario|Delete scenario|Add tool|Remove tool/})).toHaveCount(0);
  await expect(page.getByLabel('Name',{exact:true})).toHaveAttribute('readonly','');
  await page.goto('/scenarios/new');
  await expect(page.getByText('Curated content is read-only in hosted mode.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:/Save scenario/})).toHaveCount(0);
  await page.goto('/research-cases');
  await expect(page.getByRole('heading',{name:'MCP research cases',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'View case ground truth',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'View case ground truth',exact:true}).click();
  await expect(page.getByText('synthetic · version 1',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:/Save ground truth|Edit case ground truth/})).toHaveCount(0);
  await page.locator('.workspace-navigation summary').click();
  await expect(page.getByRole('button',{name:'MCP research case authoring',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'MCP research cases',exact:true})).toBeVisible();
});
