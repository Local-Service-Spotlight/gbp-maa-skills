---
name: gbp-maa
description: "Produce the weekly Google Business Profile (GBP) report for any local business using the gbp_mcp connector (Pipedream proxy → Cloud Run MCP; no data warehouse). Establishes data trust first (roster check, reporting-lag cutoff, duplicate/closed/unverified screens), picks the vertical's primary action metric, answers the owner questions (are more people finding us on Maps, are they acting, what changed, what to do), and outputs the client-facing report in the Local Service Spotlight format. Also runs the Maps Visibility Trial verdict (trial vs 3x baseline) as a second mode. Trigger on: \"GBP report/MAA for [client]\", \"Maps report\", \"run the GBP agent\", \"how is [client]'s Google Business Profile doing\", \"are we showing up on Maps\", \"trial verdict for [client]\", weekly GBP reporting runs, or any request to analyze a Google Business Profile. GBP only — website behavior belongs to the GA4 agent, paid to Google Ads, organic search terms to GSC."
author: Daniel Goodrich — Local Service Spotlight
version: 1.0.0
category: client-operations
stage: optimization
definitive_article: GAP
status: needs-work
lane: judgment
references:
  - skills/weekly-brand-maa/SKILL.md
  - skills/ga4-website-maa/SKILL.md
  - references/locked-config.md
  - references/tripwires.md
  - references/report-format.md
  - references/scheduled-prompt.md
---

# GBP Report (any local business)

## Executive Summary

This skill produces the weekly Google Business Profile report that goes to a business owner. It reads the profile's live performance through the `gbp_mcp` connector, decides which action counts as the result for that kind of business (calls for a plumber, direction requests for a restaurant, website clicks for a lawyer), and answers the four questions an owner asks about Maps: are more people finding us, are they doing something when they do, what changed since last time, and what should we do about it. Reviews, search terms, and profile hygiene feed the "what to do" answer. The owner gets plain language and real numbers; the checks that make those numbers trustworthy stay internal.

## Inputs

**Access (separate from files):**
- The `gbp_mcp` connector, enabled in the account running this skill, pointed at a deployed `gbp-mcp` (`mcp/`) whose proxy (`proxy/`) uses a Google account with manager access on the client's profile. Read-only: nothing in this chain can post, reply, or edit a profile.
- Read access to the client vault (`{client_vault}/{client}/`) for `locked-config-gbp.md` and the report writeback.

**Files:**
- `locked-config-gbp.md` (Recurring mode). Absent → First-Run.
- `references/locked-config.md`, `references/tripwires.md`, `references/report-format.md`, `references/grading-rubric.md`, `references/scheduled-prompt.md`, all bundled here.

**Prerequisites with checked outputs:**
- `gbp_list_locations` returns the client's `location_id`(s) (checked in Phase 0.3).
- `gbp_get_data_freshness` returns a window whose `end_date` is at least 8 days before today (Phase 0.2).

**Missing-access rule (the only one):** if any of the above is missing, stop, write a one-paragraph hand-off naming which item is missing and which function restores it (analytics for the connector, client success for vault or profile access), and do not produce a report on partial pulls.

## Steps

1. Phase 0: read config, get freshness window (`lag_days: 8`), screen the roster, confirm liveness.
2. Phase 1: the seven-pull Standard Pull; compute the working table in code and assert sums against Google's totals.
3. Phase 2: lock or apply the vertical's primary metric; decompose any ≥ 20% swing (2.6).
4. Phase 3: run hygiene checks H1–H16; grade clarity; Recurring runs pass the tripwire gate (3.5).
5. Phase 4: rule-triggered expansions only.
6. Phase 5–6: write the owner report to `references/report-format.md`.
7. Phase 7: lint, self-grade, write back report and config, deliver as a draft.
8. Phase 8 (Trial mode only): lag guard, windows, verdict, trial report.

The full procedure for each phase is below under "Run modes" onward.

## Definition of done

