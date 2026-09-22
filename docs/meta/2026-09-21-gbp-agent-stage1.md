# How I built a Google Business Profile agent with no data warehouse

**Execution ID:** gbp-agent-stage1-20260921-214600
**Started:** 2026-09-21 (UTC) · **Status:** completed (stage 1, including first client run) · **Owner:** Daniel Goodrich
**Canonical task:** none yet. This is the first end-to-end run of a new pipeline; no Task Library recipe exists. If it recurs, `definitive-article-writer` should turn the steps below into one.
**Agent receipt:** drafted by Claude (Fable 5.1) in a claude.ai chat, operated by Daniel Goodrich.

## Task summary

We run weekly Metrics → Analysis → Action reports for clients from GA4 and Google Ads through MCP servers on Cloud Run. Google Business Profile was the gap. Google has locked GBP data behind an approval-gated API, so the plan was to route through Pipedream, which already holds an authorized OAuth connection. The first design assumed we needed to store the data in BigQuery. We did not. Stage 1 shipped in one afternoon as a read-only proxy plus a thin MCP server, and the agent now reads 128 locations live.

## Step-by-step

1. **Read the old build.** An earlier project in the same Pipedream workspace already pulled GBP Performance metrics daily into BigQuery for a Maps Visibility Trial. Reading its five workflows through the browser gave us the working API call, the metric names, and the reporting-lag rule (end the window five days before today).
2. **Change the design.** Google keeps about 18 months of daily metrics, monthly search keywords, all reviews, and the current profile state. A 13-week MAA needs none of that stored locally. Dropping the warehouse removed a dispatcher, two MERGE queries, and a date bug.
3. **Build the proxy.** One Pipedream workflow: HTTP trigger with a shared-secret header, one Node step, six read-only ops (`list_locations`, `daily_metrics`, `search_keywords`, `reviews`, `profile`, `media_posts`). Every call is a GET; the op list is a fixed allowlist; location IDs are format-checked. It can't post, reply, or edit even if the key leaks.
4. **Smoke test.** Wrong key → 401. `list_locations` → 128 rows under one manager account. August daily metrics for a two-location painting contractor matched the GBP dashboard's action counts exactly.
5. **Build the MCP.** Python FastMCP, streamable HTTP, stateless, seven tools (the six ops plus `gbp_get_data_freshness`, which bakes in the lag rule and returns aligned current and previous 13-week windows). Holds only the proxy key. Deployed to the same Cloud Run project as the GA4 and Google Ads servers.
6. **Connect and verify.** Added as a custom connector in claude.ai with a bearer token. First agent run returned the roster and freshness window, and flagged data-quality issues on its own: a duplicate `place_id` across two profiles, five profiles with no Maps presence, one permanently closed listing, one non-English category.
7. **Write the skill.** `gbp-maa` mirrors the GA4 skill: First-Run vs Recurring modes, a locked config per client, a Phase 0 roster screen, a fixed Standard Pull, vertical-based primary metric, swing decomposition, 14 hygiene checks, tripwires, a QA gate, and a Trial mode that replaces the old OpenAI-scored workflow.

8. **First client run.** A First-Run report for one location of a two-location personal injury firm, 13 weeks vs the prior 13. Every daily row was re-summed and matched Google's totals. Calls 329 vs 308 (+7%), website clicks 205 vs 236 (−13%), directions flat, all actions 714 vs 729. Maps views read +95%, but 183 of them landed on one day against a normal day of 0–14; without that day the lift is +32%. The report shows both numbers and commits to a check rather than a cause. Reviews: 35 vs 35, all five-star, all replied to, plus four text-less one-star reviews from five months earlier still unanswered. The start-here item: the profile advertises a practice area the firm refers out, and Google had surfaced it for that search in July.

8. **First client run.** A two-office personal-injury firm, one office, First-Run mode, 13 weeks (Jun 18 to Sep 16) against the prior 13. Every daily row re-summed and matched Google's totals. Calls 329 vs 308 (+6.8%), website clicks 205 vs 236 (−13%), directions 180 vs 185, all actions 714 vs 729. Maps views 569 vs 292 (+95%), except that 183 of those views landed on a single day against a normal day of 0 to 14; without that day, +32%. The agent reported both numbers and committed to a check instead of a cause. Reviews 35 vs 35, all five stars, 100% replied. The start-here item came from reading the profile, not the metrics: the description and service list advertised a practice area the firm refers out, and the profile had surfaced for that search in July.

## Critical judgment calls

