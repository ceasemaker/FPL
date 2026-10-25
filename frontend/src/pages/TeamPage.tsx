import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { compById } from "../components/match/competitions";
import { Crest } from "../components/match/icons";
import { ZonesPanel } from "../components/match/MatchSections";
import "./MatchPage.css";
import "./TeamPage.css";

// The Team page (/teams/:teamId, Opta team id): one club's season in every
// competition. The filters choose which games count (competition, venue, the
// last few); every total, the shot zones and the game-by-game xG follow them.

type Stats = Record<string, number | null>;
interface TeamMatch {
  matchId: string; kickoff: string | null; competitionId: number; competition: string; round: string; home: boolean;
  opp: { id: string; name: string; short: string }; status: "finished" | "upcoming"; gf: number | null; ga: number | null;
  res: "W" | "D" | "L" | null; penalties: [number, number] | null; formation: string; for: Stats | null; against: Stats | null;
}
interface TableRow { team: string; name: string; short: string; pos: number; p: number; w: number; d: number; l: number; gf: number; ga: number; gd: number; pts: number }
interface SquadRow {
  optaId: string; fplId: number | null; name: string; short: string; position: string; apps: number; starts: number; minutes: number;
  goals: number; assists: number; fplPoints: number | null; price: number | null; status: string | null; news: string;
}
interface TeamData {
  team: { id: string; name: string; short: string }; season: number; seasons: number[]; table: TableRow[]; position: number | null;
  matches: TeamMatch[]; leagueAverages: Stats; squad: SquadRow[];
}
type Group = "all" | "league" | "europe" | "cup";

const ordinal = (n: number) => `${n}${["th", "st", "nd", "rd"][(n % 100 - 20) % 10] ?? ["th", "st", "nd", "rd"][n % 100] ?? "th"}`;
const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;
const words = ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const said = (n: number) => words[n] ?? String(n);

