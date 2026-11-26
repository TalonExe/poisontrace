import { test, expect } from "./verification-test.js";

test("case dropdowns use the authored dataset categories", async ({ page }) => {
  const cases = [
    { case_id: "incident", case_version: "1", name: "Incident", dataset_category: "malicious-incident" },
    { case_id: "backup", case_version: "2", name: "Backup", dataset_category: "benign-activity" },
    { case_id: "alert", case_version: "1", name: "Alert", dataset_category: "false-positive-alert" },
    { case_id: "legacy", case_version: "1", name: "Legacy" },
  ];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/session")
      return route.fulfill({ json: { user: { username: "analyst", role: "analyst", content_read_only: true } } });
    if (path === "/api/runs/investigation-cases")
      return route.fulfill({ json: cases });
    return route.fulfill({ json: [] });
  });

  for (const [route, label] of [
    ["/dashboard/single", "Synthetic case"],
    ["/dashboard", "Group case"],
    ["/research-cases", "Research case"],
  ]) {
    await page.goto(route);
    const picker = page.getByRole("combobox", { name: new RegExp(`^${label}`) });
    await expect(picker.locator("optgroup")).toHaveCount(4);
    expect(await picker.locator("optgroup").evaluateAll((groups) => groups.map((group) => group.label))).toEqual([
      "Benign activity", "False-positive alerts", "Malicious incidents", "Uncategorized",
    ]);
    await expect(picker.locator('optgroup[label="Benign activity"] option')).toHaveAttribute("value", "backup");
    await picker.selectOption("backup");
    await expect(picker).toHaveValue("backup");
  }
});

