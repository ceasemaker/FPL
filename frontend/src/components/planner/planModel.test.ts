// Run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";

import { legalXI, lineupAt, sheetPoints, swapPlayers, type Plan, type PlannerData, type PlannerPlayer } from "./planModel.ts";

// A 15-man squad: ids 1-2 GKP, 3-7 DEF, 8-12 MID, 13-15 FWD, plus a spare defender (16) to buy.
const POS: Record<number, PlannerPlayer["position"]> = {};
for (let id = 1; id <= 16; id++) POS[id] = id <= 2 ? "GKP" : id <= 7 || id === 16 ? "DEF" : id <= 12 ? "MID" : "FWD";
const player = (id: number): PlannerPlayer => ({
  id, code: id, name: `P${id}`, fullName: `Player ${id}`, team: "1", teamShort: "AAA", position: POS[id], price: 50,
  points: 0, form: 0, ppg: 0, ownership: 0, minutes: 0, status: "a", news: "", chance: null, epNext: null,
});
const byId = new Map(Object.keys(POS).map((k) => [Number(k), player(Number(k))]));

// FPL sheet: 4-4-2 with 7 (DEF), 12 (MID) and 15 (FWD) on the bench behind GK 2; 13 captain, 8 vice.
const xi = [1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14];
const benchIds = [2, 7, 12, 15];
const data = {
  nextGameweek: 9,
  squad: [...xi, ...benchIds].map((id, i) => ({ id, slot: i + 1, purchase: 50, selling: 50, captain: id === 13, vice: id === 8 })),
  projections: { points: Object.fromEntries([...xi, ...benchIds, 16].map((id) => [String(id), { "9": id, "10": id }])), fplOnly: [], covers: [9, 10], record: null },
} as unknown as PlannerData;
const empty: Plan = { name: "A", transfers: [] };

test("the coming week starts from the FPL team sheet", () => {
  const sheet = lineupAt(data, empty, 9, byId);
  assert.deepEqual(sheet.xi, xi);
  assert.deepEqual(sheet.bench, benchIds);
  assert.equal(sheet.captain, 13);
  assert.equal(sheet.vice, 8);
  assert.equal(sheet.custom, false);
});

test("a starter and a sub swap only into a legal formation", () => {
  const sheet = lineupAt(data, empty, 9, byId);
  const fourFiveOne = swapPlayers(sheet, 14, 12, byId)!;
  assert.ok(legalXI(fourFiveOne.xi, byId), "FWD off, MID on: 4-5-1");
  assert.equal(swapPlayers(fourFiveOne, 13, 7, byId), null, "taking off the only forward is illegal");
  assert.ok(swapPlayers(sheet, 3, 15, byId), "DEF off, FWD on: 3-4-3 is legal");
});

test("goalkeepers only swap with goalkeepers, and the bench keeper stays first", () => {
  const sheet = lineupAt(data, empty, 9, byId);
  assert.equal(swapPlayers(sheet, 1, 7, byId), null);
  assert.ok(swapPlayers(sheet, 1, 2, byId));
  assert.equal(swapPlayers(sheet, 2, 7, byId), null);
  assert.deepEqual(swapPlayers(sheet, 7, 12, byId)!.bench, [2, 12, 7, 15]);
});

test("benching the captain hands the armband to the player coming on", () => {
  const sheet = lineupAt(data, empty, 9, byId);
  const next = swapPlayers(sheet, 13, 15, byId)!;
  assert.equal(next.captain, 15);
});

test("a transferred-in player takes the outgoing player's place, and sheets carry forward", () => {
  const plan: Plan = { name: "A", transfers: [{ gw: 9, out: 4, in: 16, sell: 50, buy: 50 }], lineups: { "9": { xi, bench: benchIds, captain: 8, vice: 13 } } };
  const gw9 = lineupAt(data, plan, 9, byId);
  assert.equal(gw9.xi[2], 16);
  assert.equal(gw9.custom, true);
  const gw10 = lineupAt(data, plan, 10, byId);
  assert.equal(gw10.captain, 8, "GW10 carries GW9's armband");
  assert.equal(gw10.custom, false);
});

test("points count the XI, the captain twice, and the bench only on Bench Boost", () => {
  const sheet = lineupAt(data, empty, 9, byId);
  const xiTotal = xi.reduce((s, id) => s + id, 0);
  assert.equal(sheetPoints(data, sheet, 9).total, xiTotal + 13);
  assert.equal(sheetPoints(data, sheet, 9, "3xc").total, xiTotal + 26);
  assert.equal(sheetPoints(data, sheet, 9, "bboost").total, xiTotal + 13 + benchIds.reduce((s, id) => s + id, 0));
});
