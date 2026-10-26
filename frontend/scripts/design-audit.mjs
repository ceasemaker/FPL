// Design audit: counts how far the stylesheets stray from the design system.
// Run from frontend/: `node scripts/design-audit.mjs` (add --list to see values).
// Targets come from REDESIGN_PLAN.md section 1.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../src/", import.meta.url).pathname;
const TOKEN_FILE = "styles/design-system.css";

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk(root).filter((f) => /\.(css|tsx)$/.test(f));
const css = files.filter((f) => f.endsWith(".css"));
const read = (f) => readFileSync(f, "utf8");

const distinct = (list, re) => {
  const seen = new Map();
  for (const f of list) for (const m of read(f).matchAll(re)) {
    const v = m[1].trim().replace(/\s+/g, " ");
    seen.set(v, (seen.get(v) ?? 0) + 1);
  }
  return seen;
};

const rows = [
  ["Font sizes", distinct(css, /font-size:\s*([^;}]+)/g), 7],
  ["Font weights", distinct(css, /font-weight:\s*([^;}]+)/g), 3],
  ["Letter-spacing values", distinct(css, /letter-spacing:\s*([^;}]+)/g), 3],
  ["Corner radii", distinct(css, /border-radius:\s*([^;}]+)/g), 4],
  ["Breakpoints", distinct(css, /@media\s*([^{]*\bwidth[^{]*)/g), 2],
  ["Raw hex colours (outside tokens)", distinct(files.filter((f) => !f.endsWith(TOKEN_FILE)), /(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)/g), 0],
];

const count = (list, re) => list.reduce((n, f) => n + (read(f).match(re)?.length ?? 0), 0);
const singles = [
  ["All-caps labels", count(css, /text-transform:\s*uppercase/g), 0],
  ["Inline style={{}} in TSX", count(files.filter((f) => f.endsWith(".tsx")), /style=\{\{/g), null],
];

const list = process.argv.includes("--list");
const pad = (s, n) => String(s).padEnd(n);
console.log(`${pad("Measure", 36)}${pad("Now", 8)}Target`);
for (const [name, map, target] of rows) {
  console.log(`${pad(name, 36)}${pad(map.size, 8)}${target}`);
  if (list) console.log("   ", [...map].sort((a, b) => b[1] - a[1]).map(([v, n]) => `${v} (${n})`).join(", "));
}
for (const [name, n, target] of singles) console.log(`${pad(name, 36)}${pad(n, 8)}${target ?? "-"}`);
