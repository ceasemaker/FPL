import { useMemo, type ReactNode } from "react";
import { seasonLabel, strength, useFetch, useNarrow } from "./hooks";
import { BarChart, type BarItem } from "./LabCharts";

// Hold-up play: lay-offs (the one-touch "wall pass" back to a team-mate),
// plus aerial duels and fouls won. From Sincere FC's "Why 'Hold-Up Play'
// Needs To Become a Statistic in Football".

interface HoldupPlayer {
  id: string;
  name: string;
  position: string;
  team: string;
  minutes: number;
  goals: number;
  assists: number;
  layoffs_won: number;
  layoffs_lost: number;
  aerials_won: number;
  aerials_lost: number;
  fouls_won: number;
}
interface HoldupPayload {
  season: number;
  seasonLabel: string;
  competition: string;
  available: [string, number][];
  players: HoldupPlayer[];
  pointsLink: { seasons: string[]; players: number; minMinutes: number; withPoints: number; withAssists: number } | null;
}

type Measure = "layoffs90" | "layoffPct" | "aerials90" | "fouls90";

export interface HoldupConfig {
  season: number;
  competition: string;
  measure: Measure;
  position: "ALL" | "DEF" | "MID" | "FWD";
  minMinutes: number;
}

export const DEFAULT_HOLDUP: HoldupConfig = {
  season: 2025,
  competition: "premier-league",
  measure: "layoffs90",
  position: "FWD",
  minMinutes: 900,
};

const MEASURES: Record<Measure, { label: string; phrase: string }> = {
  layoffs90: { label: "Successful lay-offs per 90", phrase: "lays the ball off most" },
  layoffPct: { label: "Lay-off success rate", phrase: "lays it off most cleanly" },
  aerials90: { label: "Aerial duels won per 90", phrase: "wins the most headers" },
  fouls90: { label: "Fouls won per 90", phrase: "draws the most fouls" },
};
const COMPETITION_LABELS: Record<string, string> = {
  "premier-league": "Premier League",
  "champions-league": "Champions League",
  championship: "Championship",
};
const MIN_LAYOFFS = 20; // attempts, before a success rate means anything
const ROWS = 15;

function measureValue(p: HoldupPlayer, measure: Measure): number | null {
  const per90 = (v: number) => (v / p.minutes) * 90;
  if (measure === "layoffs90") return per90(p.layoffs_won);
  if (measure === "aerials90") return per90(p.aerials_won);
  if (measure === "fouls90") return per90(p.fouls_won);
  const attempts = p.layoffs_won + p.layoffs_lost;
  return attempts >= MIN_LAYOFFS ? (100 * p.layoffs_won) / attempts : null;
}

