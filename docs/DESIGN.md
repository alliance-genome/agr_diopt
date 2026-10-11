---
name: DIOPT at the Alliance
description: An Alliance-themed ortholog search tool with a search-first entry, a per-method evidence strip, and light and dark themes.
colors:
  accent: "#256a88"
  accent-hover: "#22546c"
  on-accent: "#fff"
  band: "#256a88"
  tint: "#dbeaf3"
  canvas: "#f4f7f9"
  surface: "#fff"
  subtle: "#f7f9fb"
  ink: "#1f2a30"
  muted: "#55636b"
  line: "#d9e1e6"
  field-border: "#7b8a93"
  focus: "#d95f02"
  error: "#a33a2c"
  method-match: "#256a88"
  method-empty: "#7b8a93"
  confidence-high-bg: "#e6f2e4"
  confidence-high-text: "#2f5f34"
  confidence-moderate-bg: "#f8efd9"
  confidence-moderate-text: "#765716"
  confidence-low-bg: "#f8e8e4"
  confidence-low-text: "#8a4336"
  confidence-unknown-bg: "#eef1f3"
  confidence-unknown-text: "#4b5961"
typography:
  headline:
    fontFamily: "Lato, Helvetica, Arial, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
  title:
    fontFamily: "Lato, Helvetica, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
  body:
    fontFamily: "Lato, Helvetica, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 400
  label:
    fontFamily: "Lato, Helvetica, Arial, sans-serif"
    fontSize: ".95rem"
    fontWeight: 700
rounded:
  chip: "3px"
  control: "4px"
  panel: "8px"
spacing:
  gutter: "24px"
  gutter-mobile: "16px"
  card: "24px"
  cell: "10px 14px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.control}"
    padding: "10px 20px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "6px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
  method-cell:
    size: "18px"
    rounded: "{rounded.chip}"
---

# Design System: DIOPT at the Alliance

## Overview

DIOPT is presented as an Alliance of Genome Resources tool. Colors, type and page
structure follow alliancegenome.org (source: `agr_ui/src/_theme.module.scss` and
`src/containers/layout/`). The implementation lives in `web/src/style.css` and the
components under `web/src/components/`.

## Colors

The Alliance primary scale supplies the blues. Alliance primary-500 `#2598c5` is only
3.3:1 against white, so it is not used for text. Every blue that carries text (links, the primary button, the header band, the footer) uses
primary-700 `#256a88`, which passes WCAG AA. Focus uses Alliance accent-700 `#d95f02`;
on the blue band and footer the focus ring switches to white.

Confidence keeps semantic hue with text labels (high green, moderate amber, low red,
unknown gray). Method-strip marks meet 3:1 non-text contrast in both themes.

## Typography

Lato (self-hosted via `@fontsource/lato`, weights 400 and 700) with Helvetica and Arial
fallbacks. Body and table text are 16px; secondary text is never below 14px (0.875rem).

## Header and footer

The header matches the alliancegenome.org structure. A white logo row holds the
full-color Alliance logo (the white logo in dark mode) linking to alliancegenome.org,
"DIOPT" linking to the app root, and the theme toggle. Below it, a blue band holds a
breadcrumb with real links only: "Alliance home › DIOPT". There is no other site
navigation.

The blue footer carries the DRSC credit, the citation, dataset provenance and the
prototype status. On short pages the footer sits at the bottom of the viewport.

## Entrance page

Before a search, the page shows the DIOPT title, one descriptive sentence, and a
centered search card (about 760px wide). The card holds From ⇄ To species, the
identifier box with its count, file import and clear, example links (rut fly→human,
PAX6 human→fly, a three-gene list), and the primary "Find orthologs" button. A disabled
button uses a gray fill with readable text, not a faded blue. Examples fill the form and
focus the identifier box; they do not submit. Citation and "About the scores and
methods" links sit under the card.

## Results

After a search, the card collapses into a summary bar: species pair heading (for
example "Fly → Human orthologs"), the submitted identifiers (first three, then
"+N more"), the pair count, "Edit search", and TSV/JSON exports. "Edit search" reopens
the card with the previous values; the existing results stay visible and are labeled
when inputs change. The results heading receives focus after each search.

A coverage line ("1 of 4 inputs have orthologs · …") and the list of identifiers that
need attention appear only when some input is ambiguous, unmapped or has no orthologs.

Table columns:

- **Ortholog:** symbol with its stable ID below.
- **Score:** stored score over the species pair's maximum (for example 11/13), the bare
  score when no maximum exists, and "—" when no score is supplied.
- **Best match (forward / reverse):** Yes, No, "Yes (adjusted)", or "—" with
  "Not supplied". Values are never inferred.
- **Confidence:** labeled badge.
- **Methods:** one 18px square per method that covers the species pair, under vertical
  method-name headers. A filled square means the method predicts the pair. An outlined
  square means it covers the species pair but does not predict this pair. A dashed
  square means coverage is not recorded for that method. Each square has the method
  name and state as its accessible name and tooltip.

Rows do not expand. Mapping type and gene IDs are in the TSV and JSON exports.
Pagination shows 25 pairs per page, with server time and the dataset ID.

At 760px and below, the method grid is replaced by a "N/M methods" disclosure listing
each method's state, the table scrolls sideways inside its labeled region, and a hint
says so.

## Theme preference

The header toggle switches light and dark mode. The initial theme follows the system
preference and is remembered in `localStorage` (`diopt-theme`), applied before render.
Dark mode uses charcoal surfaces (`#111418` canvas, `#1a1e23` surface), accent
`#8fc0dc`, and band/footer `#1e4050`.

## Do's and Don'ts

### Do:

- Do keep search, comparison and evidence readable at their real data density.
- Do accompany every color with text or an accessible name.
- Do keep visible keyboard focus and the reduced-motion override.
- Do keep horizontal scrolling inside the labeled table region.

### Don't:

- Don't imply scientific certainty through color or decorative statistics.
- Don't reintroduce weighted score; it is no longer used.
- Don't present coverage-unknown methods as "no match".
- Don't add marketing heroes, dead navigation links, or decorative charts.
