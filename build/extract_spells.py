#!/usr/bin/env python3
"""Faithfully transcribe the 27 monster-referenced WC5E custom spells from the
Heroes Handbook Spell Descriptions into intermediate/wc5e_spells_src.json:
regular header fields (level/school/time/range/components/duration) + full
description HTML. The activity MECHANICS are hand-authored in build_spells.py.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HHB = os.path.join(os.path.dirname(REPO), "Warcraft-5e-Conversion",
                   "Heroes Handbook, Main File.txt")

USED = ["arcane explosion", "asphyxiate", "blizzard", "chain heal", "cyclone",
        "dark void", "demon skin", "earthen spike", "elemental shock",
        "fel flame", "flurry", "frostfire bolt", "glacial spike", "ice block",
        "ice nova", "invoke elements", "lava burst", "lightning blast",
        "mind blast", "shadow bolt", "shadow crash", "solar wrath",
        "spellsteal", "starfall", "starfire", "starsurge", "void shift"]

SCHOOL = {"abjuration": "abj", "conjuration": "con", "divination": "div",
          "enchantment": "enc", "evocation": "evo", "illusion": "ill",
          "necromancy": "nec", "transmutation": "trs"}


def clean(t):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.DOTALL)
    t = t.replace("&shy;", "").replace("­", "")
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<div[^>]*>|</div>|\\columnbreak|\\pagebreakNum", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def md_html(text):
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


def parse_level_school(line):
    s = line.strip().strip("*").strip().lower()
    ritual = "ritual" in s
    s = s.replace("(ritual)", "").strip()
    if "cantrip" in s:
        school = next((v for k, v in SCHOOL.items() if k in s), "evo")
        return 0, school, ritual
    m = re.match(r"(\d+)(?:st|nd|rd|th)[- ]level\s+(\w+)", s)
    if m:
        return int(m.group(1)), SCHOOL.get(m.group(2), "evo"), ritual
    return 0, "evo", ritual


def parse_range(v):
    v = v.strip()
    low = v.lower()
    special = ""
    if "(" in v:
        special = v[v.index("(") + 1:v.rindex(")")] if ")" in v else ""
    if low.startswith("self"):
        return {"value": None, "units": "self", "special": special}
    if low.startswith("touch"):
        return {"value": None, "units": "touch", "special": special}
    m = re.match(r"(\d+)", v)
    if m:
        return {"value": m.group(1), "units": "ft", "special": special}
    return {"value": None, "units": "", "special": special}


def parse_components(v):
    vv = v
    material = ""
    mm = re.search(r"M\s*\(([^)]*)\)", vv)
    if mm:
        material = mm.group(1).strip()
    props = []
    if re.search(r"\bV\b", vv):
        props.append("vocal")
    if re.search(r"\bS\b", vv):
        props.append("somatic")
    if re.search(r"\bM\b", vv):
        props.append("material")
    return props, material


def parse_duration(v):
    low = v.strip().lower()
    conc = "concentration" in low
    if "instant" in low:
        return {"units": "inst", "value": "", "concentration": False}
    m = re.search(r"(\d+)\s*(round|minute|hour|day)", low)
    if m:
        return {"units": m.group(2), "value": m.group(1), "concentration": conc}
    return {"units": "inst", "value": "", "concentration": conc}


def main():
    lines = open(HHB, encoding="utf-8").read().split("\n")
    # collect all #### blocks in the Spell Descriptions region
    blocks = {}
    cur, buf = None, []
    for i in range(8204, 8941):
        m = re.match(r"^#### (.+)", lines[i].strip())
        if m:
            if cur:
                blocks[cur.lower()] = buf
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(lines[i])
    if cur:
        blocks[cur.lower()] = buf

    out = []
    for name in USED:
        b = blocks.get(name, [])
        # first non-empty line = *level school*
        idx = 0
        while idx < len(b) and not b[idx].strip():
            idx += 1
        level, school, ritual = parse_level_school(b[idx])
        rec = {"name": name.title().replace("'S", "'s"), "level": level,
               "school": school, "ritual": ritual,
               "activation": {"type": "action", "value": 1, "condition": ""},
               "range": {}, "properties": [], "material": "",
               "duration": {}, "description": ""}
        desc_lines = []
        for l in b[idx + 1:]:
            s = l.strip()
            fm = re.match(r"-\s*\*\*(.+?):\*\*\s*(.*)", s)
            if fm:
                label, val = fm.group(1).strip().lower(), fm.group(2).strip()
                if label == "casting time":
                    lv = val.lower()
                    if "bonus action" in lv:
                        rec["activation"] = {"type": "bonus", "value": 1,
                                             "condition": ""}
                    elif "reaction" in lv:
                        cond = val.split(",", 1)[1].strip() if "," in val else ""
                        rec["activation"] = {"type": "reaction", "value": 1,
                                             "condition": cond}
                    elif "minute" in lv:
                        n = re.match(r"(\d+)", val)
                        rec["activation"] = {"type": "minute",
                                             "value": int(n.group(1)) if n else 1,
                                             "condition": ""}
                    else:
                        rec["activation"] = {"type": "action", "value": 1,
                                             "condition": ""}
                elif label == "range":
                    rec["range"] = parse_range(val)
                elif label == "components":
                    rec["properties"], rec["material"] = parse_components(val)
                elif label == "duration":
                    rec["duration"] = parse_duration(val)
            elif s in ("___", "___ ") or re.match(r"^_+$", s):
                continue
            elif s.startswith("<div") or s.startswith("<img") or not s:
                if desc_lines and desc_lines[-1] != "":
                    desc_lines.append("")
            else:
                desc_lines.append(clean(s))
        # build description HTML: paragraphs split on blank lines
        paras, cur_p = [], []
        for dl in desc_lines:
            if dl == "":
                if cur_p:
                    paras.append(" ".join(cur_p))
                    cur_p = []
            else:
                cur_p.append(dl)
        if cur_p:
            paras.append(" ".join(cur_p))
        rec["description"] = "".join(f"<p>{md_html(p)}</p>" for p in paras if p)
        if rec["ritual"]:
            rec["properties"].append("ritual")
        if rec["duration"].get("concentration"):
            rec["properties"].append("concentration")
        out.append(rec)

    with open(os.path.join(REPO, "intermediate", "wc5e_spells_src.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Extracted {len(out)} spell descriptions -> wc5e_spells_src.json")
    for r in out:
        lvl = "cantrip" if r["level"] == 0 else f"L{r['level']}"
        print(f"  {r['name']:20s} {lvl:8s} {r['school']} "
              f"{r['range'].get('units','')}/{r['range'].get('value','')} "
              f"props={r['properties']}")


if __name__ == "__main__":
    main()
