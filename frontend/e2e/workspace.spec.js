import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  let authenticated = false;
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/login") authenticated = true;
      const data = path.startsWith("/api/auth/")
        ? {
            user: authenticated
              ? { username: "analyst", role: "analyst", redirect: "/sessions" }
              : null,
          }
        : path === "/api/scenarios"
          ? [{ scenario_id: "002", name: "Synthetic case", valid: true }]
          : [];
      await route.fulfill({ json: data });
    },
  );
  await page.goto("/");
});

async function signIn(page) {
  await page.getByLabel("Username").fill("analyst");
  await page.getByLabel("Local passcode").fill("synthetic-only");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Configurations" }),
  ).toBeVisible();
}

test("login accepts the synthetic demo account", async ({ page }) => {
  await signIn(page);
  await expect(page.getByText("Authentication alert study")).toBeVisible();
});

test("session workspace creates a session and selects a provider", async ({
  page,
}) => {
  await signIn(page);
  await page.getByRole("button", { name: /New configuration/ }).click();
  await page.getByLabel("Configuration name").fill("OpenAI browser study");
  const openAiOption = page.getByRole("button", {
    name: /OpenAI API LLM gpt-5-mini/,
  });
  await openAiOption.click();
  await expect(openAiOption).toHaveClass(/active/);
  await page.getByRole("button", { name: /Save configuration/ }).click();
  await expect(page.getByText("OpenAI browser study")).toBeVisible();
});

test("sidebar navigates to scenarios and back to sessions", async ({
  page,
}) => {
  await signIn(page);
  await page.getByRole("button", { name: /Scenarios/ }).click();
  await expect(
    page.getByRole("heading", { name: "Scenario library" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Configurations", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Configurations" }),
  ).toBeVisible();
});

test("credential selector displays masked references without plaintext secrets", async ({
  page,
}) => {
  await page.route("**/api/credentials", async (route) =>
    route.fulfill({
      json: [
        {
          credential_id: "cred-1",
          provider: "gemini",
          label: "Research",
          masked: "••••1234",
        },
      ],
    }),
  );
  await signIn(page);
  await page.getByRole("button", { name: /Edit/ }).first().click();
  await expect(
    page.locator(".credential-row").getByText("Research · ••••1234"),
  ).toBeVisible();
  const credentialSelect = page
    .locator("select")
    .filter({ hasText: "Research" });
  await credentialSelect.selectOption("cred-1");
  await expect(credentialSelect).toHaveValue("cred-1");
  await expect(page.locator("body")).not.toContainText("synthetic-only");
});
