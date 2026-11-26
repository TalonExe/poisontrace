import { test, expect } from "./verification-test.js";

const plan = {
  case: {
    case_id: "soc-auth-001",
    case_version: "1",
    name: "Synthetic incident",
  },
  model: "scripted-soc-v2",
  provider: "scripted",
  conditions: ["clean", "poisoned", "defended"],
  repeats: 1,
  attack: { payload_id: "soc-auth-shadow-v2" },
};
const value = { numerator: 0, denominator: 0, value: null };
const row = {
  requested: 1,
  scheduled: 1,
  saved: 1,
  saved_failed: 1,
  missing: 0,
  excluded: 0,
  duration: { count: 1, mean_ms: 30 },
  all_saved_error_rate: { numerator: 1, denominator: 1, value: 1 },
  unavailable: {},
  ...Object.fromEntries(
    [
      "verdict_correctness",
      "priority_correctness",
      "handling_correctness",
      "decision_correctness",
      "attacker_goal",
      "discovery_restriction",
      "invocation_rejection",
      "marker_influence",
      "system_error",
    ].map((k) => [k, value]),
  ),
};
const group = {
  group_id: "fixed-group",
  status: "finished",
  plan,
  attempts: [
    {
      attempt: 1,
      repeat: 1,
      condition: "clean",
      run_id: 4,
      status: "failed",
      error_category: "investigation_time_limit",
      execution_time_ms: 30,
    },
  ],
  comparison: {
    attempted: 1,
    excluded_attempts: [
      { attempt: 2, run_id: 5, reasons: ["payload version or snapshot"] },
    ],
    missing_attempts: [3],
    missing_conditions: ["poisoned", "defended"],
    by_condition: {
      clean: row,
      poisoned: { ...row, excluded: 1 },
      defended: { ...row, missing: 1 },
    },
  },
};

