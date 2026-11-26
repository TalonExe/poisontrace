import { test, expect } from "./verification-test.js";
import { fileURLToPath } from "node:url";

async function fixture(page) {
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      const data =
        path === "/api/auth/session"
          ? {
              user: {
                username: "researcher",
                display_name: "Researcher",
                role: "analyst",
              },
            }
          : path === "/api/scenarios"
            ? [
                {
                  scenario_id: "002",
                  name: "Synthetic authentication",
                  valid: true,
                },
              ]
            : [];
      await route.fulfill({ json: data });
    },
  );
}

async function captures(page, name) {
  for (const [width, height, suffix] of [
    [1440, 1000, "desktop"],
    [390, 844, "mobile"],
  ]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => window.scrollTo(0, 0));
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: fileURLToPath(
        new URL(
          `../../.impeccable/review/${name}-${suffix}.png`,
          import.meta.url,
        ),
      ),
      fullPage: true,
      animations: "disabled",
    });
  }
}

test("editing a configuration keeps selection and provider text in the light theme", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/sessions");
  await page.getByRole("button", { name: "Edit", exact: true }).first().click();
  await expect(
    page.getByRole("heading", { name: "Edit configuration", exact: true }),
  ).toBeVisible();
  await captures(page, "configuration-editor");
  await expect(page.locator(".session-row.selected")).toHaveCSS(
    "background-color",
    "rgb(241, 233, 247)",
  );
  await expect(page.locator(".model-option.active span")).toHaveCSS(
    "color",
    "rgb(39, 46, 36)",
  );
  await expect(page.locator(".model-option strong").first()).toHaveCSS(
    "color",
    "rgb(108, 41, 154)",
  );
  await expect(
    page.getByRole("textbox", { name: "Configuration name", exact: true }),
  ).toHaveCSS("color", "rgb(39, 46, 36)");
  await expect(page.locator(".session-editor .editor-note").last()).toHaveCSS(
    "color",
    "rgb(86, 98, 78)",
  );
  await page
    .getByRole("textbox", { name: "Configuration name", exact: true })
    .focus();
  await expect(
    page.getByRole("textbox", { name: "Configuration name", exact: true }),
  ).toHaveCSS("outline-style", "solid");
  await page
    .getByRole("button", { name: "O OpenAI API LLM gpt-5-mini", exact: true })
    .click();
  await expect(page.locator(".model-option.active span")).toHaveText(
    "OpenAI API LLM",
  );
  await expect(page.locator(".model-option.active span")).toHaveCSS(
    "color",
    "rgb(39, 46, 36)",
  );
  await captures(page, "configuration-editor-openai");
});

test("Configurations provides direct history access without opening a configuration", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/sessions");
  await expect(
    page.getByRole("heading", { name: "Settings", exact: true }),
  ).toBeVisible();
  await captures(page, "configurations");
  await page
    .getByRole("navigation", { name: "Workspace navigation" })
    .getByRole("button", { name: "Results", exact: true })
    .click();
  await expect(page).toHaveURL(/\/results\/groups$/);
  await page.getByRole("button", { name: "Runs", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Recorded experiments" }),
  ).toBeVisible();
});

test("researcher reviews the exact offline attack setup before launch", async ({
  page,
}) => {
  await fixture(page);
  let submitted;
  await page.route("**/api/runs/investigation-cases", (route) =>
    route.fulfill({
      json: [
        {
          case_id: "soc-auth-001",
          case_version: "1",
          name: "Synthetic authentication",
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
      ],
    }),
  );
  await page.route("**/api/investigation-jobs", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    submitted = route.request().postDataJSON();
    await route.fulfill({
      status: 400,
      json: { detail: "Fixture request stopped after inspection" },
    });
  });
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Single run", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Condition", exact: true })
    .selectOption("poisoned");
  await page
    .getByRole("combobox", { name: "Attack family", exact: true })
    .selectOption("cross-server-shadowing");
  const summary = page.getByRole("region", {
    name: "This experiment",
    exact: true,
  });
  await expect(summary).toContainText("soc-auth-001");
  await expect(summary).toContainText("soc-auth-shadow-v2");
  await expect(summary).toContainText("No API key used");
  await expect(summary).toContainText("Disabled");
  await captures(page, "experiment");
  await summary
    .getByRole("button", {
      name: "Run MCP investigation",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Fixture request stopped",
  );
  expect(submitted).toMatchObject({
    workflow: "mcp-investigation-v1",
    case_id: "soc-auth-001",
    mode: "poisoned",
    provider: "scripted",
    attack_family: "cross-server-shadowing",
  });
  expect(submitted.credential_id).toBeUndefined();
});

test("a result leads with its decision and references open collapsed evidence", async ({
  page,
}) => {
  await fixture(page);
  const saved = {
    run_id: 81,
    id: "EXP-081",
    scenario_id: "soc-auth-001",
    mode: "Clean",
    status: "completed",
    model: "scripted-soc-v2",
    scoring_version: "investigation-scoring-v1",
    execution_time_ms: 25,
    investigation: {
      case_id: "soc-auth-001",
      case_version: "1",
      decision: {
        verdict: "malicious",
        priority: "P1",
        handling: "escalate",
        explanation: "Returned evidence indicates unapproved access.",
        evidence_refs: ["auth-001"],
      },
      scores: {
        verdict_correctness: true,
        priority_correctness: true,
        handling_correctness: true,
        decision_correctness: true,
        attacker_goal: null,
        marker_influence: null,
        evidence_references_valid: true,
      },
      manifest: {
        enforced: true,
        discovered: [{ name: "get_evidence" }],
        exposed: [{ name: "get_evidence" }],
        restrictions: [],
        invocation_rejections: [],
        executed_calls: 1,
        no_call: false,
      },
      evidence: [
        {
          server_id: "trusted-soc",
          tool_name: "get_evidence",
          arguments: { case_id: "soc-auth-001" },
          result: {
            records: [{ evidence_id: "auth-001", unauthorized_access: true }],
          },
        },
      ],
    },
    trace: [
      { kind: "investigation_completed", data: { verdict: "malicious" } },
    ],
  };
  await page.route("**/api/runs", (route) =>
    route.fulfill({
      json: [saved, { ...saved, run_id: 80, id: "EXP-080", mode: "Defended" }],
    }),
  );
  await page.route("**/api/runs/81", (route) => route.fulfill({ json: saved }));
  await page.goto("/results/runs/81");
  await expect(
    page.getByRole("heading", { name: "Investigation decision", exact: true }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Filter runs", exact: true }).focus();
  await expect(page.locator(".search-field")).toHaveCSS(
    "outline-style",
    "solid",
  );
  await captures(page, "results");
  await expect(page.locator(".evidence-panel")).not.toHaveAttribute("open", "");
  await expect(page.locator(".trace")).not.toHaveAttribute("open", "");
  await page.getByRole("link", { name: "auth-001", exact: true }).click();
  await expect(
    page.getByText('"unauthorized_access": true', { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".evidence-panel")).toHaveAttribute("open", "");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Investigation decision", exact: true }),
  ).toBeVisible();
});
