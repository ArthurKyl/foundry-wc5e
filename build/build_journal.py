#!/usr/bin/env python3
"""Build the module's 'Read Me' JournalEntry (welcome + roadmap + credits) into
src/journals/ for the journals compendium."""
import json
import os
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

_B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def mkid(*p):
    n = int.from_bytes(hashlib.sha1("::".join(p).encode()).digest(), "big")
    return "".join(_B62[(n // (62 ** i)) % 62] for i in range(16))

STATS = {"systemId": "dnd5e", "systemVersion": "5.3.3"}

WELCOME = """
<h2>Warcraft 5e (WC5E)</h2>
<p>An unofficial, fan-made Foundry VTT module for playing in the world of
<strong>Warcraft</strong> using the community <strong>Warcraft 5e (WC5E)</strong>
conversion on the <strong>dnd5e</strong> system.</p>
<p>The goal is a <strong>complete</strong> WC5E module — everything needed to run a
Warcraft campaign without hand-entering content. Monsters, spells, items and the
full set of player options are in; backgrounds and class spell lists are what's
left (see <em>Roadmap</em>).</p>
<p><strong>What's inside</strong></p>
<ul>
  <li><strong>WC5E Monsters</strong> — 420 NPC actors (Manual of Monsters + WIP
    drafts), organised into folders by creature type. Attacks and save-based
    abilities (breath weapons, etc.) roll from the sheet; casters have their
    spells embedded.</li>
  <li><strong>WC5E Items</strong> — 21 Warcraft weapons &amp; gear: firearms,
    exotic weapons, shields, ammunition, explosives (Bomb, Dynamite), and
    adventuring gear.</li>
  <li><strong>WC5E Spells</strong> — the full 101-spell WC5E custom spell list,
    foldered by level.</li>
  <li><strong>Player Options</strong> — 12 classes, 36 subclasses, 28 races,
    class features, feats, equipment and summons, with dnd5e advancement
    configured. Drag a class and a race onto a blank sheet and level up.
    Created by <strong>GoC45</strong>, included with permission.</li>
</ul>
<p><strong>How to use</strong></p>
<ul>
  <li>Open the <em>Compendium Packs</em> sidebar tab → drag monsters onto the
    canvas and items/spells onto character sheets.</li>
  <li>Some monster spells and abilities reference <em>non-SRD</em> spells
    (Tasha's/Xanathar's) that can't be bundled — those stay listed as text; drag
    them from your own content if you own it.</li>
</ul>
"""

ROADMAP = """
<h2>Roadmap</h2>
<p>What's in the module today, and what's planned.</p>
<p><strong>Done</strong></p>
<ul>
  <li>&#9745; Monsters (420 NPCs, foldered by type)</li>
  <li>&#9745; Monster attacks &amp; save abilities (rollable)</li>
  <li>&#9745; Monster spellcasting (embedded, ~79% of references)</li>
  <li>&#9745; Weapons, firearms, shields, ammunition</li>
  <li>&#9745; Explosives &amp; adventuring gear</li>
  <li>&#9745; Full WC5E custom spell list (101 spells)</li>
  <li>&#9745; Player options: 12 classes, 36 subclasses, 28 races, class
    features and feats, with advancement configured</li>
  <li>&#9745; Summons &amp; pets</li>
  <li>&#9745; Compendium folders &amp; this guide</li>
</ul>
<p><strong>Planned</strong></p>
<ul>
  <li>&#9744; Backgrounds</li>
  <li>&#9744; Class spell lists</li>
  <li>&#9744; Per-monster / creature token art</li>
  <li>&#9744; Wire the remaining non-SRD spells (needs official content)</li>
</ul>
"""

CREDITS = """
<h2>Credits &amp; License</h2>
<p>This is unofficial fan content. <strong>Warcraft</strong> is a trademark of
Blizzard Entertainment; this module is not affiliated with or endorsed by
Blizzard.</p>
<ul>
  <li><strong>WC5E content</strong> (monsters, items, spells) is from the
    community <em>Warcraft 5e Conversion</em>. Please credit and support the
    WC5E project and follow their licensing.</li>
  <li><strong>Player options</strong> (classes, subclasses, races, class
    features, feats, equipment, summons) were built by <strong>GoC45</strong> for
    the <em>WC5E Character Creation Compendium</em> and are included here with
    their permission.</li>
  <li><strong>SRD spells</strong> embedded on casters are from the
    <em>System Reference Document 5.1</em>, &copy; Wizards of the Coast, used
    under <strong>CC-BY-4.0</strong>.</li>
  <li>Built for the Foundry VTT <strong>dnd5e</strong> system (5.3.x, rules
    version 2014).</li>
</ul>
"""


def page(journal_id, name, html, sort):
    pid = mkid(journal_id, name)
    return {
        "_id": pid, "name": name, "type": "text",
        "title": {"show": True, "level": 1},
        "text": {"content": html.strip(), "format": 1, "markdown": ""},
        "image": {}, "video": {"controls": True, "volume": 0.5}, "src": None,
        "system": {}, "sort": sort, "ownership": {"default": -1}, "flags": {},
        "_stats": STATS,
        "_key": f"!journal.pages!{journal_id}.{pid}",
    }


def main():
    jid = mkid("journal", "wc5e-readme")
    entry = {
        "_id": jid, "name": "Warcraft 5e — Read Me",
        "pages": [
            page(jid, "Welcome", WELCOME, 100000),
            page(jid, "Roadmap", ROADMAP, 200000),
            page(jid, "Credits & License", CREDITS, 300000),
        ],
        "folder": None, "sort": 0, "ownership": {"default": 0}, "flags": {},
        "_stats": STATS, "_key": f"!journal!{jid}",
    }
    out_dir = os.path.join(REPO, "src", "journals")
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        if fn.endswith(".json"):
            os.remove(os.path.join(out_dir, fn))
    with open(os.path.join(out_dir, "readme.json"), "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    print(f"Wrote journal 'Warcraft 5e — Read Me' ({len(entry['pages'])} pages)")


if __name__ == "__main__":
    main()
