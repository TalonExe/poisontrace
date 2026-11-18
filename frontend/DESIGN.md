---
name: PoisonTrace
description: Research route for synthetic security investigations
colors:
  canvas: "#f8faf4"
  surface: "#ffffff"
  surface-raised: "#ffffff"
  surface-inset: "#f1f4ec"
  border: "#cbd3c2"
  border-strong: "#89977c"
  text: "#272e24"
  text-muted: "#56624e"
  text-subtle: "#606c59"
  primary: "#6c299a"
  primary-strong: "#542078"
  primary-ink: "#ffffff"
  info: "#54328c"
  info-surface: "#f1e9f7"
  success: "#27603f"
  success-surface: "#e7f2e8"
  danger: "#a02e3a"
  danger-surface: "#fbecef"
  warning: "#79500b"
  warning-surface: "#f4edcf"
  focus: "#6c299a"
  rail: "#eaf0de"
  active: "#eadcf4"
typography:
  headline:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "34px"
    lineHeight: 1.25
    fontWeight: 650
    letterSpacing: "-0.025em"
  headline-mobile:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "28px"
    lineHeight: 1.25
    fontWeight: 650
    letterSpacing: "-0.025em"
  title:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "19px"
    lineHeight: 1.35
    fontWeight: 600
    letterSpacing: "-0.015em"
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "15px"
    lineHeight: 1.5
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    lineHeight: 1.5
rounded:
  control: "6px"
  panel: "12px"
  tag: "5px"
spacing:
  compact: "8px"
  field: "12px"
  control: "16px"
  panel-compact: "20px"
  panel: "26px"
  section: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-strong}"
  button-text:
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  input:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "11px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel}"
  navigation-current:
    backgroundColor: "{colors.active}"
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
    padding: "13px 14px"
  tag:
    backgroundColor: "{colors.info-surface}"
    textColor: "{colors.info}"
    rounded: "{rounded.tag}"
    padding: "4px 8px"
---
# Design System: PoisonTrace

## Overview

**Creative North Star: "Research route"**

PoisonTrace uses white working panels, an olive navigation rail and purple markers for the current task. System sans typography supports repeated setup and saved-evidence review. Conventional controls keep configuration, execution and inspection readable.

This record describes the verified frontend. The interface uses CSS and inline graphics and requires no raster illustration. Product claims remain limited to synthetic research. Page composition and task-specific direction belong in the brief under `.impeccable/surfaces/`.

**Key Characteristics:**

- White panels and olive navigation separate work from orientation.
- Purple identifies actions, selection and keyboard focus.
- Labels and independent observations explain results before technical detail.

## Colors

The palette combines pale olive neutrals with purple actions and separate semantic status colors. Frontmatter values are normative.

### Primary

Purple primary identifies launch actions, text actions, active navigation and focus. Its stronger variant supplies primary-button hover. Purple information ink and its pale surface group explanatory notes and selected history records.

### Secondary

Success green, danger red and warning ochre identify observed states. Pair color with text. Availability, failure and historical score meanings remain explicit.

### Neutral

Canvas surrounds white surface and raised-surface panels. Inset backgrounds support raw data. Olive rail separates navigation from work. Pale purple active fill marks the current destination. Text, muted text and subtle text form the hierarchy. Border and strong-border distinguish panel boundaries from input boundaries.

**The Current Task Rule.** Use purple for the active destination and available task actions. A colored tag alone does not establish a successful investigation.

## Typography

The frontmatter system stack is shared by headings and body, including Segoe UI on Windows. There is no separate display face. Raw evidence may use the existing monospace stack; tabular numerals support counts and durations.

Page headings use headline, with headline-mobile at the narrow breakpoint. Section headings use title. Body copy uses body; supporting descriptions and metadata use label or the existing intermediate 14px size. Introductory copy is capped at 68ch where implemented. Run-summary titles use 23px and decision values use 22px.

**The Readable Evidence Rule.** Wrap long IDs and payloads, preserve complete identifiers, and keep technical detail readable when expanded.

## Layout

