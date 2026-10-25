import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Crest } from "../components/match/icons";
import "./MatchPage.css";
import "./TeamPage.css";
import "./DefconPage.css";

// DEFCON (/defcon): how reliably each outfield player earns FPL's 2-point
// defensive-contribution bonus. The hit rate (matches with the points over
// matches played) is what repeats; volume per match and recent form follow.

interface Recent { gw: number; hits: number; matches: number; dc: number }
interface Row {
  id: number; name: string; team: string; teamShort: string; position: "DEF" | "MID" | "FWD"; threshold: number;
  price: number; ownership: number; matches: number; hits: number; hitRate: number; perMatch: number; per90: number | null;
  minutes: number; points: number; recent: Recent[]; recentHits: number; recentMatches: number;
}
interface Payload { gameweek: number; thresholds: Record<string, number>; recentGameweeks: number; players: Row[]; available: boolean }
type Sort = "hitRate" | "perMatch" | "recent" | "points" | "value";

export function DefconPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pos, setPos] = useState<"DEF" | "MID" | "FWD">("DEF");
  const [minMatches, setMinMatches] = useState(4);
  const [maxPrice, setMaxPrice] = useState<number | null>(null);
  const [sort, setSort] = useState<Sort>("hitRate");

  useEffect(() => {
    document.title = "DEFCON · AeroFPL";
    fetch("/api/defcon/").then((r) => (r.ok ? r.json() : Promise.reject())).then(setData)
      .catch(() => setError("DEFCON couldn't be loaded. Try again in a minute."));
  }, []);

  const rows = useMemo(() => (data?.players ?? [])
    .filter((p) => p.position === pos && p.matches >= minMatches && (maxPrice == null || p.price <= maxPrice * 10))
    .sort((a, b) => sort === "perMatch" ? b.perMatch - a.perMatch : sort === "recent" ? b.recentHits / (b.recentMatches || 1) - a.recentHits / (a.recentMatches || 1)
      : sort === "points" ? b.points - a.points : sort === "value" ? b.hitRate / b.price - a.hitRate / a.price : b.hitRate - a.hitRate || b.perMatch - a.perMatch),
  [data, pos, minMatches, maxPrice, sort]);

  const top = rows[0];
  const threshold = data?.thresholds[pos] ?? (pos === "DEF" ? 10 : 12);

  return (
    <main className="aero-page mp-page tp-page dc-page">
      <header className="tp-index-head">
        <h1>DEFCON</h1>
        <p>Who earns FPL's defensive-contribution points most reliably. A {pos === "DEF" ? "defender" : pos === "MID" ? "midfielder" : "forward"} gets 2 points for {threshold}+ {pos === "DEF" ? "clearances, blocks, interceptions and tackles" : "clearances, blocks, interceptions, tackles and recoveries"} in a match.</p>
      </header>
      {error && <p className="mp-error" role="alert">{error}</p>}
      {!data && !error && <div className="mp-skeleton tall" aria-busy="true" />}
      {data && !data.available && <p className="mp-note">Defensive contributions are still being loaded for this season.</p>}
      {data && data.available && (
        <>
          {top && <p className="tp-summary">{top.name} ({top.teamShort}) has reached the bar in {top.hits} of {top.matches} matches ({Math.round(top.hitRate * 100)}%), averaging {top.perMatch} actions a match{top.recentMatches ? `, and ${top.recentHits} of the last ${top.recentMatches}` : ""}. Through gameweek {data.gameweek}.</p>}
          <div className="tp-filters">
            <div className="tp-seg" role="group" aria-label="Position">
              {(["DEF", "MID", "FWD"] as const).map((p) => <button key={p} type="button" aria-pressed={pos === p} onClick={() => setPos(p)}>{p === "DEF" ? "Defenders" : p === "MID" ? "Midfielders" : "Forwards"}</button>)}
            </div>
            <label className="dc-label">At least
              <select className="aero-select" value={minMatches} onChange={(e) => setMinMatches(Number(e.target.value))}>{[1, 3, 4, 6].map((n) => <option key={n} value={n}>{n} match{n === 1 ? "" : "es"}</option>)}</select>
            </label>
            <label className="dc-label">Price up to
              <select className="aero-select" value={maxPrice ?? ""} onChange={(e) => setMaxPrice(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Any</option>{[4.5, 5, 5.5, 6, 7].map((v) => <option key={v} value={v}>£{v.toFixed(1)}m</option>)}
              </select>
            </label>
          </div>
          <div className="mp-sheet tp-squad dc-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  {([["hitRate", "Hit rate"], ["recent", `Last ${data.recentGameweeks} GWs`], ["perMatch", "Actions a match"], ["points", "DEFCON pts"], ["value", "Hit rate per £m"]] as [Sort, string][]).map(([k, l]) => (
                    <th key={k} scope="col" className="n"><button type="button" aria-pressed={sort === k} onClick={() => setSort(k)}>{l}</button></th>
                  ))}
                  <th scope="col" className="n">Price</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <th scope="row"><Link to={`/players/${p.id}`}><Crest team={p.team} /><span>{p.name}</span></Link><small>{p.teamShort}</small></th>
                    <td className="n"><span className="dc-rate"><i style={{ width: `${Math.round(p.hitRate * 100)}%` }} className={p.hitRate >= 0.6 ? "top" : ""} /></span>{Math.round(p.hitRate * 100)}%<small> {p.hits}/{p.matches}</small></td>
                    <td className="n"><span className="dc-dots" aria-label={`${p.recentHits} of the last ${p.recentMatches} matches`}>{p.recent.map((r) => <i key={r.gw} className={r.hits ? "hit" : ""} title={`GW${r.gw}: ${r.dc} actions${r.hits ? ", points" : ""}`} />)}</span></td>
                    <td className="n">{p.perMatch.toFixed(1)}</td>
                    <td className="n">{p.points}</td>
                    <td className="n">{(p.hitRate / (p.price / 10) * 100).toFixed(0)}</td>
                    <td className="n">£{(p.price / 10).toFixed(1)}m</td>
                  </tr>
                ))}
                {rows.length === 0 && <tr><td colSpan={7} className="mp-note">No players match.</td></tr>}
              </tbody>
            </table>
          </div>
          <p className="mp-foot">From FPL's own defensive-contribution figures, match by match. A lime dot is a match with the points. "Hit rate per £m" is hit rate (%) divided by price: the cheap reliable ones rank highest.</p>
        </>
      )}
    </main>
  );
}
