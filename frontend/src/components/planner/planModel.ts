// Transfer planner model: pure functions over the imported squad and a plan
// (a list of transfers by gameweek). Prices are in tenths of £m, like FPL's.

export interface PlannerPlayer {
  id: number; code: number; name: string; fullName: string; team: string; teamShort: string;
  position: "GKP" | "DEF" | "MID" | "FWD" | ""; price: number; points: number; form: number; ppg: number;
  ownership: number; minutes: number; status: string; news: string; chance: number | null; epNext: number | null;
}
export interface SquadPick { id: number; slot: number; purchase: number; selling: number; captain: boolean; vice: boolean }
export interface FixtureCell { opp: string; oppCode: string; home: boolean; difficulty: number | null }
export interface BeforeGame { competition: string; kickoff: string; home: boolean; opp: string }
export interface PlannerData {
  managerId: number; name: string; teamName: string; overallRank: number | null; points: number | null;
  currentGameweek: number; nextGameweek: number; bank: number; teamValue: number | null; freeTransfers: number;
  chips: { key: string; name: string; available: boolean }[];
  squad: SquadPick[];
  gameweeks: { gameweek: number; deadline: string | null }[];
  fixtures: Record<string, Record<string, { fixtures: FixtureCell[]; before: BeforeGame[] }>>;
  players: PlannerPlayer[];
  projections: { points: Record<string, Record<string, number>>; fplOnly: number[]; covers: [number, number];
    record: { version: string; playerWeeks: number; modelError: number; formError: number; seasons: string[] } | null };
  rotation: Record<string, { starts: number; minutes: number; clubGames: number; next14: number }>;
  // AeroFPL's seven-day price-rise forecast: only sent when its backtest passed.
  priceForecast: { chances: Record<string, number>; record: { precision: number; flagged: number; testDays: number; rulePrecision: number } } | null;
}

export interface Transfer { gw: number; out: number; in: number; sell: number; buy: number }
export type ChipKey = "wildcard" | "freehit" | "bboost" | "3xc";
/** A gameweek's team sheet: starting XI (FPL order), bench in substitution order (goalkeeper first), armbands. */
export interface Lineup { xi: number[]; bench: number[]; captain: number | null; vice: number | null }
export interface Plan {
  name: string; transfers: Transfer[]; bank?: number; freeTransfers?: number; chips?: Record<string, ChipKey>;
  /** Team sheets the manager set, by gameweek. Later weeks carry the latest one forward, like FPL. */
  lineups?: Record<string, Lineup>;
}
export const CHIP_NAMES: Record<ChipKey, string> = { wildcard: "Wildcard", freehit: "Free Hit", bboost: "Bench Boost", "3xc": "Triple Captain" };
const chipAt = (plan: Plan, gw: number) => plan.chips?.[String(gw)];

export const SQUAD_SHAPE: Record<string, number> = { GKP: 2, DEF: 5, MID: 5, FWD: 3 };
export const MAX_PER_CLUB = 3;
export const MAX_FREE = 5;
export const HIT = 4;

export interface Holding { id: number; purchase: number; selling: number }

/** The squad going into gameweek ``gw`` after every planned transfer up to and including it. */
export function squadAt(data: PlannerData, plan: Plan, gw: number): Holding[] {
  let squad: Holding[] = data.squad.map((p) => ({ id: p.id, purchase: p.purchase, selling: p.selling }));
  // A Free Hit squad lasts one week: its transfers don't carry into later weeks.
  for (const t of plan.transfers.filter((t) => t.gw <= gw && (t.gw === gw || chipAt(plan, t.gw) !== "freehit"))) {
    squad = squad.map((h) => (h.id === t.out ? { id: t.in, purchase: t.buy, selling: t.buy } : h));
  }
  return squad;
}

export interface WeekSummary {
  gw: number; transfers: Transfer[]; free: number; hits: number; cost: number; bankAfter: number;
  clubsOver: string[]; overBudget: boolean; chip?: ChipKey;
}

/** Bank, free transfers and hits for each planned gameweek, in order. */
export function summarise(data: PlannerData, plan: Plan, byId: Map<number, PlannerPlayer>): WeekSummary[] {
  let bank = plan.bank ?? data.bank;
  let free = plan.freeTransfers ?? data.freeTransfers;
  return data.gameweeks.map(({ gameweek: gw }) => {
    const transfers = plan.transfers.filter((t) => t.gw === gw);
    const chip = chipAt(plan, gw);
    const unlimited = chip === "wildcard" || chip === "freehit";
    const bankBefore = bank;
    for (const t of transfers) bank += t.sell - t.buy;
    const hits = unlimited ? 0 : Math.max(0, transfers.length - free);
    const clubs = new Map<string, number>();
    for (const h of squadAt(data, plan, gw)) {
      const team = byId.get(h.id)?.teamShort ?? "";
      clubs.set(team, (clubs.get(team) ?? 0) + 1);
    }
    const week: WeekSummary = {
      gw, transfers, free, hits, cost: hits * HIT, bankAfter: bank, chip,
      clubsOver: [...clubs].filter(([, n]) => n > MAX_PER_CLUB).map(([c]) => c), overBudget: bank < 0,
    };
    // Wildcard and Free Hit keep the banked transfers; a Free Hit also hands the money back.
    free = unlimited ? Math.min(MAX_FREE, free + 1) : Math.min(MAX_FREE, Math.max(0, free - transfers.length) + 1);
    if (chip === "freehit") bank = bankBefore;
    return week;
  });
}

