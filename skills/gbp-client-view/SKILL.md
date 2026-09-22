---
name: gbp-client-view
description: Render a finished GBP MAA (from gbp-maa) into the client-facing one-page executive summary (print-ready PDF + self-contained HTML), following the Local Service Spotlight display standard shared with ga4-client-view: stoplight coloring, a "prepared by" human owner, the client logo, the two standard charts (13-week primary-action trend + actions-by-type bars), an owned "what to do next" checklist, a source-citations footer, and "we" voice. It does NO new analysis; every value is DERIVED from the source MAA, never invented. Runs as the final step after gbp-maa writes the report. Trigger on "render the GBP client view", "make the Maps report pretty", "display version of the GBP MAA", "GBP one-pager for {client}".
author: Daniel Goodrich — Local Service Spotlight
version: 1.0.0
category: client-operations
stage: optimization
definitive_article: GAP
status: needs-work
lane: execution
references:
  - skills/gbp-maa/SKILL.md
  - skills/ga4-client-view/SKILL.md
  - references/page1-schema.md
  - references/style-spec.md
  - references/example-ridgeline.json
---

# GBP Client View

## Executive Summary

This skill turns a finished Google Business Profile report into a single page an owner can read at a glance: the headline action (calls, directions, or website visits, whichever the client's locked config names), a 13-week trend, the split of what people did after finding the profile, anything urgent in red, and an owned list of what happens next. It performs no analysis. Every figure comes from the MAA it was handed, so the one-pager and the full report always agree. It uses the same renderer and the same display standard as `ga4-client-view`, so a client who gets both reports sees one product.

## Inputs

**Access:** read access to the client vault for the dated GBP MAA. No connector needed; this skill never pulls data.
**Files:** the dated MAA (`{client}/MAAs-GBP/{date}.md`); optional `logo` and `prepared_by` photo; `references/page1-schema.md`, `references/style-spec.md`, `references/example-ridgeline.json`; `scripts/`.
**Prerequisite with checked output:** the MAA exists for the period and passed its own QA gate (its internal section shows the lint result).
**Missing-access rule:** no dated MAA → stop and hand off to `gbp-maa`; nothing to render.

## Steps

1. Load the MAA read-only.
2. Derive `page1-spec.json` per Step 2 mapping below.
3. Attach assets with fallbacks.
4. Render with `scripts/render_page1.py`, then `scripts/render_pdf.py`; merge with the MAA PDF if supplied.
5. Verify (Step 5) and deliver as a draft.

## Definition of done

- [ ] Every pill, flag, chart point, and action traces to a line in the MAA (trace list in the delivery note).
- [ ] Right-chart rows sum to the MAA's total actions; four pills equal the MAA's numbers table; chart endpoint equals the latest weekly value.
- [ ] Stoplight correct: every missing/critical item red; spike-inflated numbers amber; no green over a hedge.
- [ ] "We" voice, zero em-dashes, one `start`, at least one `us` and one `client` where supported.
- [ ] Subline `location_id` matches the MAA; per-location clients have one sheet each.
- [ ] Files saved as `{client}_gbp_page1_{date}.html` and `.pdf` and read back; hand-off to the human who sends.

## Example(s)

`references/example-ridgeline.json` and `shared/examples/ridgeline-2026-09/page1.pdf`: derived from the first real run (anonymized).

## Definitive article & links

Definitive article: **GAP** (shared with `gbp-maa`). Renderer and display standard shared with `ga4-client-view`.

## Routing lane and tools

Lane: `execution`. Derivation is mechanical once the MAA exists; a smaller model can do it. Tools: Python (`scripts/`), headless Chromium for the PDF. No connectors.

## Sources and labels

Palette, pill count, chart titles, and section order: house standard (`references/style-spec.md`, Dennis Yu feedback Aug 2026). No external thresholds.

## What this skill does

Takes a completed GBP MAA (from `gbp-maa`, `{client}/MAAs-GBP/{date}.md`) and produces:

1. A self-contained HTML page-1 (`{client}_gbp_page1_{date}.html`).
2. A print-ready Letter PDF (`{client}_gbp_page1_{date}.pdf`).
3. Optionally, a merged full PDF (`{client}_gbp_full_{date}.pdf`) = page 1 + the full MAA, when a MAA PDF is supplied.

Multi-location clients reported `per-location` get one page per location; the renderer accepts a list of specs and emits one sheet each. A `rollup-with-table` client gets one page using the roll-up numbers, with the per-location table left to the MAA pages.

## What this skill does NOT do

- No analysis, no re-weighting, no second-guessing the MAA.
- No edits to the source MAA.
- No metric invention and no severity reclassification (see the Cardinal Rule).
- No trial verdicts. The Maps Visibility Trial report (gbp-maa Phase 8) has its own fixed format and is not a page-1 candidate.

## Where it sits

```
gbp-maa          ->  {client}/MAAs-GBP/{date}.md   (analysis, pages 2+)
                                 |
                                 v  (final step, every run)
gbp-client-view  ->  derives page1-spec JSON from that MAA
                 ->  renders page1 HTML + PDF, optional merged full PDF
```

## THE CARDINAL RULE: derive, don't invent

Every value on page 1 traces to a specific line in the source MAA. If you cannot point to where the MAA says it, leave it out. Never add a metric, never upgrade a hedge into confidence, never invent reassurance, never editorialize a chart title, never reclassify severity. The MAA's hygiene flags and clarity grade drive the stoplight; you translate, you do not re-decide. Machinery stays off the page: no H-flags, tripwires, Clear/Hazy/Opaque, tool names, "impressions_total".

## The display standard

Shared with GA4; full rules in `references/style-spec.md`. Non-negotiables:

1. **Stoplight, always.** Red = critical or missing (unverified profile, a service the client does not take advertised on the profile, an unanswered negative review, a category that is wrong). Amber = watch or needs confirmation (a single-day spike, stale photos or posts, a lag footnote). Green = producing or resolved. Grey = flat only.
2. **Prepared by** the human owner.
3. **Client logo** in the header, styled name as fallback.
4. **Two standard charts, fixed titles:** left "Weekly {primary} · last 13 weeks", right "Actions by type · last 13 weeks". A lag-shortened window keeps the title and explains in the caption.
5. **Owned checklist:** one `start`, at least one `us` and one `client` where the MAA supports it. Owners come from the MAA's tags; never invent one.
6. **Citations footer:** project link, the profile's Maps link (`gbp_url`, from the roster's `maps_uri`), report date, prepared-by.
7. **"We" voice**, no em dashes.

