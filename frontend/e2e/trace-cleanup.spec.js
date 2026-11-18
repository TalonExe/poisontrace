import { test, expect } from "@playwright/test";

for (const [version, status] of [
  ["legacy", "completed"],
  ["recommendation-v1", "failed"],
  ["investigation-unscored-v1", "failed"],
]) {
  test(`one complete ordered trace survives refresh and mobile: ${version}`, async ({
    page,
  }) => {
    const events = [
      {
        kind: "discovery_started",
        data: {
          text: "literal null",
          nothing: null,
          flag: false,
          number: 0,
          nested: {
            records: [
              {
                id: "synthetic-1",
                text: "line one\nline two",
                long: "x".repeat(500),
              },
            ],
          },
        },
      },
      {
        kind: "tool_result",
        data: {
          server_id: "synthetic-soc",
          records: [{ evidence_id: "evidence-1" }],
        },
        recorded_at: "synthetic timestamp",
      },
      {
        kind: "attempt_failed",
        data: { safe_error: "synthetic_timeout", partial: true },
      },
    ];
    const saved = {
      run_id: 700,
      id: "EXP-700",
      scoring_version: version,
      status,
      scenario_id: "synthetic-case",
      result: "Synthetic result",
      recommendation: "Synthetic recommendation",
      execution_time_ms: 12,
      trace: events,
    };
    await page.route(
      (url) => url.pathname.startsWith("/api/"),
      (route) => {
        const path = new URL(route.request().url()).pathname;
        return route.fulfill({
          json:
            path === "/api/auth/session"
              ? { user: { username: "synthetic", role: "analyst" } }
              : path === "/api/runs/700"
                ? saved
                : path === "/api/runs"
                  ? [saved]
                  : [],
        });
      },
    );
    await page.goto("/results/runs/700");
    const trace = page.locator(".trace");
    await trace.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(trace).toHaveAttribute("open", "");
    await expect(
      page.getByRole("button", { name: "Open full trace" }),
    ).toHaveCount(0);
    const entries = trace.locator(".timeline > div");
    await expect(entries).toHaveCount(3);
    for (let index = 0; index < events.length; index++) {
      await expect(entries.nth(index).locator("time")).toHaveText(
        String(index + 1),
      );
      expect(
        JSON.parse(await entries.nth(index).locator("pre").innerText()),
      ).toEqual(events[index]);
    }
    for (const [width, height, name] of [
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
        path: `../.scratch/cleanup-37/trace-${version}-${name}.png`,
        fullPage: true,
      });
    }
    await trace.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(trace).not.toHaveAttribute("open", "");
    await page.reload();
    await trace.locator("summary").click();
    expect(JSON.parse(await entries.nth(1).locator("pre").innerText())).toEqual(
      events[1],
    );
  });
}
