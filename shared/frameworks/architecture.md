# Architecture

```
claude.ai scheduled task ──▶ gbp-mcp (Cloud Run) ──▶ GBP Proxy (Pipedream) ──▶ Google APIs
  runs gbp-maa,               7 read tools,           6 read-only ops,          Performance,
  then gbp-client-view        bearer token,           allowlisted GETs,         Business Info,
                              holds proxy key only    holds Google OAuth        v4 reviews/media
```

- **No storage.** Google keeps ~18 months of daily metrics, monthly keywords, all reviews, and the current profile. A 13-week MAA reads them live. The only persisted state is the client's `locked-config-gbp.md` (profile snapshot, baselines, run history).
- **Read-only by construction.** The proxy only issues GETs to six named endpoints. Tokens guard cost, not safety.
- **Key by `location_id`, never by name.** Multi-location clients are the norm.
- **The lag rule lives in the skill.** `gbp_get_data_freshness` accepts `lag_days`; `gbp-maa` passes 8 (impressions post ~8 days after the fact, actions sooner; observed 2026-09-21).

Why not Pipedream's hosted GBP MCP: its tools cover management actions (posts, review replies, locations), not the Performance API an MAA runs on. The custom proxy reaches every endpoint and is read-only.
