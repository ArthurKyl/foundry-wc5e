/**
 * pack.mjs -- Compile src/monsters/*.json into the LevelDB compendium pack at
 * packs/monsters using the official Foundry CLI. Run: `npm run pack`.
 */
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repo = path.dirname(__dirname);

// Each source folder under src/ compiles to a like-named pack under packs/.
const PACKS = ["monsters", "items", "spells"];

for ( const name of PACKS ) {
  const src = path.join(repo, "src", name);
  if ( !fs.existsSync(src) ) { console.log(`skip ${name} (no source)`); continue; }
  const dest = path.join(repo, "packs", name);
  // Clean destination so removed documents don't linger in the pack.
  fs.rmSync(dest, { recursive: true, force: true });
  fs.mkdirSync(dest, { recursive: true });
  console.log(`Compiling ${src} -> ${dest}`);
  await compilePack(src, dest, { log: true, recursive: false });
}
console.log("Done.");
