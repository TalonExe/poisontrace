import { test, expect } from "@playwright/test";

test("attacked investigation selects a family and reopens saved payload provenance", async ({page}) => {
  let submitted;
  const saved = {run_id:71,id:'EXP-071',workflow:'mcp-investigation-v1',mode:'Poisoned',status:'failed',
    model:'scripted-soc-v1',scoring_version:'investigation-unscored-v1',error_category:'investigation_call_limit',
    investigation:{case_id:'soc-auth-001',case_version:'1',decision:null,evidence:[],
      attack:{family:'cross-server-shadowing',payload_id:'soc-auth-shadow-v2',target_verdict:'benign',target_priority:'P4',target_handling:'close'},
      expected_decision:{verdict:'malicious',priority:'P1',handling:'escalate'}},trace:[]};
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if(path === '/api/auth/session') data={user:{username:'researcher',role:'analyst'}};
    if(path === '/api/runs/investigation-cases') data=[{case_id:'soc-auth-001',case_version:'1',name:'Synthetic authentication',
      attacks:[{family:'description-poisoning',payload_id:'soc-auth-description-v2'},{family:'cross-server-shadowing',payload_id:'soc-auth-shadow-v2'}]}];
    if(path === '/api/runs' && route.request().method() === 'POST') {submitted=route.request().postDataJSON();data=saved;}
    if(path === '/api/runs/71') data=saved;
    await route.fulfill({json:data});
  });
  await page.goto('/dashboard');
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await page.getByRole('combobox',{name:'Condition',exact:true}).selectOption('poisoned');
  await page.getByRole('combobox',{name:'Attack family',exact:true}).selectOption('cross-server-shadowing');
  await expect(page.locator('.launcher')).toContainText('soc-auth-shadow-v2');
  await page.screenshot({path:'.scratch/bounded-core/attack-dashboard-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'.scratch/bounded-core/attack-dashboard-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Run MCP investigation',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/71$/);
  expect(submitted).toMatchObject({mode:'poisoned',attack_family:'cross-server-shadowing',provider:'scripted'});
  expect(submitted.credential_id).toBeUndefined();
  await expect(page.locator('.outcome')).toContainText('soc-auth-shadow-v2');
  await expect(page.locator('.outcome')).toContainText('benign / P4 / close');
  await expect(page.locator('.decision-expected')).toHaveText(['Expected: malicious','Expected: P1','Expected: escalate']);
  await page.reload();
  await expect(page.locator('.outcome')).toContainText('cross-server-shadowing');
  await page.screenshot({path:'.scratch/bounded-core/attack-results-mobile.png',fullPage:true});
  await page.setViewportSize({width:1280,height:900});
  await page.screenshot({path:'.scratch/bounded-core/attack-results-desktop.png',fullPage:true});
});

