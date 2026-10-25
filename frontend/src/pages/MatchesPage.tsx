import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { compById } from "../components/match/competitions";
import { Crest } from "../components/match/icons";
import "./MatchesPage.css";

// Matches (/matches): every game the Premier League clubs play, in every
// competition, on one calendar. Rows are clubs, columns are days, so a
// Thursday in Europe before a Sunday kick-off reads at a glance; the list view
// is the same window grouped by day.

interface Club { id: string; name: string; short: string }
interface CalMatch {
  matchId: string; kickoff: string; competitionId: number; competition: string; round: string;
  home: Club; away: Club; status: "finished" | "upcoming"; score: [number, number] | null; penalties: [number, number] | null;
  gameweek: number | null; fixtureId: number | null; chances: [number, number, number] | null;
}
interface Calendar { start: string; days: number; today: string; clubs: Club[]; matches: CalMatch[]; previous: Record<string, string> }
type Group = "all" | "league" | "europe" | "cup";

const DAYS = 35;
const DAY_MS = 86_400_000;
const GROUPS: [Group, string][] = [["all", "Every competition"], ["league", "Premier League"], ["europe", "Europe"], ["cup", "Domestic cups"]];

const dayKey = (d: Date) => d.toLocaleDateString("en-CA");                      // YYYY-MM-DD in the viewer's time zone
const parseDay = (key: string) => { const [y, m, d] = key.split("-").map(Number); return new Date(y, m - 1, d); };
const addDays = (key: string, n: number) => dayKey(new Date(parseDay(key).getTime() + n * DAY_MS + 3_600_000));
const daysBetween = (a: string, b: string) => Math.round((parseDay(b).getTime() - parseDay(a).getTime()) / DAY_MS);
const mondayBefore = (key: string) => { const d = parseDay(key); return addDays(key, -((d.getDay() + 6) % 7)); };
const words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
const count = (n: number) => words[n] ?? String(n);

interface Cell { match: CalMatch; home: boolean; opp: Club; rest: number | null; res: "W" | "D" | "L" | null; gf: number | null; ga: number | null }

function cellFor(m: CalMatch, club: string, rest: number | null): Cell {
  const home = m.home.id === club;
  const [gf, ga] = m.score ? (home ? m.score : [m.score[1], m.score[0]]) : [null, null];
  let res: Cell["res"] = null;
  if (gf != null && ga != null) {
    res = gf > ga ? "W" : gf < ga ? "L" : "D";
    if (res === "D" && m.penalties) { const [pf, pa] = home ? m.penalties : [m.penalties[1], m.penalties[0]]; res = pf > pa ? "W" : "L"; }
  }
  return { match: m, home, opp: home ? m.away : m.home, rest, res, gf, ga };
}

