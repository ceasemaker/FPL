import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Crest } from "../components/match/icons";
import { WatchStar } from "../components/WatchStar";
import "./MatchPage.css";
import "./TeamPage.css";
import "./TeamNewsPage.css";

// Team news (/team-news): who's out or doubtful, ranked by how many managers
// it affects, and who takes each club's set pieces. Flags and news are FPL's;
// set-piece counts are this season's league matches (Opta).

interface Flag { id: number; name: string; position: string; status: string; label: string; chance: number | null; news: string; since: string | null; ownership: number }
interface Taker { id: number; name: string; count: number }
interface Club { id: string; name: string; short: string; flagged: Flag[]; setPieces: { penalties: Taker[]; corners: Taker[]; freeKicks: Taker[] } }
interface Payload { deadline: { gameweek: number; time: string } | null; season: number; clubs: Club[]; flaggedCount: number }
interface Row extends Flag { club: Club; injury: string; detail: string }
type View = "injuries" | "setpieces";
type Status = "all" | "out" | "doubt" | "ban";

// FPL news reads "Hamstring injury - Expected back 01 Nov": split the what from the when.
function splitNews(news: string): { injury: string; detail: string } {
  const [head, ...rest] = news.split(" - ");
  const detail = rest.join(" - ").trim();
  // "75% chance of playing" repeats the status chip; keep only real return news.
  return { injury: head.trim() || "No details", detail: /chance of playing/i.test(detail) ? "" : detail };
}

function countdown(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "passed";
  const h = Math.floor(ms / 3_600_000), d = Math.floor(h / 24);
  return d >= 1 ? `${d}d ${h % 24}h` : `${h}h ${Math.floor((ms % 3_600_000) / 60_000)}m`;
}

function chip(r: Flag): { text: string; tone: string } {
  if (r.status === "s") return { text: "Suspended", tone: "ban" };
  if (r.status === "i" || r.chance === 0) return { text: "Out", tone: "out" };
  return { text: r.chance != null ? `${r.chance}%` : "Doubt", tone: r.chance != null && r.chance >= 75 ? "likely" : "doubt" };
}

