# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React with Tailwind CSS; one UI component library may be selected if needed.

## Users

SOC analysts investigating synthetic authentication alerts and evaluating how model-facing tool metadata affects agent decisions.

## Product Purpose

PoisonTrace lets analysts run controlled clean, poisoned, and defended SOC investigations, inspect the ordered trace, and compare benchmark outcomes.

## Positioning

It evaluates observable security-policy violations caused by malicious MCP tool metadata, rather than treating suspicious model text alone as an attack.

## Operating Context

The dashboard is a local research prototype used during experiment setup, execution, trace review, and comparison of repeated benchmark runs.

## Capabilities and Constraints

- The first workflow is synthetic authentication-alert triage.
- Experiments have clean, poisoned, and defended modes.
- Protected actions require explicit approval.
- Tool definitions are compared with an approved manifest.
- The primary dashboard action is starting a new experiment.
- The dashboard is dark-first, responsive, and optimized for low interaction delay.
- A future light-mode toggle must be supported by the design system.
- No real credentials, production systems, or non-synthetic data may be connected.

## Brand Commitments

The interface should feel professional, minimal, operational, and trustworthy.

## Evidence on Hand

Synthetic scenarios, experiment results, ordered trace events, and benchmark metrics are implemented in the repository. No production customer, benchmark, or deployment claims are available.

## Product Principles

- Make experiment setup immediate.
- Make policy outcomes observable.
- Keep model behavior distinguishable from security impact.
- Prefer fast scanning over decorative density.
- Preserve an honest boundary between synthetic research data and production security operations.
