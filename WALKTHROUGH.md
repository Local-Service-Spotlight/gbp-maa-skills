# Walkthrough: from nothing to a weekly Maps report

1. **Data path** (one-time): `shared/frameworks/mcp-setup-guide.md`. About 30 minutes including secrets.
2. **First run, by hand**: in a chat with the GBP connector enabled, `Use the gbp-maa skill on {client} {office}.` The skill has no config yet, so it runs First-Run: pulls, computes, screens, writes the owner report and an internal notes section with a proposed `locked-config-gbp.md`.
3. **Review**: a human reads the report against the internal notes. Fix anything, then save the config to the client vault with `mode_ready: recurring`.
4. **Render**: `Render the GBP client view for {client}.` Produces the one-pager HTML and PDF from the MAA; trace-check before it goes anywhere.
5. **Schedule**: create a weekly scheduled task from `skills/gbp-maa/references/scheduled-prompt.md` with the PARAMETERS block filled. Name the skill explicitly; give the run a stable ID and a receipt destination.
6. **Each week**: the run delivers a draft. Clean tripwires → a human sends. A fired tripwire → the banner holds it for team review and the next run is First-Run again.

What good output looks like: `shared/examples/ridgeline-2026-09/` (client report, page-1 spec, rendered one-pager).
