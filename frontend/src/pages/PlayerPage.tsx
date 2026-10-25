import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { compById } from "../components/match/competitions";
import { Crest } from "../components/match/icons";
import { PlayerHeatmap } from "../components/PlayerHeatmap";
import { PriceChangePanel } from "../components/priceChange/PriceChange";
import "./MatchPage.css";
import "./TeamPage.css";
import "./PlayerPage.css";

// The Player page (/players/:playerId, FPL id): the one place a player opens,
// wherever he's clicked. FPL first (price, status, points), then his season in
// every competition, how he compares with his position, and what's next.

interface LogRow {
  matchId: string; kickoff: string | null; competitionId: number; competition: string; round: string; home: boolean;
  opp: { id: string; name: string; short: string }; res: "W" | "D" | "L" | null; gf: number | null; ga: number | null;
  started: boolean; minutes: number; unused: boolean; goals: number; assists: number; captain: boolean;
  gameweek: number | null; fpl: number | null; bonus: number | null; xg: number | null; xa: number | null;
}
interface PlayerData {
  id: number; code: number; name: string; short: string; position: string; positionId: number;
  team: { id: string; name: string; short: string }; price: number | null; ownership: number; status: string; news: string; chance: number | null;
  fpl: { points: number; form: number; ppg: number; epNext: number | null; minutes: number; transfersInEvent: number; transfersOutEvent: number };
  season: number;
  byCompetition: { competitionId: number; competition: string; apps: number; starts: number; minutes: number; goals: number; assists: number }[];
  log: LogRow[];
  upcoming: { matchId: string; kickoff: string; competitionId: number; competition: string; home: boolean; opp: { id: string; name: string; short: string }; gameweek: number | null; difficulty: number | null }[];
  compare: { rows: { key: string; label: string; value: number; pct: number | null; decimals: number }[]; poolSize: number; positionName: string; minMinutes: number; qualified: boolean };
  heatmaps: { gameweek: number }[];
}

const POSITION_WORD: Record<string, string> = { GKP: "Goalkeeper", DEF: "Defender", MID: "Midfielder", FWD: "Forward" };
const words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const said = (n: number) => words[n] ?? String(n);
const lower = (t: string) => t[0].toLowerCase() + t.slice(1);  // keeps acronyms like xG
const plural = (n: number, w: string) => `${said(n)} ${w}${n === 1 ? "" : "s"}`;

