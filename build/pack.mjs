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
const src = path.join(repo, "src", "monsters");
const dest = path.join(repo, "packs", "monsters");

// Ensure a clean destination so removed monsters don't linger in the pack.
fs.rmSync(dest, { recursive: true, force: true });
fs.mkdirSync(dest, { recursive: true });

console.log(`Compiling ${src} -> ${dest}`);
await compilePack(src, dest, { log: true, recursive: false });
console.log("Done.");
