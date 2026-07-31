# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`wc5e-bestiary` — a **Foundry VTT v13–v14 compendium module** for the **dnd5e 5.3.3** system,
generated from the community [Warcraft 5e Conversion](https://github.com/WC5E/Warcraft-5e-Conversion)
markdown. There is no runtime JavaScript: the module ships only `module.json`, `assets/`, and
compiled LevelDB packs. Everything else in the repo is build tooling.

Current packs: **monsters** (420 NPC actors), **items** (21), **spells** (99), **journals** (1 guide entry).

## Prerequisite: the upstream source repo

The parsers read the WC5E markdown from a **sibling clone** that is *not* in this repo and is
currently **absent** — `npm run parse` / `npm run spells` will fail until it exists:

```bash
git clone https://github.com/WC5E/Warcraft-5e-Conversion ../Warcraft-5e-Conversion
```

Hard-coded paths inside `../Warcraft-5e-Conversion`:

| Script | Reads |
|---|---|
| `build/parse.py` | `Manual of Monsters, Main File.txt` (finished) and every file in `WIP Manual of Monsters/` |
| `build/extract_spells.py` | `WIP 3.0 Chapters/Chapter 6 Spells.md` (the most complete spell list) |

`parse.py` accepts an alternate main-file path as `argv[1]`; `extract_spells.py` does not.
Because `src/` is committed, you can rebuild the packs (`npm run pack`) and edit the item/journal
builders **without** the upstream clone.

## Commands

```bash
npm install                     # Foundry CLI (only dependency); node_modules/ is not present by default
npm run build                   # full pipeline: parse → actors → items → spells → journal → pack
npm run pack                    # src/**/*.json → packs/** LevelDB (the only step Foundry cares about)
node build/_chk.mjs             # sanity check: extract each pack back out, print doc counts
python3 build/validate_wip.py   # report incomplete/duplicate WIP statblocks (read-only, needs intermediate/)
```

Individual stages: `npm run parse`, `npm run actors`, `npm run items`, `npm run spells`,
`npm run journal`. There is no test suite and no linter — `_chk.mjs` plus loading the module in
Foundry is the verification loop.

**Build-order gotcha:** `npm run build` runs `actors` *before* `spells`, but `spell_embed.py`
indexes `src/spells/*.json` to embed spells onto casters. If you change spell output, run
`npm run spells && npm run actors && npm run pack` (or `npm run build` twice) or the casters will
carry the previous run's spell data.

## Pipeline architecture

Three stages, each writing plain JSON so every step is inspectable:

```
../Warcraft-5e-Conversion/*.txt|md          upstream Homebrewery/GMBinder markdown
  → parse.py / extract_spells.py            → intermediate/*.json   (system-agnostic statblocks)
  → build_actors.py / build_spells.py /     → src/{monsters,items,spells,journals}/*.json
    build_items.py / build_journal.py         (one file per Foundry document, dnd5e 5.3.3 schema)
  → pack.mjs (Foundry CLI compilePack)      → packs/{monsters,items,spells,journals}/  (LevelDB)
```

- **`parse.py`** knows nothing about Foundry. Its job is surviving the source's typesetting:
  blockquote-run statblock detection, `heal_blockquotes()` for author-forgotten `>` markers,
  merging column-split statblocks separated only by layout noise, en-dash normalisation.
- **`build_actors.py`** is the biggest converter (statblock → NPC actor). It imports
  `spell_embed` and `folders`.
- **`build_items.py`** is *hand-transcribed* data from the Heroes Handbook, not machine-parsed —
  edit the Python literals in `build()` to change gear.
- **`pack.mjs`** compiles every folder in its `PACKS` array, `rm -rf`ing the destination first so
  deleted documents don't linger.

### Hard invariants

- **`src/` is generated output, not source.** `build_actors.py`, `build_spells.py`,
  `build_items.py`, and `build_journal.py` each **delete every `*.json`** in their target
  directory before writing. Hand-edits to `src/monsters/*.json` survive only until the next build —
  fix things in the build script instead (see the escape hatches below). The README's
  "edit these, then re-pack" advice is only safe for one-off local tweaks.
- **Document `_id`s are deterministic**: sha1 of a name-derived key rendered into 16 base62 chars
  (`make_id()` in each builder, `folders.fid()` for folders). This keeps ids stable across
  rebuilds so worlds don't lose references. Never randomise them, and don't change the hashed
  key strings for existing documents.
- **Every document needs a `_key`** (`!actors!<id>`, `!items!<id>`, `!actors.items!<actor>.<item>`,
  `!journal.pages!<j>.<p>`, `!folders!<id>`) — the Foundry CLI uses it to route the document.
- **`_stats: {systemId: "dnd5e", systemVersion: "5.3.3"}`** is written on every document and
  `rules: "2014"` on every `source`. Bumping the target dnd5e version means updating these
  literals in all builders plus `module.json` `relationships`.
- **Bump `module.json` `version`** whenever packs change, or Foundry won't pull the update for
  users (see commit `3cc6182`).

### dnd5e conversion conventions in use

- Statblock numbers are reproduced **exactly** rather than recomputed. Attacks use
  `attack.flat: true` with the printed to-hit; save abilities use
  `save.dc = {calculation: "", formula: "<DC>"}` — an *empty* `calculation` is what makes dnd5e
  honour the literal DC (a truthy value like `"flat"` makes it recompute `8+prof+mod`; see
  commit `7d2c0fa`).
- Every trait/action/reaction/legendary becomes a **`feat` item** whose description carries the
  full statblock text, so nothing is lossy even when unautomated. Passive traits get
  `properties: ["trait"]`; actions get an activity (`attack` → `save` → `utility` fallback) so
  they land in the right sheet section. Legendary preamble sets `resources.legact`.
- Saves/skills are expressed as proficiency plus a delta in `bonuses` so the printed total matches.
- Caster monsters (`spell_embed.py`) get `attributes.spellcasting`, `spells.spellN` slots, a
  `bonuses.spell.dc` delta to honour the printed DC, and embedded spell items with the right
  `preparation.mode` (`prepared` / `atwill` / `innate` + per-day `uses`).
- Compendium folders are ordinary documents emitted alongside the content as `_folder-*.json`
  (monsters by creature type, spells by level, items by category); `module.json` `packFolders`
  groups the four packs in the sidebar.

### Escape hatches for bad conversions

Rather than patching `src/`, add to the small curated tables:

- `spell_embed.ALIAS` — upstream spell-name typos/variants → canonical name.
- `build_spells.OVERRIDES` — spells whose mechanics `auto_detect()` can't infer (keyed by
  lowercase name).
