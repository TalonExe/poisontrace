# Whole-site UI and UX review

Date: 2026-11-03. Operate mode. Two independent source assessments using Impeccable critique and technical audit guidance. Source detector returned no findings. No numerical visual, contrast, accessibility, or responsive score is assigned without rendered evidence.

## Recommended flow

Analyst: sign in, choose or create a session, configure provider and credential, save and open the session, choose a valid scenario and experiment condition, run, inspect the outcome and ordered trace, select another recorded run or campaign scenario. Scenario management is a supporting branch that returns to the working context. Superadmins sign in to user management, select or create an account, then explicitly edit its name, role or status. Keep the two role destinations separate.

A session is a saved experiment configuration, not a login session. The scenario should be selected once at run time. Results should distinguish marker injection, task completion, tool execution and system error. Do not imply that a blocked tool means the model resisted injection.

## Research basis

- [W3C forms guidance](https://www.w3.org/WAI/tutorials/forms/) supports explicit labels, logical task grouping and corrective feedback.
- [W3C user notifications](https://www.w3.org/WAI/tutorials/forms/notifications/) supports concise success and error feedback with recovery instructions.
- [W3C status messages](https://www.w3.org/WAI/WCAG21/Understanding/status-messages) supports announcing asynchronous progress without moving focus.
- [Nielsen Norman Group system status](https://www.nngroup.com/articles/visibility-system-status/) supports prompt feedback that helps users understand the result of an action.

The following recommendations are applications of those principles to inspected source, not findings from user testing.

## Confirmed findings and disposition

| Priority | Surface and evidence | User impact | Disposition |
| --- | --- | --- | --- |
| P1 | LoginPage advertises fixed demo credentials despite backend-configured accounts | Wrong instructions prevent entry and exclude admin mental model | Fixed role-neutral sign-in copy, account guidance, autocomplete and service-error distinction |
| P1 | App session check has no rejection handler | API outage leaves an indefinite access check | Added connection failure and retry |
| P1 | SessionWorkspace persists new draft before Save | Closing editor leaves unintended saved configurations | Draft remains transient until Save; required name; deletion confirmation |
| P1 | Session row is a keyboard button containing other buttons | Nested keyboard actions conflict | Removed interactive row semantics, retained explicit Open/Edit/Delete |
| P1 | Recorded dashboard run rows have no action | Cannot inspect earlier recorded evidence | Added keyboard-operable selection with loading/error feedback |
| P1 | Dashboard interprets empty scenario response as loading | User cannot recover from an empty usable library | Added distinct loading and actionable empty state |
| P2 | Dashboard menu navigates to sessions | Closed navigation cannot be reopened as expected | Menu now toggles navigation; separate return action retained |
| P2 | Trace title uses latest run while body uses selected run; future-placeholder copy | Evidence identity is misleading | Selected-run title and recorded-trace copy; region semantics replace unsupported dialog claim |
| P2 | Comparison link has no handler | Dead-end control implies unavailable capability | Removed unsupported action |
| P2 | Provider changes retain incompatible credential | Run fails for apparently valid settings | Provider switch clears credential selection |
| P2 | Credential inputs lack accessible names; execution switch has incomplete tabs | Controls are difficult to identify or operate | Added names and pressed-button mode semantics |
| P1 | Sidebar transform hides buttons visually but not from keyboard | Off-screen focus targets | Next layout slice: closed-state semantics, focus return and Escape, plus scenario reopen control |
| P1 | Scenario editor lacks raw malformed-YAML repair | Documented repair task is incomplete | Separate tested repair slice; confirm raw payload contract before implementation |
| P2 | Scenario/admin mutations lack pending guards; admin search races | Duplicate actions and stale directory results | Add pending states and latest-request guard during form redesign |
| P2 | Scenario and dashboard headers differ; dashboard has fixed identity | Conflicting account identity and navigation | Shared authenticated layout in redesign |
| P2 | Forbidden screens lack recovery; credential-load failure looks empty | Dead ends and misleading status | Add role-home recovery and explicit credential retry |
| P2 | Dashboard displays 100% completion and live wording for recorded evidence | Implies measurement/streaming not established by data | Replace with recorded event count during results redesign |

## Visual redesign direction

User explicitly requested a visual redesign after the initial flow review. The current dark graphite identity is evidence, not an approved replacement concept. Do not claim that the functional fixes constitute a complete visual redesign. Pending clarification: guided first-run experience versus repeated-experiment efficiency, and any elements the user wants retained. Develop a coherent navigation, hierarchy, forms and results treatment across all routes after that answer. Use standard task controls, restrained semantic status colors, consistent identity and readable density. Avoid adding dashboards full of decorative metrics.

The concept-seed command ran with no remote challengers because its roll service was unavailable. No replacement world has been implemented or approved. Existing PRODUCT.md has stale marker-success positioning relative to the glossary; this was reported rather than silently rewritten.

## What to preserve

Keep backend role authority, navbar-free sessions, invalid-file visibility, exact-file scenario deletion confirmations, masked credential references, ordered persisted traces and distinct outcome categories. Preserve domain terminology and synthetic-data labeling. No backend behavior change is required for the initial usability fixes.

## Verification limits and remaining work

Node 22 is installed under the NVM installs directory and can run directly without changing the user's global active version. Production build passed after initial fixes. Frontend baseline tests exposed extensionless imports and stale adapter expectations, repaired separately in this working tree. New auth recovery test covers 401 versus unavailable service. Python suite: 76 passed, one existing deprecation warning; source compilation passed. Source detector: no findings. Browser screenshots, desktop/mobile layout, contrast, keyboard focus and complete journey tests remain required before calling the redesign finished.

## Visual proposal for repeated experiments

Seven grounded visual systems considered: research journal data figures, scientific conference proceedings, peer-review annotation, technical standards publications, cartographic reference keys, library catalog organization, and laboratory specimen indexes. These supply typography, palette, density and one visual signature, not novelty controls. The concept seed selected the fourth direction, technical standards publications: compact aligned controls, measured spacing, tinted deep-green surfaces and a selected-run rule shared with trace rows. No remote challengers were available. The concrete code-led preview is .scratch/ux-review/redesign-proposal.html. It uses explicitly illustrative results and does not execute actions. Approval of this direction precedes replacement of DESIGN.md and full-site visual implementation.

Rendered first-pass evidence: browser smoke passed connection recovery and cancelling new-session creation using mocked HTTP responses. Sessions desktop/mobile captures exist in .scratch/ux-review. Desktop inspection confirms excessive unused left margin on navbar-free sessions and small supporting text. Full-site visual validation and real backend journeys remain outstanding.

## Approved redesign implementation, 2026-11-03

The approved review-focused design is applied to login, sessions, experiments, scenario library/create/edit, and user management. DESIGN.md is the current visual authority. Persistent top navigation replaces the drawer on analyst workspaces; navbar-free sessions and isolated administration remain intact. All shared identity now arrives through explicit props. Removed duplicate headers and fixed persona text, obsolete sidebar placeholders, decorative completion percentage, and duplicate scenario selection in session settings. Scenario saving has pending/success feedback; forbidden routes offer a home/sign-out recovery.

Validation: 14 desktop/mobile captures, no page errors or horizontal overflow in the capture run. Independent visual review passed with no material blockers; minor singular labels and mobile list height were corrected. Three focused Playwright tests pass for cancelled drafts, selected evidence and mobile navigation. Capture/test HTTP responses were mocked. Full real-provider journeys, invalid YAML repair, admin search races and broader accessibility checks remain separate work. Existing legacy e2e workspace tests still target the earlier demo authentication and need migration before a full e2e suite claim.
