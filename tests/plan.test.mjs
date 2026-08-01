import { test } from "node:test";
import assert from "node:assert/strict";
import { buildPlan, listsAvailable, TARGETS, DESTINATIONS }
  from "../scripts/auto-assign/plan.mjs";

const MANIFEST = {
  aliases: {},
  monsters: {
    m1: { name: "Frost Revenant", pack: "monsters", spells: [
      { name: "Ice Knife", key: "ice knife", prep: "prepared", level: 1, perDay: null },
      { name: "Shape Water", key: "shape water", prep: "atwill", level: 0, perDay: null },
    ] },
    m2: { name: "Fel Imp", pack: "monsters", spells: [
      { name: "Hex", key: "hex", prep: "innate", level: 1, perDay: 2 },
    ] },
  },
  spellLists: {
    "j.p1": { name: "Mage Spells", identifier: "wc5e-mage", pack: "spell-lists", spells: [
      { name: "Synaptic Static", key: "synaptic static", source: "XGE" },
      { name: "Ice Knife", key: "ice knife", source: "XGE" },
    ] },
  },
};

const MATCHES = {
  "ice knife": { uuid: "Compendium.x.Item.1", name: "Ice Knife", packId: "x", packLabel: "X" },
  "hex": { uuid: "Compendium.x.Item.2", name: "Hex", packId: "x", packLabel: "X" },
};
const index = { get: k => MATCHES[k], size: 2, failed: [] };

function state({ have = {}, listHave = [], scopes = { m1: "pack", m2: "pack" } } = {}) {
  return {
    monsters: Object.keys(MANIFEST.monsters).map(id => ({
      id, name: MANIFEST.monsters[id].name, scope: scopes[id],
      uuid: `Compendium.wc5e-bestiary.monsters.Actor.${id}`,
      haveKeys: new Set(have[id] ?? []),
    })),
    lists: [{ pageKey: "j.p1", name: "Mage Spells",
              uuid: "Compendium.wc5e-bestiary.spell-lists.JournalEntry.j.JournalEntryPage.p1",
              haveUuids: new Set(listHave) }],
  };
}

const ALL = [TARGETS.MONSTERS, TARGETS.LISTS];

test("plans the matches it found and reports the rest", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH, state: state() });
  assert.equal(p.counts.spells, 2);        // ice knife on m1, hex on m2
  assert.equal(p.counts.monsters, 2);
  assert.equal(p.counts.listEntries, 1);   // ice knife on the mage list
  assert.deepEqual(p.notFound.map(n => n.key), ["shape water", "synaptic static"]);
});

test("not-found records name who wanted them", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH, state: state() });
  const sw = p.notFound.find(n => n.key === "shape water");
  assert.deepEqual(sw.wantedBy, ["Frost Revenant"]);
  assert.equal(sw.name, "Shape Water");
});

test("not-found carries the source book when a record has one", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH, state: state() });
  assert.equal(p.notFound.find(n => n.key === "synaptic static").source, "XGE");
  assert.equal(p.notFound.find(n => n.key === "shape water").source, "");
});

test("carries preparation mode and per-day uses onto the write", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH, state: state() });
  const imp = p.writes.find(w => w.targetName === "Fel Imp");
  assert.equal(imp.spells[0].prep, "innate");
  assert.equal(imp.spells[0].perDay, 2);
  assert.equal(imp.spells[0].match.uuid, "Compendium.x.Item.2");
});

test("skips a spell the monster already has", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH,
                        state: state({ have: { m1: ["ice knife"] } }) });
  assert.equal(p.counts.spells, 1);
  assert.equal(p.writes.find(w => w.targetName === "Frost Revenant"), undefined);
});

test("skips a list entry that already points at that spell", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH,
                        state: state({ listHave: ["Compendium.x.Item.1"] }) });
  assert.equal(p.counts.listEntries, 0);
});

test("a fully satisfied plan is empty — the second run adds nothing", () => {
  const p = buildPlan({
    manifest: MANIFEST, index, targets: ALL, destination: DESTINATIONS.BOTH,
    state: state({ have: { m1: ["ice knife"], m2: ["hex"] },
                   listHave: ["Compendium.x.Item.1"] }),
  });
  assert.equal(p.writes.length, 0);
  assert.equal(p.counts.spells, 0);
  assert.equal(p.counts.listEntries, 0);
});

test("still reports not-found on a second run", () => {
  const p = buildPlan({
    manifest: MANIFEST, index, targets: ALL, destination: DESTINATIONS.BOTH,
    state: state({ have: { m1: ["ice knife"], m2: ["hex"] },
                   listHave: ["Compendium.x.Item.1"] }),
  });
  assert.equal(p.counts.notFound, 2);
});

test("monsters-only target skips the lists", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: [TARGETS.MONSTERS],
                        destination: DESTINATIONS.BOTH, state: state() });
  assert.equal(p.counts.listEntries, 0);
  assert.ok(!p.notFound.some(n => n.key === "synaptic static"));
});

test("lists-only target skips the monsters", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: [TARGETS.LISTS],
                        destination: DESTINATIONS.BOTH, state: state() });
  assert.equal(p.counts.spells, 0);
  assert.equal(p.counts.listEntries, 1);
});

test("world destination writes no list entries — lists exist only in the compendium", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.WORLD,
                        state: state({ scopes: { m1: "world", m2: "world" } }) });
  assert.equal(p.counts.listEntries, 0);
  assert.equal(p.counts.spells, 2);
});

test("listsAvailable is false only for the world destination", () => {
  assert.equal(listsAvailable(DESTINATIONS.WORLD), false);
  assert.equal(listsAvailable(DESTINATIONS.BOTH), true);
  assert.equal(listsAvailable(DESTINATIONS.COMPENDIUM), true);
});

test("compendium destination skips world-scoped monsters", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.COMPENDIUM,
                        state: state({ scopes: { m1: "world", m2: "pack" } }) });
  assert.deepEqual(p.writes.filter(w => w.kind === "monster").map(w => w.targetName),
    ["Fel Imp"]);
});

test("world destination skips pack-scoped monsters", () => {
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.WORLD,
                        state: state({ scopes: { m1: "world", m2: "pack" } }) });
  assert.deepEqual(p.writes.filter(w => w.kind === "monster").map(w => w.targetName),
    ["Frost Revenant"]);
});

test("a monster in the manifest but absent from state is ignored", () => {
  const s = state();
  s.monsters = s.monsters.filter(m => m.id === "m1");
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH, state: s });
  assert.equal(p.writes.filter(w => w.kind === "monster").length, 1);
});

test("the same monster imported twice gets one write each", () => {
  const s = state();
  s.monsters.push({ id: "m1", name: "Frost Revenant", scope: "world",
                    uuid: "Actor.copy", haveKeys: new Set() });
  const p = buildPlan({ manifest: MANIFEST, index, targets: ALL,
                        destination: DESTINATIONS.BOTH, state: s });
  assert.equal(p.writes.filter(w => w.targetName === "Frost Revenant").length, 2);
  assert.equal(p.counts.spells, 3);
});

test("an empty index puts everything in not-found and plans nothing", () => {
  const p = buildPlan({ manifest: MANIFEST, index: { get: () => undefined, size: 0, failed: [] },
                        targets: ALL, destination: DESTINATIONS.BOTH, state: state() });
  assert.equal(p.writes.length, 0);
  assert.equal(p.counts.notFound, 4);
});
