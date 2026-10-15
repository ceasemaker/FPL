import { useEffect, useMemo, useState, type ReactNode } from "react";
import { BarChart, ChangeChart, type BarItem, type ChangeItem } from "./LabCharts";

// Year-on-year squad changes, two ideas from Sincere FC's videos:
// - Defenders lost: the goalkeeper and defender minutes each club lost since
//   last season ("The Iraola Files").
// - Made the leap: players at the same club two seasons running whose share
//   of the ball or output moved the most.

interface Leaver { name: string; position: string; minutes: number; to: string }
interface Club {
  code: number;
  team: string;
  promoted: boolean;
  minutesLost: number | null;
  share: number | null;
  defensiveMinutes: number | null;
  leavers: Leaver[];
  concededBefore: number | null;
  concededNow: number | null;
  matchesNow: number;
}
interface TurnoverPayload {
  season: number;
  seasonLabel: string;
  previousLabel: string;
  inProgress: boolean;
  available: number[];
  clubs: Club[];
  relationship: {
    seasons: string[];
    clubSeasons: number;
    heavyCount: number;
    heavyMinShare: number;
    heavyChange: number;
    restChange: number;
    difference: number;
    differenceRange: [number, number] | null;
  } | null;
}

type LeapMetric = "usage" | "created90" | "xgi90" | "box90";
interface Profile { minutes: number; usage: number | null; created90: number | null; xgi90: number | null; box90: number | null }
interface LeapPlayer { id: string; name: string; position: string; team: string; before: Profile; now: Profile }
interface LeapPayload {
  season: number;
  seasonLabel: string;
  previousLabel: string;
  inProgress: boolean;
  available: number[];
  players: LeapPlayer[];
  persistence: {
    seasons: string[];
    minMinutes: number;
    metrics: Partial<Record<LeapMetric, { risers: number; medianKept: number; stillAbove: number }>>;
  } | null;
}

export interface ChangesConfig {
  view: "turnover" | "leap";
  season: number | null; // null = latest
  turnoverBy: "minutes" | "share";
  metric: LeapMetric;
  position: "ALL" | "DEF" | "MID" | "FWD";
  minBefore: number;
  minNow: number;
  direction: "rise" | "fall";
}

export const DEFAULT_CHANGES: ChangesConfig = {
  view: "turnover",
  season: null,
  turnoverBy: "minutes",
  metric: "usage",
  position: "ALL",
  minBefore: 900,
  minNow: 450,
  direction: "rise",
};