test("researcher runs an offline MCP case and reopens its structured evidence", async ({
  page,
}) => {
  let submitted;
  const result = {
    run_id: 41,
    id: "EXP-041",
    scenario_id: "soc-auth-001",
    mode: "Clean",
    workflow: "mcp-investigation-v1",
    status: "completed",
    model: "scripted-soc-v1",
    scoring_version: "investigation-unscored-v1",
    task_outcome: "Investigation complete; correctness unscored",
    result: "Investigation complete; correctness unscored",
    execution_time_ms: 20,
    investigation: {
      case_id: "soc-auth-001",
      case_version: "1",
      decision: {
        verdict: "malicious",
        priority: "P1",
        handling: "escalate",
        explanation: "Retrieved evidence indicates unapproved access.",
        evidence_refs: ["auth-001"],
      },
      evidence: [
        {
          server_id: "trusted-soc",
          tool_name: "get_evidence",
          arguments: { case_id: "soc-auth-001" },
          result: {
            records: [{ evidence_id: "auth-001", unauthorized_access: true }],
          },
        },
      ],
    },
    trace: [
      {
        kind: "tool_result",
        data: {
          server_id: "trusted-soc",
          tool_name: "get_evidence",
          result: { records: [{ evidence_id: "auth-001" }] },
        },
      },
      { kind: "model_continued", data: { evidence_refs: ["auth-001"] } },
      {
        kind: "investigation_completed",
        data: { verdict: "malicious", priority: "P1" },
      },
    ],
  };
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data = [];
      if (path === "/api/auth/session")
        data = { user: { username: "researcher", role: "analyst" } };
      if (path === "/api/runs/investigation-cases")
        data = [
          {
            case_id: "soc-auth-001",
            case_version: "1",
            name: "Unrecognized privileged authentication",
          },
        ];
      if (path === "/api/runs" && route.request().method() === "POST") {
        submitted = route.request().postDataJSON();
        data = result;
      }
      if (path === "/api/runs/41") data = result;
      await route.fulfill({ json: data });
    },
  );
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Condition", exact: true }),
  ).toBeVisible({ timeout: 2000 });
  await page
    .getByRole("combobox", { name: "Condition", exact: true })
    .selectOption("clean");
  await expect(
    page.getByText("No API key used."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Run MCP investigation",
      exact: true,
    }),
  ).toBeEnabled();
  await page.screenshot({
    path: ".scratch/bounded-core/mcp-dashboard-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: ".scratch/bounded-core/mcp-dashboard-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page
    .getByRole("button", { name: "Run MCP investigation", exact: true })
    .click();
  await expect(page).toHaveURL(/\/results\/runs\/41$/);
  expect(submitted).toMatchObject({
    workflow: "mcp-investigation-v1",
    case_id: "soc-auth-001",
    mode: "clean",
    provider: "scripted",
  });
  expect(submitted.credential_id).toBeUndefined();
  await expect(page).toHaveURL(/\/results\/runs\/41$/);
  await expect(page.locator(".outcome")).toContainText("malicious");
  await expect(page.locator(".outcome")).toContainText("P1");
  await expect(page.locator(".outcome")).toContainText("escalate");
  await expect(
    page.getByRole("region", { name: "Returned evidence" }),
  ).toContainText("unauthorized_access");
  await page.getByRole("link", { name: "auth-001", exact: true }).click();
  await expect(page.locator("#evidence-41-auth-001")).toBeInViewport();
  await page.reload();
  await expect(page.locator(".outcome")).toContainText(
    "Correctness is unscored",
  );
  await expect(page.locator(".timeline")).toContainText("model continued");
  await page.screenshot({
    path: ".scratch/bounded-core/mcp-results-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: ".scratch/bounded-core/mcp-results-mobile.png",
    fullPage: true,
  });
});

test("failed MCP attempt keeps partial evidence and unavailable outcomes visible", async ({
  page,
}) => {
  const failed = {
    run_id: 42,
    id: "EXP-042",
    workflow: "mcp-investigation-v1",
    scoring_version: "investigation-unscored-v1",
    status: "failed",
    error_category: "investigation_call_limit",
    scenario_id: "soc-auth-001",
    mode: "Clean",
    execution_time_ms: 30,
    investigation: {
      case_id: "soc-auth-001",
      case_version: "1",
      decision: null,
      evidence: [
        {
          server_id: "trusted-soc",
          tool_name: "get_alert",
          arguments: { case_id: "soc-auth-001" },
          result: {
            records: [{ evidence_id: "alert-001", failed_logins: 18 }],
          },
        },
      ],
    },
    trace: [
      {
        kind: "investigation_failed",
        data: { error_category: "investigation_call_limit" },
      },
    ],
  };
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      await route.fulfill({
        json:
          path === "/api/auth/session"
            ? { user: { username: "researcher", role: "analyst" } }
            : path === "/api/runs"
              ? [failed]
              : path === "/api/runs/42"
                ? failed
                : [],
      });
    },
  );
  await page.goto("/results/runs/42");
  await expect(page.locator(".outcome")).toContainText("Investigation failed");
  await expect(page.locator(".outcome")).toContainText(
    "Correctness is unscored",
  );
  await expect(page.locator(".outcome")).toContainText(
    "No final decision saved",
  );
  await expect(
    page.getByRole("region", { name: "Returned evidence" }),
  ).toContainText("alert-001");
  await expect(page.locator(".timeline")).toContainText(
    "investigation_call_limit",
  );
});