Desktop navigation occupies a fixed 224px rail. Content offsets by that width and uses fluid horizontal padding, `clamp(24px, 3vw, 52px)`. At 1600px the implemented padding changes to `max(48px, calc((100vw - 1550px) / 2))`. Panels use panel spacing and panel-compact spacing at 1120px and below.

Experiment setup places the form beside a stable run specification. Its desktop ratio is 1.55fr to 1fr, with a 285px minimum summary column and a 26px gap. At 1120px the ratio changes to 1.2fr to 1fr with a 260px summary minimum and 20px gap. The specification sticks 28px from the top. Configurations use list/editor columns and stack at 1120px. Results place independently scrollable history beside inspection.

At 900px and below, the rail becomes visible horizontal wrapping navigation. Results stack, sticky history becomes static, and history caps at 260px. An explicit return control becomes visible. At 650px and below, setup stacks, its summary becomes static, heading typography changes to headline-mobile, and shell padding becomes 18px. Wider mobile layouts use 24px shell padding. Shared controls have a 40px minimum height; mobile navigation uses at least 44px. Setup fields, launch and desktop navigation use 46px targets.

## Elevation & Depth

Working panels are flat, with one border and no ornamental panel or primary-action shadow. Tonal fills separate navigation, selected history, notes and raw payloads. Buttons, links and summaries use a 2px purple focus outline with a 3px offset. The history-filter wrapper uses the same outline and offset on focus-within because its input has no independent outline. The general focus-visible fallback uses a 4px offset. Reduced-motion preferences disable animation, transitions and smooth scrolling.

**The Flat Panel Rule.** Separate working regions with borders, space and tonal fills; retain visible focus independently of depth.

## Shapes

Use control corners for buttons, fields and note blocks; panel corners for working containers; tag corners for status chips and evidence links. Rows and section dividers stay square. Small circular navigation markers identify desktop destinations and disappear in mobile navigation.

## Components

### Buttons

Primary actions use primary ink on purple, strengthen on hover and have no shadow. The run-specification action fills its column and uses 13px 16px padding. Text and secondary actions use purple, with stronger purple on hover. Disabled controls keep their label, reduce opacity and use a not-allowed cursor. Some legacy button classes retain a stronger disabled-opacity override; it is not a new shared token.

### Chips

Informational pills use information ink and the information surface with tag corners. More-specific legacy outcome and campaign selectors still supply semantic success, error and pending fills. Preserve status text and those distinctions.

### Cards / Containers

White bordered panels use panel corners and responsive panel padding. Recent activity is a flat section with a top divider. Selected history rows use the information surface, square row edges and explicit selection state.

The configuration row being edited also uses the information surface with dark text. Keep its existing row shape; selection must not restore a legacy dark background.

### Inputs / Fields

Fields use raised-surface fill, strong borders and control corners. Labels remain visible above fields. Setup fields use 12px padding. History-filter focus belongs to its wrapper; retain that indicator. Errors retain explanatory text and recovery actions. The legacy error border has a hard-coded override; its tint is not a reusable token.

Configuration editors use text ink for input values and provider names, muted ink for supporting notes, and primary ink on the information surface for provider badges. Selected provider options keep dark text on the information surface. Inputs and selects retain the visible focus outline even where legacy editor selectors reset native outlines.

### Navigation

The olive rail holds brand, visible workspace destinations and signed-in controls. The current page has purple text, pale purple fill and a filled circular marker. Hover uses the implemented pale olive fill. At the mobile breakpoint the same destinations stay visible; identity copy condenses and sign-out remains reachable.

The primary destinations are Configurations, Experiment and Results. Experiment opens matched group setup and allows Scripted offline without a saved configuration; Single run opens the secondary MCP launcher. Results in shared navigation opens Groups. Overview explicitly opens the pooled `/results` view, and Runs and Campaigns retain saved history and deep links.

