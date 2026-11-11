# ADR 0001: Scenario library identities and CRUD

## Status

Accepted

## Context

PoisonTrace stores synthetic investigation definitions as YAML files. The existing files use descriptive identifiers embedded in the domain data, while the scenario library needs separate list, create, edit, and delete flows. Invalid files must remain visible so an analyst can repair them, but they must never be runnable.

## Decision

Scenario files use a required human-readable `name` and a quoted three-digit `scenario_id`, starting at `001` and incrementing from the highest existing ID. Canonical filenames use the scenario name slug and ID, such as `authentication-alert-001.yaml`.

The library route is `/scenarios`. Creation uses `/scenarios/new`, and editing uses `/scenarios/:scenarioId`. Existing development fixtures are migrated to numeric IDs and canonical filenames. Legacy traces, campaign records, and browser session configurations may be discarded during this development migration.

The backend owns scenario listing, validation, YAML serialization, atomic writes, and deletion. The frontend does not read or write scenario files directly. Malformed files appear in the library with their error and raw text, can be repaired through the editor, and are excluded from runs and campaigns until valid.

Scenario IDs are immutable in the structured editor. Scenario names can change without changing the scenario ID or existing filename. Discovered tool names and descriptions, and approved tool names and descriptions, are editable scenario test metadata. Renaming a discovered tool does not automatically rename its approved entry; the user must keep the two lists aligned manually when the tool is approved. Approved tools remain a separate ordered list from discovered tools and must refer to declared tools.

## Consequences

The runner must reject invalid scenario files and must not silently substitute another file. The library needs separate valid-scenario and invalid-file states, including an empty usable-scenario state. Scenario creation and updates must reject duplicate IDs and names, and failed writes must leave the original file unchanged.
