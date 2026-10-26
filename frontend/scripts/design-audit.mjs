// Design audit: counts how far the stylesheets stray from the design system.
// Run from frontend/: `node scripts/design-audit.mjs` (add --list to see values).
// Targets come from REDESIGN_PLAN.md section 1.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../src/", import.meta.url).pathname;
// Token files: the only places a raw colour value may live.
const TOKEN_FILES = ["styles/design-system.css", "styles/tokens.ts"];

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk(root).filter((f) => /\.(css|tsx?)$/.test(f) && !/\.test\.ts$/.test(f));
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

// Radii: count the lengths in use. Circles (50%), 0 and inherit are shapes,
// not radii; a calc() built on a token counts as that token.
const radii = () => {
  const seen = new Map();
  for (const f of css) for (const m of read(f).matchAll(/border(?:-[a-z]+)*-radius:\s*([^;}]+)/g)) {
    const value = m[1].replace("!important", "").trim();
    const parts = value.startsWith("calc(") ? (value.match(/var\(--[\w-]+\)/g) ?? [value]) : value.split(/\s+/);
    for (const part of parts) {
      if (["0", "50%", "inherit"].includes(part)) continue;
      seen.set(part, (seen.get(part) ?? 0) + 1);
    }
  }
  return seen;
};

// Breakpoints: count widths, treating a min-width one pixel past a max-width
// as the same breakpoint (1068 and 1069).
const breakpoints = () => {
  const seen = new Map();
  for (const f of css) for (const m of read(f).matchAll(/\((max|min)-width:\s*(\d+)px\)/g)) {
    const px = Number(m[2]) - (m[1] === "min" ? 1 : 0);
    seen.set(`${px}px`, (seen.get(`${px}px`) ?? 0) + 1);
  }
  return seen;
};

const rows = [
  ["Font sizes", distinct(css, /font-size:\s*([^;}]+)/g), 7],
  ["Font weights", distinct(css, /font-weight:\s*([^;}]+)/g), 3],
  ["Letter-spacing values", distinct(css, /letter-spacing:\s*([^;}]+)/g), 3],
  ["Corner radii", radii(), 4],
  ["Breakpoints", breakpoints(), 2],
  ["Raw hex colours (outside tokens)", distinct(files.filter((f) => !TOKEN_FILES.some((t) => f.endsWith(t))), /(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)/g), 0],
];

// Token integrity: every --aero-*/--fs-* used is defined, and none is defined as itself.
const tokenProblems = () => {
  const all = files.map(read).join("\n");
  const defined = new Set([...all.matchAll(/(--(?:aero|fs)-[\w-]+)\s*:/g)].map((m) => m[1]));
  const used = new Set([...all.matchAll(/var\((--(?:aero|fs)-[\w-]+)/g)].map((m) => m[1]));
  const selfRef = [...all.matchAll(/(--[\w-]+)\s*:\s*var\((--[\w-]+)\)/g)].filter((m) => m[1] === m[2]).map((m) => m[1]);
  return [...selfRef.map((t) => `${t} (defined as itself)`), ...[...used].filter((t) => !defined.has(t)).map((t) => `${t} (undefined)`)];
};

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
const problems = tokenProblems();
console.log(`${pad("Broken tokens", 36)}${pad(problems.length, 8)}0`);
if (problems.length) {
  console.log("   ", problems.join(", "));
  process.exitCode = 1;
}