test("durable group reconnects after an uncertain response and retains its submission intent", async ({ page }) => {
  const record = {...group, status: "queued", attempts: [], progress: {completed:0, failed:0, interrupted:0, missing:0, queued:3, active:0}};
  await setup(page, {record});
  const capture = async (state) => {
    for (const [width,height] of [[1440,1000],[390,844]]) {
      await page.setViewportSize({width,height});
      const layout = await page.evaluate(() => ({viewportWidth:innerWidth,viewportHeight:innerHeight,documentWidth:document.documentElement.scrollWidth,documentHeight:document.documentElement.scrollHeight}));
      expect(layout.documentWidth).toBeLessThanOrEqual(width);
      await page.screenshot({path:`.scratch/ticket-46-${state}-${width}-viewport.png`});
      await page.screenshot({path:`.scratch/ticket-46-${state}-${width}-full-page.png`,fullPage:true});
      await test.info().attach(`${state}-${width}-accessibility`, {body:await page.locator('body').ariaSnapshot(),contentType:'text/yaml'});
      await test.info().attach(`${state}-${width}-layout`, {body:JSON.stringify(layout),contentType:'application/json'});
    }
  };
  const intents = [];
  let releaseSubmission;
  const submission = new Promise(resolve => { releaseSubmission = resolve; });
  await page.route("**/api/runs/investigation-cases", route => route.fulfill({json:[{case_id:"soc-auth-001",case_version:"1",name:"Synthetic incident",attacks:[{family:"cross-server-shadowing",payload_id:"soc-auth-shadow-v2"}]}]}));
  await page.route("**/api/investigation-jobs", route => route.fulfill({json: intents.length ? [{job_id:"durable-group",group_id:"fixed-group",status:record.status === "interrupted" ? "interrupted" : "active"}] : []}));
  await page.route("**/api/run-groups", async route => {
    if (route.request().method() !== "POST") return route.fulfill({json:[record]});
    intents.push(route.request().headers()["idempotency-key"]);
    if (intents.length === 1) {
      await submission;
      return route.abort("failed");
    }
    return route.fulfill({status:202,json:{job_id:"durable-group",group_id:"fixed-group",status:"active"}});
  });
  await page.goto("/dashboard");
  const launch = page.getByRole("button", {name:/^Run matched group/});
  await expect(launch).toBeEnabled();
  await launch.focus();
  await page.keyboard.press("Enter");
  try {
    await expect(launch).toBeFocused();
    await expect(launch).toHaveAttribute("aria-disabled", "true");
    await expect(page.getByText(/Submitting a durable schedule/)).toBeVisible();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Space");
    expect(intents).toHaveLength(1);
    await capture("submitting");
  } finally {
    releaseSubmission();
  }
  await expect(page.getByText(/The submission response is uncertain/)).toBeVisible();
  await page.reload();
  await expect(page.getByText(/Matched group active/)).toBeVisible();
  await capture("active");
  await page.getByRole("button", {name:"Retry group submission",exact:true}).click();
  await expect(page).toHaveURL(/\/results\/groups\/fixed-group$/);
  const notification = page.getByRole("region", {name:"Run notification"});
  await expect(notification).toContainText("Matched group running");
  expect(intents).toHaveLength(2);
  expect(intents[0]).toMatch(/^[A-Za-z0-9_-]{16,128}$/);
  expect(intents[1]).toBe(intents[0]);
  await expect(page.getByRole("status", {name:"Group execution progress"})).toContainText("3 queued");
  record.status = "interrupted";
  record.progress = {completed:1,failed:0,interrupted:1,missing:1,queued:0,active:0};
  await expect(page.getByRole("status", {name:"Group execution progress"})).toContainText("1 completed, 0 failed, 1 interrupted, 1 missing");
  await expect(page.getByText(/No work replays automatically/)).toBeVisible();
  await expect(notification).toContainText("Matched group interrupted");
  await capture("interrupted");
  await page.getByRole("button", {name:"Overview", exact:true}).click();
  await expect(page).toHaveURL(/\/results$/);
  await notification.getByRole("button", {name:"See the results"}).click();
  await expect(page).toHaveURL(/\/results\/groups\/fixed-group$/);
  await expect(notification).toHaveCount(0);
});
async function setup(
  page,
  { record = group } = {},
) {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      const body =
        path === "/api/auth/session"
          ? { user: { username: "researcher", role: "analyst" } }
          : path === "/api/run-groups"
            ? [record]
            : path === "/api/run-groups/fixed-group"
              ? record
              : [];
      await route.fulfill({ json: body });
    },
  );
}
test("condition cards filter retained attempts and open the exact saved trace", async ({ page }) => {
  await setup(page);
  await page.setViewportSize({ width: 390, height: 844 });
  const run = { run_id: 4, id: "EXP-004", status: "failed", trace: [] };
  await page.route("**/api/runs", (route) => route.fulfill({ json: [run] }));
  await page.route("**/api/runs/4", (route) => route.fulfill({ json: run }));
  await page.goto("/results/groups/fixed-group");
  const retained = page.getByRole("region", { name: "Retained attempts" });
  await page.getByRole("button", { name: /^poisoned/i }).click();
  await expect(retained.getByText("No retained attempts for this selection.")).toBeVisible();
  await page.getByRole("button", { name: /^clean/i }).click();
  const traceLink = retained.getByRole("link", { name: "View trace · Attempt 1 · EXP-004" });
  await expect(traceLink).toBeVisible();
  await retained.getByRole("button", { name: "Show all attempts" }).focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(traceLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/results\/runs\/4$/);
  await expect(page.getByText("No persisted trace events.")).toBeVisible();
  await page.getByRole("button", { name: "Back to group" }).click();
  await expect(page).toHaveURL(/\/results\/groups\/fixed-group$/);
  await expect(page.getByRole("button", { name: /^clean/i })).toHaveAttribute("aria-pressed", "true");
});

