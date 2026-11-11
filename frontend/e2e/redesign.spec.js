import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route(url => url.pathname.startsWith("/api/"), async route => {
    const path = new URL(route.request().url()).pathname;
    const run = id => ({ run_id: id, id: `EXP-00${id}`, mode: "Clean", scenario_id: "002", result: "Blocked", trace: [{ kind: "recommendation_created", data: { value: `Recommendation ${id}` } }] });
    const data = path === "/api/auth/session" ? { user: { username: "researcher", display_name: "Researcher", role: "analyst" } }
      : path === "/api/runs" ? [run(2), run(1)]
      : path.startsWith("/api/runs/") ? run(Number(path.split("/").pop()))
      : path === "/api/scenarios" ? [{ scenario_id: "002", name: "Synthetic case", filename: "case-002.yaml", valid: true }] : [];
    await route.fulfill({ json: data });
  });
});

test("closing a new session leaves saved configurations unchanged", async ({ page }) => {
  await page.goto("/sessions");
  await expect(page.getByRole("heading", { name: "Choose a session", exact: true })).toBeVisible();
  const count = await page.locator(".session-row").count();
  await page.getByRole("button", { name: "New session", exact: true }).click();
  await page.getByLabel("Session name").fill("Unsaved draft");
  await page.getByRole("button", { name: "Close editor" }).click();
  await expect(page.locator(".session-row")).toHaveCount(count);
  await page.reload();
  await expect(page.getByText("Unsaved draft")).toHaveCount(0);
});

test("recorded-run selection updates the inspected evidence", async ({ page }) => {
  await page.goto("/dashboard");
  await page.getByRole("button", { name: /EXP-001/ }).click();
  await expect(page.getByRole("button", { name: /EXP-001/ })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("value: Recommendation 1", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Scenario library", exact: true })).toBeVisible();
});

test("mobile navigation remains available without an off-screen drawer", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await expect(page.getByRole("navigation", { name: "Workspace navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sessions", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