test("Gemini investigation uses the configured session credential and actual model", async ({ page }) => {
  let submitted;
  await page.addInitScript(() => localStorage.setItem('poisontrace.synthetic.sessions', JSON.stringify([{id:'session-1', name:'Gemini study', model:'gemini', credentialId:'private-ref'}])));
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if (path === '/api/credentials') data = [{credential_id:'private-ref',provider:'gemini',label:'Synthetic credential',masked:'***test'}];
    if (path === '/api/auth/session') data = {user:{username:'researcher',role:'analyst'}};
    if (path === '/api/runs/investigation-cases') data = [{case_id:'soc-auth-001',name:'Synthetic authentication',case_version:'1'}];
    if (path === '/api/runs' && route.request().method() === 'POST') { submitted = route.request().postDataJSON(); data = {run_id:61}; }
    if (path === '/api/runs/61') data = {run_id:61, id:'EXP-061', status:'failed', scoring_version:'investigation-unscored-v1', error_category:'investigation_validation_error', workflow:'mcp-investigation-v1', model:'gemini-3.5-flash-lite', mode:'Clean', investigation:{case_id:'soc-auth-001',case_version:'1',decision:null,evidence:[]},trace:[]};
    await route.fulfill({json:data});
  });
  await page.goto('/dashboard');
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await page.getByRole('combobox',{name:'Condition',exact:true}).selectOption('clean');
  await page.getByRole('combobox',{name:'Execution model and credential',exact:true}).selectOption('config:session-1');
  await expect(page.locator('.welcome')).toContainText('Gemini API LLM');
  await expect(page.getByText('gemini-3.5-flash-lite · Credential: Synthetic credential · ***test')).toBeVisible();
  await page.screenshot({path:'.scratch/bounded-core/gemini-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'.scratch/bounded-core/gemini-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Run MCP investigation',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/61$/);
  expect(submitted).toMatchObject({provider:'gemini',model:'gemini-3.5-flash-lite',credential_id:'private-ref'});
  await expect(page.locator('.outcome')).toContainText('Investigation failed');
  await expect(page.locator('.outcome')).toContainText(submitted.model);
});

test("OpenAI investigation uses the configured session credential and actual model", async ({ page }) => {
  let submitted;
  await page.addInitScript(() => localStorage.setItem('poisontrace.synthetic.sessions', JSON.stringify([{id:'session-1', name:'OpenAI study', model:'openai', credentialId:'private-ref'}])));
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if (path === '/api/credentials') data = [{credential_id:'private-ref',provider:'openai',label:'Synthetic credential',masked:'***test'}];
    if (path === '/api/auth/session') data = {user:{username:'researcher',role:'analyst'}};
    if (path === '/api/runs/investigation-cases') data = [{case_id:'soc-auth-001',name:'Synthetic authentication',case_version:'1'}];
    if (path === '/api/runs' && route.request().method() === 'POST') { submitted = route.request().postDataJSON(); data = {run_id:61}; }
    if (path === '/api/runs/61') data = {run_id:61, id:'EXP-061', status:'failed', scoring_version:'investigation-unscored-v1', error_category:'investigation_validation_error', workflow:'mcp-investigation-v1', model:'gpt-5-mini', mode:'Clean', investigation:{case_id:'soc-auth-001',case_version:'1',decision:null,evidence:[]},trace:[]};
    await route.fulfill({json:data});
  });
  await page.goto('/dashboard');
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await page.getByRole('combobox',{name:'Condition',exact:true}).selectOption('clean');
  await page.getByRole('combobox',{name:'Execution model and credential',exact:true}).selectOption('config:session-1');
  await expect(page.locator('.welcome')).toContainText('OpenAI API LLM');
  await expect(page.getByText('gpt-5-mini · Credential: Synthetic credential · ***test')).toBeVisible();
  await page.screenshot({path:'.scratch/bounded-core/openai-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'.scratch/bounded-core/openai-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Run MCP investigation',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/61$/);
  expect(submitted).toMatchObject({provider:'openai',model:'gpt-5-mini',credential_id:'private-ref'});
  await expect(page.locator('.outcome')).toContainText('Investigation failed');
  await expect(page.locator('.outcome')).toContainText(submitted.model);
});