test("retained attempts page and sort on mobile and link to the exact trace", async ({ page }) => {
  const attempts = Array.from({ length: 11 }, (_, index) => ({
    attempt: index + 1,
    repeat: 1,
    condition: "clean",
    status: index === 10 ? "interrupted" : "failed",
    run_id: index === 10 ? null : index + 4,
  }));
  await setup(page, { record: { ...group, attempts } });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/results/groups/fixed-group");
  const retained = page.getByRole("region", { name: "Retained attempts" });
  const grid = retained.getByRole("grid", { name: "Retained attempts" });
  await expect(retained.getByRole("status")).toHaveText("1–10 of 11 attempts");
  await retained.getByRole("button", { name: "Next page" }).press("Enter");
  await expect(retained.getByRole("status")).toHaveText("11–11 of 11 attempts");
  await expect(grid.getByRole("row").nth(1)).toContainText("interrupted");
  await expect(grid.getByRole("row").nth(1)).toContainText("Trace unavailable");
  await grid.getByRole("columnheader", { name: "Attempt" }).press("Enter");
  await expect(grid.getByRole("columnheader", { name: "Attempt" })).toHaveAttribute("aria-sort", "descending");
  await expect(retained.getByRole("status")).toHaveText("1–10 of 11 attempts");
  await expect(grid.getByRole("row").nth(1)).toContainText("interrupted");
  await expect(grid.getByRole("link", { name: "View trace · Attempt 10 · EXP-013" })).toHaveAttribute("href", "/results/runs/13");
  expect(await page.locator("html").evaluate((element) => element.scrollWidth)).toBeLessThanOrEqual(390);
  await test.info().attach("retained-attempts-accessibility", {body: await retained.ariaSnapshot(), contentType: "text/yaml"});
  await page.screenshot({path: test.info().outputPath("retained-attempts-mobile.png"), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1000});
  await page.screenshot({path: test.info().outputPath("retained-attempts-desktop.png"), fullPage: true});
});

