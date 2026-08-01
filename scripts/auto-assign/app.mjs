import { loadManifest, manifestTotals } from "./manifest.mjs";
import { buildPackTree, packIdsUnder, selectedPackIds, nodeState } from "./tree.mjs";
import { buildSearchIndex } from "./index.mjs";
import { buildPlan, listsAvailable, TARGETS, DESTINATIONS } from "./plan.mjs";
import { collectState, applyPlan, MODULE_ID } from "./apply.mjs";

const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

export const SETTINGS = {
  packs: "autoAssign.searchPacks",
  targets: "autoAssign.targets",
  destination: "autoAssign.destination",
  dismissed: "autoAssign.promptDismissed",
  promptedVersion: "autoAssign.lastPromptedVersion",
};

/** Registered once; the tree template recurses through this partial. */
export async function registerTemplates() {
  const path = "modules/wc5e-bestiary/templates/auto-assign/nodes.hbs";
  const [tpl] = await foundry.applications.handlebars.loadTemplates([path]);
  Handlebars.registerPartial("wc5eAutoAssignNodes", tpl);
}

export function registerHelpers() {
  Handlebars.registerHelper("wc5eEq", (a, b) => a === b);
  Handlebars.registerHelper("wc5eNot", a => !a);
  Handlebars.registerHelper("wc5eAnd", (a, b) => !!(a && b));
}

export class AutoAssignApp extends HandlebarsApplicationMixin(ApplicationV2) {
  static DEFAULT_OPTIONS = {
    id: "wc5e-auto-assign",
    tag: "form",
    window: { title: "WC5E.AutoAssign.Title", icon: "fa-solid fa-wand-magic-sparkles",
              resizable: true },
    position: { width: 640, height: 720 },
    actions: {
      scan: AutoAssignApp.#onScan,
      apply: AutoAssignApp.#onApply,
      back: AutoAssignApp.#onBack,
      copy: AutoAssignApp.#onCopy,
    },
  };

  static PARTS = {
    body: { template: "modules/wc5e-bestiary/templates/auto-assign/configure.hbs" },
    footer: { template: "templates/generic/form-footer.hbs" },
  };

  /** @type {"configure"|"preview"|"report"} */
  #stage = "configure";
  #manifest = null;
  #tree = [];
  #checked = new Set();
  #expanded = new Set();
  #plan = null;
  #indexFailures = [];
  #result = null;
  #busy = false;

  static async show() {
    const app = new AutoAssignApp();
    await app.render(true);
    return app;
  }

  /**
   * ApplicationV2 awaits this before the first render, which is what lets the
   * settings menu instantiate this class directly instead of needing a shim.
   */
  async _preFirstRender(context, options) {
    await super._preFirstRender(context, options);
    try {
      await this.#init();
    }
    catch ( err ) {
      console.error("wc5e-bestiary | could not open auto-assign", err);
      ui.notifications.error(game.i18n.format("WC5E.AutoAssign.LoadFailed",
        { error: err.message ?? String(err) }));
      throw err;   // don't open a half-built window
    }
  }