export function TeamNewsPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("injuries");
  const [status, setStatus] = useState<Status>("all");
  const [pos, setPos] = useState<string>("all");
  const [owned, setOwned] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    document.title = "Team news · AeroFPL";
    fetch("/api/team-news/").then((r) => (r.ok ? r.json() : Promise.reject())).then(setData).catch(() => setError("Team news couldn't be loaded. Try again in a minute."));
  }, []);

  const all: Row[] = useMemo(() => (data?.clubs ?? []).flatMap((c) => c.flagged.map((f) => ({ ...f, club: c, ...splitNews(f.news) })))
    .sort((a, b) => b.ownership - a.ownership), [data]);
  const rows = all.filter((r) => {
    const tone = chip(r).tone;
    if (status === "out" && tone !== "out") return false;
    if (status === "doubt" && tone !== "doubt" && tone !== "likely") return false;
    if (status === "ban" && tone !== "ban") return false;
    if (pos !== "all" && r.position !== pos) return false;
    if (owned && r.ownership < 5 && !q) return false;
    return !q || `${r.name} ${r.club.name} ${r.club.short}`.toLowerCase().includes(q.toLowerCase());
  });
  const big = all.filter((r) => r.ownership >= 5);
  const top = big[0];

  return (
    <main className="aero-page mp-page tp-page tn-page">
      <header className="tn-head">
        <div>
          <h1>Team news</h1>
          <p>Who's out or in doubt, and who takes the set pieces.</p>
        </div>
        {data?.deadline && (
          <div className="tn-deadline" role="timer" aria-label={`Gameweek ${data.deadline.gameweek} deadline`}>
            <span>GW{data.deadline.gameweek} deadline</span>
            <b>{countdown(data.deadline.time)}</b>
            <small>{new Date(data.deadline.time).toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</small>
          </div>
        )}
      </header>

      {error && <p className="mp-error" role="alert">{error}</p>}
      {!data && !error && <div className="mp-skeleton tall" aria-busy="true" />}
      {data && (
        <>
          {top && <p className="tp-summary">{big.length} player{big.length === 1 ? "" : "s"} owned by 5% or more of managers {big.length === 1 ? "is" : "are"} flagged. The most owned is {top.name} ({top.club.short}, {top.ownership.toFixed(1)}% owned): {chip(top).text === "Out" ? "out" : chip(top).text === "Suspended" ? "suspended" : `${chip(top).text.toLowerCase()} to play`}{top.detail ? `, ${top.detail.toLowerCase()}` : ""}.</p>}

          <div className="tp-filters">
            <div className="tp-seg" role="group" aria-label="View">
              <button type="button" aria-pressed={view === "injuries"} onClick={() => setView("injuries")}>Injuries &amp; bans</button>
              <button type="button" aria-pressed={view === "setpieces"} onClick={() => setView("setpieces")}>Set-piece takers</button>
            </div>
            {view === "injuries" && <>
              <div className="tp-seg" role="group" aria-label="Status">
                {([["all", "All"], ["out", "Out"], ["doubt", "Doubtful"], ["ban", "Suspended"]] as [Status, string][]).map(([k, l]) => <button key={k} type="button" aria-pressed={status === k} onClick={() => setStatus(k)}>{l}</button>)}
              </div>
              <div className="tp-seg" role="group" aria-label="Position">
                {["all", "GKP", "DEF", "MID", "FWD"].map((p) => <button key={p} type="button" aria-pressed={pos === p} onClick={() => setPos(p)}>{p === "all" ? "Any" : p}</button>)}
              </div>
              <label className="tn-check"><input type="checkbox" checked={owned} onChange={(e) => setOwned(e.target.checked)} /> Owned by 5%+</label>
              <input className="aero-input tn-search" placeholder="Search player or club" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
            </>}
          </div>

          {view === "injuries" ? (
            <div className="mp-sheet tn-table">
              <table>
                <thead><tr><th scope="col">Player</th><th scope="col">Status</th><th scope="col">What</th><th scope="col" className="hide-s">Return</th><th scope="col" className="n">Owned</th></tr></thead>
                <tbody>
                  {rows.map((r) => {
                    const c = chip(r);
                    return (
                      <tr key={r.id}>
                        <th scope="row"><Link to={`/players/${r.id}`}><Crest team={r.club.id} /><span>{r.name}</span></Link><WatchStar id={r.id} name={r.name} size={14} /><small>{r.club.short} · {r.position}</small></th>
                        <td><span className={`tn-chip ${c.tone}`}>{c.text}</span></td>
                        <td className="what">{r.injury}<small className="show-s">{r.detail}</small></td>
                        <td className="hide-s ret">{r.detail || "–"}</td>
                        <td className="n">{r.ownership.toFixed(1)}%</td>
                      </tr>
                    );
                  })}
                  {rows.length === 0 && <tr><td colSpan={5} className="mp-note">{owned ? "Nobody owned by 5%+ matches. Untick it to see everyone." : "No players match."}</td></tr>}
                </tbody>
              </table>
              <p className="mp-note tn-foot">{rows.length} of {data.flaggedCount} flagged players, most owned first. Flags and news from FPL.</p>
            </div>
          ) : (
            <div className="mp-sheet tn-table tn-sp">
              <table>
                <thead><tr><th scope="col">Club</th><th scope="col">Penalties</th><th scope="col">Corners</th><th scope="col">Free kicks</th></tr></thead>
                <tbody>
                  {data.clubs.map((c) => (
                    <tr key={c.id}>
                      <th scope="row"><Link to={`/teams/${c.id}`}><Crest team={c.id} /><span>{c.short}</span></Link></th>
                      {(["penalties", "corners", "freeKicks"] as const).map((k) => (
                        <td key={k}>
                          {c.setPieces[k].length === 0 ? <span className="none">None yet</span> : <>
                            <Link className="main" to={`/players/${c.setPieces[k][0].id}`}>{c.setPieces[k][0].name}<b>{c.setPieces[k][0].count}</b></Link>
                            {c.setPieces[k].slice(1, 3).map((t) => <Link key={t.id} className="alt" to={`/players/${t.id}`}>{t.name} {t.count}</Link>)}
                          </>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mp-note tn-foot">How many each player has taken in this season's league matches (Opta): penalties taken, corners taken, and free kicks shot or crossed. Counts, not official orders.</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
