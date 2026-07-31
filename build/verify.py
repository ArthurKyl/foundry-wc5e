#!/usr/bin/env python3
"""
verify.py -- One gate over the whole module, independent of how content was made.

Generation is an implementation detail per content type; these invariants are not.
Every check here corresponds to a bug that actually shipped or was caught late, and
crucially they all work the same on hand-authored documents as on generated ones --
which is what makes hand-maintaining the class content safe.

Exits non-zero on any failure. Run with `npm run verify`.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

failures, warnings, notes = [], [], []

def fail(check, msg):
    failures.append((check, msg))

def warn(check, msg):
    warnings.append((check, msg))


def load_all():
    """-> manifest, {pack: [docs]}"""
    manifest = json.load(open(os.path.join(REPO, "module.json"), encoding="utf-8"))
    packs = {}
    for entry in manifest["packs"]:
        d = os.path.join(REPO, "src", entry["name"])
        docs = []
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".json"):
                    docs.append((fn, json.load(open(os.path.join(d, fn), encoding="utf-8"))))
        packs[entry["name"]] = docs
    return manifest, packs


def check_packs_present(manifest, packs):
    for entry in manifest["packs"]:
        if not packs[entry["name"]]:
            fail("packs", f"{entry['name']} declared in module.json but src/ is empty or missing")
        compiled = os.path.join(REPO, entry["path"])
        if not os.path.isdir(compiled) or not any(f.endswith(".ldb") for f in os.listdir(compiled)):
            fail("packs", f"{entry['name']} has no compiled .ldb at {entry['path']} -- run npm run pack")


def check_ids_and_keys(packs):
    """Duplicate ids silently overwrite each other at compile time."""
    for pack, docs in packs.items():
        seen = defaultdict(list)
        for fn, d in docs:
            if not d.get("_id"):
                fail("ids", f"{pack}/{fn} has no _id")
                continue
            seen[d["_id"]].append(fn)
            if not d.get("_key"):
                fail("keys", f"{pack}/{fn} has no _key")
            elif not re.match(r"^!(actors|items|journal|folders)(\.\w+)?!", d["_key"]):
                fail("keys", f"{pack}/{fn} has an unrecognised _key: {d['_key']}")
        for _id, files in seen.items():
            if len(files) > 1:
                fail("ids", f"{pack}: _id {_id} used by {len(files)} documents: {', '.join(files[:3])}")


def check_references(packs):
    """Every internal UUID must resolve. A broken ItemGrant is a silent no-op."""
    ids = {pack: {d["_id"] for _, d in docs if d.get("_id")} for pack, docs in packs.items()}
    SELF = re.compile(r"Compendium\.wc5e-bestiary\.([A-Za-z0-9_-]+)\.(?:[A-Za-z]+\.)?([A-Za-z0-9]{10,})")
    total, ccc = 0, 0
    for pack, docs in packs.items():
        for fn, d in docs:
            raw = json.dumps(d, ensure_ascii=False)
            if "wc5e-ccc" in raw:
                ccc += 1
                fail("references", f"{pack}/{fn} still references the old wc5e-ccc module")
            for m in SELF.finditer(raw):
                total += 1
                target_pack, target_id = m.group(1), m.group(2)
                if target_pack not in ids:
                    fail("references", f"{pack}/{fn} points at unknown pack '{target_pack}'")
                elif target_id not in ids[target_pack]:
                    fail("references", f"{pack}/{fn} dangling -> {target_pack}.{target_id}")
    notes.append(f"{total} internal references checked")


def check_assets(packs):
    ASSET = re.compile(r"modules/wc5e-bestiary/([A-Za-z0-9/_.\-]+?\.(?:svg|png|webp|jpg|jpeg))")
    missing, total = set(), 0
    for pack, docs in packs.items():
        for fn, d in docs:
            for m in ASSET.finditer(json.dumps(d, ensure_ascii=False)):
                total += 1
                if not os.path.exists(os.path.join(REPO, m.group(1))):
                    missing.add(m.group(1))
    for p in sorted(missing):
        fail("assets", f"referenced but not on disk: {p}")
    notes.append(f"{total} asset references checked")


def check_spell_lists(manifest, packs):
    """dnd5e registers spell lists ONLY from flags.dnd5e.spellLists, and rejects any
    entry whose page type isn't 'spells'. Getting this wrong makes the lists inert
    with no error -- exactly how v1.7.0 and v1.8.0 shipped."""
    declared = (manifest.get("flags", {}).get("dnd5e", {}) or {}).get("spellLists")
    if not isinstance(declared, list) or not declared:
        fail("spellLists", "module.json flags.dnd5e.spellLists missing or empty -- "
                           "every spell list will be silently inert")
        return set()
    pages = {}
    for _, d in packs.get("spell-lists", []):
        for p in d.get("pages", []):
            pages[(d["_id"], p["_id"])] = p
    identifiers = set()
    for uuid in declared:
        parts = uuid.split(".")
        if len(parts) < 7 or parts[3] != "JournalEntry" or parts[5] != "JournalEntryPage":
            fail("spellLists", f"not a JournalEntryPage uuid: {uuid}")
            continue
        page = pages.get((parts[4], parts[6]))
        if page is None:
            fail("spellLists", f"registered uuid resolves to nothing: {uuid}")
        elif page.get("type") != "spells":
            fail("spellLists", f"registered page is type '{page.get('type')}', not 'spells': {uuid}")
        else:
            identifiers.add(page["system"]["identifier"])
            if not page["system"].get("spells"):
                warn("spellLists", f"'{page['system']['identifier']}' list is empty")
    # every page in the pack should be registered
    for (jid, pid), p in pages.items():
        if p.get("type") != "spells":
            continue
        if not any(f".{jid}.JournalEntryPage.{pid}" in u for u in declared):
            fail("spellLists", f"page '{p['system']['identifier']}' exists but is NOT registered")
    notes.append(f"{len(identifiers)} spell lists registered")
    return identifiers


def check_advancement(packs, list_identifiers):
    """Advancement fails silently: a duplicate id, an empty choice pool, or a level
    key the flow never visits all produce no prompt and no error."""
    for pack in ("classes", "races", "backgrounds", "class-features", "feats"):
        for fn, d in packs.get(pack, []):
            sys_ = d.get("system")
            if not isinstance(sys_, dict):
                continue
            adv = sys_.get("advancement") or []
            ids = Counter(a.get("_id") for a in adv)
            for _id, n in ids.items():
                if n > 1:
                    fail("advancement", f"{pack}/{fn} has {n} advancements sharing _id {_id}")
            for a in adv:
                cfg = a.get("configuration") or {}
                if a.get("type") == "ItemChoice" and cfg.get("type") == "spell":
                    lists = (cfg.get("restriction") or {}).get("list") or []
                    if not lists and not cfg.get("pool"):
                        fail("advancement", f"{pack}/{fn}: ItemChoice(spell) '{a.get('title')}' "
                                            f"has neither a restriction list nor a pool")
                    for entry in lists:
                        ident = entry.split(":", 1)[-1]
                        if ident not in list_identifiers:
                            fail("advancement", f"{pack}/{fn}: ItemChoice '{a.get('title')}' "
                                                f"restricted to '{entry}' but no such spell list "
                                                f"is registered")
                    for lvl, spec in (cfg.get("choices") or {}).items():
                        if not str(lvl).isdigit():
                            fail("advancement", f"{pack}/{fn}: non-numeric choice level '{lvl}'")
                        elif d.get("type") not in ("class", "subclass") and int(lvl) > 1:
                            warn("advancement", f"{pack}/{fn}: '{a.get('title')}' keyed at level "
                                                f"{lvl} on a non-class item; flows run 0..current so "
                                                f"'1' is the safe key")


def check_sources(manifest, packs):
    declared = (manifest.get("flags", {}).get("dnd5e", {}) or {}).get("sourceBooks") or {}
    SYSTEM = {"SRD 5.1", "SRD 5.2", "Free Rules"}
    used = Counter()
    for pack, docs in packs.items():
        for fn, d in docs:
            s = (d.get("system") or {}).get("source")
            if not isinstance(s, dict):
                continue
            value = (s.get("custom") or s.get("book") or "").strip()
            if not value:
                continue
            used[value] += 1
            if re.match(r"^(https?://|www\.)", value):
                fail("sources", f"{pack}/{fn} cites a URL as its source book: {value}")
    for value in used:
        if value not in SYSTEM and value not in declared:
            fail("sources", f"source '{value}' used by {used[value]} documents but not declared "
                            f"in flags.dnd5e.sourceBooks -- the browser will show it raw")
    notes.append(f"{len(used)} distinct source books")


def check_spell_coverage(packs, list_identifiers):
    """A spell on no class list is unreachable in play."""
    cited = set()
    for _, d in packs.get("spell-lists", []):
        for p in d.get("pages", []):
            for u in p.get("system", {}).get("spells", []):
                if ".wc5e-bestiary.spells.Item." in u:
                    cited.add(u.rsplit(".", 1)[1])
    ours = {d["_id"]: d["name"] for fn, d in packs.get("spells", [])
            if d.get("type") == "spell"}
    orphans = sorted(name for _id, name in ours.items() if _id not in cited)
    for n in orphans:
        warn("spells", f"'{n}' is on no class spell list -- unreachable in play")
    notes.append(f"{len(ours) - len(orphans)}/{len(ours)} spells reachable from a class list")


def check_release_shape(manifest):
    v = manifest.get("version")
    dl = manifest.get("download", "")
    if not dl.endswith(f"/releases/download/v{v}/module.zip"):
        fail("release", f"download URL doesn't match version {v}: {dl}")
    if "/releases/latest/download/module.json" not in manifest.get("manifest", ""):
        fail("release", "manifest URL should be the releases/latest form so Foundry sees updates")


def main():
    manifest, packs = load_all()
    check_packs_present(manifest, packs)
    check_ids_and_keys(packs)
    check_references(packs)
    check_assets(packs)
    idents = check_spell_lists(manifest, packs)
    check_advancement(packs, idents)
    check_sources(manifest, packs)
    check_spell_coverage(packs, idents)
    check_release_shape(manifest)

    total = sum(len(d) for d in packs.values())
    print(f"  {total} documents across {len(packs)} packs")
    for n in notes:
        print(f"  · {n}")
    if warnings:
        print(f"\n  {len(warnings)} warning(s):")
        for c, m in warnings[:20]:
            print(f"    [{c}] {m}")
        if len(warnings) > 20:
            print(f"    … and {len(warnings) - 20} more")
    if failures:
        print(f"\n  {len(failures)} FAILURE(S):")
        for c, m in failures[:40]:
            print(f"    [{c}] {m}")
        if len(failures) > 40:
            print(f"    … and {len(failures) - 40} more")
        sys.exit(1)
    print("\n  all checks passed")


if __name__ == "__main__":
    main()
