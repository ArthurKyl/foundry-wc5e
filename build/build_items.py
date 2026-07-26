#!/usr/bin/env python3
"""
build_items.py -- Author the WC5E-specific gear from the Heroes Handbook
(Chapter 4) as dnd5e 5.3.3 Item documents, one JSON per item in src/items/.

The data below is transcribed directly from the WC5E Heroes Handbook tables
(racial weapons, firearms, shields, ammunition) -- not machine-parsed. Schema
verified against dnd5e release-5.3.3 (weapon/equipment/consumable models + the
SRD Ogre weapon source).
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
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "item"

WEAPON_ICON = "icons/svg/sword.svg"
GUN_ICON = "icons/svg/sword.svg"
SHIELD_ICON = "icons/svg/shield.svg"
AMMO_ICON = "icons/svg/item-bag.svg"
SRC = {"custom": "Warcraft 5e - Heroes Handbook", "book": "", "page": "",
       "license": "", "revision": 1, "rules": "2014"}

FIREARM_RULE = (
    "<p><em>Misfire.</em> When your attack roll's d20 is at or below this "
    "firearm's misfire score, the weapon misfires: the attack misses and the "
    "weapon can't be used again until you spend an action to repair it "
    "(DC 8 + misfire score Intelligence or Tinker's Tools check). On a failed "
    "check the weapon is broken and must be mended out of combat at a quarter "
    "of its cost.</p><p><em>Reload.</em> After the listed number of shots you "
    "must reload using an action or bonus action (your choice).</p>")

EMPTY_DMG = {"number": None, "denomination": None, "bonus": "", "types": [],
             "custom": {"enabled": False, "formula": ""},
             "scaling": {"mode": "", "number": None, "formula": ""}}


def dmg(n, d, types, bonus=""):
    return {"number": n, "denomination": d, "bonus": bonus, "types": types,
            "custom": {"enabled": False, "formula": ""},
            "scaling": {"mode": "", "number": None, "formula": ""}}


def attack_activity(item_id, atk_type, ability, rng_value):
    aid = make_id(item_id, "attack")
    return {aid: {
        "_id": aid, "type": "attack", "sort": 0,
        "activation": {"type": "action", "value": 1, "condition": "",
                       "override": False},
        "consumption": {"targets": [], "scaling": {"allowed": False, "max": ""},
                        "spellSlot": True},
        "description": {"chatFlavor": ""},
        "duration": {"concentration": False, "value": "", "units": "",
                     "special": "", "override": False},
        "effects": [],
        "range": {"value": rng_value, "units": "ft", "special": "",
                  "override": False},
        "target": {"template": {"count": "", "contiguous": False, "type": "",
                    "size": "", "width": "", "height": "", "units": ""},
                   "affects": {"count": "", "type": "", "choice": False,
                    "special": ""}, "prompt": True, "override": False},
        "uses": {"spent": 0, "max": "", "recovery": []},
        "attack": {"ability": ability, "bonus": "", "critical": {"threshold": None},
                   "flat": False,
                   "type": {"value": atk_type, "classification": "weapon"}},
        "damage": {"critical": {"bonus": ""}, "includeBase": True, "parts": []},
    }}


def weapon(name, price, weight, base, props, wtype, ability, desc,
           versatile=None, rng=None, reach=5):
    item_id = make_id("item", name)
    atk_type = "ranged" if wtype == "martialR" else "melee"
    rng_value = str(rng[0]) if rng else str(reach)
    range_obj = {"value": rng[0] if rng else None,
                 "long": rng[1] if rng else None,
                 "reach": None if rng else reach, "units": "ft"}
    system = {
        "description": {"value": desc, "chat": ""},
        "source": SRC, "quantity": 1,
        "weight": {"value": weight, "units": "lb"},
        "price": {"value": price, "denomination": "gp"},
        "attunement": "", "equipped": False, "rarity": "", "identified": True,
        "range": range_obj,
        "uses": {"spent": 0, "max": "", "recovery": []},
        "damage": {"versatile": versatile or dict(EMPTY_DMG), "base": base},
        "armor": {"value": 0}, "hp": {"value": 0, "max": 0, "dt": None,
                                      "conditions": ""},
        "properties": props, "proficient": None,
        "type": {"value": wtype, "baseItem": ""},
        "activities": attack_activity(item_id, atk_type, ability, rng_value),
        "identifier": "", "magicalBonus": None, "mastery": "",
        "ammunition": {"type": ""},
    }
    return _wrap(item_id, name, "weapon",
                 GUN_ICON if wtype == "martialR" else WEAPON_ICON, system)


def shield(name, price, weight, ac_bonus, desc, strength=None, stealth_dis=False):
    item_id = make_id("item", name)
    props = ["stealthDisadvantage"] if stealth_dis else []
    system = {
        "description": {"value": desc, "chat": ""},
        "source": SRC, "quantity": 1,
        "weight": {"value": weight, "units": "lb"},
        "price": {"value": price, "denomination": "gp"},
        "attunement": "", "equipped": False, "rarity": "", "identified": True,
        "armor": {"value": ac_bonus, "dex": None, "magicalBonus": None},
        "hp": {"value": 0, "max": 0, "dt": None, "conditions": ""},
        "speed": {"value": None, "conditions": ""},
        "strength": strength, "proficient": None,
        "type": {"value": "shield", "baseItem": ""},
        "properties": props, "activities": {}, "identifier": "",
    }
    return _wrap(item_id, name, "equipment", SHIELD_ICON, system)


def ammo(name, price, weight, qty, desc):
    item_id = make_id("item", name)
    system = {
        "description": {"value": desc, "chat": ""},
        "source": SRC, "quantity": qty,
        "weight": {"value": weight, "units": "lb"},
        "price": {"value": price, "denomination": "gp"},
        "attunement": "", "equipped": False, "rarity": "", "identified": True,
        "uses": {"spent": 0, "max": "", "recovery": []},
        "type": {"value": "ammo", "subtype": ""},
        "properties": [], "activities": {}, "identifier": "",
        "magicAvailable": False,
    }
    return _wrap(item_id, name, "consumable", AMMO_ICON, system)


def _wrap(item_id, name, itype, img, system):
    return {
        "_id": item_id, "name": name, "type": itype, "img": img,
        "system": system, "effects": [], "folder": None, "sort": 0,
        "ownership": {"default": 0}, "flags": {},
        "_stats": {"systemId": "dnd5e", "systemVersion": "5.3.3"},
        "_key": f"!items!{item_id}",
    }


def p(text):
    return f"<p>{text}</p>"


def firearm_desc(category, reload_n, misfire, extra=""):
    return (p(f"<em>{category} firearm.</em> Reload {reload_n}, misfire "
              f"{misfire}. {extra}".strip()) + FIREARM_RULE)


def build():
    items = []

    # ---- Racial weapons (martial melee) ----
    items.append(weapon(
        "Kaldorei Moon Sword", 15, 4, dmg(1, 8, ["slashing"]),
        ["ver"], "martialM", "str",
        p("A night elf circular moon blade."),
        versatile=dmg(2, 6, ["slashing"])))
    items.append(weapon(
        "Kaldorei Moonglaive", 20, 3, dmg(1, 6, ["slashing"]),
        ["fin", "lgt", "thr"], "martialM", "dex",
        p("A crescent throwing glaive favored by night elf sentinels."),
        rng=(20, 60)))
    items.append(weapon(
        "Sin'dorei Warblade", 25, 5, dmg(1, 8, ["slashing"]),
        ["spc"], "martialM", "str",
        p("A blood elf double-ended warblade.") +
        p("<em>Special.</em> Immediately after attacking an enemy with this "
          "blade, you may make an additional attack with its second blade "
          "using your bonus action.")))
    items.append(weapon(
        "Tauren Totem", 20, 45, dmg(2, 8, ["bludgeoning"]),
        ["hvy", "two"], "martialM", "str",
        p("A massive tauren totem, capable of crushing most men.")))
    items.append(weapon(
        "Warglaive", 30, 3, dmg(1, 8, ["slashing"]),
        ["lgt"], "martialM", "str",
        p("A curved glaive wielded in pairs by demon hunters.")))

    # ---- Firearms (martial ranged) ----
    F = [
        ("Blunderbuss", 300, 10, dmg(2, 8, ["piercing"]), (15, 60),
         ["amm", "fir", "rel"], "Flintlock", 1, 2, "Uses special ammunition."),
        ("Musket", 300, 10, dmg(1, 12, ["piercing"]), (120, 480),
         ["amm", "fir", "rel", "two"], "Flintlock", 1, 2, ""),
        ("Pistol", 150, 3, dmg(1, 10, ["piercing"]), (60, 240),
         ["amm", "fir", "rel"], "Flintlock", 2, 1, ""),
        ("Pepperbox", 350, 5, dmg(2, 4, ["piercing"]), (80, 320),
         ["amm", "fir", "rel"], "Caplock", 4, 2, ""),
        ("Revolver", 525, 6, dmg(1, 10, ["piercing"]), (120, 380),
         ["amm", "fir", "rel"], "Caplock", 6, 1, ""),
        ("Rifle", 600, 10, dmg(2, 6, ["piercing"]), (300, 600),
         ["amm", "fir", "rel", "two"], "Caplock", 8, 2, ""),
        ("Scattergun", 400, 12, dmg(2, 10, ["piercing"]), (30, 90),
         ["amm", "fir", "rel"], "Caplock", 1, 3, "Uses special ammunition."),
    ]
    for name, price, wt, base, rng, props, cat, rl, mf, extra in F:
        items.append(weapon(name, price, wt, base, props, "martialR", "dex",
                            firearm_desc(cat, rl, mf, extra), rng=rng))

    # ---- Shields (equipment) ----
    items.append(shield(
        "Buckler", 5, 2, 1,
        p("<em>Special.</em> A buckler is strapped to your forearm, letting "
          "you hold an item in that hand. If you use the shielded hand as part "
          "of an action or bonus action, you lose the buckler's bonus to your "
          "Armor Class until the start of your next turn.")))
    items.append(shield(
        "Standard Shield", 10, 6, 2,
        p("A common shield worn on Azeroth.")))
    items.append(shield(
        "Tower Shield", 25, 24, 2,
        p("<em>Special.</em> You use your Strength modifier, instead of your "
          "Dexterity, for determining your Armor Class while this shield is "
          "donned. Imposes disadvantage on Stealth checks; requires Strength "
          "15."), strength=15, stealth_dis=True))

    # ---- Ammunition (consumable) ----
    items.append(ammo("Flintlock Bullets (10)", 3, 2, 10,
                      p("Ammunition for flintlock firearms.")))
    items.append(ammo("Blunderbuss Bullets (5)", 5, 2, 5,
                      p("Special ammunition for the blunderbuss.")))
    items.append(ammo("Caplock Rifle Bullets (10)", 5, 3, 10,
                      p("Ammunition for caplock firearms.")))
    items.append(ammo("Scattergun Bullets (5)", 8, 3, 5,
                      p("Special ammunition for the scattergun.")))

    return items


def main():
    out_dir = os.path.join(REPO, "src", "items")
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        if fn.endswith(".json"):
            os.remove(os.path.join(out_dir, fn))
    items = build()
    for it in items:
        with open(os.path.join(out_dir, slugify(it["name"]) + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump(it, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(items)} item files to {out_dir}")


if __name__ == "__main__":
    main()
