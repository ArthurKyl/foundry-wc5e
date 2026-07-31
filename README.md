# Warcraft 5e (WC5E) — Foundry VTT module

Compendium content for playing in the world of **Warcraft** on Foundry VTT,
converted from the community
[Warcraft 5e (WC5E)](https://github.com/WC5E/Warcraft-5e-Conversion) project to
the **dnd5e** system.

**Foundry VTT** v13–v14 (verified on v14) · **dnd5e system** 5.3.3

The goal is a **complete WC5E module** — everything you need to run a Warcraft
campaign without hand-entering content. Monsters, items and spells are done;
races, classes, backgrounds and feats are next. See [Roadmap](#roadmap).

> Unofficial fan content. Warcraft is a trademark of Blizzard Entertainment.
> This module is not affiliated with or endorsed by Blizzard, Wizards of the
> Coast, or the WC5E team. All WC5E text belongs to its respective authors — see
> [Attribution](#attribution--license).

---

## Install

### Option A — Manifest URL (recommended)

In Foundry: **Add-on Modules → Install Module**, paste this into the *Manifest
URL* box at the bottom, and click **Install**:

```
https://raw.githubusercontent.com/ArthurKyl/foundry-wc5e/main/module.json
```

Then in your world: **Game Settings → Manage Modules** → enable
**Warcraft 5e (WC5E)**.

Installing from the manifest always pulls the current `main`, and Foundry will
offer an update whenever the module version here is bumped.

### Option B — Manual install

1. Download the repo as a ZIP (**Code → Download ZIP**) and extract it.
2. **Rename the extracted folder to `wc5e-bestiary`.** This matters: the module
   id is `wc5e-bestiary`, and monster token art is referenced as
   `modules/wc5e-bestiary/assets/…`. A folder named `foundry-wc5e-main` will
   load but every token will show a broken image.
3. Move it into your Foundry data modules folder:
   - **Windows:** `%localappdata%/FoundryVTT/Data/modules/`
   - **macOS:** `~/Library/Application Support/FoundryVTT/Data/modules/`
   - **Linux:** `~/.local/share/FoundryVTT/Data/modules/`
4. Restart Foundry, then enable the module under **Manage Modules**.

Only `module.json`, `packs/` and `assets/` are needed to play — `build/` and
`src/` are just for rebuilding.

### Using it

Open the **Compendium Packs** sidebar tab and find the **Warcraft 5e** group.
Drag monsters onto the canvas or into the Actors directory (attacks roll from
the sheet like any dnd5e NPC), and drag gear or spells onto a character sheet.
Start with the **WC5E Guide** journal for a short in-module orientation.

---

## What's inside

**WC5E Monsters** — 420 NPC actors, foldered by creature type, with full stats,
traits, actions, reactions and legendary actions. Weapon and spell attacks are
rollable using the exact statblock to-hit and damage; save-based abilities
(breath weapons and the like) roll their save at the printed DC. Every trait and
action also carries its complete descriptive text. This is 248 monsters from the
finished *Manual of Monsters* plus 172 net-new draft creatures from the *WIP
Manual of Monsters* (full dragonflights, demons, the Scourge, dinosaurs, NPCs
and more). WIP entries are tagged `Warcraft 5e - Manual of Monsters (WIP)` in
their source field; duplicates of finished monsters were skipped.

**WC5E Items** — 21 Warcraft-specific weapons and gear from the *Heroes
Handbook*: 6 exotic weapons (Battle Totem, Moon Sword, Moonglaive, Twinblade,
Warclaw, Warglaive), 2 firearms (Pistol, Rifle) using dnd5e's native
firearm/ammunition properties, 3 shields, firearm ammunition, 2 explosives
(Bomb, Dynamite — thrown, rollable Dex save) and 7 pieces of adventuring gear
(Bayonet, Beacon, Buzzbox, Firestarter, Flashlight, Glowstick, Parachute).
SRD-standard equipment is intentionally left out since the dnd5e system already
ships it.

**WC5E Spells** — the complete WC5E custom spell list (99 spells) as real dnd5e
spell items, foldered by level: correct level/school/components/duration, with
rollable attack / save / heal activities and slot scaling derived from each
spell's rules text (Solar Wrath, Pyroblast, Death and Decay, Chain Heal,
Bloodlust and Heroism, Army of the Dead, …). These are the Warcraft spells that
don't exist in core D&D; the SRD spells monsters also use ship with the dnd5e
system. A few utility/buff spells with unusual wording carry their full text but
aren't auto-wired to roll — open an issue and they're a quick fix.

**WC5E Guide** — a short in-module journal: what's included, how to use it,
roadmap and credits.

---

## Roadmap

**Done**

- [x] Monsters — 420 NPCs, foldered by creature type
- [x] Monster attacks & save abilities (breath weapons etc.) rollable
- [x] Monster spellcasting embedded (~77% of references)
- [x] Weapons, firearms, shields, ammunition
- [x] Explosives & adventuring gear
- [x] Full WC5E custom spell list (99 spells), foldered by level
- [x] Compendium folders + in-module guide journal

**Planned**

- [ ] Backgrounds
- [ ] Races
- [ ] Classes & subclasses
- [ ] Feats
- [ ] Per-monster / creature token art
- [ ] Wire the remaining non-SRD spells (needs official content)

Races and classes are the most involved — they need dnd5e *advancement*
configuration to actually build a character rather than just describe one — and
are being tackled manually over time.

This project is in conversation with the WC5E team about becoming a proper
first-party Foundry module. Suggestions, bug reports and corrections are
welcome via issues.

---

## Rebuilding from source

Everything is generated from the WC5E markdown, so the whole pipeline can be
re-run — after a dnd5e update, when upstream adds content, or to tweak the
conversion.

Requirements: **Node 18+**, **Python 3**, and a clone of the upstream
conversion **as a sibling directory**:

```bash
git clone https://github.com/WC5E/Warcraft-5e-Conversion ../Warcraft-5e-Conversion
npm install          # installs the Foundry CLI (only dependency)
npm run build        # parse → spells → actors → items → journal → pack
```

The parsers read `Manual of Monsters, Main File.txt`, `WIP Manual of Monsters/`
and `WIP 3.0 Chapters/Chapter 6 Spells.md` from that sibling clone. Because
`src/` is committed, you can recompile the packs (`npm run pack`) and work on the
item/journal builders **without** the upstream clone.

| Command             | What it does                                                        |
|---------------------|---------------------------------------------------------------------|
| `npm run parse`     | `build/parse.py`: statblocks → `intermediate/monsters.json` + `monsters_wip.json` |
| `npm run spells`    | `build/extract_spells.py` + `build/build_spells.py`: WC5E custom spells → `src/spells/*.json` |
| `npm run actors`    | `build/build_actors.py`: intermediate → `src/monsters/*.json` (main + net-new WIP, deduped, spells embedded) |
| `npm run items`     | `build/build_items.py`: authors `src/items/*.json` (hand-transcribed gear tables) |
| `npm run journal`   | `build/build_journal.py`: the in-module guide → `src/journals/*.json` |
| `npm run pack`      | `build/pack.mjs`: `src/*` → LevelDB packs under `packs/` |

`spells` must run before `actors`: caster monsters get their spells embedded from
`src/spells/`, so building actors first bakes in stale spell data. Rebuilds are
deterministic — identical inputs give byte-identical output.

`node build/_chk.mjs` extracts the compiled packs back out and prints document
counts as a sanity check. `python3 build/validate_wip.py` reports incomplete or
duplicated WIP statblocks.

### Layout

```
foundry-wc5e/
├── module.json              # Foundry manifest
├── packs/<pack>/            # compiled LevelDB compendiums (what Foundry loads)
├── src/<pack>/*.json        # generated, human-readable Foundry documents
├── intermediate/            # parsed statblock / spell JSON (build artifacts)
├── build/                   # the conversion pipeline
└── assets/                  # bundled default token emblem
```

> **`src/` is generated output, not source.** Each builder deletes and rewrites
> its target directory, so hand-edits there are lost on the next build. Fix
> conversions in the `build/` scripts instead. See **CLAUDE.md** for the build
> invariants (deterministic document ids, `_key` fields, pinned dnd5e version)
> before changing the pipeline.

---

## Conversion notes & known limitations

- **Attacks** (`Melee/Ranged Weapon/Spell Attack`) are built as rollable
  activities with a *flat* to-hit and the exact damage dice from the statblock,
  so rolls match the book regardless of ability modifiers.
- **Save abilities** (breath weapons, AoEs) roll a save at the literal printed
  DC, with damage and half-on-success where the text says so.
- **Other actions** (Multiattack, save-or-suck oddities) are features with a
  utility activity so they appear in the right sheet section and can be posted to
  chat; the mechanics live in the description text.
- **Spellcasting** monsters have their spells embedded and rollable: the build
  sets each caster's spellcasting ability, spell slots and a DC bonus so the
  printed statblock DC is honoured, and bakes in every spell it can resolve —
  **~77% of references** (WC5E custom spells + dnd5e SRD spells) — with the
  correct prepared / at-will / X-per-day mode. The remaining ~23% are **non-SRD
  spells** (Tasha's/Xanathar's-era, e.g. *shape water, cause fear, mold earth*)
  that can't legally be bundled; they stay listed in the Spellcasting feature
  text (customs marked `✦`). If your world has those spells from official
  content, drag them on manually.
- **Damage resistances "from nonmagical attacks"** map to the proper physical
  types plus the *magical bypass* flag.
- Where an ability isn't fully automated, its **full text is always present** —
  nothing from the book is lost.

## Token art

Every monster uses a single bundled emblem (`assets/default-token.svg`) for both
portrait and token, so the bestiary looks consistent out of the box. Per-monster
art was left out because the community source only has loosely-placed page
illustrations, not tokens, and auto-matching them proved unreliable. To give a
monster its own art, set its image on the actor in Foundry (or edit `img` /
`prototypeToken.texture.src` in its `src/monsters/*.json` and re-pack).

## Attribution & License

**WC5E content** (monsters, items, spells) is from the
[Warcraft 5e Conversion](https://github.com/WC5E/Warcraft-5e-Conversion),
created by the WC5E community; all rights to that conversion remain with its
authors. This module only reformats that text into Foundry documents. Please
credit and support the WC5E project.

**SRD spells** embedded on caster monsters are from the **System Reference
Document 5.1**, © Wizards of the Coast, used under **CC-BY-4.0** (as distributed
with the Foundry dnd5e system).

The build tooling under `build/` is MIT-licensed by the module author; the
bundled content is governed by its own sources. Full text in
[LICENSE.md](LICENSE.md).
