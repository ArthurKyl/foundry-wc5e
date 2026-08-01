#!/usr/bin/env python3
"""audit_spells.py -- What is actually wired up on each spell, and what isn't.

Reads src/spells/*.json and reports, per spell: the rules text, and the dnd5e
mechanics configured on it -- attack rolls, damage, saving throws, healing,
area templates, scaling, effects. Then cross-checks the text against the
mechanics and flags the gaps: text that describes a saving throw with no save
activity, damage dice with no damage part, an area with no template.

The cross-check is a heuristic on prose, so it is a to-do list to review, not a
verdict. It is deliberately noisy in one direction only: it can suggest work
that turns out to be unnecessary, but it will not stay quiet about a spell
whose text promises something the sheet cannot do.

Writes dist/spell-audit.json and dist/spell-audit.html. Read-only over src/.
Run with `npm run audit`.
"""
import json
import os
import re
import html
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "src", "spells")
OUT = os.path.join(REPO, "dist")

SCHOOLS = {"abj": "Abjuration", "con": "Conjuration", "div": "Divination",
           "enc": "Enchantment", "evo": "Evocation", "ill": "Illusion",
           "nec": "Necromancy", "trs": "Transmutation"}
ACTIVATION = {"action": "Action", "bonus": "Bonus action", "reaction": "Reaction",
              "minute": "Minute", "hour": "Hour", "special": "Special"}


def strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = re.sub(r"</p>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(s)).strip()


def casting_time(sys):
    a = sys.get("activation") or {}
    t = ACTIVATION.get(a.get("type"), a.get("type") or "—")
    v = a.get("value")
    return f"{v} {t.lower()}" if v and v != 1 else t


def spell_range(sys):
    r = sys.get("range") or {}
    if r.get("special"):
        return r["special"]
    if r.get("units") == "self":
        return "Self"
    if r.get("units") == "touch":
        return "Touch"
    if r.get("value"):
        return f"{r['value']} {r.get('units') or 'ft'}"
    return r.get("units") or "—"


def duration(sys):
    d = sys.get("duration") or {}
    u = d.get("units")
    if u == "inst":
        return "Instantaneous"
    if u == "perm":
        return "Permanent"
    if d.get("value"):
        return f"{d['value']} {u}"
    return u or "—"


def area(sys):
    t = (sys.get("target") or {}).get("template") or {}
    if not t.get("type"):
        return None
    size = t.get("size") or ""
    unit = t.get("units") or "ft"
    return f"{size} {unit} {t['type']}".strip()


def describe_activity(a):
    """-> (kind, [human-readable bullets])"""
    kind = a.get("type")
    bits = []

    atk = a.get("attack") or {}
    if atk:
        at = (atk.get("type") or {})
        bits.append(f"Attack roll — {at.get('value') or '?'} "
                    f"{at.get('classification') or 'spell'}")

    sv = a.get("save") or {}
    if sv:
        ab = sv.get("ability")
        ab = ", ".join(ab) if isinstance(ab, list) else (ab or "?")
        dc = (sv.get("dc") or {}).get("calculation") or (sv.get("dc") or {}).get("formula")
        bits.append(f"Saving throw — {ab.upper()} (DC: {dc or 'spellcasting'})")

    dmg = a.get("damage") or {}
    for part in dmg.get("parts") or []:
        n = part.get("number")
        die = part.get("denomination")
        bonus = part.get("bonus")
        types = part.get("types") or []
        formula = part.get("custom", {}).get("formula") if part.get("custom", {}).get("enabled") else None
        f = formula or (f"{n}d{die}" if n and die else "")
        if bonus:
            f = f"{f} + {bonus}" if f else str(bonus)
        bits.append(f"Damage — {f or '?'} {'/'.join(types) if types else ''}".strip())
        sc = part.get("scaling") or {}
        if sc.get("number"):
            bits.append(f"  scales +{sc['number']}d{sc.get('denomination') or die} per level")

    heal = a.get("healing") or {}
    if heal:
        n, die = heal.get("number"), heal.get("denomination")
        cust = (heal.get("custom") or {})
        f = cust.get("formula") if cust.get("enabled") else (f"{n}d{die}" if n and die else heal.get("bonus"))
        bits.append(f"Healing — {f or '?'}")

    if a.get("effects"):
        bits.append(f"Applies {len(a['effects'])} effect(s)")
    if (a.get("duration") or {}).get("concentration"):
        bits.append("Concentration")

    return kind, bits


def audit(doc):
    sys_ = doc["system"]
    text = strip_html((sys_.get("description") or {}).get("value"))
    low = text.lower()
    acts = list((sys_.get("activities") or {}).values())

    activities = []
    for a in sorted(acts, key=lambda x: x.get("sort", 0)):
        kind, bits = describe_activity(a)
        activities.append({"kind": kind, "name": a.get("name") or "", "detail": bits})

    has_save = any(a.get("save") for a in acts)
    has_damage = any((a.get("damage") or {}).get("parts") for a in acts)
    has_attack = any(a.get("attack") for a in acts)
    has_heal = any(a.get("healing") for a in acts)
    has_area = bool(area(sys_))
    has_effects = bool(doc.get("effects")) or any(a.get("effects") for a in acts)

    gaps = []
    if "saving throw" in low and not has_save:
        gaps.append("Text describes a saving throw, but no save is configured")
    if re.search(r"\d+d\d+", low) and not (has_damage or has_heal):
        gaps.append("Text contains damage dice, but nothing rolls them")
    if re.search(r"\b(\d+[- ]foot|radius|cone|line|cube|sphere|cylinder)\b", low) and not has_area:
        gaps.append("Text describes an area, but no template is placed")
    if "spell attack" in low and not has_attack:
        gaps.append("Text describes a spell attack, but no attack roll is configured")
    # A named condition alone is far too broad -- half the corpus mentions one in
    # passing. An effect worth automating has to persist, so require a duration
    # to sustain it, and the condition to be something the target *becomes*.
    lasting = (sys_.get("duration") or {}).get("units") not in ("inst", "perm", None, "")
    becomes = re.search(r"\b(is|are|becomes|become)\s+(?:\w+\s+){0,2}"
                        r"(restrained|frightened|poisoned|stunned|paralyzed|prone|blinded|"
                        r"charmed|incapacitated|deafened|petrified|invisible|unconscious)\b", low)
    grants = re.search(r"\b(gains?|has|have)\s+(?:\w+\s+){0,3}"
                       r"(resistance|immunity|advantage|disadvantage|temporary hit points)\b", low)
    if lasting and (becomes or grants) and not has_effects:
        what = (becomes or grants).group(0)
        gaps.append(f"Lasting effect in the text (\u201c{what}\u201d) with no Active Effect to apply it")
    if not acts:
        gaps.append("No activities at all — nothing is rollable from the sheet")

    return {
        "name": doc["name"],
        "level": sys_.get("level", 0),
        "school": SCHOOLS.get(sys_.get("school"), sys_.get("school") or "—"),
        "castingTime": casting_time(sys_),
        "range": spell_range(sys_),
        "duration": duration(sys_),
        "components": [p for p in (sys_.get("properties") or [])],
        "area": area(sys_),
        "source": (sys_.get("source") or {}).get("custom") or "",
        "text": text,
        "activities": activities,
        "wired": {"attack": has_attack, "damage": has_damage, "save": has_save,
                  "heal": has_heal, "area": has_area, "effects": has_effects},
        "gaps": gaps,
    }


def main():
    spells = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".json") or fn.startswith("_folder-"):
            continue
        spells.append(audit(json.load(open(os.path.join(SRC, fn), encoding="utf-8"))))
    spells.sort(key=lambda s: (s["level"], s["name"].lower()))

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "spell-audit.json"), "w", encoding="utf-8") as f:
        json.dump(spells, f, indent=2, ensure_ascii=False)

    tally = Counter()
    for s in spells:
        for k, v in s["wired"].items():
            if v:
                tally[k] += 1
        if s["gaps"]:
            tally["withGaps"] += 1
    tally["total"] = len(spells)

    tpl = open(os.path.join(HERE, "spell_audit_template.html"), encoding="utf-8").read()
    body = tpl.replace("/*DATA*/", json.dumps(spells, ensure_ascii=False)) \
              .replace("/*TALLY*/", json.dumps(dict(tally)))
    # The template is body content only, so it can be published as an Artifact
    # as-is; the local copy gets a minimal document shell wrapped round it.
    with open(os.path.join(OUT, "spell-audit.body.html"), "w", encoding="utf-8") as f:
        f.write(body)
    with open(os.path.join(OUT, "spell-audit.html"), "w", encoding="utf-8") as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                + body + "\n</html>\n")

    print(f"{len(spells)} spells audited")
    for k in ("attack", "damage", "save", "heal", "area", "effects"):
        print(f"  {k:8s} {tally[k]:3d}")
    print(f"  {tally['withGaps']} spells have at least one flagged gap")
    print(f"\nWrote dist/spell-audit.html and dist/spell-audit.json")


if __name__ == "__main__":
    main()
