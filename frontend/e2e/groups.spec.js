import { test, expect } from "@playwright/test";

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
async function setup(
  page,
  { error = false, empty = false, record = group } = {},
) {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (error && path.startsWith("/api/run-groups"))
        return route.fulfill({
          status: 503,
          json: { detail: "Groups unavailable. Retry loading." },
        });
      const body =
        path === "/api/auth/session"
          ? { user: { username: "researcher", role: "analyst" } }
          : path === "/api/run-groups"
            ? empty
              ? []
              : [record]
            : path === "/api/run-groups/fixed-group"
              ? record
              : [];
      await route.fulfill({ json: body });
    },
  );
}
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
  await expect(page.getByText(/Repeat 1 · clean · failed/)).toContainText(
    "investigation_time_limit",
  );
  await expect(
    page.getByRole("region", { name: "Condition comparison" }),
  ).toContainText("Unavailable · 0 eligible");
});
test("group history has an empty state", async ({ page }) => {
  await setup(page, { empty: true });
  await page.goto("/results/groups");
  await expect(
    page.getByText("No matched groups yet. Configure one on Experiment."),
  ).toBeVisible();
});
test("group loading errors support retry", async ({ page }) => {
  await setup(page, { error: true });
  await page.goto("/results/groups");
  await expect(page.getByRole("alert")).toContainText(
    "Groups unavailable. Retry loading.",
  );
  await expect(
    page.getByRole("button", { name: "Retry groups", exact: true }),
  ).toBeVisible();
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
      page.getByRole("link", { name: "Inspect attempt 1 · EXP-004" }),
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
  await expect(page.getByRole('link',{name:'Inspect attempt 1 · EXP-004'})).toBeVisible();
});