const METRICS: Record<LeapMetric, { label: string; short: string; digits: number }> = {
  usage: { label: "Usage rate (share of the team's ball, %)", short: "usage rate", digits: 1 },
  created90: { label: "Chances created per 90", short: "chances created per 90", digits: 2 },
  xgi90: { label: "xG + xA per 90", short: "xG + xA per 90", digits: 2 },
  box90: { label: "Touches in the box per 90", short: "touches in the box per 90", digits: 1 },
};
const ROWS = 15;
const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;
const pct = (v: number) => `${Math.round(v * 100)}%`;
const goals = (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}`;

// Phone widths get the compact charts (larger text, no detail labels).
function useNarrow(query = "(max-width: 600px)") {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const onChange = () => setNarrow(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  return narrow;
}

function useFetch<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!url) return;
    let alive = true;
    setData(null);
    fetch(url)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<T>; })
      .then((p) => { if (alive) { setData(p); setError(null); } })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [url]);
  return { data, error };
}

export function useChangesView(active: boolean, config: ChangesConfig, update: (patch: Partial<ChangesConfig>) => void) {
  const seasonQuery = config.season ? `?season=${config.season}` : "";
  const turnover = useFetch<TurnoverPayload>(active && config.view === "turnover" ? `/api/chart-lab/turnover/${seasonQuery}` : null);
  const leap = useFetch<LeapPayload>(active && config.view === "leap" ? `/api/chart-lab/leap/${seasonQuery}` : null);
  const narrow = useNarrow();
  const payload = config.view === "turnover" ? turnover.data : leap.data;
  const error = config.view === "turnover" ? turnover.error : leap.error;

  // ---------------------------------------------------------------- defenders lost
  const clubs = useMemo(() => (turnover.data?.clubs ?? []).filter((c) => !c.promoted && c.minutesLost !== null), [turnover.data]);
  const promoted = useMemo(() => (turnover.data?.clubs ?? []).filter((c) => c.promoted).map((c) => c.team), [turnover.data]);
  const barItems = useMemo<BarItem[]>(() => {
    const value = (c: Club) => (config.turnoverBy === "share" ? (c.share ?? 0) * 100 : c.minutesLost ?? 0);
    return [...clubs].sort((a, b) => value(b) - value(a)).map((c) => ({
      id: c.code,
      label: c.team,
      detail: `${c.leavers.length} player${c.leavers.length === 1 ? "" : "s"} · ${pct(c.share ?? 0)}`,
      value: value(c),
      highlighted: false,
    }));
  }, [clubs, config.turnoverBy]);

  // ---------------------------------------------------------------- made the leap
  const leapItems = useMemo<ChangeItem[]>(() => {
    if (!leap.data) return [];
    const m = config.metric;
    const rows = leap.data.players.flatMap((p) => {
      const before = p.before[m], after = p.now[m];
      if (before === null || after === null) return [];
      if (p.before.minutes < config.minBefore || p.now.minutes < config.minNow) return [];
      if (config.position !== "ALL" && p.position !== config.position) return [];
      return [{ id: p.id, label: p.name, detail: `${p.team} ${p.position}`, before, after }];
    });
    const sign = config.direction === "rise" ? 1 : -1;
    rows.sort((a, b) => sign * ((b.after - b.before) - (a.after - a.before)));
    return rows.slice(0, ROWS).filter((r) => sign * (r.after - r.before) > 0);
  }, [leap.data, config.metric, config.minBefore, config.minNow, config.position, config.direction]);

  const seasons = payload?.available ?? [];
  const season = payload?.season ?? config.season ?? null;

  // The one-sentence answer shown above each chart.
  let takeaway: ReactNode = null;
  if (config.view === "turnover" && turnover.data) {
    const top = barItems[0];
    const r = turnover.data.relationship;
    const noEffect = r?.differenceRange && r.differenceRange[0] < 0 && r.differenceRange[1] > 0;
    takeaway = (
      <>
        {top && <><strong>{top.label}</strong> lost the most: {Math.round(clubs.find((c) => c.code === top.id)?.minutesLost ?? 0).toLocaleString()} minutes of {turnover.data.previousLabel} goalkeeping and defending, {top.detail.split(" · ")[1]} of their total. </>}
        {r && (noEffect
          ? <>Does it matter? Not on its own: across {r.clubSeasons} club-seasons ({r.seasons[0]}–{r.seasons[r.seasons.length - 1]}), the clubs that lost the most did not concede noticeably more the next season than everyone else ({goals(r.heavyChange)} vs {goals(r.restChange)} goals a game).</>
          : <>Across {r.clubSeasons} club-seasons ({r.seasons[0]}–{r.seasons[r.seasons.length - 1]}), the clubs that lost the most conceded {goals(r.heavyChange)} goals a game the next season, against {goals(r.restChange)} for everyone else.</>)}
      </>
    );
  }
  if (config.view === "leap" && leap.data) {
    const top = leapItems[0];
    const kept = leap.data.persistence?.metrics[config.metric];
    const info = METRICS[config.metric];
    takeaway = (
      <>
        {top && <><strong>{top.label}</strong> moved the most: {info.short} {top.before.toFixed(info.digits)} → {top.after.toFixed(info.digits)}. </>}
        {kept && config.direction === "rise" && <>Do big rises last? Mostly: the biggest risers in past seasons kept about {pct(kept.medianKept)} of the rise the season after, and {pct(kept.stillAbove)} stayed above their old level.</>}
        {leap.data.inProgress && <> This season is still early, so these numbers can still swing.</>}
      </>
    );
  }

  const title = config.view === "turnover"
    ? `Defenders and keepers lost since ${turnover.data?.previousLabel ?? "last season"}`
    : `Made the leap: ${METRICS[config.metric].short}`;
  const subtitle = config.view === "turnover"
    ? turnover.data ? `Premier League ${turnover.data.seasonLabel} · ${config.turnoverBy === "share" ? "share of last season's goalkeeper and defender minutes" : "minutes played last season by goalkeepers and defenders who have since left"}` : ""
    : leap.data ? `${leap.data.previousLabel} → ${leap.data.seasonLabel} · same club both seasons · ${config.position === "ALL" ? "outfield players" : config.position} · ${config.minBefore}+ and ${config.minNow}+ minutes` : "";

  const controls = (
    <>
      <div className="lab-mode lab-mode-two" role="tablist" aria-label="Which change">
        {(["turnover", "leap"] as const).map((view) => (
          <button key={view} role="tab" aria-selected={config.view === view}
            className={`lab-pill ${config.view === view ? "active" : ""}`} onClick={() => update({ view, season: null })}>
            {view === "turnover" ? "Defenders lost" : "Made the leap"}
          </button>
        ))}
      </div>
      <label className="aero-field">
        Season
        <select className="aero-select" value={season ?? ""} onChange={(e) => update({ season: Number(e.target.value) })}>
          {(seasons.length ? seasons : season ? [season] : []).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
        </select>
      </label>
      {config.view === "turnover" ? (
        <label className="aero-field">
          Measure
          <select className="aero-select" value={config.turnoverBy} onChange={(e) => update({ turnoverBy: e.target.value as ChangesConfig["turnoverBy"] })}>
            <option value="minutes">Minutes lost</option>
            <option value="share">Share of last season's minutes</option>
          </select>
        </label>
      ) : (
        <>
          <label className="aero-field">
            Measure
            <select className="aero-select" value={config.metric} onChange={(e) => update({ metric: e.target.value as LeapMetric })}>
              {(Object.keys(METRICS) as LeapMetric[]).map((m) => <option key={m} value={m}>{METRICS[m].label}</option>)}
            </select>
          </label>
          <div className="lab-filter-row">
            <label className="aero-field">
              Show
              <select className="aero-select" value={config.direction} onChange={(e) => update({ direction: e.target.value as ChangesConfig["direction"] })}>
                <option value="rise">Biggest rises</option>
                <option value="fall">Biggest falls</option>
              </select>
            </label>
            <label className="aero-field">
              Position
              <select className="aero-select" value={config.position} onChange={(e) => update({ position: e.target.value as ChangesConfig["position"] })}>
                {(["ALL", "DEF", "MID", "FWD"] as const).map((p) => <option key={p} value={p}>{p === "ALL" ? "All outfield" : p}</option>)}
              </select>
            </label>
          </div>
          <div className="lab-filter-row">
            <label className="aero-field">
              Min minutes, last season
              <input className="aero-input" type="number" min={0} step={90} value={config.minBefore}
                onChange={(e) => update({ minBefore: Math.max(0, Number(e.target.value) || 0) })} />
            </label>
            <label className="aero-field">
              Min minutes, this season
              <input className="aero-input" type="number" min={0} step={90} value={config.minNow}
                onChange={(e) => update({ minNow: Math.max(0, Number(e.target.value) || 0) })} />
            </label>
          </div>
        </>
      )}
    </>
  );

  const chart = error ? (
    <p className="aero-empty lab-chart-empty">Couldn't load the data ({error}).</p>
  ) : !payload ? <div className="lab-skeleton" /> : config.view === "turnover" ? (
    <BarChart items={barItems} compact={narrow} format={(v) => (config.turnoverBy === "share" ? `${Math.round(v)}%` : Math.round(v).toLocaleString())} />
  ) : (
    <ChangeChart items={leapItems} beforeLabel={leap.data!.previousLabel} afterLabel={leap.data!.seasonLabel} digits={METRICS[config.metric].digits} compact={narrow} />
  );

  const details = config.view === "turnover" && turnover.data ? (
    <div className="lab-table-wrap">
      <table className="lab-table">
        <thead>
          <tr><th>Club</th><th>Who left (minutes last season)</th><th>Goals conceded a game</th></tr>
        </thead>
        <tbody>
          {barItems.map((item) => {
            const club = clubs.find((c) => c.code === item.id)!;
            return (
              <tr key={club.code}>
                <td>{club.team}</td>
                <td>{club.leavers.length ? club.leavers.slice(0, 4).map((l) => `${l.name} ${l.minutes.toLocaleString()}`).join(", ") + (club.leavers.length > 4 ? `, +${club.leavers.length - 4} more` : "") : "Nobody"}</td>
                <td className="lab-table-num">{club.concededBefore?.toFixed(2) ?? "—"} → {club.matchesNow ? club.concededNow?.toFixed(2) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  ) : null;

  const hint = config.view === "turnover" ? (
    <>
      A player who played every minute of a season would account for 3,420 minutes. "Left" means he was not at the club when the season
      began: sold, loaned out, released or retired. Goals conceded compare last season with this one{turnover.data?.inProgress ? " so far" : ""}.
      {promoted.length > 0 && ` Promoted clubs (${promoted.join(", ")}) have no Premier League minutes to compare, so they are left out.`}
      {" "}Idea from Sincere FC's "The Iraola Files".
    </>
  ) : (
    <>
      Only players at the same club in both seasons, so a change reflects his role, not a new team. Usage rate is his share of the team's
      possession-ending actions (shots plus losing the ball) while he is on the pitch; xG + xA is Premier League only.
      {leap.data?.persistence && ` "Do big rises last?" uses the top fifth of rises in ${leap.data.persistence.seasons.join(", ")} among players with ${leap.data.persistence.minMinutes}+ minutes in all three seasons.`}
    </>
  );

  return { controls, chart, details, title, subtitle, hint, takeaway };
}