- [ ] Working table exists with every number re-summed from daily rows; sums equal Google's totals (assertion output pasted in the internal notes).
- [ ] Window used equals `gbp_get_data_freshness` output with `lag_days: 8`; no date after `end_date` appears anywhere.
- [ ] Every claim in the report traces to a working-table row; every number has a comparison.
- [ ] Lint passes: zero banned-vocabulary hits, ≤ 1 em-dash, under 550 prose words, actions in future tense.
- [ ] Self-grade against `references/grading-rubric.md` recorded; one revision on any fail.
- [ ] Report saved to `{client_vault}/{client}/MAAs-GBP/YYYY-MM-DD.md` and read back; config `run_history` appended and `profile_snapshot` replaced.
- [ ] Recurring: tripwire results recorded; any fired tripwire carries the team-review banner.
- [ ] Hand-off named: the receiving task is `gbp-client-view` (render) and, for a fired tripwire, the analytics function (review).

## Example(s)

- `shared/examples/ridgeline-2026-09/`: the first real run (client anonymized), First-Run mode, one office of a two-office personal-injury firm. Contains the owner report, the page-1 spec derived from it, and the rendered one-pager. The run's meta article is `docs/meta/2026-09-21-gbp-agent-stage1.md`.
- Missing: a Recurring-mode example and a Trial-mode example. Both are gaps until a second run and a graded trial exist.

## Definitive article & links

- Definitive article: **GAP**. No canonical recipe article exists yet for this skill; `docs/definitive-article/gbp-maa.md` states what it must contain.
- Meta article: `docs/meta/2026-09-21-gbp-agent-stage1.md` (build and first run).
- Related skills: `gbp-client-view` (render), `ga4-website-maa` (the pattern this mirrors), `weekly-brand-maa` (the MAA discipline).

## Routing lane and tools

- Lane: `judgment`. Analysis, swing decomposition, and hygiene interpretation need the top model; the pulls and arithmetic can run on a smaller model in a subagent.
- Tools: `gbp_mcp` (7 read tools), Python for the working table, the client vault for read/write. No browser, no email, no posting tools.

## Sources and labels

| Threshold or rule | Label |
|---|---|
| Google withholds keyword counts under 15 searches | Google-published (Performance API docs) |
| Impressions post ~8 days later than actions; cutoff 8 days | Observed in the first run (2026-09-21); house rule until contradicted |
| Single-day spike: > 25% of a surface's period total or > 10× median day | House heuristic |
| Stable band: ±10% on a base under 30 | House heuristic |
| Reply coverage target 80%; photo staleness 90 days; post staleness 60 days | House heuristic |
| Trial verdict bands (+5%, −10%, +15%) | House rule carried from the MVS trial workflow, unverified against outcomes |
| Primary metric by vertical | House rule |

## Data path (know this so you never look for a table)

There is no stored GBP data. Every number comes live from Google at run time:

```
claude.ai scheduled task → gbp_mcp (Cloud Run, bearer token) → GBP Proxy - Read Only (Pipedream, holds Google OAuth) → Google APIs
```

Seven tools: `gbp_list_locations`, `gbp_get_data_freshness`, `gbp_get_daily_metrics`, `gbp_get_search_keywords`, `gbp_get_reviews`, `gbp_get_profile`, `gbp_get_media_posts`. All read-only. If a tool errors, the error message names the layer (proxy unreachable, key mismatch, Google 403). Report the layer; do not retry more than twice; never fabricate a number to fill the gap.

State that must persist between runs (the previous profile snapshot, the review count last week, run history) lives in the client's `locked-config-gbp.md`, not in Google. Write it back every run.

## Contract

Same evidence → same flags, same structure. You MUST:

1. Run the fixed sequence Phase 0 → 7 in order. Never skip a phase.
2. Pull the Standard Pull exactly as written (Phase 1). Use the window from `gbp_get_data_freshness` and nothing else; never include the trailing lag days and never use "today".
3. Compute every number in the working table before interpreting. Percent changes, sums, review velocity, and reply coverage are arithmetic you do on pulled rows, never estimates.
4. Trigger expansions only by the decision tables (Phase 4).
5. Pass the QA gate (Phase 7) before delivering.

Hard boundary, stated internally always: GBP measures profile interactions (a tap on Call, a tap on Directions, a click to the website), not answered calls, booked jobs, or revenue. Report interactions and say so. Read-only: every profile fix is written as an action for a human; this skill never edits a profile, replies to a review, or posts.

## Run modes — decide FIRST