test("OpenAI metadata single run and campaign forward gpt-5-mini", async ({page}) => {
  const submitted = [];
  await page.addInitScript(() => localStorage.setItem('poisontrace.synthetic.sessions', JSON.stringify([{id:'session-1',name:'OpenAI configuration',model:'openai',credentialId:'private-ref'}])));
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if (path === '/api/auth/session') data = {user:{username:'researcher',role:'analyst'}};
    if (path === '/api/scenarios') data = [{scenario_id:'002',name:'Synthetic case',valid:true}];
    if (route.request().method() === 'POST' && ['/api/runs','/api/campaigns'].includes(path)) {
      submitted.push(route.request().postDataJSON());
      await route.fulfill({status:400,json:{detail:'Synthetic stop after request capture'}});
      return;
    }
    await route.fulfill({json:data});
  });
  await page.goto('/dashboard/metadata');
  await page.getByRole('button',{name:'Run new experiment',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Synthetic stop');
  expect(submitted[0]).toMatchObject({provider:'openai',model:'gpt-5-mini',credential_id:'private-ref'});
  await page.locator('.workspace-navigation summary').click();
  await page.getByRole('button',{name:'Metadata campaigns',exact:true}).click();
  await page.getByRole('button',{name:'Run all poisoned scenarios',exact:true}).click();
  await expect.poll(() => submitted.length).toBe(2);
  expect(submitted[1]).toMatchObject({provider:'openai',model:'gpt-5-mini',credential_id:'private-ref'});
});

test("defended investigation explains restrictions independently of its final answer", async ({page}) => {
  let submitted;
  const saved = {run_id:71,id:'EXP-071',workflow:'mcp-investigation-v1',mode:'Defended',status:'completed',
    model:'scripted-soc-v1',scoring_version:'investigation-unscored-v1',execution_time_ms:20,
    investigation:{case_id:'soc-auth-001',case_version:'1',decision:{verdict:'benign',priority:'P4',handling:'close',explanation:'Deliberately wrong offline fixture.',evidence_refs:['auth-001']},evidence:[{server_id:'trusted-soc',tool_name:'get_evidence',arguments:{case_id:'soc-auth-001'},result:{records:[{evidence_id:'auth-001',unauthorized_access:true}]}}],manifest:{enforced:true,discovered:[{name:'get_evidence'},{name:'get_advisory'}],exposed:[{name:'get_evidence'}],restrictions:[{server_id:'controlled-malicious',tool_name:'get_advisory',reason:'definition_mismatch'}],invocation_rejections:[],executed_calls:1,no_call:false},
      attack:{family:'cross-server-shadowing',payload_id:'soc-auth-shadow-v1',target_verdict:'benign',target_priority:'P4',target_handling:'close'},
      expected_decision:{verdict:'malicious',priority:'P1',handling:'escalate'}},trace:[]};
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    let data = [];
    if(path === '/api/auth/session') data={user:{username:'researcher',role:'analyst'}};
    if(path === '/api/runs/investigation-cases') data=[{case_id:'soc-auth-001',case_version:'1',name:'Synthetic authentication',
      attacks:[{family:'description-poisoning',payload_id:'soc-auth-description-v1'},{family:'cross-server-shadowing',payload_id:'soc-auth-shadow-v1'}]}];
    if(path === '/api/runs' && route.request().method() === 'POST') {submitted=route.request().postDataJSON();data=saved;}
    if(path === '/api/runs/71') data=saved;
    await route.fulfill({json:data});
  });
  await page.goto('/dashboard');
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await page.getByRole('combobox',{name:'Condition',exact:true}).selectOption('defended');
  await page.getByRole('combobox',{name:'Attack family',exact:true}).selectOption('cross-server-shadowing');
  await expect(page.locator('.launcher')).toContainText('soc-auth-shadow-v1');
  await page.screenshot({path:'.scratch/bounded-core/defense-dashboard-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'.scratch/bounded-core/defense-dashboard-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Run MCP investigation',exact:true}).click();
  await expect(page).toHaveURL(/\/results\/runs\/71$/);
  expect(submitted).toMatchObject({mode:'defended',attack_family:'cross-server-shadowing',provider:'scripted'});
  expect(submitted.credential_id).toBeUndefined();
  await expect(page.locator('.outcome')).toContainText('soc-auth-shadow-v1');
  await expect(page.locator('.outcome')).toContainText('benign / P4 / close');
  await expect(page.locator('.decision-expected')).toHaveText(['Expected: malicious','Expected: P1','Expected: escalate']);
  await expect(page.locator('.outcome')).toContainText('Definitions withheld: 1');
  await expect(page.locator('.outcome')).toContainText('Calls rejected: 0');
  await expect(page.locator('.outcome')).toContainText('controlled-malicious / get_advisory: definition_mismatch');
  await page.reload();
  await expect(page.locator('.outcome')).toContainText('cross-server-shadowing');
  await page.screenshot({path:'.scratch/bounded-core/defense-results-mobile.png',fullPage:true});
  await page.setViewportSize({width:1280,height:900});
  await page.screenshot({path:'.scratch/bounded-core/defense-results-desktop.png',fullPage:true});
});