export function PlayerPage() {
  const { playerId } = useParams();
  const [data, setData] = useState<PlayerData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [heatGw, setHeatGw] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    setData(null); setError(null);
    fetch(`/api/players/${playerId}/page/`)
      .then((r) => { if (!r.ok) throw new Error(r.status === 404 ? "We don't have this player." : `HTTP ${r.status}`); return r.json() as Promise<PlayerData>; })
      .then((d) => { if (alive) { setData(d); setHeatGw(d.heatmaps[0]?.gameweek ?? null); } })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [playerId]);

  useEffect(() => { if (data) document.title = `${data.name} · AeroFPL`; }, [data]);

  if (error) return <main className="aero-page mp-page tp-page pp-page"><p className="mp-crumbs"><Link to="/players">Players</Link></p><p className="mp-error" role="alert">{error}</p></main>;
  if (!data) return <main className="aero-page mp-page tp-page pp-page" aria-busy="true"><div className="mp-skeleton" /><div className="mp-skeleton tall" /></main>;

  const played = data.log.filter((r) => !r.unused);
  const out = data.status !== "a" && data.news;

  return (
    <main className="aero-page mp-page tp-page pp-page">
      <nav className="mp-crumbs" aria-label="Breadcrumb">
        <Link to="/players">Players</Link><span aria-hidden="true">/</span>
        {data.team.id && <><Link to={`/teams/${data.team.id}`}>{data.team.name}</Link><span aria-hidden="true">/</span></>}
        <span>{data.short}</span>
      </nav>

      <header className="pp-head">
        <div className="pp-photo">
          <img src={`https://resources.premierleague.com/premierleague25/photos/players/110x140/${data.code}.png`} alt=""
            onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} />
          {data.team.id && <Crest className="pp-badge" team={data.team.id} />}
        </div>
        <div className="pp-title">
          <h1>{data.name}</h1>
          <p>
            {POSITION_WORD[data.position] ?? data.position}
            {data.team.id && <> · <Link to={`/teams/${data.team.id}`}>{data.team.name}</Link></>}
          </p>
          <dl className="pp-facts">
            <div><dt>Price</dt><dd>{data.price != null ? `£${data.price.toFixed(1)}m` : "–"}</dd></div>
            <div><dt>Owned by</dt><dd>{data.ownership.toFixed(1)}%</dd></div>
            <div><dt>FPL points</dt><dd>{data.fpl.points}</dd></div>
            <div><dt>Form</dt><dd>{data.fpl.form.toFixed(1)}</dd></div>
            <div><dt>Points a game</dt><dd>{data.fpl.ppg.toFixed(1)}</dd></div>
          </dl>
        </div>
        <div className="pp-price"><PriceChangePanel athleteId={data.id} /></div>
      </header>
      {out && <p className={`pp-news${data.status === "d" ? " doubt" : ""}`} role="status">{data.news}{data.chance != null ? ` (${data.chance}% chance of playing next round)` : ""}</p>}

      <p className="tp-summary">{summary(data)}</p>

      <div className="pp-grid">
        <section>
          <div className="mp-sec-title"><div><h2>His season, competition by competition</h2><p>Appearances (starts), minutes from the lineups, goals and assists.</p></div></div>
          <div className="mp-sheet tp-squad">
            <table>
              <thead><tr><th scope="col">Competition</th><th scope="col" className="n">Apps</th><th scope="col" className="n">Mins</th><th scope="col" className="n">Goals</th><th scope="col" className="n">Assists</th></tr></thead>
              <tbody>
                {data.byCompetition.map((c) => {
                  const comp = compById(c.competitionId, c.competition);
                  return (
                    <tr key={c.competitionId}>
                      <th scope="row"><span className={`tp-tag c-${comp.group}`}>{comp.tag}</span><span className="pp-cname">{comp.name}</span></th>
                      <td className="n">{c.apps}<small> ({c.starts})</small></td><td className="n">{c.minutes}</td><td className="n">{c.goals}</td><td className="n">{c.assists}</td>
                    </tr>
                  );
                })}
                {data.byCompetition.length === 0 && <tr><td colSpan={5} className="mp-note">No appearances stored this season.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
        <section>
          <div className="mp-sec-title"><div><h2>How he compares</h2><p>Per 90 minutes in the league, against {data.compare.positionName} with {data.compare.minMinutes}+ league minutes ({data.compare.poolSize} of them).</p></div></div>
          <div className="mp-sheet pp-compare">
            {!data.compare.qualified || !data.compare.rows.length ? (
              <p className="mp-note">Not enough league minutes yet to compare fairly (he needs {data.compare.minMinutes}).</p>
            ) : data.compare.rows.map((r) => (
              <div className="pp-crow" key={r.key}>
                <span className="l">{r.label}</span>
                <span className="v">{r.value.toFixed(r.decimals)}</span>
                <span className="bar" role="img" aria-label={`Better than ${r.pct}% of ${data.compare.positionName}`}><i style={{ width: `${Math.max(2, r.pct ?? 0)}%` }} className={(r.pct ?? 0) >= 80 ? "top" : (r.pct ?? 0) < 25 ? "low" : ""} /></span>
                <span className="p">{r.pct != null ? `better than ${r.pct}%` : ""}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="mp-sec-title"><div><h2>Every game</h2><p>Every match he was in the squad for, in every competition. FPL points, xG and xA are for league games.</p></div></div>
      <div className="mp-sheet tp-log pp-log">
        <table>
          <thead><tr><th scope="col">Date</th><th scope="col">Comp</th><th scope="col">Opponent</th><th scope="col">Result</th><th scope="col" className="n">Mins</th><th scope="col" className="n">G</th><th scope="col" className="n">A</th><th scope="col" className="n">FPL</th><th scope="col" className="n">xG</th><th scope="col" className="n">xA</th></tr></thead>
          <tbody>
            {[...data.log].reverse().map((r) => {
              const comp = compById(r.competitionId, r.competition);
              return (
                <tr key={r.matchId} className={r.unused ? "unused" : ""}>
                  <td className="d">{r.kickoff ? new Date(r.kickoff).toLocaleDateString([], { day: "numeric", month: "short" }) : ""}</td>
                  <td><span className={`tp-tag c-${comp.group}`}>{comp.tag}</span></td>
                  <th scope="row"><Link to={`/matches/${r.matchId}`}><Crest team={r.opp.id} /><span>{r.home ? "v" : "at"} {r.opp.name}</span></Link></th>
                  <td className={`res r-${r.res ?? "x"}`}>{r.res ? `${r.res} ${r.gf}–${r.ga}` : ""}</td>
                  <td className="n">{r.unused ? <small>Unused</small> : <>{r.minutes}{!r.started && <small> sub</small>}</>}</td>
                  <td className="n">{r.goals || ""}</td>
                  <td className="n">{r.assists || ""}</td>
                  <td className="n b">{r.fpl ?? ""}{r.bonus ? <small> +{r.bonus}b</small> : ""}</td>
                  <td className="n">{r.xg != null ? r.xg.toFixed(2) : ""}</td>
                  <td className="n">{r.xa != null ? r.xa.toFixed(2) : ""}</td>
                </tr>
              );
            })}
            {data.log.length === 0 && <tr><td colSpan={10} className="mp-note">No matches stored for him this season.</td></tr>}
          </tbody>
        </table>
      </div>
      {played.length > 0 && <p className="mp-note">FPL bonus is included in the FPL figure and shown as +b.</p>}

      <div className="pp-grid">
        <section>
          <div className="mp-sec-title"><div><h2>What's next</h2><p>{data.team.name}'s next games in every competition. FDR is FPL's 1–5 difficulty rating for league games.</p></div></div>
          <ul className="mp-sheet pp-next">
            {data.upcoming.map((u) => {
              const comp = compById(u.competitionId, u.competition);
              return (
                <li key={u.matchId}><Link to={`/matches/${u.matchId}`}>
                  <span className="d">{new Date(u.kickoff).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" })}</span>
                  <span className={`tp-tag c-${comp.group}`}>{comp.tag}</span>
                  <Crest team={u.opp.id} /><span className="o">{u.home ? "v" : "at"} {u.opp.name}</span>
                  {u.difficulty != null ? <span className={`pp-fdr fdr-${u.difficulty}`} title="FPL difficulty rating">FDR {u.difficulty}</span> : <span />}
                </Link></li>
              );
            })}
            {data.upcoming.length === 0 && <li className="mp-note">No upcoming games stored.</li>}
          </ul>
        </section>
        <section>
          <div className="mp-sec-title"><div><h2>In FPL this gameweek</h2><p>FPL's own numbers.</p></div></div>
          <dl className="mp-sheet pp-fpl">
            <div><dt>FPL's expected points, next gameweek</dt><dd>{data.fpl.epNext != null ? data.fpl.epNext.toFixed(1) : "–"}</dd></div>
            <div><dt>Transferred in this gameweek</dt><dd>{data.fpl.transfersInEvent.toLocaleString()}</dd></div>
            <div><dt>Transferred out this gameweek</dt><dd>{data.fpl.transfersOutEvent.toLocaleString()}</dd></div>
            <div><dt>League minutes (FPL)</dt><dd>{data.fpl.minutes.toLocaleString()}</dd></div>
          </dl>
        </section>
      </div>

      {data.heatmaps.length > 0 && heatGw != null && (
        <>
          <div className="mp-sec-title"><div><h2>Where he played</h2><p>SofaScore heatmap for one league game. Collected while SofaScore heatmaps were switched on.</p></div></div>
          <div className="mp-sheet pp-heat">
            <label>Gameweek <select className="aero-select" value={heatGw} onChange={(e) => setHeatGw(Number(e.target.value))}>
              {data.heatmaps.map((h) => <option key={h.gameweek} value={h.gameweek}>GW{h.gameweek}</option>)}
            </select></label>
            <PlayerHeatmap playerId={data.id} gameweek={heatGw} />
          </div>
        </>
      )}
      <p className="mp-foot">FPL data from the official game; match data from the Premier League's stats feeds (Opta). Percentiles use league games only.</p>
    </main>
  );
}

// Two plain sentences: what he's done, then where he stands out.
function summary(d: PlayerData): string {
  const played = d.log.filter((r) => !r.unused);
  const mins = played.reduce((s, r) => s + r.minutes, 0);
  const g = played.reduce((s, r) => s + r.goals, 0), a = played.reduce((s, r) => s + r.assists, 0);
  const comps = new Set(played.map((r) => r.competitionId)).size;
  if (!played.length) return `${d.short} hasn't played for ${d.team.name || "his club"} yet this season.`;
  let text = `${d.short} has played ${mins.toLocaleString()} minutes in ${plural(played.length, "game")}${comps > 1 ? ` across ${said(comps)} competitions` : ""}: ${plural(g, "goal")} and ${plural(a, "assist")}.`;
  const rows = d.compare.rows.filter((r) => r.pct != null && r.key !== "points");
  if (d.compare.qualified && rows.length) {
    const best = [...rows].sort((x, y) => (y.pct ?? 0) - (x.pct ?? 0))[0];
    const worst = [...rows].sort((x, y) => (x.pct ?? 0) - (y.pct ?? 0))[0];
    if ((best.pct ?? 0) >= 70) text += ` In the league his ${lower(best.label)} per 90 is better than ${best.pct}% of ${d.compare.positionName}`;
    else text += ` In the league he is around the middle of the ${d.compare.positionName} on most measures`;
    if (worst !== best && (worst.pct ?? 100) <= 30) text += `; his ${lower(worst.label)} is lower than most (better than only ${worst.pct}%).`;
    else text += ".";
  }
  return text;
}