| | First-Run (team-operated, gated) | Recurring Re-Run (owner-facing, guarded) |
|---|---|---|
| When | First touch for a location; any run flagged by a tripwire last week; operator forces it | Location has a `locked-config-gbp.md` with `mode_ready: recurring` and a clean prior run |
| Judgment work | Full procedure. Proposes and locks vertical, primary metric, roll-up rule for multi-location clients, exclusions. Seeds the profile snapshot baseline. | Reuses the locked config. Does not re-litigate vertical or primary metric. |
| Gate before delivery | Human review, always | Tripwire gate (`references/tripwires.md`), then deliver. A fired tripwire holds the week for the team. |

No locked config → you are in First-Run. Produce one.

**Trial mode** (Maps Visibility Trial verdict) is a third entry point, always team-gated: see Phase 8.

## Phase 0 — Pre-flight (never skip)

1. **Read the client config** `{client_vault}/{client}/locked-config-gbp.md` (`references/locked-config.md`). It holds the location ID(s), account ID, vertical, primary metric, roll-up rule, previous profile snapshot, and baselines. In First-Run, also read any Narrative and seed the config at writeback.
2. **Freshness window.** Call `gbp_get_data_freshness` with `weeks: 13, lag_days: 8`. The lag lives here, in the skill, not in the server: 8 days because impressions were still posting zero on days 6–8 before today in the first client run while actions had already landed. Record `current_period`, `previous_period`, `last_full_month`. Every later pull uses these dates. If the tool rejects `lag_days` (older server build), compute the same window yourself: end = today − 8, start = end − 90, previous = the 91 days before that. Revisit the value when H16 fires or stops firing two runs in a row.
3. **Roster check.** Call `gbp_list_locations`. Confirm every locked `location_id` is present and its `title` still matches. Then screen the row:

| Condition | Verdict | Action |
|---|---|---|
| Locked location missing from roster | Access lost or profile removed | Stop. Escalate: "our manager access to this profile ended" vs "the profile was removed"; ask which. Never report on a location you cannot read. |
| Title changed vs locked | Rename or wrong profile | Note it; First-Run confirms with human; Recurring escalates (T2). |
| `place_id` null or `maps_uri` null | Unverified or suspended profile | Pull metrics anyway (they may be zero); lead the report with "this profile is not live on Maps"; the one action is verification. |
| Title contains "permanently closed" | Closed | Exclude from the run; note in config. |
| Two roster rows share one `place_id` | Duplicate listing | Escalate on First-Run: metrics may be split or doubled across the pair. Report only once the human names the canonical row. |
| Client has more than one location | Multi-location | Apply the locked `rollup` rule (per-location report, or one roll-up with a per-location table). Never sum locations silently. |

4. **Liveness.** Pull `gbp_get_daily_metrics` for the current period. If total impressions across all four surfaces is 0 for the whole 13 weeks, treat as the unverified/suspended case above, not as "nobody searches for this business."

## Phase 1 — Standard Pull (fixed, every run)

For each locked location, pull exactly these and record every number in a working table before interpreting:

| # | Tool | Args | Purpose |
|---|---|---|---|
| P1 | `gbp_get_daily_metrics` | current_period, all 9 metrics | This period's daily rows and totals |
| P2 | `gbp_get_daily_metrics` | previous_period, all 9 metrics | Comparison basis |
| P3 | `gbp_get_search_keywords` | last_full_month → last_full_month | What people searched. If Google returns no rows (it publishes keywords 2–6 weeks after month end), step back one month and say which month the report covers |
| P4 | `gbp_get_search_keywords` | the month before P3's | Keyword comparison |
| P5 | `gbp_get_reviews` | max_reviews 200 | Rating, count, velocity, reply coverage |
| P6 | `gbp_get_profile` | | Snapshot for hygiene checks and diffing |
| P7 | `gbp_get_media_posts` | | Photo and post recency |

From P1 and P2 compute, per period: `impressions_maps` (desktop + mobile maps), `impressions_search` (desktop + mobile search), `impressions_total`, `actions_total` (calls + website + directions + conversations + bookings), each action individually, `action_rate = actions_total / impressions_total`, and the 13 weekly buckets of the primary metric (P1 rows grouped by ISO week, Monday start). Percent change on every one of these vs P2.

From P5: reviews with `created_at` in the current period vs the previous period (velocity), share of those with `has_reply` (reply coverage), average rating of current-period reviews vs the profile's lifetime `average_rating`, and any 1–2 star review in the current period without a reply.

