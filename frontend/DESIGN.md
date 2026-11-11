# PoisonTrace research-review design system

Approved 2026-11-03. The redesign prioritizes fast repeated experiments for researchers. It replaces the graphite/amber dashboard direction with a restrained green-tinted workspace inspired by technical standards publications. The inspiration supplies palette, typography, density and selected-row treatment; navigation and controls remain conventional web controls.

## Visual system

- Canvas #10191b, surface #182628, raised surface #1e3032, border #3c5253, strong border #65807d.
- Text #e4eeea, supporting text #b3c6bf, subtle text #a1b7b1. Pale green #b7d6be identifies primary actions and selection, with dark #13231a text on filled actions.
- Blue #a1c5df identifies informational evidence, green #a4d9b4 successful states, red #ffb3bb injection success/errors, and amber #edcf92 warnings. Labels always accompany color.
- Use the system sans family. Body 15px, supporting copy 13–14px, section titles 19px, page headings 28px desktop and 24px mobile. Monospace is reserved for raw trace payloads. Data uses tabular numerals where useful.
- Controls have 6px radii and at least 40px height, with 44px navigation/action targets on mobile. Content panels use a 12px radius and one border, without ornamental shadows.
- Keep focus outlines visible. Respect reduced motion. No decorative animation, speculative metrics, eyebrow headings, or controls for unavailable features.

## Navigation and identity

Analyst experiment/scenario routes share one authenticated header and persistent horizontal Sessions, Experiments and Scenarios navigation. The selected route has a thin rule. On mobile navigation remains visible, avoiding hidden keyboard targets. Session selection is navbar-free. Administration has its own authenticated header and role-isolated workspace. Display the actual signed-in identity from explicit props, not browser globals.

## Composition

The experiment workspace uses a full-width configuration section followed by recorded experiments on the left and selected outcome plus ordered trace on the right. At narrow widths the order becomes configuration, recorded experiments, outcome, trace. One primary Run new experiment action starts the current configuration. Batch campaign is a separate execution mode.

Sessions use a saved-configuration list and an inline editor. Drafts become persisted configurations only on Save. Provider and credential belong to the session; scenario and experiment condition are selected in the experiment workspace. Closing a new draft discards it. Deletion requires confirmation.

Scenarios use a full-width library and a bounded structured editor. Administration uses a searchable user directory and adjacent detail editor. Forms stack on narrow screens. Authentication uses a compact, centered form with configured-account guidance and recoverable connection errors.

## Data and states

Keep injection verdict, task outcome, tool-call status and system error distinct. A blocked tool call does not establish injection resistance. Trace is recorded evidence, not a live stream or a measured completion percentage. Selecting a recorded run updates its outcome and trace together.

Distinguish loading, empty, unavailable and rejected states. Empty usable scenarios lead to the scenario library. Scenario save shows pending/success feedback. Preserve backend authorization, invalid-file visibility, credential references and synthetic-data labeling.

## Implementation and verification

The approved tokens and responsive rules are in src/redesign.css, loaded after the existing structural stylesheet. Shared identity is in components/layout/AuthenticatedHeader.jsx; analyst navigation is in components/layout/Sidebar.jsx, retained under its compatibility filename. A future cleanup can consolidate obsolete stylesheet rules without changing this design.

Fourteen desktop/mobile captures under .scratch/ux-review/redesign were independently reviewed with no material visual blockers. Captures use synthetic HTTP responses. Focused browser tests cover draft cancellation, selected-run evidence and visible mobile navigation. Live provider execution, screen-reader testing and 200% zoom remain outside this visual pass.
