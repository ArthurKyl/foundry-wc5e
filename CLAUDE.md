# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`wc5e-bestiary` — a **Foundry VTT v13–v14 compendium module** for the **dnd5e 5.3.3** system,
generated from the community [Warcraft 5e Conversion](https://github.com/WC5E/Warcraft-5e-Conversion)
markdown. There is no runtime JavaScript: the module ships only `module.json`, `assets/`, and
compiled LevelDB packs. Everything else in the repo is build tooling.

Current packs (12, 1232 documents): **monsters** (420 NPC actors), **spells** (101), **items** (21),
**journals** (guide), **spell-lists** (7 class spell lists), **backgrounds** (4 + their features),
and the player options merged from GoC45's `wc5e-ccc`: **classes** (12 + 36 subclasses),
**class-features** (443), **races** (28 + racials), **feats** (18), **new-equipment** (14),
**summons** (24 actors).

## Prerequisite: the upstream source repo

The parsers read the WC5E markdown from a **sibling clone** that is not part of this repo. If it's
missing, `npm run parse` / `npm run spells` / `npm run spell-lists` fail:

```bash
git clone https://github.com/WC5E/Warcraft-5e-Conversion ../Warcraft-5e-Conversion
```

Hard-coded paths inside `../Warcraft-5e-Conversion`:

| Script | Reads |
|---|---|
| `build/parse.py` | `Manual of Monsters, Main File.txt` (finished) and every file in `WIP Manual of Monsters/` |
| `build/extract_spells.py` | `WIP 3.0 Chapters/Chapter 6 Spells.md` (the most complete spell list) |
| `build/build_spell_lists.py` | the same Chapter 6 file, for the per-class spell tables |
| `build/build_backgrounds.py` | `Heroes Handbook, Main File.txt` (`## New Backgrounds`, chapter 3) |

`parse.py` accepts an alternate main-file path as `argv[1]`; `extract_spells.py` does not.
Because `src/` is committed, you can rebuild the packs (`npm run pack`) and edit the item/journal
builders **without** the upstream clone.

## Commands

```bash
npm install                     # Foundry CLI (only dependency); node_modules/ is not present by default
npm run build                   # parse → spells → actors → items → journal → spell-lists
                                #   → backgrounds → pack
npm run pack                    # src/**/*.json → packs/** LevelDB (the only step Foundry cares about)
node build/_chk.mjs             # sanity check: extract each pack back out, print doc counts
python3 build/validate_wip.py   # report incomplete/duplicate WIP statblocks (read-only, needs intermediate/)
```

Individual stages: `npm run parse`, `npm run spells`, `npm run actors`, `npm run items`,
`npm run journal`, `npm run spell-lists`, `npm run backgrounds`. There is no test suite and no
linter — `_chk.mjs` plus loading the module in Foundry is the verification loop.

**`spells` must run before `actors` and before `spell-lists`** — both read `src/spells/*.json`:
`spell_embed.py` to embed spells onto casters, `build_spell_lists.py` to resolve spell names to
document ids. Running either first bakes in the *previous* run's spell data, and since spell ids
derive from spell *names*, a renamed spell silently breaks both. The `build` script orders them
correctly; keep it that way if you add stages. `items` and `journal` have no dependencies.
Rebuilding is deterministic: identical inputs produce byte-identical output, so `git status` after
a rebuild is a real regression check.

**A failed build is destructive.** Every builder deletes its whole output directory *before*
writing, so a crash mid-build leaves `src/<pack>/` gutted (this is how the v1.4.0 folder-document
regression wiped 433 actor files). Commit before rebuilding; `git checkout -- src/` is the recovery.

## Pipeline architecture

Three stages, each writing plain JSON so every step is inspectable:

```
../Warcraft-5e-Conversion/*.txt|md          upstream Homebrewery/GMBinder markdown
  → parse.py / extract_spells.py            → intermediate/*.json   (system-agnostic statblocks)
  → build_actors.py / build_spells.py /     → src/<pack>/*.json
    build_items.py / build_journal.py /       (one file per Foundry document, dnd5e 5.3.3 schema)
    build_spell_lists.py / build_backgrounds.py
  → pack.mjs (Foundry CLI compilePack)      → packs/<pack>/  (LevelDB)
```

The six player-option directories bypass this entirely — they are hand-maintained, not generated.

- **`parse.py`** knows nothing about Foundry. Its job is surviving the source's typesetting:
  blockquote-run statblock detection, `heal_blockquotes()` for author-forgotten `>` markers,
  merging column-split statblocks separated only by layout noise, en-dash normalisation.
- **`build_actors.py`** is the biggest converter (statblock → NPC actor). It imports
  `spell_embed` and `folders`.
- **`build_items.py`** is *hand-transcribed* data from the Heroes Handbook, not machine-parsed —
  edit the Python literals in `build()` to change gear.
- **`pack.mjs`** compiles every pack declared in `module.json`, `rm -rf`ing the destination first
  so deleted documents don't linger. It warns about a declared pack with no `src/` directory.

### Hard invariants

- **`src/` holds two different kinds of content — know which you're touching.**
  - *Generated* (`src/monsters`, `src/spells`, `src/items`, `src/journals`): `build_actors.py`,
    `build_spells.py`, `build_items.py` and `build_journal.py` each **delete every `*.json`** in
    their target directory before writing. Hand-edits survive only until the next build — fix
    things in the build script instead (see the escape hatches below).
  - *Hand-maintained* (`src/classes`, `src/class-features`, `src/races`, `src/feats`,
    `src/new-equipment`, `src/summons`): 649 documents merged from GoC45's `wc5e-ccc` module,
    with dnd5e advancement configured. **No generator produces these** — they are the source of
    truth and must be edited directly. Never add a "clean `src/`" step; keep every builder scoped
    to its own subdirectory.
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
- **`download` must be version-pinned to a release asset**, never a branch. It previously pointed
  at `archive/refs/heads/main.zip`, which made version numbers meaningless — every installer got
  whatever `main` happened to be, regardless of the version in the manifest. `release.mjs` refuses
  to build if `download` doesn't end with `/releases/download/v<version>/module.zip`.

## Cutting a release

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
- `build/data/extra_spells.json` — spells that appear in the WC5E spell *tables* but never get a
  definition block in Chapter 6, so `extract_spells.py` cannot produce them even though class
  features reference them (currently *Anti-Magic Shell* and *Feral Spirits*, transcribed by
  GoC45). Records use the same intermediate shape and go through `auto_detect()` like any other
  spell. If upstream ever defines one properly, the extracted version wins and the extra is
  skipped with a log line.
- `build_spells.DTYPE_ALIAS` — Warcraft flavour damage words (`frost`, `shadow`, `arcane`,
  `holy`, `nature`) → 5e damage types.
- `build_actors.TYPE_FOLDER`, `CONDITION_STEMS`, `SIZE_MAP` — creature-type/condition mapping.

`build_actors.py` prints a spellcasting report at the end (embedded count + unresolved spell
names by frequency) and `build_spells.py` prints the activity-kind histogram — use these to spot
regressions after a parser change.

## Backgrounds

`build_backgrounds.py` reads `## New Backgrounds` from `Heroes Handbook, Main File.txt` (chapter 3)
and emits, per background, a `background` item plus a separate `feat` for its feature, into
`src/backgrounds/`. Only 4 exist upstream.

A dnd5e background drives the sheet entirely through `system.advancement`: a `Trait` with
`grants: ["skills:dec", …]` for fixed proficiencies, a `Trait` with
`choices: [{count: n, pool: ["languages:*"]}]` for "one of your choice", and an `ItemGrant` titled
`Feature` pointing at the feature item. Trait keys verified against dnd5e 5.3.3: `skills:<abbr>`,
`languages:*`, flat kit ids like `tool:forg`, and namespaced `tool:art:*` / `tool:music:*`.

- `startingEquipment` is intentionally left `[]`. dnd5e wants typed AND/OR groups referencing item
  UUIDs, and a malformed one breaks the background sheet, so the equipment line stays verbatim in
  the description. Wiring it properly is a possible follow-up.
- `DEHYPHEN` fixes hyphenation baked into the source prose (`organi-zation`). It's mid-sentence,
  not at line ends, so joining lines can't undo it, and blanket de-hyphenation would destroy real
  compounds like *self-mastery*. Anything hyphenated that isn't in `DEHYPHEN` or
  `LEGITIMATE_HYPHENS` is reported at the end of the build rather than shipped silently.

## Class spell lists

`build_spell_lists.py` produces `src/spell-lists/` — one dnd5e `spells`-type
JournalEntryPage per casting class. This is the *only* mechanism by which dnd5e knows which
spells a class may learn: `system.identifier` on the page must equal the class document's
`system.identifier` (`wc5e-mage`, …), and class features reference it as
`restriction.list: ["class:<identifier>"]`. Without these pages a custom class has no spell
list and spell selection silently does nothing.

**Registering them in the manifest is mandatory and easy to miss.** dnd5e discovers spell lists
*only* from `flags.dnd5e.spellLists` in `module.json` — `registerSpellLists()` returns immediately
unless that key is an array, and `SpellListRegistry.register()` resolves each entry with
`fromUuid()` and throws unless `page.type === "spells"`. The UUIDs must be **JournalEntryPage**
UUIDs (`Compendium.wc5e-bestiary.spell-lists.JournalEntry.<jid>.JournalEntryPage.<pid>`).
Without the flag the pages sit inert: the compendium browser can't filter by class, and any
advancement restricted to `class:<identifier>` resolves to an empty pool — which is exactly how
v1.7.0/v1.8.0 shipped. `build_spell_lists.register_in_manifest()` writes the flag from the built
pages so the UUIDs cannot drift; never hand-edit it.

Source is `WIP 3.0 Chapters/Chapter 6 Spells.md` upstream, where each caster has a
`### <Class> Spells` section subdivided by `##### Nth Level`. Entry markup carries the
provenance that decides which pack to cite: `✦` = a WC5E custom spell (this module),
`^XGE^`/`^TCE^` = non-SRD official content (omitted, and named in the page description so the
gap is visible), bare = SRD. Blockquoted `> ##### Variant Rule:` blocks are optional
alternate lists and are skipped deliberately.

- `build/data/srd51_spell_ids.json` / `srd52_spell_ids.json` — committed name→id indexes for
  the dnd5e system's two SRD spell packs, so the build doesn't need a Foundry install to cite
  them. Regenerate by extracting `systems/dnd5e/packs/{spells,spells24}` if dnd5e reshuffles ids.
- `build_spell_lists.EXTRA_ENTRIES` — spells this module ships that the Chapter 6 tables never
  list (currently *Feral Spirits*, Heroes-Handbook-only). Without it they'd be unreachable:
  present in the compendium but on no class's list. The build asserts nothing silently: check
  that all of `src/spells` is cited by at least one list after changing spell names.
- Long names wrap in the source using `&nbsp;`/soft hyphens ("Amplify or &nbsp;&nbsp; Dampen
  Magic"); `clean_entry()` strips them, and forgetting that makes real spells look unavailable.

## Spell progression (the one generator that edits hand-maintained files)

`build_spell_progression.py` reads the Cantrips Known / Spells Known columns from the upstream
class tables and writes `ItemChoice` advancements into `src/classes/*.json`, so levelling up
actually prompts for spells. dnd5e has no built-in prompt — its own SRD casters expect you to add
spells from the spellbook by hand, and guided builders hardcode the progression per SRD class, so
custom classes get skipped. `ItemChoice` is the supported mechanism, so this is data-driven.

**It is the only generator that modifies hand-maintained documents**, so it is deliberately
surgical: each advancement's `_id` is `make_id("spellprog", class, kind, level)`, and every run
removes that entire candidate id set (all kinds × levels 1–20) before re-inserting. Hand-authored
advancement is never touched, and re-running cannot duplicate. Verify with an id-uniqueness
assertion after changing it.

Table sources, best first: `WIP 3.0 Classes/<Class>` (extensionless for some classes) then the
Heroes Handbook section. A candidate that yields no column must **fall through**, not end the
search — `Warlock.md` carries the prose but contains no markdown tables at all, so the Warlock
table only comes from the Heroes Handbook.

`SPELLBOOK` covers casters whose learning rule is in **prose, not a table column**: the Mage is a
spellbook caster ("a spellbook containing six 1st-level mage spells", "each time you gain a mage
level, you add two"), so it gets 6 at level 1 and 2 at every level after. Priest and Druid
deliberately get nothing beyond cantrips — they prepare from the *entire* class list, so there is no
learning step to prompt for. Only `kind == "spell"` (known casters) sets `replacement: true`;
cantrips are fixed and a spellbook is only added to.

Known-good output: Death Knight 10 spell picks (L2,3,5,7,9,11,13,15,17,19); Druid/Mage/Priest 3
cantrip picks; Shaman 3 cantrip + 16 spell; Warlock 3 cantrip + 14 spell. **Paladin generates
nothing on purpose** — it has no Known column in either source, being a prepared half-caster whose
only cantrips come from the Blessed Fighter fighting style. Cantrip choices use
`restriction.level: "0"`; spell choices use `"available"` (any level the character has slots for),
and only spells get `replacement: true`.

## Advancement levels on non-class items

`AdvancementManager.forNewItem` creates flows for **every level from 0 to the current level** for
anything that isn't a class — so an `ItemChoice` on a feature, race or background should key its
`configuration.choices` at **`"1"`**, which then fires no matter what class level the item was
granted at. Keying it at the class level (e.g. `"2"` for a level-2 fighting style) works only for a
character who took it at exactly that level. `ItemChoiceAdvancement.configuredForLevel` treats any
level absent from `choices` as already satisfied, so a wrong key fails **silently** — no error, no
prompt. The races use `"1"`; match them.

Features that grant spells from *another* class's list (the `Profane Warrior` and `Blessed Fighter`
fighting styles) need an explicit `ItemChoice` with
`restriction: {type: "spell", level: "0", list: ["class:wc5e-warlock"]}`, because the sheet would
otherwise only offer the character's own class list. The main `Spellcasting` features do **not**
need one — dnd5e's own SRD casters have no cantrip `ItemChoice` either; players add cantrips from
the spellbook browser, which works once the lists are registered.

## Cross-document references (the fragile part of the merged content)

The player-options documents contain **1,045 internal `Compendium.wc5e-bestiary.*` UUIDs** —
advancement `ItemGrant`/`ItemChoice` targets, `effects.origin`, `startingEquipment.key`, and
`@UUID[…]` links in description text — plus 387 references into the dnd5e system's own packs and
864 asset paths. These came from GoC45's module as `Compendium.wc5e-ccc.*` and were rewritten
during the merge.

**Consequences:** renaming a pack, changing the module id, or regenerating a document id breaks
advancement silently — a broken `ItemGrant` is a no-op on level-up, not an error. So pack names
(`class-features`, `new-equipment`, …) are load-bearing and must not be "tidied", and the spell
ids that class features point at are derived from spell *names* via `make_id("spell", name)` —
renaming a spell in the source breaks any feature granting it.

After touching any of this, re-run the integrity check: index every `_id` per pack, then confirm
every internal UUID resolves, no `wc5e-ccc` strings survive, and every `modules/wc5e-bestiary/…`
asset exists on disk.

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
