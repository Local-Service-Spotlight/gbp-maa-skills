# Publishing (maintainer)

Never push to `/upload/main`. Create the repo, push `main` once, then every change is branch → PR → checks → merge.

```bash
cd gbp-maa-skills
gh repo create Local-Service-Spotlight/gbp-maa-skills --public --description "Google Business Profile MAA skill suite: weekly Maps report + client-view renderer, read-only MCP, Pipedream proxy" --source . --remote origin
git init -b main 2>/dev/null; git add -A
git commit -m "gbp-maa-skills 1.0.0: gbp-maa, gbp-client-view, gbp-mcp, proxy, first-run example"
git tag v1.0.0
git push -u origin main --tags
```

Then, in order:

1. **Branch protection** on `main`: require the `validate` check and one review (CODEOWNERS).
2. **Register in the Task Library** (`Local-Service-Spotlight/task-library`): source pin `Local-Service-Spotlight/gbp-maa-skills@v1.0.0`, two entries (`gbp-maa`, `gbp-client-view`), the same way `google-ads-analyzer` is referenced by pin rather than inlined.
3. **Marketplace PR** to `dennisyu/local-service-spotlight-skills`: add both skills under `skills/`, list them in `lss-everything` and the `client-operations` bundle, bump the manifest, mirror how the GA4 pair landed in PR #27.
4. **Inventory**: in `skill-registry/references/inventory.md` record both as Available after the marketplace merge; Installed/Enabled/Tested only with a receipt from a named account.
5. **State the evidence ladder honestly** when announcing: Available ≠ Installed ≠ Scheduled ≠ Observed.
