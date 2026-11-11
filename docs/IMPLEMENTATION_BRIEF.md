# PoisonTrace implementation brief

## Product boundary

The first release is a local, containerised benchmark for one SOC authentication-alert triage workflow. It is a research prototype, not a production SOC platform.

Current distribution decision, 2026-11-03: ADR 0003 adds a public demonstration with live models and analyst-supplied API keys alongside the open-source local edition. Public accounts are issued by the operator, keys/history are private, scenarios are curated and read-only, and provider keys remain encrypted until revoked. These are requirements awaiting implementation, not current hosting capabilities. DEPLOYMENT_REVIEW.md lists launch prerequisites. The historical open questions and frontend build notes below predate backend authentication and the redesign; ADRs and current STATUS take precedence.

## Core flow

- The analyst signs in through a local prototype login page before entering the dashboard.
1. Load a versioned scenario.
2. Start or connect to the sandboxed MCP tools.
3. Present the agent with the alert and discovered tool definitions.
4. Run the agent through the selected clean, poisoned, or defended condition.
5. Enforce manifest and least-privilege policy checks before tool execution.
6. Require explicit approval for a high-impact action.
7. Record discovery, calls, arguments, outputs, policy decisions, approvals, and final recommendations.
8. Calculate benchmark metrics and store the result.

## First scenario

The scenario concerns a suspicious authentication event. The agent retrieves the alert, gathers related synthetic evidence, classifies severity, produces a recommendation, and escalates when appropriate. A mock high-impact tool represents disabling an account or changing a firewall rule.

## Required boundaries

- The model may only access synthetic scenario data.
- MCP containers may not mount the host filesystem.
- No real cloud credentials or production security systems may be connected.
- Tool definitions must be versioned and compared with an approved manifest.
- High-impact actions require an approval record.
- Plaintext API keys must never enter source files, scenarios, traces, logs or ordinary database records. ADR 0003 permits encrypted provider-key storage until revocation; the encryption key stays outside those records.
- Prototype login credentials must not be treated as production credentials or reused for external services.

## Build order

1. Repository and dependency baseline.
2. Domain contracts and scenario loader.
3. Fake model and agent orchestration seam.
4. Mock MCP tools and tool policy.
5. Trace and SQLite persistence.
6. Clean, poisoned, and defended runner.
7. Metric calculations and repeat execution.
8. OpenAI `gpt-5-mini` adapter.
9. Minimal dashboard.

## Open implementation questions

- Whether the prototype login uses a fixed local demo account, a local session, or a replaceable authentication adapter.
- Which routes require authentication, and whether the login session survives a browser refresh.
- Exact tool names and input schemas.
- Exact synthetic protected assets and ground truth.
- Whether the high-impact mock action is account disablement or firewall change.
- Container health checks and process startup order.
- Exact SQLite schema and trace event types.
- Prompt versions and structured output contract for the agent.

## Next frontend slice

Build the login page and local authentication seam before connecting the dashboard to a web API. The page should match the dark Evidence Control system, identify the workspace as synthetic, support loading and invalid-credential states, and redirect authenticated users to the dashboard. Do not add real credential storage.
