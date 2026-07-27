#!/usr/bin/env python3
"""Build ALL WC5E custom spells as dnd5e 5.3.3 spell items in src/spells/.

Header fields + descriptions come from extract_spells.py (WIP Ch.6, the most
complete list). Activity mechanics are AUTO-DETECTED from each description
(attack / save / heal / utility, damage dice+type, save ability, AoE template,
slot scaling) using the same phrasing patterns proven on monster statblocks,
with a small OVERRIDES table for cases the detector can't get exactly right.
Schema verified against dnd5e 5.3.3 SRD spells.
"""
import json
import os
import re
import hashlib

import folders

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

USED_SPELL_FOLDERS = set()

def _level_folder(level):
    if level == 0:
        return "Cantrips"
    suf = {1: "st", 2: "nd", 3: "rd"}.get(level, "th")
    return f"{level}{suf}-Level"

_B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def make_id(*p):
    n = int.from_bytes(hashlib.sha1("::".join(map(str, p)).encode()).digest(), "big")
    return "".join(_B62[(n // (62 ** i)) % 62] for i in range(16))

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

SRC = {"custom": "Warcraft 5e - Chapter 6 Spells", "book": "", "page": "",
       "license": "", "rules": "2014"}
IMG = "icons/svg/daze.svg"

DAMAGE_TYPES = {"acid", "bludgeoning", "cold", "fire", "force", "lightning",
                "necrotic", "piercing", "poison", "psychic", "radiant",
                "slashing", "thunder"}
# WC5E flavour damage words -> 5e types
DTYPE_ALIAS = {"frost": "cold", "shadow": "necrotic", "arcane": "force",
               "holy": "radiant", "nature": "poison"}
ABBR = {"strength": "str", "dexterity": "dex", "constitution": "con",
        "intelligence": "int", "wisdom": "wis", "charisma": "cha"}


def dpart(n, d, types, scale=None, bonus=""):
    tl = [] if not types else ([types] if isinstance(types, str) else types)
    return {"number": n, "denomination": d, "bonus": bonus, "types": tl,
            "custom": {"enabled": False, "formula": ""},
            "scaling": {"mode": "whole" if scale else "", "number": scale,
                        "formula": ""}}


# ---------------------------------------------------------------------------
# Auto-detect mechanics from a spell description
# ---------------------------------------------------------------------------
def _strip(html):
    return re.sub(r"<[^>]+>", " ", html)

def _dtype(word):
    w = word.lower()
    if w in DAMAGE_TYPES:
        return w
    return DTYPE_ALIAS.get(w, None)

DMG_RE = re.compile(r"(\d+)d(\d+)(?:\s*\+\s*\d+)?\s+(\w+)\s+damage", re.I)
SAVE_RE = re.compile(r"(strength|dexterity|constitution|intelligence|wisdom|charisma)"
                     r"\s+saving throw", re.I)
ATK_RE = re.compile(r"make a (ranged|melee) spell attack", re.I)


def auto_detect(desc_html):
    t = _strip(desc_html)
    tl = t.lower()

    # base damage is stated before any scaling clause; truncate there so the
    # "increases by NdM ... damage" sentence isn't read as a base damage part.
    cut = len(t)
    for marker in ("at higher levels", "increases by", "this spell's damage",
                   "this spell’s damage"):
        i = tl.find(marker)
        if i != -1:
            cut = min(cut, i)
    dmg_text = t[:cut]

    # Base damage is in the FIRST sentence that mentions damage. Later sentences
    # describe conditional / ongoing / "instead" damage, which we don't bake in.
    # (Simultaneous dual damage — "2d6 fire and 2d6 cold damage" — is one
    # sentence, so it's still captured.)
    dmg_sentence = ""
    for sent in re.split(r"(?<=[.;])\s+", dmg_text):
        if "damage" in sent.lower() and DMG_RE.search(sent):
            dmg_sentence = sent
            break

    dmg, seen = [], set()
    for m in DMG_RE.finditer(dmg_sentence):
        typ = _dtype(m.group(3))
        key = (m.group(1), m.group(2), typ)
        if key in seen:
            continue
        seen.add(key)
        dmg.append([int(m.group(1)), int(m.group(2)), typ, None])

    # slot / cantrip scaling
    scale = None
    mc = re.search(r"increases by (\d+)d(\d+) when you reach 5th", t, re.I)
    ml = re.search(r"increases by (\d+)d(\d+).{0,40}for each slot level above", t, re.I)
    if "for every two slot" not in tl:   # non-standard scaling -> leave off
        if mc:
            scale = int(mc.group(1))
        elif ml:
            scale = int(ml.group(1))
    if scale:
        for p in dmg:
            p[3] = scale

    # AoE template
    tpl = None
    for pat, kind in [(r"(\d+)[- ]foot[- ]radius", "sphere"),
                      (r"(\d+)[- ]foot[- ](?:tall |high )?cylinder", "cylinder"),
                      (r"(\d+)[- ]foot[- ]cone", "cone"),
                      (r"(\d+)[- ]foot .{0,8}line", "line")]:
        mm = re.search(pat, tl)
        if mm:
            tpl = (kind, mm.group(1), "5" if kind == "line" else None)
            break

    atk = ATK_RE.search(tl)
    sv = SAVE_RE.search(tl)
    if atk and dmg:
        return {"kind": "attack", "atk": atk.group(1), "dmg": dmg}
    if sv:
        onsave = "half" if re.search(r"half as much|half the|half damage", tl) else "none"
        return {"kind": "save", "save": ABBR[sv.group(1).lower()], "dmg": dmg,
                "onsave": onsave if dmg else "none", "tpl": tpl}
    if re.search(r"regains?\b.{0,40}hit points", tl) and not dmg:
        hm = re.search(r"(\d+)d(\d+)", t)
        if hm:
            return {"kind": "heal",
                    "heal": (int(hm.group(1)), int(hm.group(2)), "@mod", scale)}
    return {"kind": "utility"}


# Overrides where the detector can't be exact (flat damage, weird scaling, etc.)
OVERRIDES = {
    "glacial spike": {"kind": "save", "save": "con", "onsave": "half",
                      "dmg": [(7, 8, "cold", 2)], "flat": [("30", "bludgeoning")]},
}


# ---------------------------------------------------------------------------
# Activity + item assembly
# ---------------------------------------------------------------------------
def base_act(aid, kind, activation):
    return {
        "_id": aid, "type": kind, "sort": 0, "name": "", "img": "",
        "activation": {"type": activation["type"], "value": activation["value"],
                       "condition": activation.get("condition", ""), "override": False},
        "consumption": {"targets": [], "scaling": {"allowed": False, "max": ""}, "spellSlot": True},
        "description": {"chatFlavor": ""},
        "duration": {"units": "inst", "concentration": False, "override": False},
        "effects": [], "range": {"override": False},
        "target": {"template": {"contiguous": False, "units": "ft"},
                   "affects": {"choice": False}, "prompt": True, "override": False},
        "uses": {"spent": 0, "recovery": [], "max": ""},
    }


def build_activity(spell_id, mech, activation):
    aid = make_id(spell_id, "act")
    kind = mech["kind"]
    if kind == "attack":
        a = base_act(aid, "attack", activation)
        a["attack"] = {"ability": "", "bonus": "", "critical": {"threshold": None},
                       "flat": False,
                       "type": {"value": mech.get("atk", "ranged"), "classification": ""}}
        a["damage"] = {"critical": {"bonus": ""}, "includeBase": True,
                       "parts": [dpart(*p) for p in mech["dmg"]]}
        return {aid: a}
    if kind == "save":
        a = base_act(aid, "save", activation)
        parts = [dpart(*p) for p in mech.get("dmg", [])]
        for bonus, t in mech.get("flat", []):
            parts.append(dpart(None, None, t, None, bonus=bonus))
        a["save"] = {"ability": [mech["save"]],
                     "dc": {"calculation": "spellcasting", "formula": ""}}
        a["damage"] = {"onSave": mech.get("onsave", "half" if parts else "none"),
                       "parts": parts}
        return {aid: a}
    if kind == "heal":
        a = base_act(aid, "heal", activation)
        n, d, bonus, scale = mech["heal"]
        a["healing"] = dpart(n, d, "healing", scale, bonus=bonus)
        return {aid: a}
    a = base_act(aid, "utility", activation)
    a["roll"] = {"formula": "", "name": "", "prompt": False, "visible": False}
    return {aid: a}


def build_spell(src):
    name = src["name"]
    spell_id = make_id("spell", name)
    mech = OVERRIDES.get(name.lower()) or auto_detect(src["description"])
    activation = src["activation"]

    tpl = mech.get("tpl")
    if tpl:
        ttype, size, width = tpl
        target = {"affects": {"type": "", "count": "", "choice": False, "special": ""},
                  "template": {"count": "", "contiguous": False, "type": ttype,
                               "size": size, "width": width or "", "height": "", "units": "ft"}}
    else:
        aff = "creature" if mech["kind"] in ("attack", "save", "heal") else ""
        target = {"affects": {"type": aff, "count": "1" if aff else "", "choice": False, "special": ""},
                  "template": {"count": "", "contiguous": False, "type": "", "size": "",
                               "width": "", "height": "", "units": ""}}

    rng = src["range"]
    system = {
        "description": {"value": src["description"], "chat": ""},
        "source": SRC,
        "activation": {"type": activation["type"], "condition": activation.get("condition", ""),
                       "value": activation["value"]},
        "duration": {"value": src["duration"].get("value", ""),
                     "units": src["duration"].get("units", "inst")},
        "target": target,
        "range": {"value": rng.get("value"), "units": rng.get("units", ""),
                  "special": rng.get("special", "")},
        "uses": {"max": "", "recovery": [], "spent": 0},
        "level": src["level"], "school": src["school"],
        "materials": {"value": src["material"], "consumed": False, "cost": 0, "supply": 0},
        "preparation": {"mode": "prepared", "prepared": False},
        "properties": src["properties"],
        "activities": build_activity(spell_id, mech, activation),
        "identifier": slugify(name),
    }
    fname = _level_folder(src["level"])
    USED_SPELL_FOLDERS.add(fname)
    return {
        "_id": spell_id, "name": name, "type": "spell", "img": IMG,
        "system": system, "effects": [], "folder": folders.fid("Item", fname),
        "sort": 0, "ownership": {"default": 0}, "flags": {},
        "_stats": {"systemId": "dnd5e", "systemVersion": "5.3.3"},
        "_key": f"!items!{spell_id}",
    }, mech["kind"]


def main():
    src = json.load(open(os.path.join(REPO, "intermediate", "wc5e_spells_src.json"),
                         encoding="utf-8"))
    out_dir = os.path.join(REPO, "src", "spells")
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        if fn.endswith(".json"):
            os.remove(os.path.join(out_dir, fn))
    from collections import Counter
    kinds = Counter()
    for s in src:
        item, kind = build_spell(s)
        kinds[kind] += 1
        with open(os.path.join(out_dir, slugify(s["name"]) + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
    for fname in USED_SPELL_FOLDERS:
        doc = folders.folder_doc("Item", fname)
        with open(os.path.join(out_dir, "_folder-" + slugify(fname) + ".json"),
                  "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(src)} spell items to {out_dir}")
    print("  activity kinds:", dict(kinds))


if __name__ == "__main__":
    main()
