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
}

export interface Lens {
  label: string;
  columns: string[];
  keeperColumns?: string[];
}

export type Counts = Record<string, number>;

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
  const pl = player.pl.mins_played ?? 0;
  if (scope === "pl" || plOnly) return pl;
  return pl + (player.ucl?.mins_played ?? 0);
}

function sum(player: ExplorerPlayer, keys: string[], scope: Scope, plOnly: boolean): number {
  let total = 0;
  for (const key of keys) {
    total += player.pl[key] ?? 0;
    if (scope === "all" && !plOnly) total += player.ucl?.[key] ?? 0;
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
    return den > 0 ? sum(player, stat.num ?? [], scope, stat.plOnly) / den : null;
  }
  const value = stat.kind === "diff"
    ? sum(player, stat.plus ?? [], scope, stat.plOnly) - sum(player, stat.minus ?? [], scope, stat.plOnly)
    : sum(player, (stat.raw as string[]) ?? [], scope, stat.plOnly);
  if (norm === "total") return value;
  const minutes = minutesFor(player, scope, stat.plOnly);
  return minutes > 0 ? (value / minutes) * 90 : null;
}

/** Whether per 90 applies to this stat (rates and FPL fields never change). */
export function isNormalised(stat: Stat): boolean {
  return stat.kind === "count" || stat.kind === "diff";
}

export function formatStat(stat: Stat, value: number | null, norm: Norm): string {
  if (value === null || Number.isNaN(value)) return "–";
  if (stat.kind === "rate") return `${Math.round(value * 100)}%`;
  if (stat.format === "price") return `£${value.toFixed(1)}m`;
  if (stat.format === "percent") return `${(stat.key === "ownership" ? value : value * 100).toFixed(1)}%`;
  if (stat.kind === "fpl") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (norm === "total" && Number.isInteger(Math.round(value * 1000) / 1000)) return String(Math.round(value));
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

/** Shading band 0–4 (bottom fifth to top fifth). */
export function band(pct: number | null): number | null {
  if (pct === null) return null;
  return Math.min(4, Math.floor(pct / 20));
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
