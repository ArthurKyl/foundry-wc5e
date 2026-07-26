#!/usr/bin/env python3
"""Build the 27 monster-referenced WC5E custom spells as dnd5e 5.3.3 spell items
in src/spells/. Header fields + descriptions come from extract_spells.py
(faithful transcription); the activity MECHANICS below are hand-authored from
reading each spell. Schema verified against dnd5e release-5.3.3 SRD spells
(fire-bolt = attack cantrip, fireball = save + slot scaling).
"""
import json
import os
import re
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

_B62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def make_id(*parts):
    h = hashlib.sha1("::".join(str(p) for p in parts).encode()).digest()
    n = int.from_bytes(h, "big")
    return "".join(_B62[(n // (62 ** i)) % 62] for i in range(16))

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

SRC = {"custom": "Warcraft 5e - Heroes Handbook", "book": "", "page": "",
       "license": "", "rules": "2014"}
IMG = "icons/svg/daze.svg"

# --- hand-authored activity mechanics, keyed by lowercase spell name ---
# kind: attack | save | heal | utility
# dmg parts: (num, denom, type|None, scale_per_slot|None)
# tpl (AoE): (template_type, size, width|None)
# flat: [(bonus_str, type)]  extra flat damage (e.g. Glacial Spike +30)
MECH = {
    # cantrips (spell attack, cantrip die scaling)
    "fel flame":       {"kind": "attack", "dmg": [(1, 8, "fire", 1)]},
    "flurry":          {"kind": "attack", "dmg": [(1, 8, "cold", 1)]},
    "lightning blast": {"kind": "attack", "dmg": [(1, 8, "lightning", 1)]},
    "shadow bolt":     {"kind": "attack", "dmg": [(1, 10, "necrotic", 1)]},
    "solar wrath":     {"kind": "attack", "dmg": [(1, 10, "radiant", 1)]},
    "invoke elements": {"kind": "utility"},
    # leveled spell attacks
    "elemental shock": {"kind": "attack", "dmg": [(3, 8, None, 1)]},  # choice type
    "frostfire bolt":  {"kind": "attack", "dmg": [(2, 6, "fire", 1), (2, 6, "cold", 1)]},
    "starfire":        {"kind": "attack", "dmg": [(2, 12, "radiant", None)]},
    # saves w/ damage
    "arcane explosion": {"kind": "save", "save": "con", "dmg": [(12, 4, "force", 2)], "tpl": ("sphere", "10", None)},
    "blizzard":         {"kind": "save", "save": "dex", "dmg": [(3, 6, "cold", 1)], "tpl": ("cylinder", "20", None)},
    "shadow crash":     {"kind": "save", "save": "con", "dmg": [(6, 6, "necrotic", 1)], "tpl": ("sphere", "20", None)},
    "starsurge":        {"kind": "save", "save": "dex", "dmg": [(8, 6, "radiant", 1)], "tpl": ("line", "100", "5")},
    "starfall":         {"kind": "save", "save": "dex", "dmg": [(10, 6, "radiant", 1)], "tpl": ("cylinder", "20", None)},
    "lava burst":       {"kind": "save", "save": "dex", "dmg": [(3, 6, "fire", 1), (3, 6, "bludgeoning", 1)]},
    "mind blast":       {"kind": "save", "save": "wis", "dmg": [(2, 6, "psychic", 1)]},
    "earthen spike":    {"kind": "save", "save": "dex", "dmg": [(6, 8, "bludgeoning", 1)]},
    "ice nova":         {"kind": "save", "save": "dex", "dmg": [(10, 6, "cold", None)], "tpl": ("sphere", "15", None)},
    "glacial spike":    {"kind": "save", "save": "con", "dmg": [(7, 8, "cold", 2)], "flat": [("30", "bludgeoning")]},
    "dark void":        {"kind": "save", "save": "con", "dmg": [(1, 8, "necrotic", 1)]},
    # saves, control only (no damage)
    "cyclone":    {"kind": "save", "save": "dex", "dmg": []},
    "asphyxiate": {"kind": "save", "save": "dex", "dmg": []},
    # healing
    "chain heal": {"kind": "heal", "heal": (1, 8, "@mod", 1)},
    # utility / buffs / effects with no attack or save roll
    "demon skin": {"kind": "utility"},
    "ice block":  {"kind": "utility"},
    "spellsteal": {"kind": "utility"},
    "void shift": {"kind": "utility"},
}


def dpart(n, d, types, scale=None, bonus=""):
    tl = [] if types is None else ([types] if isinstance(types, str) else types)
    return {"number": n, "denomination": d, "bonus": bonus, "types": tl,
            "custom": {"enabled": False, "formula": ""},
            "scaling": {"mode": "whole" if scale else "", "number": scale,
                        "formula": ""}}


def base_act(aid, kind, activation):
    return {
        "_id": aid, "type": kind, "sort": 0, "name": "", "img": "",
        "activation": {"type": activation["type"], "value": activation["value"],
                       "condition": activation.get("condition", ""),
                       "override": False},
        "consumption": {"targets": [], "scaling": {"allowed": False, "max": ""},
                        "spellSlot": True},
        "description": {"chatFlavor": ""},
        "duration": {"units": "inst", "concentration": False, "override": False},
        "effects": [],
        "range": {"override": False},
        "target": {"template": {"contiguous": False, "units": "ft"},
                   "affects": {"choice": False}, "prompt": True, "override": False},
        "uses": {"spent": 0, "recovery": [], "max": ""},
    }


def build_activity(spell_id, mech, activation):
    aid = make_id(spell_id, "act")
    kind = mech["kind"]
    if kind == "attack":
        a = base_act(aid, "attack", activation)
        parts = [dpart(*p) for p in mech["dmg"]]
        a["attack"] = {"ability": "", "bonus": "", "critical": {"threshold": None},
                       "flat": False, "type": {"value": "ranged", "classification": ""}}
        a["damage"] = {"critical": {"bonus": ""}, "includeBase": True, "parts": parts}
        return {aid: a}
    if kind == "save":
        a = base_act(aid, "save", activation)
        parts = [dpart(*p) for p in mech.get("dmg", [])]
        for bonus, t in mech.get("flat", []):
            parts.append(dpart(None, None, t, None, bonus=bonus))
        a["save"] = {"ability": [mech["save"]],
                     "dc": {"calculation": "spellcasting", "formula": ""}}
        a["damage"] = {"onSave": "half" if parts else "none", "parts": parts}
        return {aid: a}
    if kind == "heal":
        a = base_act(aid, "heal", activation)
        n, d, bonus, scale = mech["heal"]
        h = dpart(n, d, "healing", scale, bonus=bonus)
        a["healing"] = h
        return {aid: a}
    # utility
    a = base_act(aid, "utility", activation)
    a["roll"] = {"formula": "", "name": "", "prompt": False, "visible": False}
    return {aid: a}


def build_spell(src):
    name = src["name"]
    spell_id = make_id("spell", name)
    mech = MECH[name.lower()]
    activation = src["activation"]

    # target / template
    tpl = mech.get("tpl")
    if tpl:
        ttype, size, width = tpl
        target = {"affects": {"type": "", "count": "", "choice": False, "special": ""},
                  "template": {"count": "", "contiguous": False, "type": ttype,
                               "size": size, "width": width or "", "height": "",
                               "units": "ft"}}
    else:
        aff = "creature" if mech["kind"] in ("attack", "save", "heal") else ""
        target = {"affects": {"type": aff, "count": "1" if aff else "",
                              "choice": False, "special": ""},
                  "template": {"count": "", "contiguous": False, "type": "",
                               "size": "", "width": "", "height": "", "units": ""}}

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
        "level": src["level"],
        "school": src["school"],
        "materials": {"value": src["material"], "consumed": False, "cost": 0,
                      "supply": 0},
        "preparation": {"mode": "prepared", "prepared": False},
        "properties": src["properties"],
        "activities": build_activity(spell_id, mech, activation),
        "identifier": slugify(name),
    }
    return {
        "_id": spell_id, "name": name, "type": "spell", "img": IMG,
        "system": system, "effects": [], "folder": None, "sort": 0,
        "ownership": {"default": 0}, "flags": {},
        "_stats": {"systemId": "dnd5e", "systemVersion": "5.3.3"},
        "_key": f"!items!{spell_id}",
    }


def main():
    src = json.load(open(os.path.join(REPO, "intermediate", "wc5e_spells_src.json"),
                         encoding="utf-8"))
    out_dir = os.path.join(REPO, "src", "spells")
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        if fn.endswith(".json"):
            os.remove(os.path.join(out_dir, fn))
    for s in src:
        item = build_spell(s)
        with open(os.path.join(out_dir, slugify(s["name"]) + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(src)} spell items to {out_dir}")


if __name__ == "__main__":
    main()
