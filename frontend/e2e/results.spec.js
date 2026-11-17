import { test, expect } from "@playwright/test";

const run = (id, extra = {}) => ({
  run_id: id,
  id: `EXP-${String(id).padStart(3, "0")}`,
  mode: "Clean",
  scenario_id: "002",
  status: "completed",
  result: "Correct recommendation",
  model: "offline substitute",
  execution_time_ms: 12,
  scoring_version: "recommendation-v1",
  marker_influence: false,
  recommendation_correctness: true,
  recommendation: `Recommendation ${id}`,
  trace: [
    { kind: "recommendation_created", data: { value: `Recommendation ${id}` } },
  ],
  ...extra,
});

async function fixture(
  page,
  { role = "analyst", runs = [run(9), run(2)], created = run(7) } = {},
) {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      const data =
        path === "/api/auth/session"
          ? { user: { username: "researcher", role } }
          : path === "/api/scenarios"
            ? [{ scenario_id: "002", name: "Synthetic case", valid: true }]
            : path === "/api/runs/summary"
              ? {}
              : path === "/api/runs"
                ? route.request().method() === "POST"
                  ? created
                  : runs
                : path.startsWith("/api/runs/")
                  ? [...runs, created].find(
                      (item) => item.run_id === Number(path.split("/").pop()),
                    )
                  : [];
      await route.fulfill({ json: data });
    },
  );
}

test("Dashboard launches a run and opens its returned identifier on Results", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/dashboard");
  await expect(
    page.getByRole("heading", { name: "Recorded experiments" }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Recorded rates by condition", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Recorded trace" }),
  ).toHaveCount(0);
  await page.screenshot({
    path: ".scratch/bounded-core/dashboard-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Run new experiment" }).click();
  await expect(page).toHaveURL(/\/results\/runs\/7$/);
  await expect(page.locator(".outcome")).toContainText("Recommendation 7");
  await page.screenshot({
    path: ".scratch/bounded-core/results-desktop.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator(".outcome")).toContainText("Recommendation 7");
});

test("Dashboard shows pending execution and preserves configuration after a rejected request", async ({
  page,
}) => {
  await fixture(page);
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/runs", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await pending;
    await route.fulfill({
      status: 400,
      json: { detail: "Scenario is no longer usable" },
    });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await page
    .getByRole("combobox", { name: "Mode", exact: true })
    .selectOption("Clean");
  await page.getByRole("button", { name: "Run new experiment" }).click();
  await expect(
    page.getByText(
      "Experiment running. Results will open when this request finishes.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Mode", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Batch campaign", exact: true }),
  ).toBeDisabled();
  release();
  await expect(page.getByRole("alert")).toContainText(
    "Scenario is no longer usable",
  );
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("combobox", { name: "Mode", exact: true }),
  ).toHaveValue("Clean");
  await expect(
    page.getByRole("button", { name: "Run new experiment" }),
  ).toBeEnabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: ".scratch/bounded-core/dashboard-mobile.png",
    fullPage: true,
  });
});

test("empty run history and missing campaign detail are recoverable", async ({
  page,
}) => {
  await fixture(page, { runs: [] });
  await page.goto("/results/runs");
  await expect(
    page.getByText(
      "No runs recorded yet. Launch an experiment from Experiment.",
    ),
  ).toBeVisible();
  await page.route("**/api/campaigns/CMP-missing", (route) =>
    route.fulfill({ status: 404, json: { detail: "campaign not found" } }),
  );
  await page.goto("/results/campaigns/CMP-missing");
  await expect(page.getByRole("alert")).toContainText("campaign not found");
  await expect(
    page.getByRole("button", { name: "Retry selected campaign" }),
  ).toBeVisible();
  await expect(page.getByText("No campaigns recorded yet.")).toBeVisible();
});

test("a failed saved attempt opens by returned ID and keeps unscored outcomes", async ({
  page,
}) => {
  await fixture(page, {
    created: run(7, {
      status: "failed",
      result: "Failed attempt",
      recommendation: "",
      recommendation_correctness: null,
      marker_influence: null,
      system_error: true,
      error_category: "response_validation_error",
      trace: [
        {
          kind: "experiment_failed",
          data: { error_category: "response_validation_error" },
        },
      ],
    }),
  });
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Run new experiment" }).click();
  await expect(page).toHaveURL(/\/results\/runs\/7$/);
  await expect(page.locator(".outcome")).toContainText("Failed attempt");
  await expect(page.locator(".outcome")).toContainText("Unscored");
  await expect(page.locator(".timeline")).toContainText(
    "response_validation_error",
  );
});

