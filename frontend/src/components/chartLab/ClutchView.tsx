import { useMemo, type ReactNode } from "react";
import { seasonLabel, strength, useFetch, useNarrow } from "./hooks";
import { BarChart, type BarItem } from "./LabCharts";

// Clutch goals: how many league points a player's goals were worth, given
// the minute and the score when each went in. From Sincere FC's "Football's
// Most Clutch Players – By the Numbers".

interface ClutchPlayer {
  id: string;
  name: string;
  position: string;
  team: string;
  goals: number;
  penalties: number;
  pointsWon: number;
  pointsWonNoPens: number;
  decisive: number;
  lateDecisive: number;
  assists: number;
  assistPointsWon: number;
  bestGoal: { value: number; minute: number; score: string } | null;
}
interface ClutchPayload {
  season: number;
  seasonLabel: string;
  inProgress: boolean;
  available: number[];
  matches: number;
  matchesThisSeason: number;
  examples: { lateWinner: number; fourthGoal: number };
  players: ClutchPlayer[];
  persistence: { seasons: string[]; pairs: number; minGoals: number; perGoal: number; goals: number } | null;
}

type Measure = "pointsWon" | "perGoal" | "decisive" | "withAssists";

export interface ClutchConfig {
  season: number | null; // null = latest
  measure: Measure;
  penalties: boolean;
  position: "ALL" | "DEF" | "MID" | "FWD";
  minGoals: number;
}

export const DEFAULT_CLUTCH: ClutchConfig = {
  season: null,
  measure: "pointsWon",
  penalties: true,
  position: "ALL",
  minGoals: 4,
};

const MEASURES: Record<Measure, string> = {
  pointsWon: "League points won by his goals",
  perGoal: "Points won per goal",
  decisive: "Goals that levelled or took the lead",
  withAssists: "Points won by his goals and assists",
};
const ROWS = 15;

function measureValue(p: ClutchPlayer, c: ClutchConfig): number | null {
  const won = c.penalties ? p.pointsWon : p.pointsWonNoPens;
  const goals = c.penalties ? p.goals : p.goals - p.penalties;
  if (c.measure === "pointsWon") return goals ? won : null;
  if (c.measure === "perGoal") return goals >= c.minGoals ? won / goals : null;
  if (c.measure === "decisive") return goals ? p.decisive : null;
  return goals || p.assists ? won + p.assistPointsWon : null;
}

