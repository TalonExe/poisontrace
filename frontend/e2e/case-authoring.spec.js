import { test, expect } from "@playwright/test";

test("routine setup separates MCP authoring and returns with the current version", async ({
  page,
}) => {
  let current = {
    case_id: "soc-auth-001",
    case_version: "1",
    name: "Synthetic incident",
    dataset_category: "malicious-incident",
    expected_decision: {
      verdict: "malicious",
      priority: "P1",
      handling: "escalate",
    },
    attack_targets: {},
    supported_attack_families: ["description-poisoning"],
    attacks: [
      {
        family: "description-poisoning",
        payload_id: "soc-auth-description-v2",
      },
    ],
  };
  let submitted;
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data = [];
      if (path === "/api/auth/session")
        data = { user: { username: "synthetic", role: "analyst" } };
      if (path === "/api/runs/investigation-cases") data = [current];
      if (path === "/api/runs/investigation-cases/soc-auth-001") {
        if (route.request().method() === "PUT") {
          const payload = route.request().postDataJSON();
          expect(Object.keys(payload).sort()).toEqual([
            "attack_targets",
            "base_version",
            "dataset_category",
            "expected_decision",
          ]);
          expect(payload.base_version).toBe(current.case_version);
          current = { ...current, ...payload, case_version: "2" };
        }
        data = current;
      }
      if (path === "/api/run-groups" && route.request().method() === "POST") {
        submitted = route.request().postDataJSON();
        return route.fulfill({
          status: 400,
          json: { detail: "Synthetic stop before execution" },
        });
      }
      await route.fulfill({ json: data });
    },
  );
  await page.goto("/dashboard/single");
  await expect(
    page.getByRole("button", { name: "Edit case ground truth", exact: true }),
  ).toHaveCount(0);
  await page.getByText("Advanced", { exact: true }).focus();
  await page.keyboard.press("Enter");
  await page
    .getByRole("button", { name: "MCP research case authoring", exact: true })
    .click();
  await expect(page).toHaveURL(/\/research-cases$/);
  await page
    .getByRole("button", { name: "Edit case ground truth", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Expected priority", exact: true })
    .selectOption("P2");
  await page
    .getByRole("button", {
      name: "Save ground truth as new version",
      exact: true,
    })
    .click();
  await expect(page.getByRole("status")).toContainText("Saved case version 2");
  for (const [width, height, label] of [
    [1440, 1000, "desktop"],
    [390, 844, "mobile"],
  ]) {
    await page.setViewportSize({ width, height });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../.scratch/cleanup-35/authoring-${label}.png`,
      fullPage: true,
    });
  }
  await page
    .getByRole("button", { name: "Return to Experiment", exact: true })
    .click();
  await expect(page.getByLabel("Group case")).toContainText("v2");
  await expect(
    page.getByRole("button", { name: "Edit case ground truth", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("checkbox", { name: "poisoned", exact: true }).uncheck();
  await page.getByRole("checkbox", { name: "defended", exact: true }).uncheck();
  await page
    .getByRole("button", { name: "Run matched group", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Synthetic stop");
  expect(submitted.case_version).toBe("2");
  await page.reload();
  await expect(page.getByLabel("Group case")).toContainText("v2");
});

test("stale authoring keeps the base version until explicitly reopened", async ({
  page,
}) => {
  let version = "1",
    writes = [];
  const data = () => ({
    case_id: "control",
    case_version: version,
    name: "Synthetic control",
    dataset_category: "benign-activity",
    expected_decision: { verdict: "benign", priority: "P4", handling: "close" },
    attack_targets: {},
    supported_attack_families: [],
  });
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/session")
        return route.fulfill({
          json: { user: { username: "synthetic", role: "analyst" } },
        });
      if (path === "/api/runs/investigation-cases")
        return route.fulfill({ json: [data()] });
      if (path.endsWith("/control")) {
        if (route.request().method() === "PUT") {
          writes.push(route.request().postDataJSON());
          version = "2";
          return route.fulfill({
            status: 400,
            json: { detail: "Case version changed" },
          });
        }
        return route.fulfill({ json: data() });
      }
      await route.fulfill({ json: [] });
    },
  );
  await page.goto("/research-cases");
  await page
    .getByRole("button", { name: "Edit case ground truth", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Case ground truth" }),
  ).toContainText("none, clean control");
  await page
    .getByRole("button", {
      name: "Save ground truth as new version",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toContainText("Case version changed");
  expect(writes[0].base_version).toBe("1");
  await expect(
    page.getByRole("region", { name: "Case ground truth" }),
  ).toContainText("Editing control · version 1");
  await page
    .getByRole("button", { name: "Close case ground truth", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Edit case ground truth", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Case ground truth" }),
  ).toContainText("Editing control · version 2");
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "MCP research case authoring",
      exact: true,
    }),
  ).toBeVisible();
});

test("single setup notices an externally edited version before execution", async ({
  page,
}) => {
  let reads = 0,
    executions = 0;
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data = [];
      if (path === "/api/auth/session")
        data = { user: { username: "synthetic", role: "analyst" } };
      if (path === "/api/runs/investigation-cases")
        data = [
          {
            case_id: "control",
            case_version: ++reads === 1 ? "1" : "2",
            name: "Control",
            attacks: [],
          },
        ];
      if (path === "/api/runs" && route.request().method() === "POST") {
        executions++;
        return route.fulfill({
          status: 400,
          json: { detail: "Synthetic stop" },
        });
      }
      await route.fulfill({ json: data });
    },
  );
  await page.goto("/dashboard/single");
  await expect(
    page.getByRole("region", { name: "This experiment", exact: true }),
  ).toContainText("v1");
  await page
    .getByRole("button", { name: "Run MCP investigation", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Research case version changed",
  );
  expect(executions).toBe(0);
  await expect(
    page.getByRole("region", { name: "This experiment", exact: true }),
  ).toContainText("v2");
  await page
    .getByRole("button", { name: "Run MCP investigation", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Synthetic stop");
  expect(executions).toBe(1);
});

for (const role of ["superadmin", null])
  test(`authoring respects access boundary: ${role}`, async ({ page }) => {
    let caseReads = 0;
    await page.route(
      (url) => url.pathname.startsWith("/api/"),
      async (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path.includes("investigation-cases")) caseReads++;
        await route.fulfill({
          json:
            path === "/api/auth/session"
              ? { user: role ? { username: "synthetic", role } : null }
              : [],
        });
      },
    );
    await page.goto("/research-cases");
    if (role)
      await expect(
        page.getByRole("heading", { name: "403 Forbidden" }),
      ).toBeVisible();
    else await expect(page).toHaveURL(/\/login$/);
    expect(caseReads).toBe(0);
  });

test("authoring handles unavailable, empty and recovered catalogs", async ({
  page,
}) => {
  let attempt = 0;
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/session")
        return route.fulfill({
          json: { user: { username: "synthetic", role: "analyst" } },
        });
      if (path === "/api/runs/investigation-cases" && attempt++ === 0)
        return route.fulfill({
          status: 503,
          json: { detail: "Synthetic unavailable catalog" },
        });
      return route.fulfill({ json: [] });
    },
  );
  await page.goto("/research-cases");
  await expect(page.getByRole("alert")).toContainText(
    "Synthetic unavailable catalog",
  );
  await page.getByRole("button", { name: "Reload research cases" }).click();
  await expect(
    page.getByText("No MCP research cases available.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Edit case ground truth", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", {
      name: "Open Metadata scenarios (YAML)",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/\/scenarios$/);
});
