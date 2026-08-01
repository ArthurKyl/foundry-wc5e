# Cutting a release


`manifest` points at `releases/latest/download/module.json` (so Foundry can always find the newest
manifest) while `download` points at a specific tag's asset. Both URLs only resolve once the
release exists and has **both** files attached — `module.json` must be uploaded as its own asset,
not just committed.

```bash
# 1. bump module.json "version" AND the version inside "download"  (release.mjs checks this)
# 2. rebuild + repack if content changed, then commit everything
npm run release                              # -> dist/module.zip + dist/module.json
gh release create v<version> dist/module.zip dist/module.json --title "v<version>" --notes "..."
```

`release.mjs` builds the zip with `git archive` from `HEAD`, so it can only ever contain committed
content, and it aborts on a dirty tree, a version/URL mismatch, or a pack with no compiled `.ldb`.
The zip holds `module.json`, `packs/`, `assets/`, `LICENSE.md`, `README.md` at the archive root —
no wrapper directory, which is what Foundry's installer expects. `dist/` is gitignored.

# If this repo is no longer `ArthurKyl/foundry-wc5e`


As of v1.17.0 the plan is for the WC5E team (Folji) to take the module over — either by forking
this repo or by moving the content into a WC5E-owned one — and for this repo to be stood down.
**Check `git remote -v` first.** If the origin is not `ArthurKyl/foundry-wc5e`, the handover has
happened and the three things below are outstanding. None of them fails loudly.

**1. Seven URLs in `module.json` still point at the old repo:** `url`, `manifest`, `download`,
`bugs`, `readme`, `changelog`, `license`. `release.mjs` only checks that `download` matches
`version` and that `manifest` is the `releases/latest` form — it cannot tell whose repo they name,
so the other five just become dead links in Foundry's module list.

**2. Renaming the module `id` is a migration, not a rename.** The id `wc5e-bestiary` is currently
load-bearing in 1,157 internal `Compendium.wc5e-bestiary.*` UUIDs and 875 `modules/wc5e-bestiary/…`
asset paths across `src/`, plus 22 references in `scripts/` and `build/`. Changing it means
rewriting all of those, and even then **every existing world breaks**: actors dragged out carry
`_stats.compendiumSource` pointing at the old id (which is how the auto-assign tool finds
world-side monsters), and any `@UUID[…]` a user wrote into their own content dangles. A broken
`ItemGrant` is a silent no-op on level-up, not an error, so this fails invisibly. If a better id is
wanted, treat it as a deliberate migration with a version bump and release notes — never as
tidying.

**3. Do not make the old repo private — archive it (public, read-only).** Every install of v1.16.0
and v1.17.0 has `manifest` pointing at
`github.com/ArthurKyl/foundry-wc5e/releases/latest/download/module.json`. Private makes that 404:
existing users get no update notification and cannot reinstall, with no way to tell them why. An
archived public repo keeps serving releases, so a final release there can point `manifest` at the
new home and carry users across.