export const money = (tenths: number) => `£${(tenths / 10).toFixed(1)}m`;

/** Chips the plan may still use in a gameweek: each once per half (1–19, 20–38). */
export function chipOptions(data: PlannerData, plan: Plan, gw: number): ChipKey[] {
  const firstHalf = gw <= 19;
  const nowFirstHalf = data.nextGameweek <= 19;
  return (Object.keys(CHIP_NAMES) as ChipKey[]).filter((c) => {
    if (firstHalf === nowFirstHalf && !data.chips.find((x) => x.key === c)?.available) return false;
    return !Object.entries(plan.chips ?? {}).some(([g, k]) => k === c && Number(g) !== gw && (Number(g) <= 19) === firstHalf);
  });
}

export const projected = (data: PlannerData, id: number, gw: number) => data.projections.points[String(id)]?.[String(gw)] ?? null;

/** Best legal XI by projected points (1 GK, 3–5 DEF, 2–5 MID, 1–3 FWD) and its captain. */
export function bestXI(data: PlannerData, ids: number[], byId: Map<number, PlannerPlayer>, gw: number) {
  const rows = ids.map((id) => ({ id, pos: byId.get(id)?.position ?? "", pts: projected(data, id, gw) ?? 0 }))
    .sort((a, b) => b.pts - a.pts);
  const take = (pos: string, n: number, from: typeof rows) => from.filter((r) => r.pos === pos).slice(0, n);
  const xi = [...take("GKP", 1, rows), ...take("DEF", 3, rows), ...take("MID", 2, rows), ...take("FWD", 1, rows)];
  const max: Record<string, number> = { DEF: 5, MID: 5, FWD: 3 };
  for (const r of rows) {
    if (xi.length >= 11) break;
    if (r.pos === "GKP" || xi.includes(r)) continue;
    if (xi.filter((x) => x.pos === r.pos).length < max[r.pos]) xi.push(r);
  }
  const bench = rows.filter((r) => !xi.includes(r));
  const captain = [...xi].sort((a, b) => b.pts - a.pts)[0];
  // No projection for anyone this week (beyond the forecast's reach): say so rather than show 0.
  const available = ids.some((id) => projected(data, id, gw) != null);
  return { xi: xi.map((r) => r.id), bench: bench.map((r) => r.id), captain: captain?.id ?? null, available,
    points: xi.reduce((s, r) => s + r.pts, 0), captainPts: captain?.pts ?? 0, benchPts: bench.reduce((s, r) => s + r.pts, 0) };
}

/** League games per club in a gameweek: 0 is a blank, 2 a double. */
export const gamesIn = (data: PlannerData, team: string, gw: number) => data.fixtures[team]?.[String(gw)]?.fixtures.length ?? 0;


// ------------------------------------------------------------------ lineups

const LIMITS: Record<string, [number, number]> = { GKP: [1, 1], DEF: [3, 5], MID: [2, 5], FWD: [1, 3] };

/** True when an XI is a legal FPL formation (1 GK, 3–5 DEF, 2–5 MID, 1–3 FWD). */
export function legalXI(xi: number[], byId: Map<number, PlannerPlayer>): boolean {
  if (xi.length !== 11) return false;
  const count = (pos: string) => xi.filter((id) => byId.get(id)?.position === pos).length;
  return Object.entries(LIMITS).every(([pos, [lo, hi]]) => count(pos) >= lo && count(pos) <= hi);
}

/** FPL's own team sheet for the coming gameweek: shirts 1–11 start, 12–15 are the bench in order. */
function fplLineup(data: PlannerData): Lineup {
  const picks = [...data.squad].sort((a, b) => a.slot - b.slot);
  return {
    xi: picks.filter((p) => p.slot <= 11).map((p) => p.id),
    bench: picks.filter((p) => p.slot > 11).map((p) => p.id),
    captain: picks.find((p) => p.captain)?.id ?? null,
    vice: picks.find((p) => p.vice)?.id ?? null,
  };
}

/** Put players who joined the squad into the places of those who left, same position, so the sheet keeps its shape. */
function fitToSquad(sheet: Lineup, squad: number[], byId: Map<number, PlannerPlayer>): Lineup {
  const inSquad = new Set(squad);
  const listed = new Set([...sheet.xi, ...sheet.bench]);
  const arrivals = squad.filter((id) => !listed.has(id));
  const swap = (id: number) => {
    if (inSquad.has(id)) return id;
    const pos = byId.get(id)?.position;
    const i = arrivals.findIndex((a) => byId.get(a)?.position === pos);
    return i >= 0 ? arrivals.splice(i, 1)[0] : id;
  };
  const xi = sheet.xi.map(swap);
  const bench = sheet.bench.map(swap);
  const keep = (id: number | null) => (id != null && xi.includes(id) ? id : null);
  return { xi, bench, captain: keep(sheet.captain), vice: keep(sheet.vice) };
}

