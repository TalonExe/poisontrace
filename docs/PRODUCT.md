# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React, Vite, Tailwind CSS and TanStack Router, backed by a Python FastAPI application.

## Users

Researchers and SOC analysts investigating synthetic authentication alerts and evaluating how model-facing tool metadata affects agent decisions. Analyst accounts use the investigation workspace. Superadmin accounts manage users through a separate role boundary.

## Product Purpose

PoisonTrace lets analysts run controlled clean, poisoned, and defended SOC investigations, inspect the ordered trace, and compare benchmark outcomes.

## Positioning

It evaluates observable security-policy violations caused by malicious MCP tool metadata, rather than treating suspicious model text alone as an attack.

## Operating Context

The dashboard is a local research prototype used during experiment setup, execution and saved evidence review. An open-source local edition and a public demonstration with operator-issued accounts and analyst-supplied model-provider keys are accepted distribution requirements. Analyst ownership is implemented; public deployment readiness remains unverified.

## Capabilities and Constraints

- The first workflow is synthetic authentication-alert triage.
- Local authentication and analyst/superadmin authorization are implemented. Public deployment readiness is not established by the prototype login.
- Experiments have clean, poisoned, and defended modes.
- The current evidence-based MCP investigation is read-only. It uses fifteen synthetic cases, real local MCP discovery and evidence reads, and scripted offline, Gemini or OpenAI model adapters.
- Description poisoning and cross-server tool shadowing are the two retained attack families. Malicious cases support both; benign and false-positive cases are clean controls.
- Defended MCP investigations compare discovered definitions with an approved manifest before exposure and invocation. Discovery restrictions and rejected invocations are separate observations.
- Decisions record verdict, P1-P4 priority, canonical close/escalate handling and a separate explanation with returned evidence references.
- Field correctness, explicit attacker-goal achievement, marker influence, evidence-reference validity and policy observations remain separate. Reference membership does not prove every explanation claim.
- The older Metadata experiment produces a recommendation before a simulated gateway permission decision. It retrieves no evidence and executes no external MCP tool. Its historical measurements must not be pooled with newer investigation scores.
- Protected actions require explicit approval if introduced. Current MCP recommendations do not change incident state.
- The primary dashboard action is starting a new experiment.
- Keep the workspace responsive and fast during repeated research tasks.
- Only synthetic incident data may be used. Do not connect production security systems or reuse external account passwords.
- Model-provider keys are distinct from synthetic incident credentials. Keep secrets out of source, scenarios, traces and logs. Provider keys are owner-scoped and encrypted until revocation. Operational backup/revocation recovery and release gates remain required before hosted use.
- Explicit matched groups pin one selected corpus case/version, provider/model, allocated attack, condition schedule and positive repeat count. Dashboard executes groups and retained reruns; Results compares compatible saved outcomes with counts, denominators, unavailable/missing observations and links to each attempt. Historical campaigns remain separate.

## Brand Commitments

Retain the PoisonTrace name and an honest, professional research voice. The research journey separates reusable configurations, experiment setup and saved results. Its approved visual system is documented in frontend/DESIGN.md.

## Evidence on Hand

Synthetic cases, saved decisions, returned evidence, ordered traces and separately versioned measurements are implemented. Current contracts and corpus limitations are recorded in docs/research/CLEAN_MCP_INVESTIGATION.md and docs/research/SYNTHETIC_RESEARCH_CORPUS.md. Offline SDK substitutes and real local MCP tests verify implementation mechanics. Live-provider effectiveness has not been measured. No production customer or deployment claims are available.

## Product Principles

- Make experiment setup immediate.
- Make policy outcomes observable.
- Keep model behavior distinguishable from security impact.
- Prefer fast scanning over decorative density.
- Preserve an honest boundary between synthetic research data and production security operations.
