# Setting up the data path

Order matters: proxy first, then MCP, then the connector.

1. **Proxy** (`proxy/gbp-proxy-workflow.md`): a Pipedream project, one workflow, one Node step, a `GBP_PROXY_KEY` secret you invent (48+ random chars). Deploy; smoke-test with the three curls in that file. The Google account connected in Pipedream needs manager access on every client profile.
2. **MCP** (`mcp/README.md`): deploy to Cloud Run with `gcloud run deploy --source .`; two Secret Manager secrets (`gbp-proxy-key`, `gbp-mcp-token`); grant the runtime service account `roles/secretmanager.secretAccessor` on both. Verify with `tools/list` and a 401 on a missing token.
3. **Connector**: claude.ai → Settings → Connectors → custom connector, URL `<service>/mcp`, header `Authorization: Bearer <gbp-mcp-token>`. Fresh-chat test: `gbp_list_locations` returns the roster.
4. **Skills**: install this plugin; run `gbp-maa` by hand on one client (First-Run) before scheduling anything.

Pitfalls seen in the first deploy: zsh treats `#` on an interactive line as text, so never paste commands with trailing comments; a `gcloud secrets create` that half-fails leaves a secret with no versions (`gcloud secrets versions list` is the check); the MCP `/healthz` route 404s behind Cloud Run in v1.0.0 (cosmetic).