test("group Results distinguishes failure, missing and incompatible attempts", async ({
  page,
}) => {
  await setup(page);
  await page.goto("/results/groups/fixed-group");
  await expect(
    page.getByRole("heading", { name: "Matched comparison", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "1 compatible saved attempts. 1 incompatible. 1 scheduled attempts without a saved result.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText("Attempt 2: payload version or snapshot"),
  ).toBeVisible();
  await expect(page.getByRole("row").filter({ hasText: "Repeat 1 · clean" })).toContainText(
    "investigation_time_limit",
  );
  await expect(
    page.getByRole("region", { name: "Condition comparison" }),
  ).toContainText("Unavailable · 0 eligible");
});
test("retry loads saved groups after a temporary request failure", async ({ page }) => {
  await setup(page);
  await page.route("**/api/run-groups", (route) => route.fulfill({
    status: 503,
    json: { detail: "Groups unavailable. Retry loading." },
  }), { times: 1 });
  await page.goto("/results/groups");
  await expect(page.getByRole("alert")).toContainText(
    "Groups unavailable. Retry loading.",
  );
  await page.getByRole("button", { name: "Retry groups", exact: true }).click();
  await expect(page.getByRole("button", { name: /Synthetic incident/ })).toBeVisible();
});

test("matched comparison colors correctness and attacker outcomes in opposite directions", async ({
  page,
}) => {
  const rate = (numerator, denominator) => ({
    numerator,
    denominator,
    value: denominator ? numerator / denominator : null,
  });
  const clean = {
    ...row,
    requested: 3,
    scheduled: 3,
    saved: 3,
    attempted: 3,
    failed: 1,
    completed: 2,
    saved_failed: 1,
    decision_correctness: rate(0, 2),
    verdict_correctness: rate(0, 2),
    priority_correctness: rate(0, 2),
    handling_correctness: rate(0, 2),
    attacker_goal: rate(0, 0),
    system_error: rate(1, 3),
    discovery_restriction: rate(0, 3),
    invocation_rejection: rate(0, 3),
    marker_influence: rate(0, 2),
    all_saved_error_rate: rate(1, 3),
    unavailable: {
      decision_correctness: 1,
      verdict_correctness: 1,
      priority_correctness: 1,
      handling_correctness: 1,
      attacker_goal: 3,
      system_error: 0,
      discovery_restriction: 0,
      invocation_rejection: 0,
      marker_influence: 1,
    },
  };
  const poisoned = {
    ...clean,
    failed: 2,
    completed: 1,
    saved_failed: 2,
    decision_correctness: rate(1, 1),
    verdict_correctness: rate(1, 1),
    priority_correctness: rate(1, 1),
    handling_correctness: rate(1, 1),
    attacker_goal: rate(0, 1),
    system_error: rate(2, 3),
    all_saved_error_rate: rate(2, 3),
    marker_influence: rate(0, 1),
    unavailable: {
      ...clean.unavailable,
      decision_correctness: 2,
      verdict_correctness: 2,
      priority_correctness: 2,
      handling_correctness: 2,
      attacker_goal: 2,
      discovery_restriction: 3,
      invocation_rejection: 3,
      marker_influence: 2,
    },
    discovery_restriction: rate(0, 0),
    invocation_rejection: rate(0, 0),
  };
  const defended = {
    ...poisoned,
    decision_correctness: rate(0, 1),
    verdict_correctness: rate(0, 1),
    priority_correctness: rate(0, 1),
    handling_correctness: rate(0, 1),
    attacker_goal: rate(1, 1),
    discovery_restriction: rate(3, 3),
    invocation_rejection: rate(0, 3),
    unavailable: {
      ...poisoned.unavailable,
      discovery_restriction: 0,
      invocation_rejection: 0,
    },
  };
  await setup(page, {
    record: {
      ...group,
      plan: { ...plan, repeats: 3, model: "gemini-3.5-flash-lite" },
      attempts: ["clean", "poisoned", "defended"].flatMap((condition, index) =>
        Array.from({ length: 3 }, (_, i) => ({
          attempt: index * 3 + i + 1,
          repeat: i + 1,
          condition,
          run_id: index * 3 + i + 10,
          status: i < (condition === "clean" ? 2 : 1) ? "completed" : "failed",
          execution_time_ms: 30,
          error_category:
            i < (condition === "clean" ? 2 : 1)
              ? null
              : "investigation_validation_error",
        })),
      ),
      comparison: {
        ...group.comparison,
        scoring_version: "investigation-scoring-v1",
        attempted: 9,
        excluded_attempts: [],
        missing_attempts: [],
        missing_conditions: [],
        by_condition: { clean, poisoned, defended },
      },
    },
  });
  await page.goto("/results/groups/fixed-group");
  const overall = page.getByRole("region", {
    name: "Overall experiment performance",
  });
  await expect(overall).toContainText("11/100");
  await expect(overall).toContainText(
    "1 correct result from 9 attempts; 5 failed.",
  );
  await page.reload();
  await expect(overall).toContainText("11/100");
  const correct = page.getByRole("row").filter({
    has: page.getByRole("rowheader", {
      name: "All decision fields correct",
      exact: true,
    }),
  });
  await expect(correct.getByText("0/2 (0%)", { exact: true })).toHaveCSS(
    "color",
    "rgb(160, 46, 58)",
  );
  await expect(correct.getByText("1/1 (100%)", { exact: true })).toHaveCSS(
    "color",
    "rgb(39, 96, 63)",
  );
  const attacker = page.getByRole("row").filter({
    has: page.getByRole("rowheader", {
      name: "Attacker-target matches",
      exact: true,
    }),
  });
  await expect(attacker.getByText("1/1 (100%)", { exact: true })).toHaveCSS(
    "color",
    "rgb(160, 46, 58)",
  );
  await expect(attacker.getByText("0/1 (0%)", { exact: true })).toHaveCSS(
    "color",
    "rgb(39, 96, 63)",
  );
  await expect(
    attacker.getByText("Unavailable · 0 eligible", { exact: true }),
  ).toHaveClass(/measurement-unavailable/);
  await page.getByText("Policy and marker observations", {exact:true}).click();
  const policy = page.getByRole("row").filter({
    has: page.getByRole("rowheader", {
      name: "Discovery restriction observed",
      exact: true,
    }),
  });
  await expect(policy.getByText("3/3 (100%)", { exact: true })).toHaveClass(
    /measurement-observation/,
  );
  await page.getByText("Measurement definitions and colors", {exact:true}).click();
  await expect(
    page.getByRole("list", { name: "Outcome colors" }),
  ).toBeVisible();
  await expect(correct).toContainText("2 incorrect");
  await expect(attacker).toContainText("1 target match");
  for (const [width, height, name] of [
    [1440, 1000, "desktop"],
    [390, 844, "mobile"],
  ]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => window.scrollTo(0, 0));
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(overall).toBeVisible();
    await page.screenshot({
      path: `../.impeccable/review/comparison-outcomes-${name}.png`,
      fullPage: true,
    });
  }
});

for (const [name, correct, scored, completed, failed, expected] of [
  ["all correct", 3, 3, 3, 0, "100/100"],
  ["all failed", 0, 0, 0, 3, "0/100"],
  ["empty compatible data", 0, 0, 0, 0, "Unavailable"],
  ["completed unscored", 0, 0, 2, 0, "Unavailable"],
  ["unsupported scoring version", 1, 1, 1, 0, "Unavailable"],
  ["partial unscored retained rerun", 1, 1, 2, 1, "33/100"],
]) {
  test(`overall indicator handles ${name}`, async ({ page }) => {
    const empty = { ...row, attempted: 0, completed: 0, failed: 0 };
    const record = {
      ...group,
      comparison: {
        ...group.comparison,
        scoring_version: "investigation-scoring-v1",
        attempted: completed + failed,
        ...(name === "unsupported scoring version" ? {scoring_version:"future-scoring"} : {}),
        by_condition: {
          clean: {
            ...row,
            attempted: completed + failed,
            completed,
            failed,
            decision_correctness: {
              numerator: correct,
              denominator: scored,
              value: scored ? correct / scored : null,
            },
          },
          poisoned: empty,
          defended: empty,
        },
      },
    };
    await setup(page, { record });
    await page.goto("/results/groups/fixed-group");
    const overall = page.getByRole("region", {
      name: "Overall experiment performance",
    });
    await expect(overall.locator("strong")).toHaveText(expected);
    await expect(
      page.getByText("Attempt 2: payload version or snapshot"),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "View trace · Attempt 1 · EXP-004" }),
    ).toBeVisible();
    if (name === "partial unscored retained rerun") {
      await expect(overall).toContainText("1 completed but unscored");
      await overall.getByText("How this indicator works").click();
      await expect(overall).toContainText(
        "Every retained rerun attempt counts once",
      );
    }
  });
}