A native Advanced disclosure in shared navigation contains MCP research case authoring, Metadata experiments, Metadata campaigns and Metadata scenarios (YAML). Keep its summary keyboard operable and its actions reachable on mobile. Metadata launch pages identify their scenario workflow; they do not retrieve MCP evidence. `/dashboard/single`, `/dashboard/metadata` and `/dashboard/campaign` retain the selected view through refresh and browser back. Advanced metadata launch pages retain their configuration prerequisites.

Both MCP launchers use one Execution model and credential selector. Choose Scripted offline or a saved configuration, with the actual model and current matching credential label/mask directly below. Show missing or mismatched references as unavailable and disable live launch. Keep the case, schedule and repeats while reloading execution options. The management link opens Configurations in another tab; label that behavior. Saved-group reruns display the pinned model and allow only an appropriate current credential. Retain the native select, shared focus outline and responsive wrapping.

Single run presents one MCP investigation form with a native Condition selector. Use Clean · trusted metadata, Poisoned · attack exposed and Defended · manifest enforced while preserving the HTTP values clean, poisoned and defended. Show attack family and payload only for poisoned/defended. Cases without allocated attacks offer only Clean; switching to one resets the condition to Clean and announces that reset. The launch summary identifies case/version, actual model, selected condition, applicable payload and manifest enforcement before exposure/invocation. Keep metadata simulation in Advanced and the shared execution selector unchanged.

MCP research case authoring opens `/research-cases` without an execution configuration. It reuses the existing structured ground-truth editor and exact target JSON contract. Show case identity/version and immutable allocation, with return navigation to Experiment and a separate YAML library action. Routine single/group setup has no editable ground truth. Returning to Experiment reloads current case versions; a single launch detects a changed catalog version before submitting and asks for review. Existing group version validation and pinned reruns remain authoritative. Keep the same cards, fields and responsive layout.

### Run specification and disclosures

Keep the pending request summary beside setup where width permits. Workflow, input, condition and model describe the actual launch request. Recovery text explains existing launch restrictions. Saved records show the decision before independent measurements. Named native disclosures hold methodology, policy observations, returned evidence and recorded trace. Evidence links reveal the referenced collapsed record and retain a visible target outline. Disclosure summaries remain keyboard operable.

Results leads with execution status, joint correctness, actual versus expected decision fields and attacker-target matching. Keep target matches separate from injection causation. Reference membership only means references occur in returned evidence. Individual policy/marker observations occupy their own section; case/scoring/attack details remain in a native disclosure. Group decisions stay visible while Policy and marker observations, Execution accounting and Measurement definitions and colors expand separately. Preserve visible missing/excluded counts, exclusion reasons, unscheduled conditions and retained-attempt links. Every table keeps a focusable horizontal scroll region. Overview explicitly identifies pooled historical analysis. The overall group indicator and its availability rules are unchanged.

Recorded trace is the sole run-level trace view. Its native disclosure contains every saved event in order, with ordinal, readable event name and complete event JSON. Preserve typed/nested data, line breaks and additional saved fields; wrap long values at mobile widths. There is no second Open full trace rendering. Evidence links and the historical campaign reader remain available. New configuration defaults omit the unused scenario field; previously stored fields are preserved.

## Do's and Don'ts

### Do:

- Do use the shared CSS variables for color and preserve the documented import order.
- Do pair state colors with explicit text and keep independent observations separate.
- Do keep complete result IDs, readable wrapped payloads and visible keyboard focus.
- Do keep navigation visible when the rail changes to its mobile layout.

### Don't:

- Don't introduce decorative raster images or ornamental panel shadows into this system.
- Don't collapse unscored, failed or unavailable observations into a success indicator.
- Don't promote legacy literal colors or class-specific overrides into new shared tokens.

The effective stylesheet order is `styles.css`, `redesign.css`, then `research-route.css`, as imported by `src/main.jsx`. The middle file owns the current `ec` variables; the final file owns route composition and state overrides. Legacy important declarations still apply where specificity wins. This record changes no API, storage, authentication or scoring behavior. The prior dark palette is superseded. Incidental legacy literals, hidden eyebrow treatments and class-specific disabled-opacity differences are not canonized as shared rules.