test("Results works without a saved session and preserves selection on refresh and browser back", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("poisontrace.synthetic.sessions", "[]"),
  );
  await fixture(page);
  await page.goto("/results/runs/2");
  await expect(page.locator(".outcome")).toContainText("Recommendation 2");
  await page.getByRole("button", { name: /EXP-009/ }).click();
  await expect(page).toHaveURL(/\/results\/runs\/9$/);
  await expect(page.locator(".outcome")).toContainText("Recommendation 9");
  await page.goBack();
  await expect(page.locator(".outcome")).toContainText("Recommendation 2");
  await page.reload();
  await expect(page.getByRole("button", { name: /EXP-002/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.locator(".trace > summary").click();
  await page.getByRole("button", { name: "Open full trace" }).click();
  await expect(
    page.getByRole("region", { name: "Trace inspection" }),
  ).toContainText("Recommendation 2");
});

test("Results retains legacy and empty states on mobile with keyboard navigation", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await fixture(page, {
    runs: [
      run(2, {
        scoring_version: "legacy",
        result: "Legacy scoring",
        task_outcome: "Passed",
      }),
    ],
  });
  await page.goto("/results/runs");
  await expect(
    page.getByRole("heading", { name: "Select a run" }),
  ).toBeVisible();
  const entry = page.getByRole("button", { name: /EXP-002/ });
  await entry.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".outcome")).toContainText("Legacy: Passed");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: ".scratch/bounded-core/results-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Campaigns", exact: true }).click();
  await expect(page.getByText("No campaigns recorded yet.")).toBeVisible();
  await page.getByRole("button", { name: "Runs", exact: true }).click();
  await page.getByLabel("Filter runs").fill("missing");
  await expect(page.getByText("No runs match this filter.")).toBeVisible();
});

test("superadmin and signed-out users cannot enter Results", async ({
  page,
}) => {
  await fixture(page, { role: "superadmin" });
  await page.goto("/results/runs/2");
  await expect(
    page.getByRole("heading", { name: "403 Forbidden" }),
  ).toBeVisible();
  await page.route("**/api/auth/session", (route) =>
    route.fulfill({ status: 401, json: { detail: "Authentication required" } }),
  );
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Results", exact: true }),
  ).toHaveCount(0);
});

test("campaign execution opens its own saved campaign and child run", async ({
  page,
}) => {
  await fixture(page);
  const campaign = {
    campaign_id: "CMP-created",
    status: "completed_with_errors",
    provider: "fake",
    model: "fake",
    scenario_count: 1,
    completed: 1,
    scenarios: [
      {
        filename: "case-poisoned.yaml",
        scenario_id: "002",
        child_run_id: 7,
        trace: [
          {
            kind: "experiment_failed",
            data: { error_category: "response_validation_error" },
          },
        ],
      },
    ],
  };
  await page.route("**/api/campaigns**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    await route.fulfill({
      json:
        path === "/api/campaigns" && route.request().method() === "GET"
          ? [campaign]
          : campaign,
    });
  });
  await page.goto("/dashboard");
  await page
    .getByRole("button", { name: "Batch campaign", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Campaign history" }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Run all poisoned scenarios" })
    .click();
  await expect(page).toHaveURL(/\/results\/campaigns\/CMP-created$/);
  await page.reload();
  await expect(
    page.getByRole("button", { name: /CMP-created/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /case-poisoned.yaml/ }).click();
  await expect(page.locator(".campaign-timeline")).toContainText(
    "response_validation_error",
  );
  await page.getByRole("button", { name: "Open saved run 7" }).click();
  await expect(page).toHaveURL(/\/results\/runs\/7$/);
  await expect(page.locator(".outcome")).toContainText("Recommendation 7");
});

test("campaign inspection switches cases and reports rerun errors without losing evidence", async ({
  page,
}) => {
  await fixture(page);
  const campaign = {
    campaign_id: "CMP-review",
    status: "completed",
    provider: "fake",
    model: "fake",
    scenario_count: 2,
    completed: 2,
    scenarios: [1, 2].map((id) => ({
      filename: `case-${id}.yaml`,
      scenario_id: `00${id}`,
      child_run_id: id,
      trace: [
        { kind: "recommendation_created", data: { value: `Evidence ${id}` } },
      ],
    })),
  };
  await page.route("**/api/campaigns**", (route) =>
    route.fulfill({
      json:
        new URL(route.request().url()).pathname === "/api/campaigns"
          ? [campaign]
          : campaign,
    }),
  );
  await page.route("**/rerun", (route) =>
    route.fulfill({ status: 503, json: { detail: "Runner unavailable" } }),
  );
  await page.goto("/results/campaigns/CMP-review");
  await page.getByRole("button", { name: /case-1.yaml/ }).click();
  await expect(page.locator(".campaign-timeline")).toContainText("Evidence 1");
  await expect(
    page.getByRole("button", { name: "Choose another scenario" }),
  ).toBeVisible({ timeout: 2000 });
  await page.getByRole("button", { name: "Choose another scenario" }).click();
  await page.getByRole("button", { name: /case-2.yaml/ }).click();
  await expect(page.locator(".campaign-timeline")).toContainText("Evidence 2");
  await page.screenshot({
    path: ".scratch/bounded-core/campaign-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Rerun scenario" }).click();
  await expect(page.getByRole("alert")).toContainText("Runner unavailable");
  await expect(page.locator(".campaign-timeline")).toContainText("Evidence 2");
});

test("loading and forbidden or missing run detail never show another result", async ({
  page,
}) => {
  await fixture(page);
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/runs/2", async (route) => {
    await pending;
    await route.fulfill({ status: 403, json: { detail: "Forbidden" } });
  });
  await page.goto("/results/runs/2");
  await expect(
    page.getByText("Loading selected run…", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".outcome")).toHaveCount(0);
  release();
  await expect(page.getByRole("alert")).toContainText("Forbidden");
  await page.route("**/api/runs/2", (route) =>
    route.fulfill({ status: 404, json: { detail: "run not found" } }),
  );
  await page.getByRole("button", { name: "Retry selected run" }).click();
  await expect(page.getByRole("alert")).toContainText("run not found");
  await expect(page.locator(".outcome")).toHaveCount(0);
});
