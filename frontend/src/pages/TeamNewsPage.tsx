import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Crest } from "../components/match/icons";
import "./MatchPage.css";
import "./TeamPage.css";
import "./DefconPage.css";

// Team news (/team-news): every club's injured, doubtful and suspended players
// (FPL's own flags), who has taken their penalties, corners and free kicks
// this season, and the next deadline.

interface Flag { id: number; name: string; position: string; status: string; label: string; chance: number | null; news: string; since: string | null; ownership: number }
interface Taker { id: number; name: string; count: number }
interface Club { id: string; name: string; short: string; flagged: Flag[]; setPieces: { penalties: Taker[]; corners: Taker[]; freeKicks: Taker[] } }
interface Payload { deadline: { gameweek: number; time: string } | null; season: number; clubs: Club[]; flaggedCount: number }

function until(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "passed";
  const h = Math.floor(ms / 3_600_000), d = Math.floor(h / 24);
  return d >= 1 ? `${d} day${d === 1 ? "" : "s"} ${h % 24} hr` : `${h} hr ${Math.floor((ms % 3_600_000) / 60_000)} min`;
}

export function TeamNewsPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [onlyFlags, setOnlyFlags] = useState(false);
  useEffect(() => {
    document.title = "Team news · AeroFPL";
    fetch("/api/team-news/").then((r) => (r.ok ? r.json() : Promise.reject())).then(setData).catch(() => setError("Team news couldn't be loaded. Try again in a minute."));
  }, []);
  const clubs = (data?.clubs ?? []).filter((c) => (!onlyFlags || c.flagged.length)
    && (!q || `${c.name} ${c.short} ${c.flagged.map((f) => f.name).join(" ")}`.toLowerCase().includes(q.toLowerCase())));
  const takers = (list: Taker[]) => (list.length ? list.map((t, i) => <span key={t.id}>{i ? ", " : ""}<b>{t.name}</b> {t.count}</span>) : "None yet");
  return (
    <main className="aero-page mp-page tp-page tn-page">
      <header className="tp-index-head">
        <h1>Team news</h1>
        <p>Injuries, doubts and bans from FPL, and who has actually taken each club's penalties, corners and free kicks this season.</p>
      </header>
      {error && <p className="mp-error" role="alert">{error}</p>}
      {!data && !error && <div className="mp-skeleton tall" aria-busy="true" />}
      {data && (
        <>
          {data.deadline && <p className="tn-deadline">GW{data.deadline.gameweek} deadline <b>{new Date(data.deadline.time).toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</b> · in {until(data.deadline.time)}</p>}
          <div className="tn-tools">
            <input className="aero-input" placeholder="Search a club or player" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
            <div className="tp-seg" role="group" aria-label="Clubs">
              <button type="button" aria-pressed={!onlyFlags} onClick={() => setOnlyFlags(false)}>All clubs</button>
              <button type="button" aria-pressed={onlyFlags} onClick={() => setOnlyFlags(true)}>Clubs with news ({data.flaggedCount} players)</button>
            </div>
          </div>
          <div className="tn-grid">
            {clubs.map((c) => (
              <section key={c.id} className="mp-sheet tn-club" aria-label={c.name}>
                <h2><Crest team={c.id} /><Link to={`/teams/${c.id}`}>{c.name}</Link></h2>
                <h3>Injuries, doubts and bans</h3>
                {c.flagged.length === 0 ? <p className="mp-note">No one flagged.</p> : (
                  <ul>{c.flagged.map((f) => (
                    <li key={f.id}><Link to={`/players/${f.id}`}>{f.name}</Link><span className={`st s-${f.status}`}>{f.chance != null && f.status === "d" ? `${f.chance}%` : f.label}</span>
                      <span className="nw">{f.news}{f.since ? ` · ${new Date(f.since).toLocaleDateString([], { day: "numeric", month: "short" })}` : ""}</span></li>
                  ))}</ul>
                )}
                <h3>Set pieces taken this season</h3>
                <dl className="tn-sp">
                  <dt>Penalties</dt><dd>{takers(c.setPieces.penalties)}</dd>
                  <dt>Corners</dt><dd>{takers(c.setPieces.corners)}</dd>
                  <dt>Free kicks</dt><dd>{takers(c.setPieces.freeKicks)}</dd>
                </dl>
              </section>
            ))}
          </div>
          <p className="mp-foot">Flags and news from FPL. Set-piece counts are what happened in this season's league matches (Opta), not official orders: penalties taken, corners taken, and direct free-kick shots plus free-kick crosses.</p>
        </>
      )}
    </main>
  );
}