export function useHoldupView(active: boolean, config: HoldupConfig, update: (patch: Partial<HoldupConfig>) => void) {
  const { data, error } = useFetch<HoldupPayload>(
    active ? `/api/chart-lab/holdup/?season=${config.season}&competition=${config.competition}` : null,
  );
  const narrow = useNarrow();

  const items = useMemo<BarItem[]>(() => {
    if (!data) return [];
    const rows = data.players.flatMap((p, i) => {
      if (p.minutes < config.minMinutes || (config.position !== "ALL" && p.position !== config.position)) return [];
      const v = measureValue(p, config.measure);
      if (v === null) return [];
      const count = config.measure === "aerials90" ? `${p.aerials_won} won` : config.measure === "fouls90" ? `${p.fouls_won} won`
        : `${p.layoffs_won}/${p.layoffs_won + p.layoffs_lost} lay-offs`;
      return [{ id: i + 1, label: p.name, detail: `${p.team} · ${count}`, value: v, highlighted: false }];
    });
    rows.sort((a, b) => b.value - a.value);
    return rows.slice(0, ROWS);
  }, [data, config.measure, config.minMinutes, config.position]);

  const seasons = useMemo(() => [...new Set((data?.available ?? []).filter(([c]) => c === config.competition).map(([, s]) => s))].sort((a, b) => b - a), [data, config.competition]);
  const competitions = useMemo(() => [...new Set((data?.available ?? []).map(([c]) => c))], [data]);
  const format = (v: number) => (config.measure === "layoffPct" ? `${Math.round(v)}%` : v.toFixed(2));

  let takeaway: ReactNode = null;
  if (data && items[0]) {
    const top = items[0];
    const link = data.pointsLink;
    const word = link ? strength(link.withPoints) : null;
    takeaway = (
      <>
        <strong>{top.label}</strong> {MEASURES[config.measure].phrase}: {format(top.value)}{config.measure === "layoffPct" ? " of his lay-offs find a team-mate" : ` ${MEASURES[config.measure].label.toLowerCase()}`}.
        {link && config.measure !== "aerials90" && config.measure !== "fouls90" && (
          <> Does holding the ball up earn FPL points? {word === "barely" ? "Hardly" : link.withPoints < 0 ? "No, if anything the reverse" : word === "somewhat" ? "A little" : "Yes"}: across {link.players} forward-seasons ({link.seasons[0]}–{link.seasons[link.seasons.length - 1]}, {link.minMinutes}+ minutes), lay-offs per 90 and FPL points per 90 {word} move together (correlation {link.withPoints.toFixed(2)}).{word === "barely" && " It helps the team more than the player's own FPL numbers."}</>
        )}
      </>
    );
  } else if (data) {
    takeaway = <>No players match these filters.</>;
  }

  const title = `Hold-up play: ${MEASURES[config.measure].label.toLowerCase()}`;
  const subtitle = data
    ? `${COMPETITION_LABELS[config.competition] ?? config.competition} ${seasonLabel(config.season)} · ${config.position === "ALL" ? "outfield players" : config.position} · ${config.minMinutes}+ minutes${config.measure === "layoffPct" ? ` · ${MIN_LAYOFFS}+ lay-offs tried` : ""}`
    : "";

  const controls = (
    <>
      <div className="lab-filter-row">
        <label className="aero-field">
          Competition
          <select className="aero-select" value={config.competition} onChange={(e) => update({ competition: e.target.value })}>
            {(competitions.length ? competitions : Object.keys(COMPETITION_LABELS)).map((c) => (
              <option key={c} value={c}>{COMPETITION_LABELS[c] ?? c}</option>
            ))}
          </select>
        </label>
        <label className="aero-field">
          Season
          <select className="aero-select" value={config.season} onChange={(e) => update({ season: Number(e.target.value) })}>
            {(seasons.length ? seasons : [config.season]).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
          </select>
        </label>
      </div>
      <label className="aero-field">
        Measure
        <select className="aero-select" value={config.measure} onChange={(e) => update({ measure: e.target.value as Measure })}>
          {(Object.keys(MEASURES) as Measure[]).map((m) => <option key={m} value={m}>{MEASURES[m].label}</option>)}
        </select>
      </label>
      <div className="lab-filter-row">
        <label className="aero-field">
          Position
          <select className="aero-select" value={config.position} onChange={(e) => update({ position: e.target.value as HoldupConfig["position"] })}>
            {(["ALL", "DEF", "MID", "FWD"] as const).map((p) => <option key={p} value={p}>{p === "ALL" ? "All outfield" : p}</option>)}
          </select>
        </label>
        <label className="aero-field">
          Min minutes
          <input className="aero-input" type="number" min={0} step={90} value={config.minMinutes}
            onChange={(e) => update({ minMinutes: Math.max(0, Number(e.target.value) || 0) })} />
        </label>
      </div>
    </>
  );

  const chart = error ? (
    <p className="aero-empty lab-chart-empty">Couldn't load the data ({error}).</p>
  ) : !data ? <div className="lab-skeleton" /> : <BarChart stacked items={items} format={format} compact={narrow} />;

  const hint = (
    <>
      A lay-off is a short pass, usually first time, played back to a team-mate by a player receiving the ball with his back to
      goal: the "wall pass" that lets midfielders run on. Aerial duels won and fouls won show the other half of holding the ball up.
      Opta data via the Premier League. Idea from Sincere FC's "Why 'Hold-Up Play' Needs To Become a Statistic in Football".
    </>
  );

  return { controls, chart, title, subtitle, hint, takeaway };
}
