import { test, expect } from "./verification-test.js";

test("matched entry and shared Results navigation are primary", async ({
  page,
}) => {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    (route) =>
      route.fulfill({
        json:
          new URL(route.request().url()).pathname === "/api/auth/session"
            ? { user: { username: "researcher", role: "analyst" } }
            : [],
      }),
  );
  await page.goto("/dashboard");
  await expect(
    page.getByRole("button", { name: "Matched group", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("combobox", { name: "Condition", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("navigation", { name: "Workspace navigation" })
    .getByRole("button", { name: "Results", exact: true })
    .click();
  await expect(page).toHaveURL(/\/results\/groups$/);
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await expect(page).toHaveURL(/\/results$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/results\/groups$/);
});

test("Advanced omits metadata execution shortcuts and keeps YAML scenarios accessible", async ({
  page,
}) => {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    (route) =>
      route.fulfill({
        json:
          new URL(route.request().url()).pathname === "/api/auth/session"
            ? { user: { username: "researcher", role: "analyst" } }
            : [],
      }),
  );
  await page.goto("/dashboard");
  const advanced = page
    .getByRole("navigation", { name: "Workspace navigation" })
    .locator("summary");
  await expect(advanced).toHaveText("Advanced");
  await advanced.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Metadata experiments", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Metadata campaigns", exact: true })).toHaveCount(0);
  await page
    .getByRole("button", { name: "Metadata scenarios (YAML)", exact: true })
    .click();
  await expect(page).toHaveURL(/\/scenarios$/);
});

for (const [provider, model] of [
  ["scripted", null],
  ["gemini", "gemini-3.5-flash-lite"],
  ["openai", "gpt-5-mini"],
]) {
  test(`default group preserves ${provider} requests, controls and returned IDs`, async ({
    page,
  }) => {
    let submitted;
    await page.addInitScript(
      ({ provider }) =>
        localStorage.setItem(
          "poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions",
          JSON.stringify([
            {
              id: "selected-config",
              name: "Synthetic configuration",
              model: provider,
              credentialId: "synthetic-reference",
            },
          ]),
        ),
      { provider },
    );
    await page.route(
      (url) => url.pathname.startsWith("/api/"),
      async (route) => {
        const path = new URL(route.request().url()).pathname;
        let data = [];
        if (path === "/api/credentials") data = [{credential_id:"synthetic-reference",provider,label:"Synthetic reference"}];
        if (path === "/api/auth/session")
          data = { user: { username: "researcher", role: "analyst" } };
        if (path === "/api/runs/investigation-cases")
          data = [
            {
              case_id: "synthetic-attack",
              case_version: "7",
              name: "Synthetic incident",
              attacks: [
                {
                  family: "cross-server-shadowing",
                  payload_id: "soc-auth-shadow-v2",
                },
              ],
            },
            {
              case_id: "synthetic-control",
              case_version: "2",
              name: "Synthetic clean control",
              attacks: [],
            },
          ];
        if (path === "/api/run-groups" && route.request().method() === "POST") {
          submitted = route.request().postDataJSON();
          data = { group_id: "directly-returned" };
        }
        if (path === "/api/run-groups/directly-returned")
          return route.fulfill({
            status: 503,
            json: { detail: "Synthetic detail unavailable" },
          });
        await route.fulfill({ json: data });
      },
    );
    await page.goto("/dashboard");
    await page.getByRole("combobox", {name:"Execution model and credential",exact:true}).selectOption(provider === "scripted" ? "scripted" : "config:selected-config");
    await expect(page.getByLabel("Group repeats")).toHaveValue("1");
    for (const name of ["clean", "poisoned", "defended"])
      await expect(
        page.getByRole("checkbox", { name, exact: true }),
      ).toBeChecked();
    await expect(
      page.getByRole("complementary", { name: "Group specification" }),
    ).toContainText(model || "scripted-soc-v2");
    await page.getByLabel("Group repeats").fill("2");
    if (provider === "scripted") {
      await page.getByLabel("Group case").selectOption("synthetic-control");
      for (const name of ["poisoned", "defended"]) {
        await expect(
          page.getByRole("checkbox", { name, exact: true }),
        ).toBeDisabled();
        await expect(
          page.getByRole("checkbox", { name, exact: true }),
        ).not.toBeChecked();
      }
    }
    for (const [width, height] of [
      [1440, 1000],
      [390, 844],
    ]) {
      await page.setViewportSize({ width, height });
      await page.locator(".workspace-navigation summary").click();
      await expect(
        page.getByRole("button", {
          name: "Metadata scenarios (YAML)",
          exact: true,
        }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: `../.scratch/cleanup-32/${provider}-${width}.png`,
        fullPage: true,
      });
      await page.locator(".workspace-navigation summary").click();
    }
    await page
      .getByRole("button", { name: "Run matched group", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/results\/groups\/directly-returned$/);
    expect(submitted).toEqual(
      provider === "scripted"
        ? {
            case_id: "synthetic-control",
            case_version: "2",
            provider: "scripted",
            conditions: ["clean"],
            repeats: 2,
          }
        : {
            case_id: "synthetic-attack",
            case_version: "7",
            provider,
            model,
            credential_id: "synthetic-reference",
            conditions: ["clean", "poisoned", "defended"],
            repeats: 2,
            attack_family: "cross-server-shadowing",
          },
    );
    await expect(page.getByRole("alert")).toContainText(
      "Synthetic detail unavailable",
    );
    await page.reload();
    await expect(page.getByRole("alert")).toContainText(
      "Synthetic detail unavailable",
    );
  });
}

test("secondary single MCP selection survives refresh and back", async ({
  page,
}) => {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    (route) =>
      route.fulfill({
        json:
          new URL(route.request().url()).pathname === "/api/auth/session"
            ? { user: { username: "researcher", role: "analyst" } }
            : [],
      }),
  );
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard\/single$/);
  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "Condition", exact: true }),
  ).toHaveValue("clean");
  await expect(
    page
      .getByRole("combobox", { name: "Condition", exact: true })
      .locator("option"),
  ).toHaveCount(1);
  await page
    .getByRole("button", { name: "Matched group", exact: true })
    .click();
  await page.goBack();
  await expect(
    page.getByRole("combobox", { name: "Condition", exact: true }),
  ).toBeVisible();
});

test('metadata launch pages retain configuration prerequisites', async ({page}) => {
  await page.addInitScript(() => localStorage.setItem('poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions', '[]'));
  await page.route(url => url.pathname.startsWith('/api/'), route => route.fulfill({json:
    new URL(route.request().url()).pathname === '/api/auth/session'
      ? {user:{username:'researcher',role:'analyst'}} : []}));
  for (const path of ['/dashboard/metadata','/dashboard/campaign']) {
    await page.goto(path);
    await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Run matched group',exact:true})).toHaveCount(0);
  }
});