- `build_spells.DTYPE_ALIAS` — Warcraft flavour damage words (`frost`, `shadow`, `arcane`,
  `holy`, `nature`) → 5e damage types.
- `build_actors.TYPE_FOLDER`, `CONDITION_STEMS`, `SIZE_MAP` — creature-type/condition mapping.

`build_actors.py` prints a spellcasting report at the end (embedded count + unresolved spell
names by frequency) and `build_spells.py` prints the activity-kind histogram — use these to spot
regressions after a parser change.

## Licensing constraint (affects design, not just credits)

Only **WC5E community content** and **SRD 5.1** (CC-BY-4.0, as shipped with the dnd5e system) may
be bundled. Non-SRD spells (Tasha's/Xanathar's-era, ~23% of monster spell references) must stay
as plain text in the Spellcasting trait and never be reproduced as items. `build/data/srd_spells_2014.json`
is the SRD index used for embedding. See `LICENSE.md` — build scripts are MIT, content is not.

## Planned work (roadmap in README.md and the in-module journal)

Backgrounds, races, classes & subclasses, feats, per-monster token art, and wiring the remaining
non-SRD spells. Races/classes need dnd5e **advancement** configuration and are being done manually.

Adding a new pack requires five coordinated edits:
1. `module.json` → `packs[]` entry (+ add the name to `packFolders[0].packs`)
2. `build/pack.mjs` → add the name to `PACKS`
3. `build/build_<thing>.py` → emit `src/<name>/*.json` (deterministic ids, `_key`, `_stats`, folders)
4. `package.json` → a script for it, wired into `build`
5. `README.md` + `build/build_journal.py` roadmap/contents text, and bump `module.json` version
