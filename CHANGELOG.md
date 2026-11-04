# Changelog

## 1.0.2, 2026-11-04

Maintenance release. The `mcp/` changes take effect only when someone with Cloud Run rights redeploys `gbp-mcp`; this release deploys nothing.

- `gbp-maa`: reporting lag moved from 8 to 10 days (`lag_days: 10` in Phase 0, the QA checklist, Inputs and step 2; the hand-computed fallback is now end = today − 10). Daniel's 2026-09-24/25 check found Google posts impressions about 10 days late. H16 now says raise `lag_days` above 10. The skill's frontmatter version is 1.0.2.
- `gbp-maa` scheduled-prompt template: the Target Painting example points at `accounts/target-painting` in google-ads-maa-vault instead of the BlitzBase `02-Clients/` paths, `owner` is `<account lead>`, and the rules line passes `lag_days 10`. `deliver_to` stays `draft`.
- `mcp/server.py`: the health check answers on `/health` as well as `/healthz` (Cloud Run reserves paths ending in `z`, so `/healthz` never reached the container). The bearer token is compared with `hmac.compare_digest`. The server now fails closed: with `MCP_BEARER_TOKEN` unset, every non-health path returns 503 `server not configured` instead of skipping auth. The `lag_days` description says 10.
- `mcp/test_auth.py`: offline unittest checks for the health paths, fail-closed, and token comparison.
- `mcp/README.md`, `README.md`, `shared/frameworks/architecture.md`: health path, fail-closed note, and the 10-day lag.
- `CODEOWNERS`: `@Goodrich-Dev` removed; `@dennisyu` is the sole code owner.

## 1.0.1, 2026-09-22

Task Library conformance: frontmatter `category` set to the canonical `Strategy & Measurement`, `stage` to `—`, `definitive_article` to `GAP — to be written`; added the `**Use this when**` line and the `(QA checklist)` heading the validator requires. No procedure changes.

## 1.0.0, 2026-09-22

First release. Built and first-run on 2026-09-21 (see `docs/meta/2026-09-21-gbp-agent-stage1.md`).

- `gbp-maa`: weekly GBP MAA, First-Run/Recurring modes, locked config, roster screen, seven-pull standard, vertical primary metric, swing decomposition, hygiene checks H1–H16, tripwires T1–T7, QA gate, Trial mode. House-format sections (Inputs, Steps, Definition of done, Example(s), Definitive article & links, Routing lane and tools, Sources and labels) per the Task Library review standard of 2026-09-15.
- `gbp-client-view`: one-page renderer sharing the `ga4-client-view` renderer and display standard; GBP pill set and chart titles.
- `mcp/`: read-only FastMCP server for Cloud Run, seven tools, `lag_days` parameter on freshness.
- `proxy/`: Pipedream read-only proxy, six ops, allowlisted, key-gated.
- Rules learned from the first run and applied same day: 8-day lag cutoff, single-day spike rule (H15), trailing-lag footnote (H16), unanswered negatives of any age (H10), keyword month fallback, `services_not_offered` in the locked config.

Evidence state at release: `gbp-maa` Tested (one fresh-chat First-Run), `gbp-client-view` Tested (rendered from that run). Neither Scheduled nor Observed. Definitive article: GAP.
