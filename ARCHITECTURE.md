# PoisonTrace architecture

## External seams

### Scenario runner

`run(scenario_id, mode, model, run_count) -> ExperimentRun[]`

The runner loads a scenario, coordinates the agent and tools, applies the selected policy, records the trace, and returns persisted run results. Callers do not need to know how MCP sessions, model calls, or SQLite writes are coordinated.

### Agent model

`respond(prompt, tool_definitions) -> AgentDecision`

The agent model adapter receives a structured prompt and discovered tool definitions, then returns a structured decision. The fake model and the OpenAI adapter satisfy the same interface.

### Tool gateway

`invoke(tool_name, arguments, policy_context) -> ToolOutcome`

The gateway owns tool lookup, manifest validation, least-privilege checks, approval requirements, invocation, and policy decisions. The runner does not call MCP tools directly.

### Trace store

`record(event) -> None` and `save_run(result) -> RunId`

The trace store accepts domain events and saves completed experiment results. The benchmark logic does not depend on SQLite-specific queries.

### Metrics calculator

`calculate(run_results, ground_truth) -> Metrics`

The calculator derives the initial benchmark metrics from completed run results and scenario ground truth. It has no model, MCP, or database dependency.

## Internal adapters

- `FakeModelAdapter` for deterministic tests
- `OpenAIModelAdapter` for `gpt-5-mini`
- `McpToolAdapter` for sandboxed MCP servers
- `SqliteTraceStore` for local persistence
- `InMemoryTraceStore` for fast tests

## First vertical slice

The first slice crosses the scenario runner, fake model, tool gateway, in-memory trace store, and metrics calculator. It proves clean, poisoned, and defended outcomes before introducing Docker, SQLite, FastAPI, or React.

## Design constraints

- Domain contracts must not depend on FastAPI, SQLite, Docker, or an OpenAI SDK type.
- The tool gateway is the only module allowed to execute a tool.
- The trace is append-oriented and records blocked attempts as well as successful calls.
- Model adapters return structured decisions rather than raw text so benchmark outcomes are testable.