From P3/P4: top 10 keywords by impressions, brand vs non-brand split (brand = contains any token of the business title), keywords that appeared or disappeared, and the count of below-threshold terms (report as "fewer than N", never as zero). When every term is below threshold, report the term list and count only; do not compute a brand vs non-brand share, since there is nothing to weight it by.

## Phase 2 — Primary metric by vertical (locked on First-Run)

The headline is the vertical's primary action. The locked config wins; the table is the default when there is no lock.

| Vertical | Primary | Secondary | De-emphasize |
|---|---|---|---|
| Home services, trades, urgent repair (HVAC, plumbing, roofing, junk, locksmith) | Calls | Website clicks | Directions (vendors and drivers, not customers) |
| Legal, financial, medical, professional services | Calls | Website clicks | Directions |
| Restaurants, retail, gyms, spas, hotels, destinations | Directions | Calls, bookings | Website clicks |
| Service-area businesses with no storefront (cleaning, landscaping, painting) | Calls | Website clicks | Directions (should be near zero; a spike is a data question) |
| Online-only or corporate profiles (software, agencies with no walk-in) | Website clicks | Calls | Directions |

Rules:
1. Detect the vertical from `primary_category` in the roster and the locked config. If the category is not English or looks wrong (a painter categorized as "Маляр"), it is a hygiene finding for Phase 3, and you still route on what the business plainly is.
2. Conversations and bookings are reported when non-zero and never folded into the headline unless locked as primary.
3. Maps impressions are the visibility number, reported second, always. Search impressions are context.
4. A primary-metric change between −10% and +10% on a base under 30 per period is "stable"; do not narrate noise as a trend.

## Phase 2.6 — Swing decomposition (when the primary moves ≥ 20%, or any surface item)

Never narrate a swing you have not decomposed. Lay current beside previous for: each action type, maps vs search impressions, and the 13 weekly buckets. Name the largest mover. Check whether the move is (a) visibility-led (impressions moved the same direction first), (b) conversion-led (impressions flat, actions moved, so the profile or the offer changed), or (c) a step change on a single week (look for a profile edit, a suspension, a review event, or a Google reporting gap on that week). If P6's snapshot differs from the previous snapshot in the config on the same week, that is the leading candidate. If you cannot identify the driver from pulled data, say so and emit a verification action; never guess a cause.

## Phase 3 — Profile hygiene and data clarity (decision table)

| # | Check | Data | Condition | Flag |
|---|---|---|---|---|
| H1 | Verification | roster | `place_id` null | Not live on Maps |
| H2 | Category | P6 | primary category missing, non-English, or clearly wrong for the business | Wrong category |
| H3 | Hours | P6 | no `regularHours`, or `openInfo.status` not OPEN | Hours gap / marked closed |
| H4 | Website | P6 | `websiteUri` missing, or a bare domain with no UTM when the client runs GA4 | No website / unattributed clicks |
| H5 | Description | P6 | `profile.description` missing or under 250 characters | Thin description |
| H6 | Services | P6 | `serviceItems` empty for a service vertical | No services listed |
| H7 | Photos | P7 | `media.total_count` under 10, or `latest_created_at` older than 90 days | Stale photos |
| H8 | Posts | P7 | no post in 60 days | No posts |
| H9 | Review reply coverage | P5 | under 80% of current-period reviews replied | Unanswered reviews |
| H10 | Negative unanswered | P5 | any 1–2 star review, any age, with `has_reply` false (text-less ones included) | Unanswered negative: list by date and stars, most recent first |
| H11 | Review velocity | P5 | current-period reviews down more than 50% vs previous and previous was ≥ 4 | Reviews stalled |
| H12 | Brand dependence | P3 | non-brand share of keyword impressions under 30% | Found by name only |
| H13 | Reporting gap | P1 | a day in the window where every metric is 0 and neighbors are not | Google reporting gap on <date> (footnote, not a finding) |
| H15 | Single-day spike | P1 | one day carries more than 25% of a surface's period total, or exceeds 10× the median day | Anomalous day on <date>: report the period both with and without it; commit to a check, never a cause |
| H16 | Trailing impression lag | P1 | impressions read 0 on the last 1–3 days of the window while actions are non-zero | Impressions lag longer than actions; footnote the dates, and if it recurs two runs running, raise `GBP_LAG_DAYS` to 8 |
| H14 | Snapshot diff | P6 vs config | category, hours, phone, website, or address changed since last run | Profile edited (name the field) |