test("case ground truth is versioned and structured scores reopen independently", async ({page}) => {
  let saved;
  const caseData = {case_id:'soc-auth-001',case_version:'1',name:'Synthetic authentication',dataset_category:'malicious-incident',expected_decision:{verdict:'malicious',priority:'P1',handling:'escalate'},attack_targets:{'description-poisoning':{verdict:'benign',handling:'close'}}};
  const result = {run_id:88,id:'EXP-088',mode:'Poisoned',model:'offline-scoring-check',status:'completed',scoring_version:'investigation-scoring-v1',execution_time_ms:20,
    investigation:{case_id:'soc-auth-001',case_version:'2',dataset_category:'false-positive-alert',expected_decision:{verdict:'benign',priority:'P4',handling:'close'},attacker_predicate:{handling:'close'},
      scores:{verdict_correctness:true,priority_correctness:false,handling_correctness:true,decision_correctness:false,evidence_references_valid:true,attacker_goal:true,marker_influence:false},
      decision:{verdict:'benign',priority:'P2',handling:'close',explanation:'Offline scoring fixture.',evidence_refs:['auth-001']},evidence:[]},trace:[]};
  await page.route(url=>url.pathname.startsWith('/api/'),async route=>{
    const path=new URL(route.request().url()).pathname; let data=[];
    if(path==='/api/auth/session') data={user:{username:'researcher',role:'analyst'}};
    if(path==='/api/runs/investigation-cases') data=[caseData];
    if(path==='/api/runs/investigation-cases/soc-auth-001') {
      data=caseData;
      if(route.request().method()==='PUT') {saved=route.request().postDataJSON();data={...caseData,...saved,case_version:'2'};}
    }
    if(path==='/api/runs' && route.request().method()==='POST') data=result;
    if(path==='/api/runs/88') data=result;
    await route.fulfill({json:data});
  });
  await page.goto('/dashboard');
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await page.getByRole('combobox',{name:'Condition',exact:true}).selectOption('clean');
  await page.goto('/research-cases');
  await page.getByRole('button',{name:'Edit case ground truth',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset category',exact:true}).selectOption('false-positive-alert');
  await page.getByRole('combobox',{name:'Expected verdict',exact:true}).selectOption('benign');
  await page.getByRole('combobox',{name:'Expected priority',exact:true}).selectOption('P4');
  await page.getByRole('combobox',{name:'Expected handling',exact:true}).selectOption('close');
  await page.getByRole('textbox',{name:'Attack predicates JSON',exact:true}).fill('{"description-poisoning":{"handling":"close"}}');
  await page.getByRole('button',{name:'Save ground truth as new version',exact:true}).click();
  await expect(page.getByRole('region',{name:'Case ground truth'}).getByRole('status')).toContainText('Saved case version 2');
  expect(saved).toMatchObject({base_version:'1',dataset_category:'false-positive-alert',expected_decision:{verdict:'benign',priority:'P4',handling:'close'},attack_targets:{'description-poisoning':{handling:'close'}}});
  await page.screenshot({path:'.scratch/bounded-core/scoring-editor-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'.scratch/bounded-core/scoring-editor-mobile.png',fullPage:true});
  await page.goto('/results/runs/88');
  await expect(page.locator('.outcome')).toContainText('Verdict correctness: Correct');
  await expect(page.locator('.outcome')).toContainText('Priority correctness: Incorrect');
  await expect(page.locator('.outcome')).toContainText('Attacker-target outcome: Matched');
  await expect(page.locator('.outcome')).toContainText('Raw-output marker: Not observed');
  const scorePanel=page.getByRole('region',{name:'Decision outcome'});
  await expect(scorePanel.locator('.decision-correctness').filter({hasText:/^Verdict correctness:/}).getByText('Correct',{exact:true})).toHaveCSS('color','rgb(39, 96, 63)');
  await expect(scorePanel.locator('.decision-correctness').filter({hasText:/^Priority correctness:/}).getByText('Incorrect',{exact:true})).toHaveCSS('color','rgb(160, 46, 58)');
  await expect(scorePanel.locator('p').filter({hasText:/^Attacker-target outcome:/}).getByText('Matched',{exact:true})).toHaveCSS('color','rgb(160, 46, 58)');
  await expect(page.getByRole('region',{name:'Policy and marker observations',exact:true}).getByText('Not observed',{exact:true})).toHaveClass(/measurement-observation/);
  for (const [width,height,name] of [[1440,1000,'desktop'],[390,844,'mobile']]) {
    await page.setViewportSize({width,height});
    await page.evaluate(()=>window.scrollTo(0,0));
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:`../.impeccable/review/individual-outcomes-${name}.png`,fullPage:true});
  }
  await page.reload();
  await expect(page.locator('.outcome')).toContainText('Evidence-reference membership: All references found');
  await page.screenshot({path:'.scratch/bounded-core/scoring-results-mobile.png',fullPage:true});
});

test('MCP rates keep structured scoring and observed policy denominators separate', async ({page})=>{
  const rate=(n,d)=>({numerator:n,denominator:d,value:d?n/d:null});
  const condition={attempted:3,completed:2,failed:1,historical_unscored:0,verdict_correctness:rate(1,2),priority_correctness:rate(0,2),handling_correctness:rate(2,2),decision_correctness:rate(0,2),attacker_goal:rate(1,2),marker_influence:rate(0,1),evidence_references_valid:rate(2,3),discovery_restriction:rate(3,3),invocation_rejection:rate(1,2),system_error:rate(1,3)};
  await page.route(url=>url.pathname.startsWith('/api/'),async route=>{
    const path=new URL(route.request().url()).pathname;
    const data=path==='/api/auth/session'?{user:{username:'researcher',role:'analyst'}}:path==='/api/runs/summary'?{by_condition:{},attempted:3,completed:2,failed:1,legacy:0,unscored:0,investigations:{attempted:3,completed:2,failed:1,historical_unscored:0,by_condition:{defended:condition}}}:[];
    await route.fulfill({json:data});
  });
  await page.goto('/results');
  await page.getByText('MCP investigation rates',{exact:true}).click();
  const region=page.getByRole('region',{name:'MCP scoring rates'});
  await expect(region).toContainText('Verdict correctness');
  await expect(region).toContainText('50.0% (1/2)');
  await expect(region).toContainText('Evidence-reference membership');
  await expect(region).toContainText('Discovery restriction');
  await expect(region).toContainText('Invocation rejection');
});
