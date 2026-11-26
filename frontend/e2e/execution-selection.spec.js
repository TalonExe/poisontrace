import { test, expect } from "./verification-test.js";

test("offline MCP entry needs no saved configuration and shares one execution selection", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions", "[]"),
  );
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
    page.getByRole("heading", { name: "Matched group setup", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    }),
  ).toHaveValue("scripted");
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await expect(
    page.getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    }),
  ).toHaveValue("scripted");
  await page.reload();
  await expect(
    page.getByText("No API key used.", { exact: true }),
  ).toBeVisible();
});

const configurations = [
  {
    id: "legacy-g-7",
    name: "Legacy Gemini",
    model: "gemini",
    credentialId: "g-ref",
    scenario: "preserved-old-value",
    updated: "yesterday",
  },
  {
    id: "legacy-o-8",
    name: "Legacy OpenAI",
    model: "openai",
    credentialId: "o-ref",
  },
  {
    id: "mismatched",
    name: "Mismatched reference",
    model: "gemini",
    credentialId: "o-ref",
  },
];
const refs = [
  {
    credential_id: "g-ref",
    provider: "gemini",
    label: "Gemini test",
    masked: "***g",
  },
  {
    credential_id: "o-ref",
    provider: "openai",
    label: "OpenAI test",
    masked: "***o",
  },
];
const cases = [
  {
    case_id: "synthetic-case",
    case_version: "1",
    name: "Synthetic attack case",
    attacks: [
      { family: "cross-server-shadowing", payload_id: "soc-auth-shadow-v2" },
    ],
  },
];
async function fixture(page) {
  let available = true;
  const requests = [];
  await page.addInitScript(
    (configs) => {
      if (localStorage.getItem("poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions") === null)
        localStorage.setItem("poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions", JSON.stringify(configs));
    },
    configurations,
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (route.request().method() === "POST") {
        requests.push({ path, body: route.request().postDataJSON() });
        return route.fulfill({
          status: 400,
          json: { detail: "Synthetic stop after capture" },
        });
      }
      const data =
        path === "/api/auth/session"
          ? { user: { username: "researcher", role: "analyst" } }
          : path === "/api/credentials"
            ? available
              ? refs
              : []
            : path === "/api/runs/investigation-cases"
              ? cases
              : path === "/api/run-groups"
                ? [
                    {
                      group_id: "saved-live",
                      plan: {
                        provider: "openai",
                        model: "pinned-openai-model",
                        case: {
                          case_id: "synthetic-case",
                          case_version: "1",
                          name: "Saved case",
                        },
                        conditions: ["clean"],
                        repeats: 2,
                      },
                    },
                  ]
                : [];
      await route.fulfill({ json: data });
    },
  );
  return {
    requests,
    revoke: () => {
      available = false;
    },
  };
}
for (const single of [false, true]) {
  test(`${single ? "single MCP" : "group"} switches model and credential together without losing setup`, async ({
    page,
  }) => {
    const { requests, revoke } = await fixture(page);
    await page.goto(single ? "/dashboard/single" : "/dashboard");
    const select = page.getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    });
    await expect(
      page.getByRole("combobox", {
        name: single ? "Investigation model" : "Group provider",
        exact: true,
      }),
    ).toHaveCount(0);
    if (!single) await page.getByLabel("Group repeats").fill("3");
    const launch = page.getByRole("button", {
      name: single ? "Run MCP investigation" : "Run matched group",
      exact: true,
    });
    for (const [id, provider, model, credential] of [
      ["legacy-g-7", "gemini", "gemini-3.5-flash-lite", "g-ref"],
      ["legacy-o-8", "openai", "gpt-5-mini", "o-ref"],
    ]) {
      await select.selectOption(`config:${id}`);
      await expect(
        page.getByRole("region", { name: "Execution selection" }),
      ).toContainText(model);
      await launch.click();
      await expect(page.getByRole("alert")).toContainText("Synthetic stop");
      expect(requests.at(-1).body).toMatchObject({
        provider,
        model,
        credential_id: credential,
      });
      if (!single)
        expect(requests.at(-1).body).toMatchObject({
          repeats: 3,
          conditions: ["clean", "poisoned", "defended"],
        });
    }
    await page.reload();
    await expect(select).toHaveValue("config:legacy-o-8");
    if (!single) {
      await page.getByLabel("Group repeats").fill("4");
      await page
        .getByRole("checkbox", { name: "defended", exact: true })
        .uncheck();
    }
    await select.selectOption("config:mismatched");
    await expect(launch).toBeDisabled();
    await expect(
      page.getByRole("region", { name: "Execution selection" }),
    ).toContainText("Matching gemini credential required");
    await select.selectOption("config:legacy-g-7");
    revoke();
    await page
      .getByRole("button", { name: "Reload execution options", exact: true })
      .click();
    await expect(launch).toBeDisabled();
    if (!single) {
      await expect(page.getByLabel("Group repeats")).toHaveValue("4");
      await expect(
        page.getByRole("checkbox", { name: "defended", exact: true }),
      ).not.toBeChecked();
    }
    await select.selectOption("scripted");
    await launch.click();
    await expect.poll(() => requests.at(-1)?.body.provider).toBe("scripted");
    expect(requests.at(-1).body.credential_id).toBeUndefined();
    expect(requests.at(-1).body.model).toBeUndefined();
    expect(
      JSON.parse(
        await page.evaluate(() =>
          localStorage.getItem("poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions"),
        ),
      ),
    ).toEqual(configurations);
  });
}