1. **No warehouse.** The old design stored data because it was built for trial-vs-baseline math over fixed windows. A weekly MAA only needs what Google already keeps. Storage would have added an ingestion job, a freshness problem, and a SQL-injection surface for no analytical gain. The one thing worth persisting, the profile snapshot for change detection, goes in the client's locked config.
2. **Proxy, not Pipedream's hosted MCP.** Pipedream publishes a GBP MCP server, but its tool list is built from the Business Profile management actions (locations, posts, review replies). The Performance API, which is what an MAA runs on, isn't there. A custom proxy reaches every endpoint and stays read-only by construction.
3. **Read-only by construction, not by policy.** The proxy can only issue GETs to an allowlist. That decision means the bearer token on the MCP guards cost, not safety.
4. **The lag rule lives in one tool.** `gbp_get_data_freshness` is the only place the five-day cutoff is defined, so every scheduled run for every client uses the same window and the reports are comparable.
5. **Key by location ID, never by name.** The roster has two profiles each for several clients and three-to-thirteen for franchises. The old trial workflow matched on `LIKE '%name%'` and would have summed them.

## What we learned about GBP reporting lag

We built the pipeline on a five-day lag, taken from the old workflow's comment. The first run showed it is not one number. Search and Maps impressions read zero on the last three days of the window while calls and clicks on those same days were already counted. Actions post within a day or two; impressions trail by more, and monthly search keywords arrive two to six weeks after month end (August's were empty on September 21). Three rules came out of it, all now in the skill: end every window at least five days back and treat trailing zero-impression days as a footnote; if they recur, move the lag to eight days; and when the last full month's keywords are empty, step back a month and say so. A report that does not know this will call a lag a drop.

## What the first run taught the skill

Four edits landed the same day, which is the point of running it before scheduling it:

- **Impressions lag longer than actions.** Search views read zero on the last three days of a window that ended five days before today, while calls kept posting on those days. Google finishes counting actions before impressions. The cutoff moved from 5 to 8 days.
- **A single-day spike needs its own rule.** One day carrying more than a quarter of a period's Maps views is reported with and without that day, and gets a check, never a growth story.
- **Unanswered negatives have no expiry.** Four text-less one-star reviews from five months earlier were still unanswered and sat outside the window, so the period-scoped check missed them. The check now covers any age.
- **Keywords arrive late and small.** Google publishes search terms weeks after month end, and for a small profile every term sits under the 15-search reporting threshold. The skill now steps back a month when the latest is empty and skips the brand-share calculation when there's nothing to weight it by.

## What broke, and the fix

- **Browser automation stalled every few calls.** Running two Claude threads against the same Chrome instance hangs the bridge; calls time out after four minutes. Serializing browser work fixed it. Two "paste the code yourself" fallbacks got us through.
- **Shell comments in pasted commands.** zsh doesn't treat `#` as a comment on an interactive line, so a trailing comment became gcloud arguments and the token secret was never created. Bare commands only.
- **Secret shell without a version.** The first `gcloud secrets create` partially failed, leaving a secret with no versions; deploy reported "not found" after the IAM fix. `gcloud secrets versions list` is the check.
- **Old `business.google.com/n/<id>/insights` URLs 404.** The manager now redirects into a Google-Search-embedded panel; the dashboard check had to go through the locations list.

## Effort and cost

| | Agent | Human |
|---|---|---|
| Time | ~4.5 h wall clock across two chats, much of it waiting on browser timeouts | ~2 h (Pipedream setup, secrets, deploy, dashboard check, first-run review) |
| Cost | UNKNOWN (tokens not measured) | UNKNOWN |

## Capabilities and limitations

Works: live metrics, keywords, reviews, profile, media for any location under the connected manager account. Doesn't yet: multiple Google accounts (stage 2), profile change history older than the last run, GA4 or Ads cross-reads (those agents stay separate). Untested: the MCP `/healthz` route 404s on Cloud Run (cosmetic; the MCP endpoint works).

## Information ingested

Five Pipedream workflows read through the browser (~600 lines of code); one Pipedream docs search; GBP API reference from training; the GA4 MAA skill (1,167 lines) as the pattern. Tokens: UNKNOWN.

## Guidelines compliance

| Guideline | Result |
|---|---|
| Propose first, sign-off before executing | PASS (design proposal, then "Go") |
| Read-only agents; humans send and edit | PASS |
| Secrets never typed by the agent | PASS (Daniel created all keys and secrets) |
| No client data in public write-up | PASS (client named only as "a painting contractor") |
| Meta article written at task close | PASS (this) |
| Ledger record | N/A (class B, no library task) |
| Grade to A- with blog-grader | NEEDS HUMAN (not run in this session) |

## Evidence

- Public: this article; the `gbp-mcp` source and `gbp-maa` skill, to be pushed to `Goodrich-Dev` (URL pending).
- Private: the first-run client report and internal notes (SHA-256 to be recorded on save to the client vault).
- Private (SHA-256 to be recorded on save): `gbp-proxy-workflow.md`, `gbp-mcp.zip`, the smoke-test output.

## Next

Immediate: team review of the first-run draft, seed the firm's locked config, then the first Recurring run. Lock the first client's config after human review of the draft report, schedule its weekly Recurring run, then repeat for the second client. Stage 2: per-client OAuth for locations outside the manager account and a `gbp-client-view` renderer.
