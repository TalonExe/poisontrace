import { test, expect } from "@playwright/test";

async function fixture(page) {
  const requests = [];
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/runs" && route.request().method() === "POST") {
        requests.push(route.request().postDataJSON());
        return route.fulfill({
          status: 400,
          json: { detail: "Synthetic rejected request" },
        });
      }
      const data =
        path === "/api/auth/session"
          ? { user: { username: "researcher", role: "analyst" } }
          : path === "/api/runs/investigation-cases"
            ? [
                {
                  case_id: "attack-case",
                  case_version: "4",
                  name: "Synthetic incident",
                  attacks: [
                    {
                      family: "description-poisoning",
                      payload_id: "soc-auth-description-v2",
                    },
                    {
                      family: "cross-server-shadowing",
                      payload_id: "soc-auth-shadow-v2",
                    },
                  ],
                },
                {
                  case_id: "benign-control",
                  case_version: "2",
                  name: "Synthetic benign control",
                  dataset_category: "benign-activity",
                  attacks: [],
                },
                {
                  case_id: "false-positive-control",
                  case_version: "3",
                  name: "Synthetic false-positive control",
                  dataset_category: "false-positive-alert",
                  attacks: [],
                },
              ]
            : [];
      await route.fulfill({ json: data });
    },
  );
  return requests;
}

test("single MCP workflow has a separate condition and clean omits attacks", async ({
  page,
}) => {
  const requests = await fixture(page);
  await page.goto("/dashboard/single");
  await expect(
    page.getByRole("heading", { name: "MCP investigation", exact: true }),
  ).toBeVisible();
  const condition = page.getByRole("combobox", {
    name: "Condition",
    exact: true,
  });
  await expect(condition).toHaveValue("clean");
  await expect(condition.locator("option")).toHaveCount(3);
  await expect(
    page.getByRole("combobox", { name: "Attack family", exact: true }),
  ).toHaveCount(0);
  const summary = page.getByRole("region", {
    name: "This experiment",
    exact: true,
  });
  await expect(summary).toContainText("attack-case · v4");
  await expect(summary).toContainText("scripted-soc-v2");
  await expect(summary).toContainText("Enabled before exposure and invocation");
  await page
    .getByRole("button", { name: "Run MCP investigation", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Synthetic rejected request",
  );
  expect(requests).toEqual([
    {
      workflow: "mcp-investigation-v1",
      case_id: "attack-case",
      session_id: "",
      mode: "clean",
      provider: "scripted",
    },
  ]);
});

for (const condition of ["poisoned", "defended"]) {
  for (const [family, payload] of [
    ["description-poisoning", "soc-auth-description-v2"],
    ["cross-server-shadowing", "soc-auth-shadow-v2"],
  ]) {
    test(`${condition} ${family} preserves the request and summary after rejection`, async ({
      page,
    }) => {
      const requests = await fixture(page);
      await page.goto("/dashboard/single");
      await page
        .getByRole("combobox", { name: "Condition", exact: true })
        .selectOption(condition);
      await page
        .getByRole("combobox", { name: "Attack family", exact: true })
        .selectOption(family);
      const summary = page.getByRole("region", {
        name: "This experiment",
        exact: true,
      });
      await expect(summary).toContainText(payload);
      await expect(summary).toContainText(
        condition === "defended" ? "Defended" : "Poisoned",
      );
      await expect(summary).toContainText(
        condition === "defended"
          ? "Enabled before exposure and invocation"
          : "Disabled",
      );
      if (family === "cross-server-shadowing") {
        for (const [width, height] of [
          [1440, 1000],
          [390, 844],
        ]) {
          await page.setViewportSize({ width, height });
          expect(
            await page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
          ).toBe(true);
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.screenshot({
            path: `../.scratch/cleanup-34/${condition}-${width}.png`,
            fullPage: true,
          });
        }
      }
      await page
        .getByRole("button", { name: "Run MCP investigation", exact: true })
        .focus();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("alert")).toContainText(
        "Synthetic rejected request",
      );
      expect(requests).toEqual([
        {
          workflow: "mcp-investigation-v1",
          case_id: "attack-case",
          session_id: "",
          mode: condition,
          attack_family: family,
          provider: "scripted",
        },
      ]);
      await expect(
        page.getByRole("combobox", { name: "Condition", exact: true }),
      ).toHaveValue(condition);
      await expect(
        page.getByRole("combobox", { name: "Attack family", exact: true }),
      ).toHaveValue(family);
    });
  }
}
for (const [control, condition] of [
  ["benign-control", "poisoned"],
  ["false-positive-control", "defended"],
]) {
  test(`switching from ${condition} to ${control} visibly resets to clean`, async ({
    page,
  }) => {
    const requests = await fixture(page);
    await page.goto("/dashboard/single");
    await page
      .getByRole("combobox", { name: "Condition", exact: true })
      .selectOption(condition);
    await page
      .getByRole("combobox", { name: "Synthetic case", exact: true })
      .selectOption(control);
    const select = page.getByRole("combobox", {
      name: "Condition",
      exact: true,
    });
    await expect(select).toHaveValue("clean");
    await expect(select.locator("option")).toHaveCount(1);
    await expect(page.getByRole("status")).toContainText(
      "Condition reset to Clean",
    );
    await expect(
      page.getByRole("combobox", { name: "Attack family", exact: true }),
    ).toHaveCount(0);
    const summary = page.getByRole("region", {
      name: "This experiment",
      exact: true,
    });
    await expect(summary).not.toContainText("soc-auth-");
    await expect(summary).toContainText(
      "Enabled before exposure and invocation",
    );
    await page
      .getByRole("button", { name: "Run MCP investigation", exact: true })
      .click();
    await expect.poll(() => requests.length).toBe(1);
    expect(requests[0]).toMatchObject({ case_id: control, mode: "clean" });
    expect(requests[0].attack_family).toBeUndefined();
    await page
      .getByRole("combobox", { name: "Synthetic case", exact: true })
      .selectOption("attack-case");
    await expect(select).toHaveValue("clean");
    await expect(select.locator("option")).toHaveCount(3);
  });
}

test("missing credentials block a defended launch without losing condition or family", async ({
  page,
}) => {
  const requests = await fixture(page);
  await page.addInitScript(() =>
    localStorage.setItem(
      "poisontrace.synthetic.sessions",
      JSON.stringify([
        {
          id: "missing-ref",
          name: "Synthetic missing credential",
          model: "gemini",
          credentialId: "unavailable",
        },
      ]),
    ),
  );
  await page.goto("/dashboard/single");
  await page
    .getByRole("combobox", { name: "Condition", exact: true })
    .selectOption("defended");
  await page
    .getByRole("combobox", { name: "Attack family", exact: true })
    .selectOption("cross-server-shadowing");
  await page
    .getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    })
    .selectOption("config:missing-ref");
  await expect(
    page.getByRole("button", { name: "Run MCP investigation", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("region", { name: "Execution selection" }),
  ).toContainText("Matching gemini credential required");
  expect(requests).toEqual([]);
  await page
    .getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    })
    .selectOption("scripted");
  await page
    .getByRole("button", { name: "Run MCP investigation", exact: true })
    .click();
  await expect.poll(() => requests.length).toBe(1);
  expect(requests[0]).toMatchObject({
    mode: "defended",
    attack_family: "cross-server-shadowing",
    provider: "scripted",
  });
  expect(requests[0].credential_id).toBeUndefined();
});