export function MatchesPage() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<Calendar | null>(null);
  const [error, setError] = useState<string | null>(null);
  const today = dayKey(new Date());
  const start = params.get("from") ?? addDays(mondayBefore(today), -7);
  const view = (params.get("view") ?? (typeof window !== "undefined" && window.innerWidth < 720 ? "list" : "grid")) as "grid" | "list";
  const group = (params.get("comp") ?? "all") as Group;
  const club = params.get("club") ?? "";
  const [showPast, setShowPast] = useState(false);
  const set = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (v == null || v === "") next.delete(k); else next.set(k, v); }
    setParams(next, { replace: true });
  };

  useEffect(() => {
    let alive = true;
    setError(null);
    fetch(`/api/matches/calendar/?start=${addDays(start, -1)}&days=${DAYS + 2}`)
      .then((r) => { if (!r.ok) throw new Error(`The calendar couldn't be loaded (HTTP ${r.status}).`); return r.json() as Promise<Calendar>; })
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [start]);

  useEffect(() => { document.title = "Matches · AeroFPL"; }, []);

  const days = useMemo(() => Array.from({ length: DAYS }, (_, i) => addDays(start, i)), [start]);

  // Rest counts every competition, whatever the filter shows.
  const cells = useMemo(() => {
    const out: Record<string, Record<string, Cell>> = {};
    if (!data) return out;
    for (const c of data.clubs) {
      out[c.id] = {};
      let prev = data.previous[c.id] ? dayKey(new Date(data.previous[c.id])) : null;
      for (const m of data.matches.filter((x) => x.home.id === c.id || x.away.id === c.id)) {
        const key = dayKey(new Date(m.kickoff));
        if (prev && prev >= key) { prev = key; continue; }
        out[c.id][key] = cellFor(m, c.id, prev ? daysBetween(prev, key) : null);
        prev = key;
      }
    }
    return out;
  }, [data]);

  const shown = (m: CalMatch) => group === "all" || compById(m.competitionId, m.competition).group === group;
  const inView = (m: CalMatch) => { const k = dayKey(new Date(m.kickoff)); return k >= start && k < addDays(start, DAYS); };

  const clubs = useMemo(() => {
    if (!data) return [];
    const busy = (id: string) => Object.values(cells[id] ?? {}).filter((c) => shown(c.match) && inView(c.match)).length;
    return [...data.clubs].sort((a, b) => (params.get("sort") === "busy" ? busy(b.id) - busy(a.id) : 0) || a.name.localeCompare(b.name));
  }, [data, cells, group, params, start]);

  const takeaway = useMemo(() => (data ? summarise(data, cells, today) : null), [data, cells, today]);

  const list = useMemo(() => {
    if (!data) return [];
    const rows = data.matches.filter((m) => inView(m) && shown(m) && (!club || m.home.id === club || m.away.id === club)
      && (showPast || dayKey(new Date(m.kickoff)) >= today || start > today));
    const byDay: [string, CalMatch[]][] = [];
    for (const m of rows) {
      const k = dayKey(new Date(m.kickoff));
      if (byDay.length && byDay[byDay.length - 1][0] === k) byDay[byDay.length - 1][1].push(m); else byDay.push([k, [m]]);
    }
    return byDay;
  }, [data, group, club, start, showPast, today]);

  const rangeLabel = `${parseDay(start).toLocaleDateString([], { day: "numeric", month: "short" })} – ${parseDay(addDays(start, DAYS - 1)).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" })}`;

  return (
    <main className="aero-page ms-page">
      <header className="ms-head">
        <div>
          <h1>Matches</h1>
          <p>Every game the Premier League clubs play: the league, the domestic cups and Europe, on one calendar.</p>
        </div>
        <nav className="ms-switch" aria-label="Matches views">
          <span aria-current="page">Calendar</span>
          <Link to="/fixtures">Fixture planner</Link>
        </nav>
      </header>

      {takeaway && <p className="ms-takeaway">{takeaway}</p>}

      <div className="ms-tools">
        <div className="ms-range" role="group" aria-label="Dates">
          <button type="button" onClick={() => set({ from: addDays(start, -28) })} aria-label="Four weeks earlier"><Chevron dir="left" /></button>
          <button type="button" className="today" onClick={() => set({ from: null })}>Today</button>
          <button type="button" onClick={() => set({ from: addDays(start, 28) })} aria-label="Four weeks later"><Chevron dir="right" /></button>
          <span>{rangeLabel}</span>
        </div>
        <div className="ms-seg" role="group" aria-label="Competitions">
          {GROUPS.map(([k, l]) => <button key={k} type="button" aria-pressed={group === k} onClick={() => set({ comp: k === "all" ? null : k })}>{l}</button>)}
        </div>
        <div className="ms-seg" role="group" aria-label="View">
          <button type="button" aria-pressed={view === "grid"} onClick={() => set({ view: "grid" })}>Calendar</button>
          <button type="button" aria-pressed={view === "list"} onClick={() => set({ view: "list" })}>List</button>
        </div>
      </div>

      {error && <p className="ms-error" role="alert">{error}</p>}
      {!data && !error && <div className="ms-skeleton" aria-busy="true" />}

      {data && view === "grid" && (
        <>
          <div className="ms-legend">
            <span><i className="ms-dot rest" />Two or three days since the club's previous game</span>
            <span><b>H</b>/<b>A</b> home or away</span>
            <span>Percent: the bookmakers' chance of a win, where collected</span>
            <label>Order <select className="aero-select" value={params.get("sort") ?? "name"} onChange={(e) => set({ sort: e.target.value === "name" ? null : e.target.value })}>
              <option value="name">Club A–Z</option><option value="busy">Busiest first</option>
            </select></label>
          </div>
          <div className="ms-grid-wrap">
            <table className="ms-grid">
              <thead>
                <tr>
                  <th scope="col" className="club">Club</th>
                  {days.map((d) => {
                    const date = parseDay(d);
                    const first = d === start || date.getDate() === 1;
                    return (
                      <th scope="col" key={d} className={`${d === today ? "today" : ""}${date.getDay() % 6 === 0 ? " weekend" : ""}${date.getDay() === 1 ? " monday" : ""}`}>
                        <span className="m">{first ? date.toLocaleDateString([], { month: "short" }) : ""}</span>
                        <span className="w">{date.toLocaleDateString([], { weekday: "narrow" })}</span>
                        <span className="n">{date.getDate()}</span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {clubs.map((c) => (
                  <tr key={c.id}>
                    <th scope="row" className="club"><Link to={`/teams/${c.id}`}><Crest team={c.id} /><span>{c.short}</span></Link></th>
                    {days.map((d) => {
                      const cell = cells[c.id]?.[d];
                      const date = parseDay(d);
                      const cls = `${d === today ? "today" : ""}${date.getDay() % 6 === 0 ? " weekend" : ""}${date.getDay() === 1 ? " monday" : ""}`;
                      if (!cell || !shown(cell.match)) return <td key={d} className={cls} />;
                      return <td key={d} className={cls}><GridCell cell={cell} club={c} /></td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {data && view === "list" && (
        <>
          <div className="ms-legend">
            <label>Club <select className="aero-select" value={club} onChange={(e) => set({ club: e.target.value || null })}>
              <option value="">Every club</option>
              {data.clubs.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select></label>
          </div>
          {!showPast && start <= today && (
            <button type="button" className="ms-past" onClick={() => setShowPast(true)}>Show results from {parseDay(start).toLocaleDateString([], { day: "numeric", month: "short" })}</button>
          )}
          {list.length === 0 && <p className="ms-empty">No matches in these dates for this filter.</p>}
          {list.map(([d, ms]) => (
            <section key={d} className="ms-day">
              <h2 className={d === today ? "today" : ""}>{d === today ? "Today · " : ""}{parseDay(d).toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}</h2>
              <ul>{ms.map((m) => <ListRow key={m.matchId} m={m} />)}</ul>
            </section>
          ))}
        </>
      )}
    </main>
  );
}

function GridCell({ cell, club }: { cell: Cell; club: Club }) {
  const { match: m, opp, home, rest, res } = cell;
  const comp = compById(m.competitionId, m.competition);
  const chance = m.chances ? (home ? m.chances[0] : m.chances[2]) : null;
  const when = new Date(m.kickoff).toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  const title = `${club.name} ${home ? "v" : "at"} ${opp.name} · ${comp.name}${m.round ? ` ${m.round}` : ""}${m.gameweek ? ` · GW${m.gameweek}` : ""} · ${when}`
    + (m.score ? ` · ${m.score[0]}–${m.score[1]}${m.penalties ? ` (${m.penalties[0]}–${m.penalties[1]} pens)` : ""}` : "")
    + (rest != null ? ` · ${rest} days after the previous game` : "");
  return (
    <Link to={`/matches/${m.matchId}`} className={`ms-cell c-${comp.group} t-${comp.tag}${res ? ` r-${res}` : ""}`} title={title}>
      <b>{opp.short}</b>
      <small>{res ? `${res} ${cell.gf}-${cell.ga}` : chance != null ? `${home ? "H" : "A"} ${Math.round(chance)}%` : `${home ? "H" : "A"}${comp.tag !== "PL" ? ` ${comp.tag}` : ""}`}</small>
      {res && comp.tag !== "PL" && <em>{comp.tag}</em>}
      {!res && chance != null && comp.tag !== "PL" && <em>{comp.tag}</em>}
      {rest != null && rest <= 3 && <i className="ms-dot rest" aria-label={`${rest} days after the previous game`} />}
    </Link>
  );
}

function ListRow({ m }: { m: CalMatch }) {
  const comp = compById(m.competitionId, m.competition);
  const time = new Date(m.kickoff).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return (
    <li>
      <Link to={`/matches/${m.matchId}`} className="ms-row">
        <span className={`tag c-${comp.group}`}>{comp.tag}</span>
        <span className="side home"><span className="nm">{m.home.name}</span><span className="sh">{m.home.short}</span><Crest team={m.home.id} /></span>
        <span className="mid">{m.score ? <><b>{m.score[0]}–{m.score[1]}</b>{m.penalties && <small>{m.penalties[0]}–{m.penalties[1]} pens</small>}</> : <b className="ko">{time}</b>}</span>
        <span className="side away"><Crest team={m.away.id} /><span className="nm">{m.away.name}</span><span className="sh">{m.away.short}</span></span>
        <span className="meta">{m.gameweek ? `GW${m.gameweek}` : m.round || comp.name}{m.chances && !m.score ? ` · ${m.chances[0]}–${m.chances[1]}–${m.chances[2]}%` : ""}</span>
      </Link>
    </li>
  );
}

function Chevron({ dir }: { dir: "left" | "right" }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" aria-hidden="true"><path d={dir === "left" ? "M12.5 4.5 7 10l5.5 5.5" : "M7.5 4.5 13 10l-5.5 5.5"} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

// The two weeks ahead in one or two sentences: who plays most, and the
// shortest turnaround. Built only from the fixtures in view.
function summarise(data: Calendar, cells: Record<string, Record<string, Cell>>, today: string): string | null {
  const until = addDays(today, 14);
  const games = data.clubs.map((c) => {
    const upcoming = Object.entries(cells[c.id] ?? {}).filter(([k]) => k >= today && k < until).map(([, v]) => v);
    return { club: c, upcoming, comps: new Set(upcoming.map((u) => u.match.competitionId)).size };
  }).filter((g) => g.upcoming.length);
  if (!games.length) return null;
  const most = Math.max(...games.map((g) => g.upcoming.length));
  const least = Math.min(...games.map((g) => g.upcoming.length));
  const busiest = games.filter((g) => g.upcoming.length === most);
  const names = (gs: typeof games) => gs.length <= 3 ? gs.map((g) => g.club.name).join(gs.length === 2 ? " and " : ", ").replace(/, ([^,]*)$/, " and $1") : `${gs.length} clubs`;
  const comps = Math.max(...busiest.map((g) => g.comps));
  let text = `Next two weeks: ${names(busiest)} ${busiest.length === 1 ? "plays" : "play"} ${count(most)} times${comps > 1 ? ` across ${count(comps)} competitions` : ""}`;
  if (least < most) text += `; ${names(games.filter((g) => g.upcoming.length === least))} ${count(least)} ${least === 1 ? "time" : "times"}`;
  text += ".";
  const tight = games.flatMap((g) => g.upcoming.filter((u) => u.rest != null && u.rest <= 3).map((u) => ({ club: g.club, cell: u })))
    .sort((a, b) => (a.cell.rest ?? 9) - (b.cell.rest ?? 9));
  if (tight.length) {
    const t = tight[0];
    const day = new Date(t.cell.match.kickoff).toLocaleDateString([], { weekday: "long" });
    text += ` Tightest turnaround: ${t.club.name}, with ${count(t.cell.rest ?? 0)} days between games before ${day}'s ${compById(t.cell.match.competitionId, t.cell.match.competition).name} match.${tight.length > 1 ? ` ${tight.length} games in all come three days or less after the club's previous one (marked with a dot).` : ""}`;
  }
  return text;
}