/** Highest projected starters fill a missing captain or vice. */
function armbands(data: PlannerData, sheet: Lineup, gw: number): Lineup {
  const ranked = [...sheet.xi].sort((a, b) => (projected(data, b, gw) ?? 0) - (projected(data, a, gw) ?? 0));
  const captain = sheet.captain ?? ranked[0] ?? null;
  const vice = sheet.vice != null && sheet.vice !== captain ? sheet.vice : ranked.find((id) => id !== captain) ?? null;
  return { ...sheet, captain, vice };
}

/** The best projected XI as a team sheet (bench: goalkeeper first, then by projected points). */
export function bestLineup(data: PlannerData, ids: number[], byId: Map<number, PlannerPlayer>, gw: number): Lineup {
  const best = bestXI(data, ids, byId, gw);
  const order = (id: number) => ["GKP", "DEF", "MID", "FWD"].indexOf(byId.get(id)?.position ?? "");
  const xi = [...best.xi].sort((a, b) => order(a) - order(b));
  const bench = [...best.bench].sort((a, b) => (byId.get(a)?.position === "GKP" ? -1 : byId.get(b)?.position === "GKP" ? 1 : 0));
  return armbands(data, { xi, bench, captain: best.captain, vice: null }, gw);
}

/**
 * The team sheet for gameweek ``gw``: the latest sheet the manager set at or before it
 * (FPL's picks if none), refitted to that week's squad. ``custom`` says whether the
 * manager set this exact week. Falls back to the best projected XI if it can't be made legal.
 */
export function lineupAt(data: PlannerData, plan: Plan, gw: number, byId: Map<number, PlannerPlayer>): Lineup & { custom: boolean } {
  const squad = squadAt(data, plan, gw).map((h) => h.id);
  const setWeeks = Object.keys(plan.lineups ?? {}).map(Number).filter((w) => w <= gw).sort((a, b) => b - a);
  const source = setWeeks.length ? plan.lineups![String(setWeeks[0])] : fplLineup(data);
  const sheet = fitToSquad(source, squad, byId);
  const complete = sheet.xi.length + sheet.bench.length === squad.length && [...sheet.xi, ...sheet.bench].every((id) => squad.includes(id));
  const legal = complete && legalXI(sheet.xi, byId) && byId.get(sheet.bench[0])?.position === "GKP";
  const result = legal ? armbands(data, sheet, gw) : bestLineup(data, squad, byId, gw);
  return { ...result, custom: setWeeks[0] === gw && legal };
}

/** Projected points for a team sheet: the XI, the captain again (twice more on Triple Captain), the bench on Bench Boost. */
export function sheetPoints(data: PlannerData, sheet: Lineup, gw: number, chip?: ChipKey) {
  const pts = (id: number) => projected(data, id, gw) ?? 0;
  const xi = sheet.xi.reduce((s, id) => s + pts(id), 0);
  const captain = sheet.captain != null ? pts(sheet.captain) * (chip === "3xc" ? 2 : 1) : 0;
  const bench = chip === "bboost" ? sheet.bench.reduce((s, id) => s + pts(id), 0) : 0;
  return { xi, captain, bench, total: xi + captain + bench };
}

/**
 * Swap two players on a team sheet, FPL's way: a starter and a sub trade places,
 * two subs reorder the bench. Returns null when the result isn't a legal team.
 */
export function swapPlayers(sheet: Lineup, a: number, b: number, byId: Map<number, PlannerPlayer>): Lineup | null {
  if (a === b) return null;
  const isGK = (id: number) => byId.get(id)?.position === "GKP";
  const xi = [...sheet.xi], bench = [...sheet.bench];
  const ia = xi.indexOf(a), ib = xi.indexOf(b), ba = bench.indexOf(a), bb = bench.indexOf(b);
  if (ia >= 0 && ib >= 0) return null; // two starters: nothing changes on FPL's sheet
  if (ba >= 0 && bb >= 0) {
    if (isGK(a) || isGK(b)) return null; // the bench goalkeeper keeps the first bench place
    [bench[ba], bench[bb]] = [bench[bb], bench[ba]];
    return { ...sheet, bench };
  }
  const starter = ia >= 0 ? a : b, sub = ia >= 0 ? b : a;
  if (isGK(starter) !== isGK(sub)) return null;
  xi[xi.indexOf(starter)] = sub;
  bench[bench.indexOf(sub)] = starter;
  if (!legalXI(xi, byId)) return null;
  const keep = (id: number | null) => (id === starter ? sub : id);
  return { xi, bench, captain: keep(sheet.captain), vice: keep(sheet.vice) };
}