## Step 1 — Load the source MAA (read-only)

Read the latest dated GBP MAA for the client. It is the only source of numbers, findings, and actions. No dated MAA for the period → stop; there is nothing to render.

## Step 2 — Derive the page1-spec JSON

Project the MAA into the contract in `references/page1-schema.md`. The GBP mapping:

| page-1 element | Derived from the MAA |
|---|---|
| `eyebrow` | Fixed: `Maps Performance · Google Business Profile` |
| `subline` | primary category · city, state · `location_id` |
| `pulse` | Section 1, Maps pulse, trimmed to a confident lead in "we" voice |
| `pills` (4) | Fixed set in this order: **{Primary action} · {Secondary action} · {Third action} · Maps views**. For a home-services or professional client: Calls · Website clicks · Directions · Maps views. For a destination client: Directions · Calls · Website clicks · Maps views. Each with the period comparison and a state. When the MAA reports an anomalous day (H15), the Maps views pill is `watch` and its `sub` carries the without-that-day figure. |
| `callout` (optional) | One foregrounded red finding: unverified profile, wrong category, or a service advertised that the client does not take. Omit if the MAA has none. One per page; do not repeat it as a red flag. |
| `left_chart` | The MAA's 13 weekly buckets of the primary action. `last_state:"bad"` only when the MAA reads the latest move as a real decline. |
| `right_chart` | Actions by type this period, from the MAA's numbers table, right annotation = % change. Rows sum to the MAA's total actions. |
| `flags` | Section 5 "what it means" points plus the review paragraph, each routed to a state. Unanswered negatives are red; stale photos/posts amber; review velocity and reply coverage green when healthy. |
| `todo` | Section 6 actions with their owner tags; Section 7 "start here" becomes the `start` item. |
| `citations` | `project_url`, `gbp_url` (Maps link), `date`. |

Fewer real items beat padded ones. A location with an unverified profile (MAA led with "not live on Maps") renders the callout red, pills as the MAA gives them (zeros are shown with a `⚠` delta, never blank), and a single `start` action: get verified.

## Step 3 — Attach assets

`logo`, `prepared_by {name, role, photo}`, `citations.project_url`. All optional with clean fallbacks; note a missing logo, don't block.

## Step 4 — Render

```
python3 scripts/render_page1.py  <page1-spec.json>  <out.html>
python3 scripts/render_pdf.py    <out.html>         <out.pdf>
python3 scripts/merge_full.py    <page1.pdf> <maa.pdf> <full.pdf>   # optional
```

The scripts are the GA4 ones with one addition (a `gbp_url` footer link). Never hand-build the HTML or SVG. `render_pdf.py` uses the pre-installed Chromium; do not run `playwright install`.

## Step 5 — Verify before presenting (required)

1. **Trace-check:** every pill, flag, chart point, and action maps to a line in the MAA. Anything that doesn't is removed.
2. **Stoplight correctness:** every missing/critical item is red; nothing green overclaims a hedge; a spike-inflated number is amber, not green.
3. **Voice:** "we" throughout; zero em dashes.
4. **Sums:** the right chart's rows equal the MAA's total actions; the four pills match the MAA's numbers table.
5. **Chart endpoints** equal the MAA's latest weekly value.
6. **Location identity:** the subline `location_id` matches the MAA's. For per-location clients, one sheet per location, never a merged number.

Draft for review, same as the MAA. Never auto-publish.

## Example

`references/example-ridgeline.json` is a complete spec derived from the first real run (a two-office law firm (anonymized), one office, First-Run mode). Render it to see the target output.

## Connected

- `gbp-maa` produces the MAA this stage renders.
- `ga4-client-view` shares the renderer and the display standard; keep the two in step. A change to the palette, pill count, or chart titles is made in both or neither.
