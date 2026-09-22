# Changelog

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
