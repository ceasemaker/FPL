// Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";

import type { ExplorerPayload, ExplorerPlayer, Stat } from "../statsExplorer/explorerModel.ts";
import { buildReport, rankText } from "./reportModel.ts";

const stat = (key: string, extra: Partial<Stat> = {}): Stat => ({
  key, label: key[0].toUpperCase() + key.slice(1), group: "g", kind: "count", raw: [key], help: "", plOnly: false,
  source: "Opta", lowerIsBetter: false, ...extra,
});
const catalogue: Stat[] = [
  stat("goals"), stat("assists"), stat("xg", { label: "xG" }),
  stat("shot_accuracy", { label: "Shot accuracy", kind: "rate", raw: undefined, num: ["on_target"], den: ["shots"] }),
  stat("recoveries"), stat("starts", { per90: false, raw: ["game_started"] }),
];
const forward = (id: number, name: string, mins: number, goals: number, recoveries: number): ExplorerPlayer => ({
  id, name, team: "AAA", teamId: 1, position: "FWD", status: "a", news: "", fpl: {}, ucl: null,
  pl: { mins_played: mins, goals, assists: 1, xg: goals - 1, on_target: 10, shots: 20, recoveries, game_started: Math.round(mins / 90) },
});
const payload = {
  season: 2025, seasonLabel: "2025/26", latestGameweek: 38, minMinutes: 900, smallSample: 450, catalogue,
  lenses: {}, teamCatalogue: [], uclTeamIds: [], uclClubRule: "", teams: [],
  players: [forward(1, "Striker", 2700, 20, 10), forward(2, "Second", 2000, 12, 40), forward(3, "Third", 1800, 6, 30), forward(4, "Bit-part", 300, 3, 5)],
} as unknown as ExplorerPayload;

test("ranks against same-position players over the minutes bar only", () => {
  const r = buildReport(payload, 1)!;
  assert.equal(r.group, 3, "the 300-minute player is left out");
  const goals = r.sections[0].rows.find((x) => x.stat.key === "goals")!;
  assert.equal(goals.rank, 1);
  assert.equal(rankText(goals, r), "1st of 3 forwards");
  assert.equal(goals.totalDisplay, "20");
});

test("strengths and weaker areas come from the percentiles", () => {
  const r = buildReport(payload, 1)!;
  assert.ok(r.strengths.some((x) => x.stat.key === "goals"));
  assert.ok(r.weaker.some((x) => x.stat.key === "recoveries"));
});

test("the summary names the season and keeps xG's case", () => {
  const r = buildReport(payload, 1)!;
  assert.match(r.summary[0], /^Striker has 20 league goals and 1 assist in 30 starts in 2025\/26\.$/);
  assert.doesNotMatch(r.summary.join(" "), /\bxg\b/);
});

test("a finished season reads in the past tense, with the name the page passes", () => {
  const r = buildReport(payload, 1, { name: "S. Striker", finished: true })!;
  assert.match(r.summary[0], /^S\. Striker had 20 league goals/);
  assert.match(r.summary[1], /strongest area was/);
});

test("a player under the bar is described but not ranked", () => {
  const r = buildReport(payload, 4)!;
  assert.equal(r.ranked, false);
  assert.equal(r.strengths.length, 0);
  assert.match(r.summary[1], /not enough minutes to rank yet: the bar is 900 league minutes/);
});
