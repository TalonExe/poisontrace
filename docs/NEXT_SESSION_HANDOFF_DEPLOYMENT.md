# Next-session handoff: deployment assessment

Prepared 2026-11-18 at the user's request. This is the current task entry point. The user marked research tickets #29, #30 and #31 as not needed. They are closed as not planned with the wontfix label, not completed. Do not resume that research sequence. Cleanup #32-#37 is implemented and verified. Publication targets the existing cleanup/bounded-research-workflow branch, without a merge to main.

## Start here

1. Work in `C:\Users\TalonExe\Documents\FYP-implementation\Project`. Inspect actual branch, HEAD, staged/unstaged diffs and untracked files. Preserve both debug logs and local agent/tool files. Read AGENTS.md and its documents in order, then this handoff, ADRs 0001-0004, docs/DEPLOYMENT_REVIEW.md and the latest cleanup handoff. Actual source takes precedence over old deployment notes and historical next-ticket instructions.
2. Assess the best deployment approach for this application. Establish the intended audience, access model, expected concurrency, operating budget and data-retention needs. Use existing product decisions as context; ask only for deployment choices that remain unresolved. ADR 0003 records a public demonstration with operator-issued accounts, private BYOK/history, curated read-only scenarios and a local open-source edition. Confirm that this remains the desired profile before making a recommendation that depends on it.
3. Audit the current runtime from source. Inspect packaging/runtime dependencies, frontend production build and same-origin/deep-link routing, FastAPI/auth/session behavior, SQLite/YAML/case-override persistence, encrypted provider-key handling interfaces, actual local stdio MCP subprocess requirements, synchronous execution bounds, concurrency/restart behavior, ownership/isolation and public-profile mutation enforcement. Inspect implementation and synthetic tests, not private records or secret values. The November 3 deployment review contains retired module paths and blockers partly changed by later work; verify each claim rather than copying its checklist.
4. Compare practical options such as restricted local/invited access, a single persistent server/container host, and managed frontend/backend hosting. Explain MCP process support, persistent storage, request duration, isolation, backups/restores, secrets, HTTPS, maintenance and costs. Verify current hosting capabilities/prices from official sources when making recommendations. Distinguish existing capabilities from work needed for invited access and for public exposure. Do not equate passing offline tests with production readiness.
5. Produce a source-backed deployment assessment with a recommended topology, alternatives/tradeoffs, concrete gaps, a minimal staged implementation plan, verification/rollback approach and remaining decisions. Link evidence to current files/tests and primary hosting documentation. Update STATUS and this handoff with findings and the next bounded step.

## Authorization and preservation

This next session is assessment/planning, not authorization to deploy or rewrite the application. Do not provision resources, purchase plans/domains, transmit credentials, call live providers, spend credits, rerun user groups, inspect private credential/auth/raw historical databases, merge, deploy, or mutate issues without a further instruction. Use synthetic fixtures, scratch databases and offline substitutes for any checks. Preserve historical records, retained reruns, scores/provenance, credential handling, role enforcement and the existing visual system. Ordinary focused verification remains appropriate; assess first before proposing implementation.

## Latest verification and publication context

Cleanup #37 passed 300 backend tests, 49 frontend tests, 77 mocked browser journeys, nine connected browser/backend/real-local-MCP journeys, production build, compilation and pip check. The existing Starlette/httpx deprecation warning remains. Checks used synthetic data and offline substitutes and do not establish live-model effectiveness or hosted readiness. No application code changed for this handoff. The publication checkpoint contains the accumulated cleanup source, tests and documentation, excluding debug logs, local agent/tool directories, scratch artifacts, credentials and databases. Inspect actual local/remote state at entry; Git CLI networking was unavailable and the GitHub connector is the publication fallback.

## Copyable next-session prompt

```text
Work in C:\Users\TalonExe\Documents\FYP-implementation\Project.

Assess the best way to deploy this application. Read AGENTS.md and docs/NEXT_SESSION_HANDOFF_DEPLOYMENT.md and follow their reading order, source-verification, preservation and authorization boundaries. First inspect actual branch/HEAD/status/diffs/untracked files. Cleanup #32-#37 is complete; #29-#31 were cancelled as not planned at my request. Do not restart them.

Review the current code and synthetic tests, then compare deployment options suited to the actual frontend/backend/storage/local-stdio-MCP runtime. Treat docs/DEPLOYMENT_REVIEW.md as historical and revalidate its claims. Clarify unresolved audience/concurrency/budget decisions, verify current hosting facts from official sources, and recommend a topology with concrete readiness gaps, a minimal staged plan and verification/rollback steps. Preserve ADR 0003's requirements unless I change them.

Assessment only. Do not provision, deploy, purchase, transmit secrets, call live providers, spend credits, inspect private credential/auth/raw historical data, rerun user groups, merge or mutate issues. Preserve debug.log, frontend/debug.log and local agent/tool files. Update STATUS and the deployment handoff with actual findings and the next bounded step.
```
