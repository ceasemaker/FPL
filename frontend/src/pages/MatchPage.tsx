import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { crestUrl, EventIcon } from "../components/match/icons";
import { buildTimeline, findPlayer, slots, stateAt, summary, type MatchData } from "../components/match/matchModel";
import { MomentumScrubber } from "../components/match/MomentumScrubber";
import { MatchPitch, NowPanel } from "../components/match/MatchPitch";
import { MatchContext, MatchPlayers, ShotZones, TeamCompare, UpcomingTimelineNote } from "../components/match/MatchSections";
import "./MatchPage.css";

// The Match page (/matches/:matchId): the match as a timeline you can drag.
// One minute cursor drives the momentum band, the pitch and the events panel;
// full-match totals, every player's sheet and the context follow.

export function MatchPage() {
  const { matchId } = useParams();
  const [data, setData] = useState<MatchData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    let alive = true;
    setData(null); setError(null);
    fetch(`/api/matches/${matchId}/`)
      .then((r) => { if (!r.ok) throw new Error(r.status === 404 ? "We don't have this match." : `HTTP ${r.status}`); return r.json() as Promise<MatchData>; })
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [matchId]);

  const timeline = useMemo(() => (data ? buildTimeline(data) : null), [data]);
  const slotMap = useMemo(() => (data ? slots(data) : {}), [data]);

  // Open on the moment that decided it (a red card), else full time.
  useEffect(() => {
    if (!timeline) return;
    const red = timeline.events.find((e) => e.kind === "second_yellow" || e.kind === "red");
    setCursor(red ? red.idx : timeline.end - 1);
  }, [timeline]);

  useEffect(() => {
    if (data) document.title = `${data.home.name} ${data.score ? `${data.score[0]}–${data.score[1]}` : "v"} ${data.away.name} · AeroFPL`;
  }, [data]);

  if (error) {
    return (
      <main className="aero-page mp-page">
        <p className="mp-crumbs"><Link to="/fixtures">Matches</Link></p>
        <p className="mp-error" role="alert">{error}</p>
      </main>
    );
  }
  if (!data || !timeline) {
    return <main className="aero-page mp-page" aria-busy="true"><div className="mp-skeleton" /><div className="mp-skeleton tall" /></main>;
  }

  const finished = data.status === "finished";
  const state = stateAt(data, timeline, slotMap, cursor);
  const goalsOf = (team: string) => timeline.events.filter((e) => e.kind === "goal" && e.team === team);
  const redsOf = (team: string) => timeline.events.filter((e) => (e.kind === "red" || e.kind === "second_yellow") && e.team === team);
  const lastName = (n: string) => { const p = n.replace(/\s*\(own goal\)$/, "").split(" "); return p.length > 1 ? p.slice(1).join(" ") : p[0]; };
  const scorerList = (team: string) => (
    <ul>
      {goalsOf(team).map((g, k) => <li key={`g${k}`}><EventIcon kind="goal" size={13} />{lastName(g.player)} {g.minute}′{g.detail === "Penalty" ? " (pen)" : g.detail === "Own" ? " (og)" : ""}</li>)}
      {redsOf(team).map((r, k) => <li key={`r${k}`} className="red"><EventIcon kind={r.kind} size={13} />{(findPlayer(data.lineups, r.team, r.player)?.name ?? r.player).split(" ").slice(-1)[0]} {r.minute}′</li>)}
    </ul>
  );
  const kickoff = data.kickoff ? new Date(data.kickoff) : null;
  const text = summary(data, timeline);
  const hasMomentum = data.momentum.length > 0;

  return (
    <main className="aero-page mp-page">
      <nav className="mp-crumbs" aria-label="Breadcrumb">
        <Link to="/fixtures">Matches</Link><span aria-hidden="true">/</span>
        {data.gameweek && <><span>GW{data.gameweek}</span><span aria-hidden="true">/</span></>}
        <span className="long">{data.competition}{data.round ? ` · ${data.round}` : ""}{kickoff ? ` · ${kickoff.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" })}` : ""}</span>
      </nav>

      <header className="mp-head">
        <div className="mp-side home">
          <img className="mp-crest" src={crestUrl(data.home.id)} alt="" />
          <div><h1>{data.home.name}</h1>{finished && scorerList(data.home.id)}</div>
        </div>
        <div className="mp-score">
          {finished && data.score
            ? <><strong aria-label={`${data.home.name} ${data.score[0]}, ${data.away.name} ${data.score[1]}`}>{data.score[0]}–{data.score[1]}</strong><span>{data.penalties ? `${data.penalties[0]}–${data.penalties[1]} on penalties` : "Full time"}</span></>
            : <><strong className="ko">{kickoff ? kickoff.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "TBC"}</strong><span>{kickoff ? kickoff.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" }) : "Kick-off"}</span></>}
        </div>
        <div className="mp-side away">
          <img className="mp-crest" src={crestUrl(data.away.id)} alt="" />
          <div><h1>{data.away.name}</h1>{finished && scorerList(data.away.id)}</div>
        </div>
      </header>
      {finished && (
        <div className="mp-scorers-phone">
          <div>{goalsOf(data.home.id).map((g, k) => <span key={k}>{lastName(g.player)} {g.minute}′</span>)}{redsOf(data.home.id).map((r, k) => <span key={`r${k}`} className="red">{lastName(r.player)} {r.minute}′ (sent off)</span>)}</div>
          <div>{goalsOf(data.away.id).map((g, k) => <span key={k}>{lastName(g.player)} {g.minute}′</span>)}{redsOf(data.away.id).map((r, k) => <span key={`r${k}`} className="red">{lastName(r.player)} {r.minute}′ (sent off)</span>)}</div>
        </div>
      )}
      {text && <p className="mp-summary">{text}</p>}

      {finished && data.detailsAvailable ? (
        <>
          <MomentumScrubber data={data} timeline={timeline} cursor={cursor} onCursor={setCursor} hasMomentum={hasMomentum} />
          <div className="mp-at">
            <MatchPitch data={data} state={state} slotMap={slotMap} timeline={timeline} />
            <NowPanel data={data} state={state} timeline={timeline} />
          </div>

          <div className="mp-sec-title"><div><h2>The full match</h2><p>Totals over 90 minutes; the timeline above can't split these by minute. <span className="mp-badge">Full-match totals</span></p></div></div>
          <div className="mp-full">
            <TeamCompare data={data} />
            <ShotZones data={data} />
          </div>

          <div className="mp-sec-title"><div><h2>Every player</h2><p>{data.competitionId === 8 ? "Opta match sheets and FPL points. Sorted by FPL points; choose a column to sort." : "Who played and for how long, with goals and assists."}</p></div></div>
          <MatchPlayers data={data} />
        </>
      ) : finished ? (
        <p className="mp-note">The detailed timeline and stats for this match haven't been loaded yet.</p>
      ) : (
        <UpcomingTimelineNote data={data} timeline={timeline} />
      )}

      <div className="mp-sec-title"><div><h2>{finished ? "Going into the match" : "Before kick-off"}</h2><p>{finished ? (data.competitionId === 8 ? "Form in every competition, the last meetings, and who scored FPL points here." : "Form in every competition and the last meetings.") : "Form in every competition, the last meetings, and what the bookmakers expect."}</p></div></div>
      <MatchContext data={data} />
      <p className="mp-foot">Match data from the Premier League's stats feeds (Opta){data.competitionId === 8 ? " and FPL" : ""}. Momentum is Opta's per-minute chance of each side scoring, published for Premier League matches only; team and player stats are full-match totals.</p>
    </main>
  );
}

// /matches/fixture/:fixtureId: resolve an FPL fixture to its match and go there.
export function MatchFromFixture() {
  const { fixtureId } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(`/api/matches/fixture/${fixtureId}/`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("We don't have this match yet."))))
      .then((d: { matchId: string }) => navigate(`/matches/${d.matchId}`, { replace: true }))
      .catch((e: Error) => setError(e.message));
  }, [fixtureId, navigate]);
  return (
    <main className="aero-page mp-page">
      {error ? <p className="mp-error" role="alert">{error} <Link to="/fixtures">Back to fixtures</Link></p> : <div className="mp-skeleton" aria-busy="true" />}
    </main>
  );
}