export function TeamPage() {
  const { teamId } = useParams();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<TeamData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const season = params.get("season");
  const group = (params.get("comp") ?? "all") as Group;
  const venue = params.get("venue") ?? "all";
  const lastN = Number(params.get("last") ?? 0);
  const set = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (!v) next.delete(k); else next.set(k, v); }
    setParams(next, { replace: true });
  };

  useEffect(() => {
    let alive = true;
    setError(null);
    fetch(`/api/teams/${teamId}/${season ? `?season=${season}` : ""}`)
      .then((r) => { if (!r.ok) throw new Error(r.status === 404 ? "We don't have this club." : "Something went wrong loading this club. Try again in a minute."); return r.json() as Promise<TeamData>; })
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [teamId, season]);

  useEffect(() => { if (data) document.title = `${data.team.name} · AeroFPL`; }, [data]);

  const groups = useMemo(() => {
    const present = new Set((data?.matches ?? []).map((m) => compById(m.competitionId, m.competition).group));
    return ([["all", "Every competition"], ["league", "Premier League"], ["europe", "Europe"], ["cup", "Domestic cups"]] as [Group, string][])
      .filter(([k]) => k === "all" || present.has(k));
  }, [data]);

  const played = useMemo(() => {
    if (!data) return [];
    const rows = data.matches.filter((m) => m.status === "finished"
      && (group === "all" || compById(m.competitionId, m.competition).group === group)
      && (venue === "all" || (venue === "home") === m.home));
    return lastN ? rows.slice(-lastN) : rows;
  }, [data, group, venue, lastN]);
  const withStats = played.filter((m) => m.for && m.against);

  if (error) return <main className="aero-page mp-page tp-page"><p className="mp-crumbs"><Link to="/teams">Teams</Link></p><p className="mp-error" role="alert">{error} <Link to="/teams">Back to Teams</Link></p></main>;
  if (!data) return <main className="aero-page mp-page tp-page" aria-busy="true"><div className="mp-skeleton" /><div className="mp-skeleton tall" /></main>;

  const me = data.table.find((r) => r.team === data.team.id);
  const finished = data.matches.filter((m) => m.status === "finished");
  const upcoming = data.matches.filter((m) => m.status === "upcoming").slice(0, 6);
  const sum = (side: "for" | "against", k: string) => withStats.reduce((s, m) => s + (m[side]?.[k] ?? 0), 0);
  // Averages skip games without the stat (no xG outside the league).
  const per = (side: "for" | "against", k: string) => {
    const vals = withStats.map((m) => m[side]?.[k]).filter((v): v is number => v != null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  };
  const withXg = withStats.filter((m) => m.for?.expectedGoals != null);
  const goalsFor = played.reduce((s, m) => s + (m.gf ?? 0), 0), goalsAgainst = played.reduce((s, m) => s + (m.ga ?? 0), 0);
  const record = { W: played.filter((m) => m.res === "W").length, D: played.filter((m) => m.res === "D").length, L: played.filter((m) => m.res === "L").length };
  const scope = `${group === "all" ? "" : `${groups.find(([k]) => k === group)?.[1]} `}${venue === "all" ? "" : `${venue} `}`;

  return (
    <main className="aero-page mp-page tp-page">
      <nav className="mp-crumbs" aria-label="Breadcrumb">
        <Link to="/teams">Teams</Link><span aria-hidden="true">/</span><span>{data.team.name}</span>
      </nav>

      <header className="tp-head">
        <Crest className="tp-crest" team={data.team.id} />
        <div className="tp-title">
          <h1>{data.team.name}</h1>
          <p>{me ? <>{ordinal(me.pos)} in the Premier League · {me.pts} points from {me.p} games · {me.w}W {me.d}D {me.l}L · goal difference {me.gd > 0 ? `+${me.gd}` : me.gd}</> : "Premier League"}</p>
          <div className="tp-form" aria-label="Last five games">
            {finished.slice(-5).map((m) => (
              <Link key={m.matchId} to={`/matches/${m.matchId}`} className={`chip ${m.res}`} title={`${m.competition}: ${m.home ? "v" : "at"} ${m.opp.name} ${m.gf}–${m.ga}`}>
                {m.res}<small>{m.opp.short}</small>
              </Link>
            ))}
          </div>
        </div>
        <label className="tp-season">Season
          <select className="aero-select" value={data.season} onChange={(e) => set({ season: e.target.value, last: null })}>
            {data.seasons.map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
          </select>
        </label>
      </header>

      <p className="tp-summary">{summary(data, me)}</p>

      <div className="tp-filters">
        <div className="tp-seg" role="group" aria-label="Competition">
          {groups.map(([k, l]) => <button key={k} type="button" aria-pressed={group === k} onClick={() => set({ comp: k === "all" ? null : k })}>{l}</button>)}
        </div>
        <div className="tp-seg" role="group" aria-label="Venue">
          {[["all", "Home and away"], ["home", "Home"], ["away", "Away"]].map(([k, l]) => <button key={k} type="button" aria-pressed={venue === k} onClick={() => set({ venue: k === "all" ? null : k })}>{l}</button>)}
        </div>
        <div className="tp-seg" role="group" aria-label="Games">
          {[[0, "Whole season"], [10, "Last 10"], [5, "Last 5"]].map(([k, l]) => <button key={k} type="button" aria-pressed={lastN === k} onClick={() => set({ last: k ? String(k) : null })}>{l}</button>)}
        </div>
        <p className="tp-count">{played.length ? <>{played.length} {scope}game{played.length === 1 ? "" : "s"}: {record.W} won, {record.D} drawn, {record.L} lost, goals {goalsFor}–{goalsAgainst}{withStats.length < played.length ? ` · team stats for ${withStats.length}` : ""}</> : "No games played yet for this choice."}</p>
      </div>

      {withStats.length > 0 && (
        <>
          {withXg.length > 0 && <>
            <div className="mp-sec-title"><div><h2>Game by game</h2><p>Expected goals (xG) for {data.team.short} above the line, for the opponent below. Choose a game to open it.{withXg.length < withStats.length ? " Opta publishes xG for Premier League matches only, so cup and European games are left out." : ""}</p></div></div>
            <XgStrip matches={withXg} team={data.team.short} />
          </>}

          <div className="mp-sec-title"><div><h2>Per game, for and against</h2><p>Averages over these {withStats.length} games. The small figure is the Premier League average for one team in one game.</p></div></div>
          <div className="mp-full">
            <ForAgainst per={per} avg={data.leagueAverages} team={data.team.short} />
            <ZonesPanel label="Shot zones, for and against" sides={[
              { name: `${data.team.short} shots`, stats: totals(withStats, "for"), goals: withStats.reduce((s, m) => s + (m.for?.goals ?? m.gf ?? 0), 0),
                note: `${sum("for", "totalScoringAtt")} shots in ${withStats.length} games, ${sum("for", "ontargetScoringAtt")} on target` },
              { name: "Shots faced", stats: totals(withStats, "against"), goals: withStats.reduce((s, m) => s + (m.against?.goals ?? m.ga ?? 0), 0),
                note: `${sum("against", "totalScoringAtt")} shots faced, ${sum("against", "ontargetScoringAtt")} on target` },
            ]} />
          </div>
        </>
      )}

      <div className="mp-sec-title"><div><h2>Every game</h2><p>{seasonLabel(data.season)}, every competition{upcoming.length ? "; what's next is at the end" : ""}.</p></div></div>
      <MatchLog matches={[...played].reverse()} upcoming={upcoming} />

      <div className="tp-two">
        <section>
          <div className="mp-sec-title"><div><h2>Squad</h2><p>Appearances, goals and assists in every competition{data.squad.some((p) => p.fplPoints != null) ? "; FPL points and price this season" : ""}.</p></div></div>
          <Squad rows={data.squad} />
        </section>
        <section>
          <div className="mp-sec-title"><div><h2>Premier League table</h2><p>Built from the stored results.</p></div></div>
          <MiniTable rows={data.table} team={data.team.id} season={data.season} />
        </section>
      </div>
      <p className="mp-foot">Match data from the Premier League's stats feeds (Opta). Team stats are loaded for most matches; some older European ties have only the score.</p>
    </main>
  );
}

function totals(ms: TeamMatch[], side: "for" | "against"): Stats {
  const out: Stats = {};
  for (const m of ms) for (const [k, v] of Object.entries(m[side] ?? {})) out[k] = (out[k] ?? 0) + (v ?? 0);
  return out;
}

function summary(d: TeamData, me: TableRow | undefined): string {
  const fin = d.matches.filter((m) => m.status === "finished");
  if (!fin.length) return `${d.team.name} haven't played yet in ${seasonLabel(d.season)}.`;
  const parts: string[] = [];
  if (me && me.p) parts.push(`${d.team.name} are ${ordinal(me.pos)} with ${me.pts} points from ${me.p} league games.`);
  const league = fin.filter((m) => m.competitionId === 8 && m.for?.expectedGoals != null && m.against);
  if (league.length >= 3) {
    const xg = league.reduce((s, m) => s + (m.for?.expectedGoals ?? 0), 0) / league.length;
    const xga = league.reduce((s, m) => s + (m.against?.expectedGoals ?? 0), 0) / league.length;
    const avg = d.leagueAverages.expectedGoals ?? 0;
    const desc = (v: number, lowIsGood: boolean) => { const r = v / (avg || 1); const good = lowIsGood ? r < 0.85 : r > 1.15; const bad = lowIsGood ? r > 1.15 : r < 0.85; return good ? "clearly better than" : bad ? "clearly worse than" : "close to"; };
    parts.push(`In the league they create ${xg.toFixed(2)} expected goals a game and allow ${xga.toFixed(2)}; the average team manages ${avg.toFixed(2)}, so their attack is ${desc(xg, false)} average and their defence ${desc(xga, true)} average.`);
  }
  let run = 0;
  const last = fin[fin.length - 1].res;
  for (let i = fin.length - 1; i >= 0 && fin[i].res !== "L"; i--) run++;
  const won5 = fin.slice(-5).filter((m) => m.res === "W").length;
  if (run >= 4) parts.push(`Unbeaten in ${said(run)} in all competitions.`);
  else if (last === "L") parts.push(`Lost their last game; ${said(won5)} wins in the last five in all competitions.`);
  else parts.push(`${won5 === 5 ? "Five wins from five" : `${said(won5)[0].toUpperCase()}${said(won5).slice(1)} win${won5 === 1 ? "" : "s"} in the last five`} in all competitions.`);
  return parts.join(" ");
}

function XgStrip({ matches, team }: { matches: TeamMatch[]; team: string }) {
  const max = Math.max(1.5, ...matches.map((m) => Math.max(m.for?.expectedGoals ?? 0, m.against?.expectedGoals ?? 0)));
  return (
    <section className="mp-sheet tp-xg" aria-label={`Expected goals for ${team} and against, game by game`}>
      <div className="tp-xg-bars">
        {matches.map((m) => {
          const f = m.for?.expectedGoals ?? 0, a = m.against?.expectedGoals ?? 0;
          const comp = compById(m.competitionId, m.competition);
          return (
            <Link key={m.matchId} to={`/matches/${m.matchId}`} className={`tp-xg-col r-${m.res}`}
              title={`${m.home ? "v" : "at"} ${m.opp.name} (${comp.name}) ${m.gf}–${m.ga} · xG ${f.toFixed(2)}–${a.toFixed(2)}`}>
              <span className="up"><em>{f.toFixed(1)}</em><i style={{ height: `${(f / max) * 100}%` }} /></span>
              <span className="dn"><i style={{ height: `${(a / max) * 100}%` }} /><em>{a.toFixed(1)}</em></span>
              <small>{m.opp.short}</small>
              <b>{m.res}</b>
            </Link>
          );
        })}
      </div>
      <div className="tp-xg-key"><span><i className="for" />{team} xG</span><span><i className="ag" />Opponent xG</span><span>Letter: result</span></div>
    </section>
  );
}

function ForAgainst({ per, avg, team }: { per: (s: "for" | "against", k: string) => number | null; avg: Stats; team: string }) {
  const rows: [string, string, number?, string?][] = [
    ["Expected goals (xG)", "expectedGoals", 2],
    ["Shots", "totalScoringAtt", 1],
    ["Shots on target", "ontargetScoringAtt", 1],
    ["Shots inside the box", "attemptsIbox", 1],
    ["Big chances", "bigChanceCreated", 1],
    ["Touches in the opposition box", "touchesInOppBox", 1],
    ["Possession", "possessionPercentage", 0, "%"],
    ["Passes completed", "accuratePass", 0],
    ["Corners won", "wonCorners", 1],
  ];
  return (
    <section className="mp-sheet mp-compare" aria-label="Per game, for and against">
      <div className="mp-compare-head"><span>{team}</span><span>Opponents</span></div>
      {rows.map(([label, k, dp = 0, suf = ""]) => {
        const h = per("for", k), a = per("against", k);
        if (h == null || a == null) return null;
        const fmt = (x: number) => x.toFixed(dp) + suf;
        const total = h + a || 1;
        return (
          <div className="mp-crow" key={k}>
            <span className={`v${h < a ? " lo" : ""}`}>{fmt(h)}</span>
            <span className="l">{label}<span className="mp-split" aria-hidden="true"><i style={{ width: `${(h / total) * 100}%` }} /><i style={{ width: `${(a / total) * 100}%` }} /></span>{avg[k] != null && <small className="tp-avg">League average {fmt(avg[k] ?? 0)}</small>}</span>
            <span className={`v r${a < h ? " lo" : ""}`}>{fmt(a)}</span>
          </div>
        );
      })}
    </section>
  );
}

function MatchLog({ matches, upcoming }: { matches: TeamMatch[]; upcoming: TeamMatch[] }) {
  const date = (k: string | null) => (k ? new Date(k).toLocaleDateString([], { day: "numeric", month: "short" }) : "TBC");
  const row = (m: TeamMatch) => {
    const comp = compById(m.competitionId, m.competition);
    return (
      <tr key={m.matchId}>
        <td className="d">{date(m.kickoff)}</td>
        <td><span className={`tp-tag c-${comp.group}`}>{comp.tag}</span></td>
        <th scope="row"><Link to={`/matches/${m.matchId}`}><Crest team={m.opp.id} /><span>{m.home ? "v" : "at"} {m.opp.name}</span></Link></th>
        <td className={`res r-${m.res ?? "x"}`}>{m.status === "finished" ? <>{m.res} {m.gf}–{m.ga}{m.penalties ? <small> ({m.penalties[0]}–{m.penalties[1]} pens)</small> : null}</> : new Date(m.kickoff ?? "").toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
        <td className="n">{m.for?.expectedGoals != null ? `${m.for.expectedGoals.toFixed(1)}–${(m.against?.expectedGoals ?? 0).toFixed(1)}` : ""}</td>
        <td className="n">{m.for ? `${m.for.totalScoringAtt ?? 0}–${m.against?.totalScoringAtt ?? 0}` : ""}</td>
        <td className="n">{m.for?.possessionPercentage != null ? `${Math.round(m.for.possessionPercentage)}%` : ""}</td>
        <td className="f">{m.formation}</td>
      </tr>
    );
  };
  return (
    <div className="mp-sheet tp-log">
      <table>
        <thead><tr><th scope="col">Date</th><th scope="col">Comp</th><th scope="col">Opponent</th><th scope="col">Result</th><th scope="col" className="n">xG</th><th scope="col" className="n">Shots</th><th scope="col" className="n">Poss.</th><th scope="col" className="f">Shape</th></tr></thead>
        <tbody>
          {matches.map(row)}
          {upcoming.length > 0 && <tr className="sep"><td colSpan={8}>Coming up</td></tr>}
          {upcoming.map(row)}
        </tbody>
      </table>
    </div>
  );
}

function Squad({ rows }: { rows: SquadRow[] }) {
  const [sort, setSort] = useState<keyof SquadRow>("minutes");
  const cols: [keyof SquadRow, string][] = [["apps", "Apps"], ["minutes", "Mins"], ["goals", "Goals"], ["assists", "Assists"], ["fplPoints", "FPL pts"], ["price", "Price"]];
  const shown = rows.filter((r) => r.apps > 0 || r.fplPoints != null).sort((a, b) => ((b[sort] as number) ?? -1) - ((a[sort] as number) ?? -1));
  return (
    <div className="mp-sheet tp-squad">
      <table>
        <thead><tr><th scope="col">Player</th>{cols.map(([k, l]) => <th key={k} scope="col" className="n"><button type="button" aria-pressed={sort === k} onClick={() => setSort(k)}>{l}</button></th>)}</tr></thead>
        <tbody>
          {shown.map((p) => (
            <tr key={p.optaId} className={p.status && p.status !== "a" ? "out" : ""}>
              <th scope="row">{p.fplId ? <Link to={`/players/${p.fplId}`}>{p.short}</Link> : <span>{p.short}</span>}<small>{p.position}</small>{p.news && <em title={p.news} aria-label={p.news}><svg width="12" height="12" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3 18 16.5H2z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" /><path d="M10 8.2v3.6M10 14.2v.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg></em>}</th>
              <td className="n">{p.apps}{p.apps ? <small> ({p.starts})</small> : ""}</td>
              <td className="n">{p.minutes}</td>
              <td className="n">{p.goals || ""}</td>
              <td className="n">{p.assists || ""}</td>
              <td className="n">{p.fplPoints ?? ""}</td>
              <td className="n">{p.price != null ? `£${p.price.toFixed(1)}m` : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mp-note">Apps (starts). Minutes come from the lineups; extra time counts.</p>
    </div>
  );
}

function MiniTable({ rows, team, season }: { rows: TableRow[]; team: string; season: number }) {
  return (
    <div className="mp-sheet tp-table">
      <table>
        <thead><tr><th scope="col">#</th><th scope="col">Club</th><th scope="col" className="n">P</th><th scope="col" className="n">GD</th><th scope="col" className="n">Pts</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.team} className={r.team === team ? "me" : ""}>
              <td>{r.pos}</td>
              <th scope="row"><Link to={`/teams/${r.team}?season=${season}`}><Crest team={r.team} /><span>{r.name}</span></Link></th>
              <td className="n">{r.p}</td><td className="n">{r.gd > 0 ? `+${r.gd}` : r.gd}</td><td className="n b">{r.pts}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// /teams: the clubs, in league order.
export function TeamsPage() {
  const [data, setData] = useState<{ season: number; clubs: { id: string; name: string; short: string; pos?: number; p?: number; w?: number; d?: number; l?: number; gd?: number; pts?: number }[] } | null>(null);
  useEffect(() => { document.title = "Teams · AeroFPL"; fetch("/api/teams/").then((r) => r.json()).then(setData).catch(() => setData({ season: 0, clubs: [] })); }, []);
  return (
    <main className="aero-page mp-page tp-page">
      <header className="tp-index-head"><h1>Teams</h1><p>Every Premier League club: their season in every competition, the squad and the shot zones.</p></header>
      {!data ? <div className="mp-skeleton" aria-busy="true" /> : (
        <div className="tp-index">
          {data.clubs.map((c) => (
            <Link key={c.id} to={`/teams/${c.id}`} className="tp-club">
              <span className="pos">{c.pos ?? ""}</span>
              <Crest team={c.id} />
              <span className="nm">{c.name}</span>
              {c.p != null && <span className="rec">{c.pts} pts · {c.w}W {c.d}D {c.l}L</span>}
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