Clarity grade for the internal log: Clear (H1, H13, H14 all clean) · Hazy (H13 or H14 fired) · Opaque (H1 fired, or a duplicate `place_id` unresolved). Hygiene flags H2–H12 are actions, not clarity.

## Phase 3.5 — Tripwire gate (Recurring only)

Evaluate `references/tripwires.md`. Any fired tripwire: finish the analysis, write the internal draft, and emit the team-review banner. Do not format as owner-delivered.

## Phase 4 — Conditional expansions (rule-triggered only)

| Trigger | Expansion |
|---|---|
| Primary metric swing ≥ 35% | Pull P3/P4 for two more months back; check whether the keyword mix shifted (brand vs non-brand) in step with the swing |
| Directions spike ≥ 50% on a service-area business | Note as a data question (possible address exposure or category change); check H14 |
| Reviews stalled (H11) and the client has a review-request process on file | Report as fix-progress line, ask whether the process is still running |
| Multi-location client with per-location divergence ≥ 40% on the primary | Add a per-location table and name the leader and laggard |
| First-Run only | Pull P1 for a 26-week window to seed the baseline band |

## Phase 5 — Verification principle

Every interpretive claim in the report points at a pulled number in the working table. "Visibility grew" needs impressions_maps up. "Reviews are driving it" needs a velocity change on the same weeks. A causal connective ("which likely means", "should give us") that bridges a gap the data does not cover is cut or hedged to "we'll confirm".

## Phase 6 — The client report

Structure per `references/report-format.md`. Non-negotiables:

- Machinery stays internal: no H-flags, tripwires, Clear/Hazy/Opaque, tool names, or "MCP".
- Primary action first, in the owner's word (calls, directions, website visits), with the previous-period comparison and percent change. Then Maps visibility. Then the action rate.
- Every number has a comparison. No baseline → not reported.
- Winners and Opportunities: top search terms (what is working), then the hygiene items as opportunities, each as one plain sentence with the expected effect hedged ("should").
- Reviews: count this period vs last, average, and reply coverage, in one paragraph.
- What to do next: 2–3 recommendations, split ✅ our-side (forward commitments only) vs client-side asks. Start here: one move.
- Under 550 words of prose. At most one em-dash.

## Phase 7 — QA gate, then writeback

1. Mechanical lint: banned vocabulary grep (Clear/Hazy/Opaque, tripwire, H1–H14, MCP, proxy, Pipedream, impressions_total); every number has a comparison; sums-to-headline (action types sum to actions_total; the four impression surfaces sum to impressions_total); the weekly band quoted contains every week's value; em-dash count ≤ 1; action bullets are future tense.
2. Self-grade against `references/grading-rubric.md`; one revision on any fail.
3. External grade in a fresh context when the harness allows; record both.
4. Writeback: report → `02-Clients/{client}/MAAs-GBP/YYYY-MM-DD.md`; config: append `run_history` (date, mode, headline, clarity, escalated?), replace `profile_snapshot` with P6 (keep the previous one as `profile_snapshot_prev`), update `review_count_last_seen`; baselines refresh only on a team-reviewed First-Run.
5. Draft only. A human reviews before anything posts or sends.

## Phase 8 — Trial mode (Maps Visibility Trial verdict)

Replaces the old Pipedream workflow 4. Inputs: location_id, vertical, trial_start, trial_end. Always team-gated.

1. **Lag guard.** If `trial_end` is later than the freshness `end_date`, stop and say when the verdict can run (trial_end + lag). Never grade an incomplete trial.
2. **Windows.** Trial = trial_start → trial_end (D days). Baseline = the 3×D days ending the day before trial_start. If the baseline reaches back past 18 months, shorten it and say so; never pad with zeros.
3. **Pull** `gbp_get_daily_metrics` for both windows. Compute trial_total and baseline_avg (= baseline_total / 3) per metric, plus % lift, plus Total Maps Impressions and Total Actions rows. All in code, none in prose.
4. **Verdict** on the vertical's primary from Phase 2: CLEAR WIN primary > +5%; VISIBILITY WIN primary within −10%..+5% and (maps impressions or secondary) > +15%; FAILURE primary < −10% or everything flat; the band 0..+5% with flat maps is "stable, inconclusive", stated as such.
5. **Report** per `references/report-format.md` § Trial. Match on location_id, never on name; two locations means two verdicts unless the human locks a roll-up.
