# PoisonTrace context

PoisonTrace is a synthetic research prototype for studying how malicious MCP tool metadata affects AI-assisted SOC investigations. It supports an open-source local edition and a hosted demonstration profile under [ADR 0003](adr/0003-public-demonstration-and-local-distribution.md). Public release readiness is not established.

## Workflows

MCP investigations retrieve evidence through two fixed local Python stdio MCP servers before producing a verdict, P1–P4 priority, close/escalate handling and an explanation referencing returned evidence. Fifteen deterministic cases cover benign activity, false-positive alerts and malicious incidents. Scripted offline, Gemini and OpenAI adapters share the evidence loop. Description poisoning and cross-server tool shadowing are the two fixed attack families; manifest comparison is the sole evaluated defense.

Metadata experiments are a separate workflow. A model returns a recommendation and optional proposed call before a simulated gateway permission decision. This workflow retrieves no evidence and executes no external MCP tool. Metadata campaigns retain their own historical selection and measurement meanings.

The analyst dashboard opens after sign-in and summarizes the analyst's own investigation activity by calendar week or month. Configurations prepares reusable settings. Experiment submits single investigations or explicit matched groups. Results reopens saved decisions, evidence, traces and comparisons. Matched groups pin case/evidence/targets, provider/model, payload, prompts/settings, approved definitions and scoring versions. Explicit reruns append attempts under the saved plan.

## Scope and interpretation

Only synthetic data and read-only MCP evidence tools are supported. Recommendations do not change incident state or execute response actions. Ground truth and attacker targets stay outside model inputs and MCP child snapshots. Marker influence, attacker-goal achievement, decision correctness, reference membership and policy observations are independent measurements. Historical records retain their original meanings and unavailable values.

Local authoring remains available; hosted scenarios and ground truth are curated and read-only. Backend authentication supplies ownership for credentials, history, campaigns, groups and jobs. Analyst and superadmin roles remain separate. Legacy ownerless records are quarantined without guessed attribution.

Offline substitutes and real local MCP checks establish implementation mechanics, not live-model effectiveness or production SOC validity. Paid evaluation, provisioning, pilot access and public release each require separate authorization. Research tickets #29–#31 are cancelled.

## Read next

- [Domain glossary](DOMAIN_GLOSSARY.md) defines canonical terms.
- [Architecture](ARCHITECTURE.md) describes current modules and test seams.
- [Status](STATUS.md) records current implementation, verification and remaining work.
- [Research scope](SCOPE_REFINEMENT.md) defines included and excluded research capabilities.
