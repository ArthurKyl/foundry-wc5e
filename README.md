# Warcraft 5e — Manual of Monsters (Foundry VTT module)

A Foundry VTT compendium module built from the community
[Warcraft 5e (WC5E)](https://github.com/WC5E/Warcraft-5e-Conversion)
conversion, converted to the **dnd5e** system.

- **Foundry VTT:** v13–v14 (verified on v14)
- **dnd5e system:** 5.3.3 (verified)
- **Three compendiums:**
  - **WC5E Monsters** — 420 NPC actors with full stats, traits, actions,
    reactions and legendary actions. Weapon/spell attacks are rollable with
    exact statblock to-hit and damage; every trait and action also carries its
    full descriptive text. This is 248 from the finished *Manual of Monsters*
    plus 172 net-new draft creatures from the *WIP Manual of Monsters* (full
    dragonflights, demons, the Scourge, dinosaurs, NPCs, and more). WIP entries
    are tagged `Warcraft 5e - Manual of Monsters (WIP)` in their source field;
    duplicates of finished monsters were skipped.
  - **WC5E Items** — 21 Warcraft-specific weapons & gear (from the *Heroes
    Handbook*, finished edition): 6 exotic weapons (Battle Totem, Moon Sword,
    Moonglaive, Twinblade, Warclaw, Warglaive), 2 firearms (Pistol, Rifle),
    3 shields, firearm ammunition, 2 explosives (Bomb, Dynamite — thrown,
    rollable Dex save) and 7 pieces of adventuring gear (Bayonet, Beacon,
    Buzzbox, Firestarter, Flashlight, Glowstick, Parachute). Uses dnd5e's native
    firearm/ammunition properties; the SRD-standard equipment is intentionally
    left out since the dnd5e system already ships it.
  - **WC5E Spells** — 27 Warcraft-specific spells (Solar Wrath, Starfire,
    Starsurge, Shadow Bolt, Chain Heal, Lava Burst, Blizzard, Ice Nova, etc.) as
    real dnd5e spell items with rollable attacks/saves, correct level/school/
    components, and slot scaling. These are exactly the custom spells the
    monsters reference (marked `✦` in the source) that don't exist in core D&D;
    the SRD spells the monsters also use already ship with the dnd5e system.

> Fan-made conversion for personal use. Warcraft is a trademark of Blizzard
> Entertainment. This module is not affiliated with or endorsed by Blizzard or
> the WC5E team. All monster text belongs to its respective authors — see
> *Attribution* below.

---

## Installing in Foundry

### Option A — Install from a manifest URL (recommended once it's on GitHub)

1. Create a GitHub repo (e.g. `wc5e-bestiary`) and push this folder to it.
2. Edit **`module.json`** and replace every `REPLACE_ME` with your GitHub
   username (three places: `url`, `manifest`, `download`).
3. Commit & push.
4. In Foundry: **Add-on Modules → Install Module**, paste your manifest URL into
   the *Manifest URL* box at the bottom, and click **Install**:
   ```
   https://raw.githubusercontent.com/<your-username>/wc5e-bestiary/main/module.json
   ```
5. In your world: **Game Settings → Manage Modules**, enable
   *Warcraft 5e — Manual of Monsters*.

### Option B — Install locally (no GitHub needed)

1. Copy this entire `wc5e-bestiary` folder into your Foundry data modules folder:
   - **macOS:** `~/Library/Application Support/FoundryVTT/Data/modules/`
   - **Windows:** `%localappdata%/FoundryVTT/Data/modules/`
   - **Linux:** `~/.local/share/FoundryVTT/Data/modules/`
   (You only need `module.json` and the `packs/` folder for play; the `build/`,
   `src/` and `node_modules/` folders are just for rebuilding.)
2. Restart Foundry, open your world, and enable the module under
   **Manage Modules**.

### Using the monsters

Once enabled, open the **Compendium Packs** sidebar tab. Drag monsters from
**WC5E Monsters** onto the canvas or into the Actors directory (attacks roll
from the sheet like any dnd5e NPC), and drag gear from **WC5E Items** onto a
character sheet or into the Items directory.

---

## Rebuilding the pack from source

Everything is generated from the WC5E markdown, so you can re-run the pipeline
(for example after a dnd5e update, or to tweak the conversion).

Requirements: **Node 18+** and **Python 3**.

```bash
npm install          # installs the Foundry CLI (dev dependency)
npm run build        # parse -> build actors -> compile pack
```

Individual steps:

| Command             | What it does                                                        |
|---------------------|--------------------------------------------------------------------|
| `npm run parse`     | `build/parse.py`: statblocks → `intermediate/monsters.json` (Main File) + `monsters_wip.json` (WIP) |
| `npm run actors`    | `build/build_actors.py`: intermediate → `src/monsters/*.json` (Main + net-new WIP, deduped) |
| `npm run items`     | `build/build_items.py`: authors `src/items/*.json` (WC5E weapons & gear) |
| `npm run spells`    | `build/extract_spells.py` + `build/build_spells.py`: WC5E custom spells → `src/spells/*.json` |
| `npm run pack`      | `build/pack.mjs`: `src/monsters/`, `src/items/`, `src/spells/` → LevelDB packs |

The parser points at `../Warcraft-5e-Conversion/Manual of Monsters, Main File.txt`
by default; pass a path as the first argument to `parse.py` to use another source.

### Layout

```
wc5e-bestiary/
├── module.json              # Foundry manifest (edit REPLACE_ME before publishing)
├── package.json             # build scripts + Foundry CLI dependency
├── packs/monsters/          # compiled Actor compendium (what Foundry loads)
├── packs/items/             # compiled Item compendium
├── packs/spells/            # compiled Spell compendium
├── src/monsters/*.json      # human-readable actor source (edit these, then re-pack)
├── src/items/*.json         # human-readable item source
├── src/spells/*.json        # human-readable spell source
├── intermediate/            # parsed statblock / spell JSON (build artifacts)
└── build/                   # parse.py, build_actors.py, build_items.py, build_spells.py, pack.mjs
```

To fix a single monster, edit its file in `src/monsters/`, then `npm run pack`.

---

## Conversion notes & known limitations

- **Attacks** (`Melee/Ranged Weapon/Spell Attack`) are built as rollable feat
  activities using a *flat* to-hit and the exact damage dice from the statblock,
  so rolls match the book regardless of ability modifiers.
- **Non-attack actions** (Multiattack, save-or-suck abilities, etc.) are feats
  with a utility activity so they appear in the right section and can be posted
  to chat; the mechanics live in the description text.
- **Spellcasting** monsters keep their full spell list in the trait description
  (with `✦` still marking the WC5E-custom spells). The custom spells are defined
  as real items in the **WC5E Spells** compendium, but they're **not** auto-added
  to each monster's sheet — drag one on from the compendium if you want it
  rollable there. Core/SRD spells the monsters cite already exist in dnd5e's
  built-in spell compendium.
- **Saving-throw / area abilities** are not auto-converted into save activities;
  the DCs and effects are in the description text.
- **Damage resistances "from nonmagical attacks"** are mapped to the proper
  physical types plus the *magical bypass* flag.
- **Tokens** use a shared Warcraft-themed default emblem. See *Token art* below.

These are deliberate trade-offs: core stats are exact and everything loads
cleanly; the descriptive text is always complete, so nothing from the book is
lost even where an ability isn't fully automated.

## Token art

Every monster uses a single bundled default emblem
(`assets/default-token.svg`) for both its portrait and token, so the bestiary
looks consistent out of the box. Per-monster art was intentionally left out —
the community source only has loosely-placed page illustrations, not tokens, so
auto-matching them proved unreliable. To give a monster its own art, just set
its image on the actor in Foundry (or edit `img` /
`prototypeToken.texture.src` in its `src/monsters/*.json` and re-pack).

## Attribution

Monster content is from the **Warcraft 5e Conversion — Manual of Monsters**
(<https://github.com/WC5E/Warcraft-5e-Conversion>), created by the WC5E
community. This module only reformats that text into Foundry actors. Please
credit the WC5E project and respect their licensing. Built for the **dnd5e**
system for Foundry VTT.
