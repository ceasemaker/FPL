// Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";

import { percentile, qualifies, shade, statValue, type ExplorerPlayer, type Stat } from "./explorerModel.ts";

const count = (key: string, raw: string[], extra: Partial<Stat> = {}): Stat => ({
  key, label: key, group: "g", kind: "count", raw, help: "", plOnly: false, source: "Opta", lowerIsBetter: false, ...extra,
});

const player = (pl: Record<string, number | null>, ucl: Record<string, number | null> | null = null): ExplorerPlayer => ({
  id: 1, name: "P", team: "T", teamId: 1, position: "FWD", status: "a", news: "", fpl: {}, pl, ucl,
});

test("shading follows size: a big gap is visible, a tiny gap is not", () => {
  // Big chances per 90 among forwards, ascending.
  const cohort = [0.2, 0.3, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01, 1.04, 1.05, 1.06, 1.08, 1.08, 1.2, 1.4, 1.7, 2.0, 2.32];
  const stat = count("big_chances", ["big_chance_missed"]);
  const at = (v: number) => shade(stat, "FWD", v, cohort, percentile(v, cohort, false), "p90")!;
  assert.ok(at(1.7).level - at(1.08).level > 0.25, "1.70 should read clearly brighter than 1.08");
  assert.ok(Math.abs(at(1.08).level - at(1.06).level) < 0.02, "1.08 and 1.06 should look the same");
  assert.equal(at(2.32).top, true);
  assert.equal(at(1.08).top, false);
  assert.equal(at(1.7).top, false, "lime stays rare: only the very top");
});

test("DefCon columns shade against FPL's thresholds per 90", () => {
  const cbit = count("cbit", ["total_clearance"]);
  const cohort = [4, 6, 8, 9, 11];
  const onTrack = shade(cbit, "DEF", 10.5, cohort, 90, "p90")!;
  const short = shade(cbit, "DEF", 7.5, cohort, 40, "p90")!;
  assert.equal(onTrack.defcon, 10);
  assert.equal(onTrack.top, true);
  assert.equal(short.top, false);
  assert.equal(short.level, 0.75);
  // CBIT is not a midfielder's scoring rule, so it falls back to size shading.
  assert.equal(shade(cbit, "MID", 10.5, cohort, 90, "p90")!.defcon, undefined);
});

test("PL-only stats need Premier League minutes even when UCL is included", () => {
  const xg = count("xg", ["expectedGoals"], { plOnly: true });
  const goals = count("goals", ["goals"]);
  const foden = player({ mins_played: 219, expectedGoals: 1.6, goals: 1 }, { mins_played: 75, goals: 0 });
  assert.equal(qualifies(xg, foden, "all", 270), false);
  assert.equal(qualifies(goals, foden, "all", 270), true);
});

test("a feed gap stays a gap instead of becoming 0", () => {
  const xgot = count("xgot", ["expectedGoalsOnTarget"], { plOnly: true });
  assert.equal(statValue(xgot, player({ mins_played: 450, expectedGoalsOnTarget: null }), "pl", "p90"), null);
  assert.equal(statValue(xgot, player({ mins_played: 450, expectedGoalsOnTarget: 0 }), "pl", "p90"), 0);
});
