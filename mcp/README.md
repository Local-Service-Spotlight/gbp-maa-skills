# gbp-mcp

Read-only Google Business Profile MCP server for the GBP agent. Seven tools, all thin calls to the
Pipedream proxy (`GBP Proxy - Read Only`), which holds the Google OAuth. This server holds only the
proxy key.

| Tool | Purpose |
|---|---|
| `gbp_list_locations` | Roster with account_id, location_id, category, city, website |
| `gbp_get_data_freshness` | Safe date window given the 5-day reporting lag, plus previous period |
| `gbp_get_daily_metrics` | Impressions (4 surfaces), calls, website clicks, directions, conversations, bookings |
| `gbp_get_search_keywords` | Monthly keyword impressions (handles below-threshold terms) |
| `gbp_get_reviews` | Rating, count, recent reviews with reply status |
| `gbp_get_profile` | Current profile snapshot (categories, hours, services, attributes) |
| `gbp_get_media_posts` | Photo counts and recent posts |

## Environment

| Var | Required | Value |
|---|---|---|
| `GBP_PROXY_URL` | yes | `https://YOUR-TRIGGER.m.pipedream.net` |
| `GBP_PROXY_KEY` | yes | same value as the Pipedream `GBP_PROXY_KEY` secret |
| `MCP_BEARER_TOKEN` | recommended | any long random string; clients send `Authorization: Bearer <token>` |
| `GBP_LAG_DAYS` | no | default 5; set to 8 in production (impressions lag ~8 days, actions less) |

## Local test

```bash
pip install -r requirements.txt
GBP_PROXY_URL=... GBP_PROXY_KEY=... python server.py
# in another shell
npx @modelcontextprotocol/inspector   # connect to http://localhost:8080/mcp
```

## Deploy to Cloud Run (same project as the analytics MCP)

```bash
PROJECT=<your-gcp-project-id>
REGION=us-central1
gcloud config set project $PROJECT

# secrets (one-time)
printf '%s' "$GBP_PROXY_KEY" | gcloud secrets create gbp-proxy-key --data-file=-
openssl rand -hex 32 | tee /dev/tty | gcloud secrets create gbp-mcp-token --data-file=-   # save the printed value

gcloud run deploy gbp-mcp \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GBP_PROXY_URL=https://YOUR-TRIGGER.m.pipedream.net,GBP_LAG_DAYS=5 \
  --set-secrets GBP_PROXY_KEY=gbp-proxy-key:latest,MCP_BEARER_TOKEN=gbp-mcp-token:latest \
  --min-instances 0 --max-instances 3 --memory 512Mi --timeout 300
```

`--allow-unauthenticated` is required so claude.ai can reach it; the bearer token is what gates access.
If `gcloud run deploy` reports the runtime service account lacks Secret Manager access, grant
`roles/secretmanager.secretAccessor` to that service account on both secrets.

Endpoint: `https://gbp-mcp-XXXX-uc.a.run.app/mcp`. Health check: `/healthz`.

## Add to claude.ai

Settings > Connectors > Add custom connector: name `GBP`, URL `<service-url>/mcp`,
header `Authorization: Bearer <gbp-mcp-token>`.