async function captureAtBothWidths(page, state) {
  for (const width of [1360, 390]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.locator("html").evaluate((element) => element.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: `.scratch/issue-52/${state}-${width}.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1360, height: 900 });
}

test("the sample can be unavailable without blocking other experiment setup", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/session")
      return route.fulfill({ json: { user: { username: "analyst", role: "analyst" } } });
    if (path === "/api/runs/investigation-cases")
      return route.fulfill({ json: [{ case_id: "another-case", case_version: "1", name: "Another case" }] });
    return route.fulfill({ json: [] });
  });
  await page.goto("/dashboard/single");
  await expect(page.getByText(/The sample case is unavailable/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try a sample investigation" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Run MCP investigation" })).toBeEnabled();
  await page.getByRole("button", { name: "Matched group" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("an analyst starts a clean offline sample explicitly and opens its saved run", async ({
  page,
}) => {
  let signedIn = false;
  let submissions = 0;
  let sampleJob;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === "/api/auth/login") signedIn = true;
    if (path.startsWith("/api/auth/")) {
      return route.fulfill({
        json: {
          user: signedIn ? { username: "analyst", role: "analyst" } : null,
        },
      });
    }
    if (path === "/api/runs/investigation-cases") {
      return route.fulfill({
        json: [
          { case_id: "another-case", case_version: "1", name: "Another case" },
          {
            case_id: "soc-backup-002",
            case_version: "1",
            name: "Scheduled backup",
          },
        ],
      });
    }
    if (path === "/api/investigation-jobs" && request.method() === "POST") {
      submissions++;
      expect(request.postDataJSON()).toMatchObject({
        case_id: "soc-backup-002",
        mode: "clean",
        provider: "scripted",
      });
      if (submissions === 1)
        return route.fulfill({
          status: 400,
          json: { detail: "Sample temporarily unavailable. Try again." },
        });
      sampleJob = { job_id: "sample-job", status: "queued" };
      return route.fulfill({ json: sampleJob });
    }
    if (path === "/api/investigation-jobs")
      return route.fulfill({ json: sampleJob ? [sampleJob] : [] });
    return route.fulfill({ json: [] });
  });
  await page.goto("/login");
  await page.getByLabel("Username").fill("analyst");
  await page.getByLabel("Passcode").fill("synthetic-only");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/activity$/);
  await page.goto("/dashboard/single");
  await expect(
    page.getByRole("button", { name: "Try a sample investigation" }),
  ).toBeEnabled();
  await captureAtBothWidths(page, "experiment");
  await page
    .getByRole("button", { name: "Try a sample investigation" })
    .click();
  await expect(page.getByLabel("Synthetic case")).toHaveValue("soc-backup-002");
  await expect(page.getByRole("combobox", { name: /^Condition/ })).toHaveValue(
    "clean",
  );
  expect(submissions).toBe(0);
  await page
    .getByRole("button", { name: "Run investigation", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Sample temporarily unavailable.",
  );
  await expect(page.getByLabel("Synthetic case")).toHaveValue("soc-backup-002");
  await page
    .getByRole("button", { name: "Run investigation", exact: true })
    .click();
  await expect(page.getByText(/Investigation queued/)).toBeVisible();
  sampleJob = { ...sampleJob, status: "completed", run_id: 9 };
  await expect(
    page.getByRole("button", { name: "View saved run" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "View saved run" }),
  ).toBeFocused();
  await captureAtBothWidths(page, "completed");
  await page.getByRole("button", { name: "View saved run" }).click();
  await expect(page).toHaveURL(/\/results\/runs\/9$/);
  expect(submissions).toBe(2);
});

test("Settings manages API keys independently of saved configurations", async ({
  page,
}) => {
  let keys = [];
  let revokeRequests = 0;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === "/api/auth/session")
      return route.fulfill({
        json: { user: { username: "analyst", role: "analyst" } },
      });
    if (path === "/api/credentials" && request.method() === "GET")
      return route.fulfill({ json: keys });
    if (path === "/api/credentials" && request.method() === "POST") {
      keys = [
        {
          credential_id: "sample-key",
          provider: "gemini",
          label: "Research key",
        },
      ];
      return route.fulfill({ json: keys[0] });
    }
    if (path === "/api/credentials/sample-key" && request.method() === "PUT") {
      expect(request.postDataJSON().secret).toBe("replacement-test-key");
      return route.fulfill({ json: keys[0] });
    }
    if (
      path === "/api/credentials/sample-key" &&
      request.method() === "DELETE"
    ) {
      if (++revokeRequests === 1) return route.fulfill({ status: 503, json: { detail: "Try again." } });
      keys = [];
      return route.fulfill({
        json: { credential_id: "sample-key", revoked: true },
      });
    }
    return route.fulfill({ json: [] });
  });
  await page.goto("/dashboard/single");
  await expect(page.getByRole("navigation", { name: "Workspace navigation" }).getByRole("button", { name: "Settings" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /settings/i })).toHaveCount(0);
  const settings = page.locator(".authenticated-user").getByRole("button", { name: "Settings", exact: true });
  await settings.focus();
  await settings.press("Enter");
  await expect(page).toHaveURL(/\/settings$/);
  await expect(settings).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("heading", { name: "Saved configurations" }),
  ).toBeVisible();
  await page.getByLabel("Key label").fill("Research key");
  await page.getByLabel("API key", { exact: true }).fill("initial-test-key");
  await page.getByRole("button", { name: "Add API key" }).click();
  await expect(page.getByText("API key added.")).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).first().click();
  await page.getByLabel("API credential reference").selectOption("sample-key");
  await page.getByRole("button", { name: "Save configuration" }).click();
  await captureAtBothWidths(page, "settings");
  await page.getByRole("button", { name: "Replace Research key" }).click();
  await page.getByLabel("New API key").fill("replacement-test-key");
  await page.getByRole("button", { name: "Replace API key" }).click();
  await expect(page.getByText("API key replaced.")).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).first().click();
  await expect(page.getByLabel("API credential reference")).toHaveValue(
    "sample-key",
  );
  await expect(page.getByText("replacement-test-key")).toHaveCount(0);
  const revoke = page.getByRole("button", { name: "Revoke Research key" });
  await revoke.click();
  const confirmation = page.getByRole("dialog", { name: "Revoke Research key?" });
  await expect(confirmation.getByRole("button", { name: "Cancel" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(confirmation).toHaveCount(0);
  await expect(revoke).toBeFocused();
  expect(revokeRequests).toBe(0);
  await revoke.click();
  await confirmation.getByRole("button", { name: "Revoke API key" }).click();
  await expect(confirmation.getByRole("alert")).toContainText("Could not revoke the API key");
  await captureAtBothWidths(page, "revoke-confirmation");
  await confirmation.getByRole("button", { name: "Revoke API key" }).click();
  await expect(page.getByText("API key revoked.")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Replace Research key" }),
  ).toHaveCount(0);
});
