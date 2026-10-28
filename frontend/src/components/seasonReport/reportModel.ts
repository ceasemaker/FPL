// Season report: one player's Premier League season from the Stats Explorer
// feed, ranked against players in the same position who pass the minutes bar.
// Pure, so the page and its tests share every number.

import {
  formatStat, isNormalised, minutesFor, ordinal, percentile, POSITION_NAMES, qualifies, statValue,
  type ExplorerPayload, type ExplorerPlayer, type Position, type Stat,
} from "../statsExplorer/explorerModel.ts";

interface SectionDef { title: string; keys: string[] }

// What each position's report covers, most telling first.
const ATTACKER: SectionDef[] = [
  { title: "Shooting", keys: ["goals", "xg", "xgot", "shots", "shots_on_target", "big_chances", "touches_in_box", "finishing", "placement", "shot_accuracy", "conversion"] },
  { title: "Creating", keys: ["assists", "xa", "chances_created", "big_chances_created", "box_entries", "progressive_carries", "dribbles", "dribble_success"] },
  { title: "Without the ball", keys: ["cbirt", "tackles", "interceptions", "recoveries", "aerials_won", "duel_success"] },
];
export const SECTIONS: Record<Position, SectionDef[]> = {
  FWD: ATTACKER,
  MID: ATTACKER,
  DEF: [
    { title: "Defending", keys: ["cbit", "tackles", "interceptions", "clearances", "blocks", "recoveries", "aerials_won", "duel_success"] },
    { title: "Creating", keys: ["assists", "xa", "chances_created", "crosses", "progressive_carries", "final_third_passes", "box_entries"] },
    { title: "Shooting", keys: ["goals", "xg", "shots", "touches_in_box"] },
  ],
  GKP: [
    { title: "Shot-stopping", keys: ["saves", "save_pct", "goals_prevented", "xgot_faced", "clean_sheets", "goals_conceded"] },
    { title: "Commanding the box", keys: ["high_claims", "sweeper_actions"] },
    { title: "On the ball", keys: ["passes", "pass_accuracy"] },
  ],
};

export interface ReportRow {
  stat: Stat;
  value: number | null;   // per 90 where per 90 applies, else the season figure
  total: number | null;   // the season figure
  display: string;
  totalDisplay: string;
  per90: boolean;
  pct: number | null;     // 0–100, 100 = best in the group
  rank: number | null;    // 1 = best; ties share a rank
}

export interface Report {
  player: ExplorerPlayer;
  seasonLabel: string;
  positionName: string;   // "forwards"
  group: number;          // players in the comparison group
  minMinutes: number;
  minutes: number;
  ranked: boolean;        // enough minutes to be ranked at all
  smallSample: boolean;   // ranked, but on few minutes
  sections: { title: string; rows: ReportRow[] }[];
  strengths: ReportRow[];
  weaker: ReportRow[];
  headline: { label: string; value: string }[];
  summary: string[];
}

const byKey = (payload: ExplorerPayload) => new Map(payload.catalogue.map((s) => [s.key, s]));
const total = (stat: Stat, p: ExplorerPlayer) => statValue(stat, p, "pl", "total");

/** "3rd of 41 forwards" */
export function rankText(row: ReportRow, report: Pick<Report, "group" | "positionName">): string {
  return row.rank == null ? "not ranked" : `${ordinal(row.rank)} of ${report.group} ${report.positionName}`;
}

