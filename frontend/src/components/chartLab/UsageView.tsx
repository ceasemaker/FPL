import { useEffect, useMemo, useState } from "react";
import { formatValue, ScatterChart, type ScatterPoint } from "./LabCharts";

// Usage vs creation: how much of his team's ball a player uses (possession-
// ending actions: shots plus losing the ball) against what he makes of it.
// Basketball's usage rate, adapted to football as in Sincere FC's videos.

interface UsagePlayer {
  id: string;
  name: string;
  position: string;
  team: string;
  teamKnown: boolean;
  minutes: number;
  pea: number | null;
  lost: number | null;
  shots: number | null;
  created: number | null;
  goals: number | null;
  assists: number | null;
  xa: number | null;
  usage: number | null;
  teamPossession: number | null;
}
interface UsagePayload {
  season: number;
  seasonLabel: string;
  competition: string;
  available: [string, number][];
  possessionAvailable: boolean;
  players: UsagePlayer[];
}

type XMetric = "pea" | "usage";
type YMetric = "created" | "xa" | "ga";
type Position = "ALL" | "DEF" | "MID" | "FWD";

export interface UsageConfig {
  season: number;
  competition: string;
  x: XMetric;
  y: YMetric;
  position: Position;
  minMinutes: number;
  possessionAdjusted: boolean;
  sizeByOutput: boolean;
}

export const DEFAULT_USAGE: UsageConfig = {
  season: 2025,
  competition: "premier-league",
  x: "pea",
  y: "created",
  position: "MID",
  minMinutes: 900,
  possessionAdjusted: false,
  sizeByOutput: true,
};

const COMPETITION_LABELS: Record<string, string> = {
  "premier-league": "Premier League",
  "champions-league": "Champions League",
  championship: "Championship",
};
const X_LABELS: Record<XMetric, string> = {
  pea: "Possession-ending actions per 90",
  usage: "Usage rate (% of team's possession-ending actions)",
};
const Y_LABELS: Record<YMetric, string> = {
  created: "Chances created per 90",
  xa: "Expected assists (xA) per 90",
  ga: "Goals + assists per 90",
};
const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;

