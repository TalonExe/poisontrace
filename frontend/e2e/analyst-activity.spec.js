import { test, expect } from "./verification-test.js";

test.use({ timezoneId: "Asia/Kuala_Lumpur" });

test("analyst reviews period activity and opens the matching saved results", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-11-25T12:00:00+08:00"));
  const at = Date.parse("2026-11-23T00:01:00+08:00") / 1000;
  const run = { run_id: 11, id: "EXP-011", mode: "clean", result: "Completed" };
  await page.route("**/api/**", route => {
    const url = new URL(route.request().url());
    const user = { id: 1, username: "analyst", role: "analyst" };
    if (url.pathname.startsWith("/api/auth/")) return route.fulfill({ json: { user } });
    if (url.pathname === "/api/runs") {
      return route.fulfill({ json: [run, { ...run, run_id: 22, id: "EXP-022", result: "Failed" }] });
    }
    if (url.pathname === "/api/runs/activity") {
      const inside = Number(url.searchParams.get("start")) <= at && at < Number(url.searchParams.get("end"));
      return route.fulfill({ json: {
        attempts: inside ? [
          { at, run_id: 11, status: "completed", provider: "scripted" },
          { at, run_id: 22, status: "failed", provider: "openai" },
        ] : [],
        groups: inside ? [{ at, group_id: "group-one" }] : [],
        reruns: inside ? [{ at, group_id: "group-one", job_id: "rerun-one" }, { at, group_id: "group-one", job_id: "rerun-two" }] : [],
        interrupted: inside ? 1 : 0,
      } });
    }
    if (url.pathname === "/api/run-groups") return route.fulfill({ json: [
      { group_id: "group-one", status: "finished", plan: { case: { name: "First case", case_version: "1" }, conditions: ["clean"], repeats: 1, model: "scripted" } },
      { group_id: "group-two", status: "finished", plan: { case: { name: "Second case", case_version: "1" }, conditions: ["clean"], repeats: 1, model: "scripted" } },
    ] });
    return route.fulfill({ json: [] });
  });
  await page.goto("/login");
  await expect(page).toHaveURL(/\/activity$/);
  await expect(page.getByRole("heading", { name: "Analyst dashboard" })).toBeVisible();
  await expect(page.getByText("Your investigation activity · Asia/Kuala_Lumpur")).toBeVisible();
  await expect(page.getByText("In progress")).toBeVisible();
  const chart = page.getByRole("article").filter({ has: page.getByRole("heading", { name: "Saved attempts over time" }) });
  await expect(chart).toHaveAccessibleDescription("Standalone and matched-group investigations. 1 completed, 1 failed.");
  await expect(page.getByRole("button", { name: "Week", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("1 completed · 1 failed")).toBeVisible();
  await expect(page.getByRole("article").filter({ hasText: "Interrupted jobs" }).locator("strong")).toHaveText("1");
  const weekResults = "/results/runs?start=1795363200&end=1795449600&metric=attempts&value=failed";
  await expect(chart.getByRole("link", { name: /Nov 23, 2026.*1 failed/ })).toHaveAttribute("href", weekResults);
  await chart.locator('svg [aria-label*="1 failed"]').click();
  await expect(page).toHaveURL(weekResults);
  await expect(page.getByRole("button", { name: /EXP-022/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /EXP-011/ })).toHaveCount(0);
  await page.goBack();
  await page.getByRole("button", { name: "Month", exact: true }).click();
  await expect(page.getByRole("button", { name: "Month", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Previous period" }).click();
  await expect(chart.getByText("No saved attempts in this period.")).toBeVisible();
  await expect(chart.getByRole("link")).toHaveCount(0);
  await page.getByRole("button", { name: "Next period" }).click();
  await expect(chart.getByRole("link", { name: /1 failed/ })).toBeVisible();
  await expect(chart.locator('svg [aria-label*="1 failed"]')).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("activity-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const monthResults = "/results/runs?start=1795276800&end=1795881600&metric=attempts&value=failed";
  const failedLink = chart.getByRole("link", { name: /Nov 22.*28.*2026.*1 failed/ });
  await expect(failedLink).toHaveAttribute("href", monthResults);
  await expect.poll(() => failedLink.evaluate(link => link.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole("button", { name: "Previous period" }).focus();
  await page.keyboard.press("Tab");
  await expect(failedLink).toBeFocused();
  await page.screenshot({ path: test.info().outputPath("activity-mobile.png"), fullPage: true });
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(monthResults);
  await expect(page.getByRole("button", { name: /EXP-022/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /EXP-011/ })).toHaveCount(0);
  await page.getByRole("link", { name: "PoisonTrace dashboard", exact: true }).click();
  await page.getByRole("button", { name: /Scripted.*1/ }).click();
  await expect(page.getByText("Attempts by Scripted")).toBeVisible();
  await expect(page.getByRole("button", { name: /EXP-011/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /EXP-022/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Clear dashboard filter" }).click();
  await expect(page.getByRole("button", { name: /EXP-022/ })).toBeVisible();
  await page.getByRole("link", { name: "PoisonTrace dashboard", exact: true }).click();
  await expect(page).toHaveURL(/\/activity$/);
  await page.getByRole("button", { name: /2 reruns submitted/ }).click();
  await expect(page.getByText("2 matching records")).toBeVisible();
  await expect(page.getByText(/2 reruns in selected period/)).toBeVisible();
  await expect(page.locator(".recorded-run")).toHaveCount(1);
});