/** ``name`` overrides the feed's short name in sentences; ``finished`` writes them in the past tense. */
export function buildReport(payload: ExplorerPayload, playerId: number, opts: { name?: string; finished?: boolean } = {}): Report | null {
  const player = payload.players.find((p) => p.id === playerId);
  if (!player) return null;
  const stats = byKey(payload);
  const minMinutes = payload.minMinutes ?? 270;
  const position = player.position;
  const positionName = POSITION_NAMES[position];
  const minutes = minutesFor(player, "pl");
  const anyStat = payload.catalogue.find((s) => s.kind !== "fpl")!;
  const cohort = payload.players.filter((p) => p.position === position && qualifies(anyStat, p, "pl", minMinutes));
  const ranked = minutes >= minMinutes;

  const row = (stat: Stat): ReportRow => {
    const per90 = isNormalised(stat);
    const value = statValue(stat, player, "pl", "p90");
    const season = total(stat, player);
    const others = cohort.map((p) => statValue(stat, p, "pl", "p90")).filter((v): v is number => v !== null);
    const pct = ranked ? percentile(value, others, stat.lowerIsBetter) : null;
    const better = value === null ? null : others.filter((v) => (stat.lowerIsBetter ? v < value : v > value)).length;
    return {
      stat, value, total: season, per90, pct,
      rank: ranked && better !== null ? better + 1 : null,
      display: formatStat(stat, value, "p90"),
      totalDisplay: formatStat(stat, season, "total"),
    };
  };

  const sections = SECTIONS[position].map((s) => ({
    title: s.title,
    rows: s.keys.map((k) => stats.get(k)).filter((s): s is Stat => !!s).map(row),
  }));
  const rows = sections.flatMap((s) => s.rows).filter((r) => r.pct !== null);
  const strengths = [...rows].filter((r) => r.pct! >= 80).sort((a, b) => b.pct! - a.pct!).slice(0, 4);
  const weaker = [...rows].filter((r) => r.pct! <= 25).sort((a, b) => a.pct! - b.pct!).slice(0, 3);

  const find = (key: string) => sections.flatMap((s) => s.rows).find((r) => r.stat.key === key);
  const figure = (key: string) => { const r = find(key) ?? (stats.get(key) ? row(stats.get(key)!) : undefined); return r?.totalDisplay ?? "–"; };
  const starts = stats.get("starts") ? total(stats.get("starts")!, player) : null;
  const headline = position === "GKP"
    ? [{ label: "Clean sheets", value: figure("clean_sheets") }, { label: "Saves", value: figure("saves") }, { label: "Goals prevented", value: figure("goals_prevented") }]
    : [{ label: "Goals", value: figure("goals") }, { label: "Assists", value: figure("assists") }, { label: "xG", value: figure("xg") }];
  headline.push({ label: "Minutes", value: minutes.toLocaleString("en-GB") });

  const report: Report = {
    player, seasonLabel: payload.seasonLabel, positionName, group: cohort.length, minMinutes, minutes, ranked,
    smallSample: ranked && minutes < (payload.smallSample ?? 450), sections, strengths, weaker, headline, summary: [],
  };
  report.summary = summarise(report, starts, find, opts.name ?? player.name, opts.finished ?? false);
  return report;
}

// "Goals" reads "goals" mid-sentence; "xG" and "CBIRT" keep their case.
const inSentence = (label: string) => (/^[A-Z][a-z]/.test(label) ? label[0].toLowerCase() + label.slice(1) : label);

// Plain sentences built only from the numbers above, nothing invented.
function summarise(r: Report, starts: number | null, find: (key: string) => ReportRow | undefined, name: string, finished: boolean): string[] {
  const has = finished ? "had" : "has", is = finished ? "was" : "is";
  const out: string[] = [];
  const startsText = starts != null ? `${starts} start${starts === 1 ? "" : "s"}` : `${r.minutes.toLocaleString("en-GB")} minutes`;
  const when = `in ${r.seasonLabel}`;
  if (r.player.position === "GKP") {
    const sheets = find("clean_sheets")?.totalDisplay ?? "–", saves = find("saves")?.totalDisplay ?? "–";
    out.push(`${name} ${has} ${sheets} clean sheet${sheets === "1" ? "" : "s"} and ${saves} save${saves === "1" ? "" : "s"} in ${startsText} ${when}.`);
  } else {
    const goals = find("goals")?.totalDisplay ?? "–", assists = find("assists")?.totalDisplay ?? "–";
    out.push(`${name} ${has} ${goals} league goal${goals === "1" ? "" : "s"} and ${assists} assist${assists === "1" ? "" : "s"} in ${startsText} ${when}.`);
  }
  if (!r.ranked) {
    out.push(`That's not enough minutes to rank${finished ? "" : " yet"}: the bar is ${r.minMinutes.toLocaleString("en-GB")} league minutes.`);
    return out;
  }
  const best = r.strengths[0];
  if (best) out.push(`${name}'s strongest area ${is} ${inSentence(best.stat.label)}: ${best.display}${best.per90 ? " per 90" : ""}, ${rankText(best, r)}.`);
  const placement = find("placement");
  if (r.player.position !== "GKP" && placement?.total != null && placement.rank != null && Math.abs(placement.total) >= 0.5) {
    out.push(placement.total > 0
      ? `Where ${name} puts the ball added ${placement.total.toFixed(1)} goals' worth on top of the chances themselves (xGOT minus xG), ${rankText(placement, r)}.`
      : `${name}'s shots on target were worth ${Math.abs(placement.total).toFixed(1)} goals less than the chances themselves (xGOT minus xG), ${rankText(placement, r)}.`);
  }
  if (r.player.position === "GKP") {
    const prevented = find("goals_prevented");
    if (prevented?.total != null && prevented.rank != null) {
      out.push(prevented.total >= 0
        ? `${name} ${has} kept out ${prevented.total.toFixed(1)} more goals than the shots faced would suggest (goals prevented), ${rankText(prevented, r)}.`
        : `${name} ${has} let in ${Math.abs(prevented.total).toFixed(1)} more goals than the shots faced would suggest (goals prevented), ${rankText(prevented, r)}.`);
    }
  }
  return out;
}
