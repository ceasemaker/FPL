import { useEffect, useMemo, useState } from "react";
import { ChevronIcon, InfoIcon } from "./icons";
import {
  formatStat, minutesFor, ordinal, percentile, POSITION_NAMES, qualifies, statValue, TOP_PERCENTILE,
  type ExplorerPayload, type ExplorerPlayer, type Norm, type Position, type Stat,
} from "./explorerModel";
import { DEFAULT_STATE } from "./useExplorerState";

// The Stats Explorer's full stat sheet for one player (it used to live in the
// explorer's side drawer; it now sits on the Player page). Same payload and
// same maths as the explorer table, so the numbers always agree: Premier
// League, Champions League and both, with a percentile bar among players in
// his position with enough minutes behind each stat.

const GROUP_ORDER: Record<Position, string[]> = {
  GKP: ["Goalkeeping", "Involvement", "Defending", "Creating", "Shooting"],
  DEF: ["Defending", "Involvement", "Creating", "Shooting", "Goalkeeping"],
  MID: ["Creating", "Shooting", "Involvement", "Defending", "Goalkeeping"],
  FWD: ["Shooting", "Creating", "Involvement", "Defending", "Goalkeeping"],
};

// The explorer's watchlist (same key), so watching from either place is the same list.
const WATCH_KEY = "aerofpl_stats_watchlist";
export function useWatch(id: number): [boolean, () => void] {
  const read = (): number[] => { try { return JSON.parse(localStorage.getItem(WATCH_KEY) ?? "[]"); } catch { return []; } };
  const [list, setList] = useState<number[]>(read);
  const toggle = () => {
    const next = list.includes(id) ? list.filter((w) => w !== id) : [...list, id];
    setList(next);
    try { localStorage.setItem(WATCH_KEY, JSON.stringify(next)); } catch { /* private window: forgets */ }
  };
  return [list.includes(id), toggle];
}

// One request per visit: every Player page shares the payload.
let explorerRequest: Promise<ExplorerPayload | null> | null = null;
export function loadExplorer(season = 2026): Promise<ExplorerPayload | null> {
  if (!explorerRequest) {
    explorerRequest = fetch(`/api/stats-explorer/?season=${season}`)
      .then((r) => (r.ok ? (r.json() as Promise<ExplorerPayload>) : null))
      .catch(() => null);
    explorerRequest.then((d) => { if (!d) explorerRequest = null; });  // let a failure be retried
  }
  return explorerRequest;
}