test("saved group rerun pins model and accepts only a current matching credential", async ({
  page,
}) => {
  const { requests } = await fixture(page);
  await page.goto("/dashboard");
  await page
    .getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    })
    .selectOption("config:legacy-g-7");
  await page.getByLabel("Group source").selectOption("saved-live");
  const launch = page.getByRole("button", {
    name: "Rerun matched group",
    exact: true,
  });
  await expect(launch).toBeDisabled();
  await expect(
    page.getByRole("region", { name: "Execution selection" }),
  ).toContainText("pinned-openai-model");
  await page
    .getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    })
    .selectOption("config:legacy-o-8");
  await launch.click();
  await expect.poll(() => requests.length).toBe(1);
  expect(requests[0]).toEqual({
    path: "/api/run-groups/saved-live/execute",
    body: { credential_id: "o-ref" },
  });
});

test("opening an existing configuration selects its model and reference once", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/sessions");
  await page
    .locator(".session-row")
    .filter({ hasText: "Legacy OpenAI" })
    .getByRole("button", { name: "Open", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    }),
  ).toHaveValue("config:legacy-o-8");
  await expect(
    page.getByRole("region", { name: "Execution selection" }),
  ).toContainText("gpt-5-mini · Credential: OpenAI test · ***o");
  await page.reload();
  await expect(
    page.getByRole("combobox", {
      name: "Execution model and credential",
      exact: true,
    }),
  ).toHaveValue("config:legacy-o-8");
});

test("configuration editing and credential save/revoke retain legacy records", async ({
  page,
}) => {
  await fixture(page);
  let saved = false;
  await page.route("**/api/credentials", async (route) => {
    if (route.request().method() === "POST") {
      expect(route.request().postDataJSON()).toEqual({
        provider: "gemini",
        label: "New synthetic reference",
        secret: "synthetic-only-key",
      });
      saved = true;
      return route.fulfill({
        json: {
          credential_id: "new-ref",
          provider: "gemini",
          label: "New synthetic reference",
          masked: "***new",
        },
      });
    }
    return route.fulfill({
      json: saved
        ? [
            ...refs,
            {
              credential_id: "new-ref",
              provider: "gemini",
              label: "New synthetic reference",
              masked: "***new",
            },
          ]
        : refs,
    });
  });
  await page.route("**/api/credentials/new-ref", async (route) => {
    expect(route.request().method()).toBe("DELETE");
    saved = false;
    await route.fulfill({ json: { credential_id: "new-ref", revoked: true } });
  });
  await page.goto("/sessions");
  const row = () =>
    page.locator(".session-row").filter({ hasText: "Legacy Gemini" });
  await row().getByRole("button", { name: "Edit", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Key label", exact: true })
    .fill("New synthetic reference");
  await page.getByLabel("API key", { exact: true }).fill("synthetic-only-key");
  await page.getByRole("button", { name: "Add API key", exact: true }).click();
  await expect(page.getByText("API key added.")).toBeVisible();
  await page.getByLabel("API credential reference").selectOption("new-ref");
  await page
    .getByRole("button", { name: "Save configuration", exact: true })
    .click();
  await page.reload();
  await row().getByRole("button", { name: "Open", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Execution selection" }),
  ).toContainText("New synthetic reference");
  await page
    .getByRole("button", { name: "Settings", exact: true })
    .click();
  await row().getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "Revoke New synthetic reference" }).click();
  await page.getByRole("dialog", { name: "Revoke New synthetic reference?" }).getByRole("button", { name: "Revoke API key" }).click();
  await expect(page.getByText("API key revoked.")).toBeVisible();
  await expect(page.getByLabel("API credential reference")).toHaveValue("new-ref");
  await page.getByLabel("API credential reference").selectOption("");
  await page
    .getByRole("button", { name: "Save configuration", exact: true })
    .click();
  const records = JSON.parse(
    await page.evaluate(() =>
      localStorage.getItem("poisontrace.account.analyst:researcher.poisontrace.synthetic.sessions"),
    ),
  );
  expect(records.find((c) => c.id === "legacy-g-7")).toMatchObject({
    scenario: "preserved-old-value",
    model: "gemini",
    credentialId: "",
  });
  expect(records.find((c) => c.id === "legacy-o-8")).toEqual(configurations[1]);
  await row().getByRole("button", { name: "Open", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Run matched group", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("region", { name: "Execution selection" }),
  ).toContainText("Matching gemini credential required");
});