export function useClutchView(active: boolean, config: ClutchConfig, update: (patch: Partial<ClutchConfig>) => void) {
  const { data, error } = useFetch<ClutchPayload>(active ? `/api/chart-lab/clutch/${config.season ? `?season=${config.season}` : ""}` : null);
  const narrow = useNarrow();

  const items = useMemo<BarItem[]>(() => {
    if (!data) return [];
    const rows = data.players.flatMap((p, i) => {
      if (config.position !== "ALL" && p.position !== config.position) return [];
      const v = measureValue(p, config);
      if (v === null || v <= 0) return [];
      const goals = config.penalties ? p.goals : p.goals - p.penalties;
      const pens = config.penalties && p.penalties ? ` (${p.penalties} pen${p.penalties === 1 ? "" : "s"})` : "";
      const extra = config.measure === "withAssists" ? `, ${p.assists} assist${p.assists === 1 ? "" : "s"}` : "";
      return [{ id: i + 1, label: p.name, detail: `${p.team} · ${goals} goal${goals === 1 ? "" : "s"}${pens}${extra}`, value: v, highlighted: false }];
    });
    rows.sort((a, b) => b.value - a.value);
    return rows.slice(0, ROWS);
  }, [data, config]);

  const format = (v: number) => (config.measure === "decisive" ? String(Math.round(v)) : v.toFixed(config.measure === "perGoal" ? 2 : 1));

  let takeaway: ReactNode = null;
  if (data && items[0]) {
    const top = items[0];
    const player = data.players[top.id - 1];
    const p = data.persistence;
    const lead = config.measure === "decisive"
      ? <><strong>{top.label}</strong> scored the most goals that levelled the game or put {player.team} ahead: {format(top.value)}{player.lateDecisive ? `, ${player.lateDecisive} of them from the 75th minute on` : ""}.</>
      : config.measure === "perGoal"
        ? <><strong>{top.label}</strong>'s goals mattered most, one by one: about {format(top.value)} league points each.</>
        : <><strong>{top.label}</strong>'s {config.measure === "withAssists" ? "goals and assists" : "goals"} won {player.team} about {format(top.value)} league points{data.inProgress ? " so far" : ""}, more than anyone's.</>;
    takeaway = (
      <>
        {lead} For scale: a home winner at 1-1 in the 88th minute is worth about {data.examples.lateWinner.toFixed(1)} points; making it 3-0 in the 70th{data.examples.fourthGoal < 0.05 ? " is worth almost nothing" : ` about ${data.examples.fourthGoal.toFixed(1)}`}.
        {p && (
          <> Is being clutch a skill? {strength(p.perGoal) === "barely" ? "Mostly luck" : strength(p.perGoal) === "somewhat" ? "Partly" : "It looks like one"}: how much a player's goals were worth per goal one season {strength(p.perGoal)} predicts the next (correlation {p.perGoal.toFixed(2)}, {p.pairs} player pairs), while how many goals he scores {strength(p.goals)} carries over ({p.goals.toFixed(2)}).</>
        )}
      </>
    );
  } else if (data) {
    takeaway = <>No players match these filters.</>;
  }

  const title = `Clutch goals: ${MEASURES[config.measure].toLowerCase()}`;
  const subtitle = data
    ? `Premier League ${data.seasonLabel} · ${data.matchesThisSeason} matches · ${config.position === "ALL" ? "all players" : config.position} · penalties ${config.penalties ? "included" : "left out"}${config.measure === "perGoal" ? ` · ${config.minGoals}+ goals` : ""}`
    : "";

  const controls = (
    <>
      <label className="aero-field">
        Season
        <select className="aero-select" value={data?.season ?? config.season ?? ""} onChange={(e) => update({ season: Number(e.target.value) })}>
          {(data?.available ?? (config.season ? [config.season] : [])).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
        </select>
      </label>
      <label className="aero-field">
        Measure
        <select className="aero-select" value={config.measure} onChange={(e) => update({ measure: e.target.value as Measure })}>
          {(Object.keys(MEASURES) as Measure[]).map((m) => <option key={m} value={m}>{MEASURES[m]}</option>)}
        </select>
      </label>
      <div className="lab-filter-row">
        <label className="aero-field">
          Position
          <select className="aero-select" value={config.position} onChange={(e) => update({ position: e.target.value as ClutchConfig["position"] })}>
            {(["ALL", "DEF", "MID", "FWD"] as const).map((p) => <option key={p} value={p}>{p === "ALL" ? "All" : p}</option>)}
          </select>
        </label>
        {config.measure === "perGoal" && (
          <label className="aero-field">
            Min goals
            <input className="aero-input" type="number" min={1} step={1} value={config.minGoals}
              onChange={(e) => update({ minGoals: Math.max(1, Number(e.target.value) || 1) })} />
          </label>
        )}
      </div>
      <label className="lab-check">
        <input type="checkbox" checked={config.penalties} onChange={(e) => update({ penalties: e.target.checked })} />
        Include penalties
      </label>
    </>
  );

  const chart = error ? (
    <p className="aero-empty lab-chart-empty">Couldn't load the data ({error}).</p>
  ) : !data ? <div className="lab-skeleton" /> : <BarChart stacked items={items} format={format} compact={narrow} />;

  const hint = (
    <>
      Each goal is worth the rise in his team's expected league points (3 for a win, 1 for a draw) at the moment it went in, judged by
      how Premier League matches with that score at that minute ended ({data ? data.matches.toLocaleString() : "every stored"} matches
      since 2021/22). An early opener is worth a little, a late equaliser or winner a lot, a goal in a rout almost nothing. Assists get the
      value of the goal they set up. Own goals count for the score but for no player. Idea from Sincere FC's "Football's Most Clutch
      Players – By the Numbers".
    </>
  );

  return { controls, chart, title, subtitle, hint, takeaway };
}