  async #init() {
    this.#manifest = await loadManifest();
    this.#tree = buildPackTree({
      folders: game.folders.filter(f => f.type === "Compendium")
        .map(f => ({ id: f.id, name: f.name, parentId: f.folder?.id ?? null })),
      packs: game.packs.filter(p => p.documentName === "Item")
        .map(p => ({ id: p.collection, name: p.metadata.label, folderId: p.folder?.id ?? null })),
    });
    const saved = game.settings.get(MODULE_ID, SETTINGS.packs) ?? [];
    this.#checked = new Set(saved.filter(id => game.packs.get(id)));
  }

  get #destination() {
    return game.settings.get(MODULE_ID, SETTINGS.destination) ?? DESTINATIONS.BOTH;
  }

  get #targets() {
    return game.settings.get(MODULE_ID, SETTINGS.targets) ?? { monsters: true, spellLists: true };
  }

  _configureRenderParts(options) {
    const parts = super._configureRenderParts(options);
    const template = {
      configure: "configure.hbs", preview: "preview.hbs", report: "report.hbs",
    }[this.#stage];
    parts.body = { template: `modules/wc5e-bestiary/templates/auto-assign/${template}` };
    return parts;
  }

  async _prepareContext(options) {
    const context = await super._prepareContext(options);
    context.stage = this.#stage;
    if ( this.#stage === "configure" ) return Object.assign(context, this.#configureContext());
    if ( this.#stage === "preview" ) return Object.assign(context, this.#previewContext());
    return Object.assign(context, this.#reportContext());
  }

  #configureContext() {
    const destination = this.#destination;
    const targets = this.#targets;
    const available = listsAvailable(destination);
    const decorate = nodes => nodes.map(n => ({
      ...n,
      state: nodeState(n, this.#checked),
      expanded: this.#expanded.has(n.id),
      children: n.type === "folder" ? decorate(n.children) : [],
    }));
    return {
      totals: manifestTotals(this.#manifest),
      targets: { monsters: targets.monsters, lists: available && targets.spellLists },
      listsAvailable: available,
      destinations: [
        { value: DESTINATIONS.BOTH, label: game.i18n.localize("WC5E.AutoAssign.DestBoth") },
        { value: DESTINATIONS.COMPENDIUM, label: game.i18n.localize("WC5E.AutoAssign.DestPacks") },
        { value: DESTINATIONS.WORLD, label: game.i18n.localize("WC5E.AutoAssign.DestWorld") },
      ].map(d => ({ ...d, chosen: d.value === destination })),
      tree: decorate(this.#tree),
      buttons: [{ type: "button", action: "scan", icon: "fa-solid fa-magnifying-glass",
                  label: "WC5E.AutoAssign.Scan", disabled: this.#busy || !this.#checked.size }],
    };
  }

  #previewContext() {
    return {
      counts: this.#plan.counts,
      indexFailures: this.#indexFailures,
      writes: this.#plan.writes.map(w => ({
        ...w,
        scopeLabel: w.kind === "list"
          ? game.i18n.localize("WC5E.AutoAssign.ScopeList")
          : game.i18n.localize(w.scope === "pack"
            ? "WC5E.AutoAssign.ScopePack" : "WC5E.AutoAssign.ScopeWorld"),
      })),
      buttons: [
        { type: "button", action: "back", icon: "fa-solid fa-arrow-left",
          label: "WC5E.AutoAssign.Back" },
        { type: "button", action: "apply", icon: "fa-solid fa-check",
          label: "WC5E.AutoAssign.Apply",
          disabled: this.#busy || !this.#plan.writes.length },
      ],
    };
  }

  #reportContext() {
    // Grouped by source book so a GM can tell "I'm missing a whole book" from
    // "I'm missing three spells". Monster records carry no source, so those
    // land in the unknown bucket.
    const groups = new Map();
    for ( const n of this.#plan.notFound ) {
      const key = n.source || "";
      if ( !groups.has(key) ) groups.set(key, []);
      groups.get(key).push({
        ...n,
        wantedByLabel: n.wantedBy.slice(0, 3).join(", ")
          + (n.wantedBy.length > 3 ? ` +${n.wantedBy.length - 3}` : ""),
      });
    }
    const label = k => k || game.i18n.localize("WC5E.AutoAssign.SourceUnknown");
    return {
      result: this.#result,
      notFoundCount: this.#plan.notFound.length,
      notFoundGroups: [...groups.entries()]
        .sort((a, b) => label(a[0]).localeCompare(label(b[0])))
        .map(([source, spells]) => ({ label: label(source), spells })),
      buttons: [{ type: "button", action: "back", icon: "fa-solid fa-arrow-left",
                  label: "WC5E.AutoAssign.Done" }],
    };
  }

  _onRender(context, options) {
    super._onRender(context, options);
    if ( this.#stage !== "configure" ) return;

    for ( const el of this.element.querySelectorAll(".wc5e-aa-check") ) {
      const node = this.#findNode(el.dataset.nodeId);
      if ( node ) el.indeterminate = nodeState(node, this.#checked) === "indeterminate";
      el.addEventListener("change", ev => this.#onToggleNode(ev));
    }
    for ( const el of this.element.querySelectorAll(".wc5e-aa-toggle") ) {
      el.addEventListener("click", ev => {
        ev.preventDefault();
        const id = ev.currentTarget.dataset.nodeId;
        if ( this.#expanded.has(id) ) this.#expanded.delete(id);
        else this.#expanded.add(id);
        this.render();
      });
    }
    this.element.querySelector("[name=destination]")?.addEventListener("change", async ev => {
      await game.settings.set(MODULE_ID, SETTINGS.destination, ev.target.value);
      this.render();
    });
    for ( const [name, key] of [["target-monsters", "monsters"], ["target-lists", "spellLists"]] ) {
      this.element.querySelector(`[name="${name}"]`)?.addEventListener("change", async ev => {
        await game.settings.set(MODULE_ID, SETTINGS.targets,
          { ...this.#targets, [key]: ev.target.checked });
        this.render();
      });
    }
  }

  #findNode(id, nodes = this.#tree) {
    for ( const n of nodes ) {
      if ( n.id === id ) return n;
      if ( n.type === "folder" ) {
        const hit = this.#findNode(id, n.children);
        if ( hit ) return hit;
      }
    }
    return null;
  }

  #onToggleNode(ev) {
    const node = this.#findNode(ev.currentTarget.dataset.nodeId);
    if ( !node ) return;
    const ids = packIdsUnder(node);
    if ( ev.currentTarget.checked ) ids.forEach(id => this.#checked.add(id));
    else ids.forEach(id => this.#checked.delete(id));
    this.render();
  }

  static async #onScan() {
    if ( this.#busy ) return;
    this.#busy = true;
    try {
      const packIds = selectedPackIds(this.#tree, this.#checked);
      await game.settings.set(MODULE_ID, SETTINGS.packs, packIds);

      const targets = [];
      const chosen = this.#targets;
      if ( chosen.monsters ) targets.push(TARGETS.MONSTERS);
      if ( chosen.spellLists && listsAvailable(this.#destination) ) targets.push(TARGETS.LISTS);
      if ( !targets.length ) {
        ui.notifications.warn(game.i18n.localize("WC5E.AutoAssign.NoTargets"));
        return;
      }

      const index = await buildSearchIndex(packIds, { aliases: this.#manifest.aliases });
      this.#indexFailures = index.failed;
      const state = await collectState({ manifest: this.#manifest, targets,
                                         destination: this.#destination });
      this.#plan = buildPlan({ manifest: this.#manifest, index, targets,
                               destination: this.#destination, state });
      this.#stage = "preview";
    }
    catch ( err ) {
      console.error("wc5e-bestiary | auto-assign scan failed", err);
      ui.notifications.error(game.i18n.format("WC5E.AutoAssign.ScanFailed", { error: err.message }));
    }
    finally {
      this.#busy = false;
      this.render();
    }
  }

  static async #onApply() {
    if ( this.#busy ) return;
    this.#busy = true;
    this.render();
    try {
      this.#result = await applyPlan(this.#plan);
      this.#stage = "report";
    }
    catch ( err ) {
      console.error("wc5e-bestiary | auto-assign apply failed", err);
      ui.notifications.error(game.i18n.format("WC5E.AutoAssign.ApplyFailed", { error: err.message }));
    }
    finally {
      this.#busy = false;
      this.render();
    }
  }

  static #onBack() {
    this.#stage = "configure";
    this.render();
  }

  static async #onCopy() {
    const text = this.#plan.notFound.map(n => n.name).join("\n");
    await game.clipboard.copyPlainText(text);
    ui.notifications.info(game.i18n.localize("WC5E.AutoAssign.Copied"));
  }
}