test('comparison leads decisions and separates observations from execution accounting',async ({page})=>{
  await setup(page);
  await page.goto('/results/groups/fixed-group');
  await expect(page.getByRole('region',{name:'Decision outcomes',exact:true})).toBeVisible();
  await expect(page.getByRole('region',{name:'Decision outcomes',exact:true})).toContainText('Attacker-target matches');
  await expect(page.getByRole('region',{name:'Incompatible attempts'})).toBeVisible();
  await expect(page.getByText('Missing compatible conditions: poisoned, defended.')).toBeVisible();
  for(const [width,height,name] of [[1440,1000,'desktop'],[390,844,'mobile']]) {
    await page.setViewportSize({width,height});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:`../.scratch/cleanup-36/group-default-${name}.png`,fullPage:true});
  }
  for(const name of ['Policy and marker observations','Execution accounting']) {
    const details=page.locator('details').filter({has:page.locator('summary').getByText(name,{exact:true})});
    await expect(details).not.toHaveAttribute('open','');
    await details.locator('summary').focus();
    await page.keyboard.press('Enter');
    await expect(details).toHaveAttribute('open','');
  }
  await expect(page.getByRole('region',{name:'Execution accounting',exact:true})).toContainText('Mean duration, compatible attempts');
  await expect(page.getByRole('region',{name:'Execution accounting',exact:true})).toContainText('System error, all saved attempts');
  await expect(page.getByRole('link',{name:'View trace · Attempt 1 · EXP-004'})).toBeVisible();
});
