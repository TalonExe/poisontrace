# PoisonTrace implementation brief

## Product boundary

The first release is a local, containerised benchmark for one SOC authentication-alert triage workflow. It is a research prototype, not a production SOC platform.

## Core flow

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
- API keys must never enter source files, scenarios, traces, or database records.

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

- Exact tool names and input schemas.
- Exact synthetic protected assets and ground truth.
- Whether the high-impact mock action is account disablement or firewall change.
- Container health checks and process startup order.
- Exact SQLite schema and trace event types.
- Prompt versions and structured output contract for the agent.
