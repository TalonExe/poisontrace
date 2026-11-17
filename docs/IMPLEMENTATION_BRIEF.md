# PoisonTrace implementation brief

## Product boundary

The first release is a local, containerised benchmark for one SOC authentication-alert triage workflow. It is a research prototype, not a production SOC platform.

Current distribution decision, 2026-11-03: ADR 0003 adds a public demonstration with live models and analyst-supplied API keys alongside the open-source local edition. Public accounts are issued by the operator, keys/history are private, scenarios are curated and read-only, and provider keys remain encrypted until revoked. These are requirements awaiting implementation, not current hosting capabilities. DEPLOYMENT_REVIEW.md lists launch prerequisites. The historical open questions and frontend build notes below predate backend authentication and the redesign; ADRs and current STATUS take precedence.

## Current execution scope, 2026-11-11

Slice one implements matched metadata selection and corrected measurement. In Metadata experiment, the model returns one recommendation before the gateway's simulated permission decision. That workflow executes no external MCP tool and retrieves no evidence. The intended core flow below remains a research commitment, not a description of completed capability. The research objectives have not been revised. See [measurement contract](research/SLICE_ONE_MEASUREMENTS.md).

Ticket #21 adds one clean real-MCP investigation using a scripted offline model, actual alert/evidence/context reads and persisted structured decisions. Tickets #22 and #23 add Gemini and OpenAI evidence continuation with offline SDK-substitute verification. Ticket #24 adds controlled two-server attack mechanics with offline substitutes. Ticket #25 adds the manifest defense with offline implementation verification. No live-provider effectiveness has been measured. New investigation-scoring-v1 records keep field correctness, explicit goals, raw marker availability, reference validation and actual policy observations separate; historical records retain their meanings. The bounded target is SCOPE_REFINEMENT.md, not every historical promise below. See [clean MCP implementation](research/CLEAN_MCP_INVESTIGATION.md). The historical flow and build-order notes below do not expand the accepted read-only scope.

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

## Fifteen-case corpus, ticket #27, 2026-11-12

The bounded corpus is now implemented locally. Five benign activities, five false-positive alerts and five malicious incidents are selectable through the MCP launcher, with deterministic evidence and P1-P4 ground truth. Both retained families are allocated to the five malicious incidents; the other ten are clean controls. The existing explanation field carries detailed recommendations while new handling values are exactly close/escalate under canonical-handling-v2. See research/SYNTHETIC_RESEARCH_CORPUS.md for the rubric, coverage, saved revisions and offline verification. #28 remains the next software slice for matched groups/repeats/comparisons. No live evaluation has occurred.

The subsequent user-authorized payload revision replaces the active v1 descriptions with fixed v2 SOC reconciliation/connector compatibility pretexts grounded in primary MCP poisoning research. It preserves the two families, cases, attacker goals, read-only operations and manifest-only defense. Exact archives and unmeasured effectiveness are documented in research/MCP_PAYLOAD_REVISION_V2.md; no live call or paid comparison is authorized by this revision.

Ticket #28 adds explicit matched investigation groups, repeats, retained reruns and compatible Results comparisons. The immutable plan pins case/evidence/targets, payload, provider/model, prompts/settings, definitions and scoring versions. Dashboard configures execution; Results reports independent condition-specific rates, missing/unavailable values, failures and individual evidence links. Historical campaigns remain separate. See research/MATCHED_RUN_GROUPS.md for contracts and request-bound execution limits.