export function useUsageView(active: boolean, config: UsageConfig, update: (patch: Partial<UsageConfig>) => void, highlighted: Set<number>, onToggle: (id: number) => void) {
  const [data, setData] = useState<UsagePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let alive = true;
    setData(null);
    fetch(`/api/chart-lab/usage/?season=${config.season}&competition=${config.competition}`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<UsagePayload>; })
      .then((p) => { if (alive) { setData(p); setError(null); } })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [active, config.season, config.competition]);

  const possessionOn = config.possessionAdjusted && Boolean(data?.possessionAvailable);
  const xaMissing = config.y === "xa" && config.competition !== "premier-league";

  // Numeric ids for the shared scatter (Opta ids are numeric strings; a few are not).
  const ids = useMemo(() => new Map((data?.players ?? []).map((p, i) => [p.id, i + 1])), [data]);

  const points = useMemo<ScatterPoint[]>(() => {
    if (!data || xaMissing) return [];
    return data.players.flatMap((p) => {
      if (p.minutes < config.minMinutes || (config.position !== "ALL" && p.position !== config.position)) return [];
      const per90 = (v: number | null) => (v === null ? null : (v / p.minutes) * 90);
      // Scale to a side with half the ball: a player on a 40% team gets x 1.25.
      const scale = possessionOn && p.teamPossession ? 50 / p.teamPossession : 1;
      const x = config.x === "usage" ? p.usage : per90(p.pea);
      const yRaw = config.y === "created" ? per90(p.created) : config.y === "xa" ? per90(p.xa)
        : per90(p.goals === null || p.assists === null ? null : p.goals + p.assists);
      if (x === null || yRaw === null) return [];
      if (possessionOn && !p.teamPossession) return [];
      return [{
        id: ids.get(p.id) ?? 0,
        name: p.name,
        detail: `${p.team}${p.teamKnown ? "" : " (current club)"} · ${p.position} · ${Math.round(p.minutes)} min`,
        x: config.x === "usage" ? x : x * scale,
        y: yRaw * scale,
        size: config.sizeByOutput ? (p.goals ?? 0) + (p.assists ?? 0) : undefined,
      }];
    });
  }, [data, config, possessionOn, xaMissing, ids]);

  // The "worth the ball" line: the group's average return per unit of x.
  // Above it a player gets more out of each action than the group does.
  const slope = useMemo(() => {
    const sx = points.reduce((t, p) => t + p.x, 0);
    const sy = points.reduce((t, p) => t + p.y, 0);
    return sx > 0 ? sy / sx : 0;
  }, [points]);

  // Label the players who stand out: furthest from the line either way, and the heaviest users.
  const labelled = useMemo(() => {
    if (!points.length || !slope) return new Set<number>();
    const gap = [...points].sort((a, b) => (b.y - slope * b.x) - (a.y - slope * a.x));
    const users = [...points].sort((a, b) => b.x - a.x);
    return new Set([...gap.slice(0, 4), ...gap.slice(-3), ...users.slice(0, 2)].map((p) => p.id));
  }, [points, slope]);

  const seasons = useMemo(() => [...new Set((data?.available ?? []).filter(([c]) => c === config.competition).map(([, s]) => s))].sort((a, b) => b - a), [data, config.competition]);
  const competitions = useMemo(() => [...new Set((data?.available ?? []).map(([c]) => c))], [data]);

  const title = `${Y_LABELS[config.y]} vs ${X_LABELS[config.x].replace(/ \(.*\)/, "")}`;
  const subtitle = [
    `${COMPETITION_LABELS[config.competition] ?? config.competition} ${seasonLabel(config.season)}`,
    `${points.length} players`,
    config.position === "ALL" ? "outfield players" : config.position,
    `${config.minMinutes}+ minutes`,
    ...(possessionOn ? ["scaled to 50% possession"] : []),
    ...(config.sizeByOutput ? ["dot area = goals + assists"] : []),
  ].join(" · ");

  const controls = (
    <>
      <div className="lab-filter-row">
        <label className="aero-field">
          Competition
          <select className="aero-select" value={config.competition}
            onChange={(e) => update({ competition: e.target.value, possessionAdjusted: false })}>
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
        X axis: how much of the ball
        <select className="aero-select" value={config.x} onChange={(e) => update({ x: e.target.value as XMetric })}>
          <option value="pea">{X_LABELS.pea}</option>
          <option value="usage">Usage rate (% of team's actions)</option>
        </select>
      </label>
      <label className="aero-field">
        Y axis: what he makes of it
        <select className="aero-select" value={config.y} onChange={(e) => update({ y: e.target.value as YMetric })}>
          <option value="created">{Y_LABELS.created}</option>
          <option value="xa" disabled={config.competition !== "premier-league"}>{Y_LABELS.xa}{config.competition !== "premier-league" ? " (Premier League only)" : ""}</option>
          <option value="ga">{Y_LABELS.ga}</option>
        </select>
      </label>
      <div className="lab-filter-row">
        <label className="aero-field">
          Position
          <select className="aero-select" value={config.position} onChange={(e) => update({ position: e.target.value as Position })}>
            {(["ALL", "DEF", "MID", "FWD"] as Position[]).map((p) => <option key={p} value={p}>{p === "ALL" ? "All outfield" : p}</option>)}
          </select>
        </label>
        <label className="aero-field">
          Min minutes
          <input className="aero-input" type="number" min={0} step={90} value={config.minMinutes}
            onChange={(e) => update({ minMinutes: Math.max(0, Number(e.target.value) || 0) })} />
        </label>
      </div>
      <label className="lab-check">
        <input type="checkbox" checked={config.sizeByOutput} onChange={(e) => update({ sizeByOutput: e.target.checked })} />
        Size dots by goals + assists
      </label>
      <label className="lab-check" title={data && !data.possessionAvailable ? "Club possession is only published for the Premier League" : undefined}>
        <input type="checkbox" checked={possessionOn} disabled={!data?.possessionAvailable}
          onChange={(e) => update({ possessionAdjusted: e.target.checked })} />
        Adjust for team possession{data && !data.possessionAvailable ? " (Premier League only)" : ""}
      </label>
    </>
  );

  const chart = error ? (
    <p className="aero-empty lab-chart-empty">Couldn't load usage data ({error}).</p>
  ) : !data ? <div className="lab-skeleton" /> : xaMissing ? (
    <p className="aero-empty lab-chart-empty">xA is only published for the Premier League. Pick chances created or goals + assists.</p>
  ) : (
    <ScatterChart points={points} xLabel={X_LABELS[config.x]} yLabel={Y_LABELS[config.y]} highlighted={highlighted}
      onToggle={onToggle} labelled={labelled} fromZero sizeLabel="goals + assists"
      originLine={slope ? { slope, label: `Group average: ${formatValue(slope)} per action` } : undefined} />
  );

  const hint = (
    <>
      Possession-ending actions are shots plus every time the player loses the ball (an incomplete pass or cross, a failed
      take-on, being tackled, a miscontrol), from Opta via the Premier League. Players above the dashed line get more out of
      each action than the group does; below it, they use more of the ball for what they produce. Chances created are passes
      that lead directly to a shot; FBref's "shot-creating actions", used in the videos this chart is based on, aren't available here.
      Usage percentages run lower than basketball's, or the videos', because every failed pass by every player counts, defenders and goalkeepers included.
      {data && data.players.some((p) => !p.teamKnown) && " A few players' season club is unknown, so their usage uses their current club."}
    </>
  );

  return { controls, chart, title, subtitle, hint, players: data?.players ?? [], ids };
}
