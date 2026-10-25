// Stats Explorer calculations: turns raw season counts from /api/stats-explorer/
// into the numbers the table shows. Everything here is pure so the table can
// recompute instantly when a control changes.

export type Scope = "pl" | "all"; // Premier League only, or PL + Champions League
export type Norm = "p90" | "total";
export type Position = "GKP" | "DEF" | "MID" | "FWD";

export interface Stat {
  key: string;
  label: string;
  group: string;
  kind: "count" | "rate" | "diff" | "fpl";
  raw?: string[] | string;
  num?: string[];
  den?: string[];
  plus?: string[];
  minus?: string[];
  help: string;
  plOnly: boolean;
  source: "Opta" | "FPL" | "Estimate";
  lowerIsBetter: boolean;
  format?: "number" | "price" | "percent";
  shade?: boolean; // false: context, not good or bad (price, ownership)
  per90?: boolean; // false: always a season count (starts)
}

export interface Lens {
  label: string;
  columns: string[];
  keeperColumns?: string[];
}

// null = a feed gap (the player had the underlying actions but the key is
// missing), which must render as "–", never as 0.
export type Counts = Record<string, number | null>;

export interface ExplorerPlayer {
  id: number;
  name: string;
  team: string | null;
  teamId: number | null;
  position: Position;
  status: string | null;
  news: string;
  fpl: Record<string, number | null>;
  pl: Counts;
  ucl: Counts | null;
}

export interface TeamStatDef {
  key: string;
  label: string;
  group: string;
  help: string;
  perMatch: boolean;
  lowerIsBetter?: boolean;
  format?: "percent";
}

export interface ExplorerTeam {
  id: number;
  name: string;
  short: string;
  inUcl: boolean;
  stats: Record<string, number | null>;
}

export interface ExplorerPayload {
  season: number;
  seasonLabel: string;
  latestGameweek: number;
  minMinutes?: number;   // the season's ranking bar (grows with the season)
  smallSample?: number;  // under this many league minutes: rank shown, flagged
  catalogue: Stat[];
  lenses: Record<string, Lens>;
  teamCatalogue: TeamStatDef[];
  uclTeamIds: number[];
  uclClubRule: string;
  players: ExplorerPlayer[];
  teams: ExplorerTeam[];
}

/** Minutes behind a value: PL only for PL-only stats, otherwise per scope. */
export function minutesFor(player: ExplorerPlayer, scope: Scope, plOnly = false): number {
  const pl = (player.pl.mins_played ?? 0) as number;
  if (scope === "pl" || plOnly) return pl;
  return pl + ((player.ucl?.mins_played ?? 0) as number);
}

/** Whether the player has enough minutes behind this particular stat. A
 *  PL-only stat needs the minimum in Premier League minutes alone, even when
 *  Champions League minutes count towards the scope. */
export function qualifies(stat: Stat, player: ExplorerPlayer, scope: Scope, minMinutes: number): boolean {
  if (stat.kind === "fpl") return true;
  return minutesFor(player, scope, stat.plOnly) >= minMinutes;
}

function sum(player: ExplorerPlayer, keys: string[], scope: Scope, plOnly: boolean): number | null {
  let total = 0;
  for (const key of keys) {
    const pl = player.pl[key];
    if (pl === null) return null;
    total += pl ?? 0;
    if (scope === "all" && !plOnly) {
      const ucl = player.ucl?.[key];
      if (ucl === null) return null;
      total += ucl ?? 0;
    }
  }
  return total;
}

/** The number a cell shows, or null when undefined (no minutes, 0 ÷ 0). */
export function statValue(stat: Stat, player: ExplorerPlayer, scope: Scope, norm: Norm): number | null {
  if (stat.kind === "fpl") {
    const value = player.fpl[stat.raw as string];
    return value ?? null;
  }
  if (stat.kind === "rate") {
    const den = sum(player, stat.den ?? [], scope, stat.plOnly);
    const num = sum(player, stat.num ?? [], scope, stat.plOnly);
    return den !== null && num !== null && den > 0 ? num / den : null;
  }
  let value: number | null;
  if (stat.kind === "diff") {
    const plus = sum(player, stat.plus ?? [], scope, stat.plOnly);
    const minus = sum(player, stat.minus ?? [], scope, stat.plOnly);
    value = plus === null || minus === null ? null : plus - minus;
  } else {
    value = sum(player, (stat.raw as string[]) ?? [], scope, stat.plOnly);
  }
  if (value === null) return null;
  if (norm === "total" || stat.per90 === false) return value;
  const minutes = minutesFor(player, scope, stat.plOnly);
  return minutes > 0 ? (value / minutes) * 90 : null;
}

/** Whether per 90 applies to this stat (rates and FPL fields never change). */
export function isNormalised(stat: Stat): boolean {
  return (stat.kind === "count" || stat.kind === "diff") && stat.per90 !== false;
}