export function StatSheet({ playerId }: { playerId: number }) {
  const [data, setData] = useState<ExplorerPayload | null | undefined>(undefined);
  const [norm, setNorm] = useState<Norm>("p90");
  useEffect(() => { let alive = true; loadExplorer().then((d) => { if (alive) setData(d); }); return () => { alive = false; }; }, []);

  const player = data?.players.find((p) => p.id === playerId) ?? null;
  // The season's ranking bar, the same one the explorer table uses.
  const minMinutes = data?.minMinutes ?? DEFAULT_STATE.minMinutes;
  const smallSample = data?.smallSample ?? 450;

  // Cohorts as in the explorer table: same position, enough minutes behind the stat.
  const cohorts = useMemo(() => {
    const map = new Map<string, number[]>();
    if (!data || !player) return map;
    for (const stat of data.catalogue) {
      const list: number[] = [];
      for (const p of data.players) {
        if (p.position !== player.position || !qualifies(stat, p, "pl", minMinutes)) continue;
        const v = statValue(stat, p, "pl", norm);
        if (v !== null) list.push(v);
      }
      map.set(stat.key, list.sort((a, b) => a - b));
    }
    return map;
  }, [data, player, norm, minMinutes]);

  if (data === undefined) return <div className="sx-sheet-loading" aria-busy="true">Loading the full stat sheet…</div>;
  if (data === null) return <p className="mp-note">The full stat sheet couldn't be loaded. Try again in a minute.</p>;
  if (!player) return <p className="mp-note">No Opta season stats for him yet this season.</p>;

  const groups = new Map<string, Stat[]>();
  for (const s of data.catalogue) {
    if (s.kind === "fpl") continue;  // price, ownership and FPL points are at the top of the page
    groups.set(s.group, [...(groups.get(s.group) ?? []), s]);
  }
  const order = [...(GROUP_ORDER[player.position] ?? []), ...groups.keys()].filter((g, i, all) => groups.has(g) && all.indexOf(g) === i);
  const plMins = Math.round(minutesFor(player, "pl")), uclMins = Math.round(player.ucl?.mins_played ?? 0);

  const uclValue = (stat: Stat): number | null => {
    if (!player.ucl || stat.plOnly) return null;
    return statValue(stat, { ...player, pl: player.ucl, ucl: null } as ExplorerPlayer, "pl", norm);
  };

  const rows = (stats: Stat[]) => stats.map((s) => {
    const pl = statValue(s, player, "pl", norm);
    const both = statValue(s, player, "all", norm);
    const qualified = qualifies(s, player, "pl", minMinutes);
    const cohort = cohorts.get(s.key) ?? [];
    const pct = qualified && pl !== null ? percentile(pl, cohort, s.lowerIsBetter) : null;
    return (
      <tr key={s.key}>
        <th scope="row" title={s.help}>
          {s.label}
          {s.plOnly && s.source === "Opta" && <span className="sx-badge">PL only</span>}
          {s.source === "Estimate" && <span className="sx-badge">Estimate</span>}
        </th>
        <td className="n">{formatStat(s, pl, norm)}</td>
        <td className="n dim">{player.ucl ? formatStat(s, uclValue(s), norm) : "–"}</td>
        <td className="n">{player.ucl && !s.plOnly ? formatStat(s, both, norm) : "–"}</td>
        <td className="pct">
          {pct !== null && (
            <span className="ss-bar" role="img" aria-label={`Better than ${pct}% of ${POSITION_NAMES[player.position]} (${ordinal(pct)} percentile)`}>
              <i style={{ width: `${Math.max(3, pct)}%` }} className={pct >= TOP_PERCENTILE ? "top" : ""} />
            </span>
          )}
          {pct !== null && <small>{ordinal(pct)}</small>}
        </td>
      </tr>
    );
  });

  return (
    <div className="ss">
      <div className="ss-tools">
        <p>{plMins.toLocaleString()} Premier League minutes{player.ucl ? ` · ${uclMins.toLocaleString()} Champions League minutes` : ""}. Bars: percentile among {POSITION_NAMES[player.position]} with {minMinutes}+ league minutes (40% of the league minutes so far, at least 270).{plMins < minMinutes ? ` He has ${plMins}, so he isn't ranked yet.` : plMins < smallSample ? ` Small sample: under ${smallSample} minutes, so his per-90 numbers can swing on a game or two.` : ""}</p>
        <div className="tp-seg" role="group" aria-label="Show stats as">
          <button type="button" aria-pressed={norm === "p90"} onClick={() => setNorm("p90")}>Per 90</button>
          <button type="button" aria-pressed={norm === "total"} onClick={() => setNorm("total")}>Season totals</button>
        </div>
      </div>
      {order.map((g, i) => (
        <details key={g} className="mp-sheet ss-group" open={i < 2}>
          <summary><span>{g} <span className="dim">· {groups.get(g)!.length} stats</span></span><ChevronIcon size={14} /></summary>
          <div className="ss-scroll">
            <table>
              <thead><tr><th scope="col">Stat</th><th scope="col" className="n">PL</th><th scope="col" className="n">UCL</th><th scope="col" className="n">Both</th><th scope="col">Among {POSITION_NAMES[player.position]}</th></tr></thead>
              <tbody>{rows(groups.get(g)!)}</tbody>
            </table>
          </div>
        </details>
      ))}
      <p className="mp-note ss-foot"><InfoIcon size={14} /> The Champions League has no xG feed, so xG stats are Premier League only.</p>
    </div>
  );
}