export function formatStat(stat: Stat, value: number | null, norm: Norm): string {
  if (value === null || Number.isNaN(value)) return "–";
  if (stat.kind === "rate") return `${Math.round(value * 100)}%`;
  if (stat.format === "price") return `£${value.toFixed(1)}m`;
  if (stat.format === "percent") return `${(stat.key === "ownership" ? value : value * 100).toFixed(1)}%`;
  // Ratios keep two decimals even when they land on a whole number (4.00, not 4).
  if (stat.kind === "fpl") return Number.isInteger(value) && stat.key !== "points_per_m" ? String(value) : value.toFixed(2);
  if ((norm === "total" || stat.per90 === false) && Number.isInteger(Math.round(value * 1000) / 1000)) return String(Math.round(value));
  const sign = stat.kind === "diff" && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

/**
 * Percentile of `value` among `cohort` (0–100, 100 = best), counting ties
 * as half. Lower-is-better stats are inverted so 100 always means good.
 */
export function percentile(value: number | null, cohort: number[], lowerIsBetter: boolean): number | null {
  if (value === null || cohort.length < 2) return null;
  let below = 0;
  let equal = 0;
  for (const other of cohort) {
    if (other < value) below += 1;
    else if (other === value) equal += 1;
  }
  const pct = ((below + equal / 2) / cohort.length) * 100;
  return lowerIsBetter ? 100 - pct : pct;
}

/** Top-of-position highlight: lime is reserved for roughly the top 7%. */
export const TOP_PERCENTILE = 93;

/** FPL defensive contribution: points for 10 CBIT (defenders) or 12 CBIRT
 *  (midfielders and forwards) in a match. Per 90 is the per-match proxy. */
export const DEFCON_THRESHOLD: Record<string, Partial<Record<Position, number>>> = {
  cbit: { DEF: 10 },
  cbirt: { MID: 12, FWD: 12 },
};

export interface Shade {
  level: number; // 0–1 intensity, by value within the cohort
  top: boolean; // lime highlight
  defcon?: number; // the FPL threshold this cell was judged against
}

function quantile(sorted: number[], q: number): number {
  if (!sorted.length) return 0;
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

/**
 * Cell shading by size, not rank: intensity follows where the value sits
 * between the cohort's 5th and 95th percentile values, so 2.32 reads clearly
 * brighter than 1.08 and 1.08 ≈ 1.06. Lime marks only the top ~7%, or, for
 * DefCon columns per 90, a player averaging FPL's points threshold.
 */
export function shade(
  stat: Stat,
  position: Position,
  value: number | null,
  sortedCohort: number[],
  pct: number | null,
  norm: Norm,
): Shade | null {
  if (value === null || sortedCohort.length < 2 || stat.shade === false) return null;
  const threshold = norm === "p90" ? DEFCON_THRESHOLD[stat.key]?.[position] : undefined;
  if (threshold) {
    return { level: Math.max(0, Math.min(1, value / threshold)), top: value >= threshold, defcon: threshold };
  }
  const lo = quantile(sortedCohort, 0.05);
  const hi = quantile(sortedCohort, 0.95);
  let level = hi > lo ? (value - lo) / (hi - lo) : 0.5;
  level = Math.max(0, Math.min(1, level));
  if (stat.lowerIsBetter) level = 1 - level;
  return { level, top: pct !== null && pct >= TOP_PERCENTILE };
}

export function ordinal(n: number): string {
  const rounded = Math.round(n);
  const mod100 = rounded % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${rounded}th`;
  return `${rounded}${["th", "st", "nd", "rd"][rounded % 10] ?? "th"}`;
}

export const POSITION_NAMES: Record<Position, string> = {
  GKP: "goalkeepers",
  DEF: "defenders",
  MID: "midfielders",
  FWD: "forwards",
};

// Chart Lab formula for a stat, when Chart Lab has the raw stats it needs.
// Chart Lab variables: pts, mins, g, a, xg, xa, cs, gc, saves, yc, xcs, price, own, starts.
export const CHART_LAB_FORMULA: Record<string, { p90: string; total: string }> = {
  goals: { p90: "per90(g)", total: "g" },
  xg: { p90: "per90(xg)", total: "xg" },
  assists: { p90: "per90(a)", total: "a" },
  xa: { p90: "per90(xa)", total: "xa" },
  finishing: { p90: "per90(g - xg)", total: "g - xg" },
  assists_vs_xa: { p90: "per90(a - xa)", total: "a - xa" },
  clean_sheets: { p90: "per90(cs)", total: "cs" },
  goals_conceded: { p90: "per90(gc)", total: "gc" },
  saves: { p90: "per90(saves)", total: "saves" },
  xcs: { p90: "per90(xcs)", total: "xcs" },
  yellow_cards: { p90: "per90(yc)", total: "yc" },
  starts: { p90: "starts", total: "starts" },
  price: { p90: "price", total: "price" },
  ownership: { p90: "own", total: "own" },
  points: { p90: "pts", total: "pts" },
  points_per_m: { p90: "pts / price", total: "pts / price" },
};
