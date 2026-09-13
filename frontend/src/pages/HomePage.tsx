import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLandingData } from "../hooks/useLandingData";
import { useBestValuePlayers, useTop100Template } from "../hooks/useTop100Data";
import { PlayerModal } from "../components/PlayerModal";
import type { PlayerMover, ValuePlayer } from "../types";
import "./HomePage.css";

interface Fixture { event:number; opponent:string|null; location:"H"|"A"; difficulty:number|null }
interface FixtureTeam { team_id:number; team_name:string; team_short_name:string; fixtures:Fixture[]; avg_difficulty:number|null }
interface FixtureResponse { start_gameweek:number; teams:FixtureTeam[] }
const positions:Record<string,string>={goalkeepers:"GK",defenders:"DEF",midfielders:"MID",forwards:"FWD"};

export function HomePage(){
  const navigate=useNavigate();
  const {data,isLoading,error}=useLandingData();
  const {data:elite}=useTop100Template();
  const {data:values}=useBestValuePlayers();
  const [fixtures,setFixtures]=useState<FixtureResponse|null>(null);
  const [modalPlayerId,setModalPlayerId]=useState<number|null>(null);
  const [search,setSearch]=useState("");

  useEffect(()=>{
    const controller=new AbortController();
    fetch("/api/fixtures/ticker/?horizon=5",{signal:controller.signal})
      .then(r=>r.ok?r.json():Promise.reject(new Error("Fixtures unavailable")))
      .then(setFixtures)
      .catch(e=>{if(e.name!=="AbortError")console.error(e)});
    return()=>controller.abort();
  },[]);

  // `current_gameweek` on /api/landing/ is the newest gameweek we hold stats
  // for, i.e. the latest COMPLETED gameweek, while the fixtures ticker starts
  // at the next gameweek to be played. Every snapshot that carries its own
  // gameweek has to be checked against the completed one before it can be
  // presented as current, otherwise the page silently mixes seasons.
  const latestCompletedGw=data?.current_gameweek??null;
  const nextGw=fixtures?.start_gameweek??null;
  const eliteGw=elite?.game_week??null;
  const eliteIsCurrent=eliteGw!==null&&latestCompletedGw!==null&&eliteGw===latestCompletedGw;

  const captain=eliteIsCurrent?elite?.most_captained?.[0]:undefined;
  const captainPlayer=captain?elite?.template_squad.find(p=>p.athlete_id===captain.athlete_id):undefined;
  const easiest=useMemo(()=>fixtures?.teams.filter(t=>t.avg_difficulty!==null).sort((a,b)=>(a.avg_difficulty??9)-(b.avg_difficulty??9))[0],[fixtures]);

  const allValuePlayers=useMemo<ValuePlayer[]>(()=>{
    if(!values)return[];
    return[...values.goalkeepers,...values.defenders,...values.midfielders,...values.forwards];
  },[values]);
  const formLeader=useMemo(()=>[...allValuePlayers].sort((a,b)=>b.form-a.form)[0],[allValuePlayers]);

  const watchlist=useMemo(()=>{
    if(!values)return[];
    return Object.entries({goalkeepers:values.goalkeepers,defenders:values.defenders,midfielders:values.midfielders,forwards:values.forwards})
      .flatMap(([group,players])=>players.slice(0,2).map(p=>({...p,position:positions[group]})))
      .sort((a,b)=>b.value_score-a.value_score)
      .slice(0,3);
  },[values]);

  const movers=[...(data?.movers.price.risers??[]).slice(0,2),...(data?.movers.price.fallers??[]).slice(0,1)];
  const moveCount=(data?.movers.price.risers.length??0)+(data?.movers.price.fallers.length??0);

  if(error)return <main className="command-page"><div className="command-error">Dashboard data could not be loaded.</div></main>;

  return <main className="command-page">
    <header className="command-toolbar">
      <form className="command-search" onSubmit={(event)=>{event.preventDefault();if(search.trim())navigate(`/players?search=${encodeURIComponent(search.trim())}`)}}><span>⌕</span><input aria-label="Search players" placeholder="Search players…" value={search} onChange={event=>setSearch(event.target.value)}/></form>
      <Link className="gameweek-select" to="/fixtures"><span>□</span> Next: Gameweek {nextGw??"—"}<span>›</span></Link>
    </header>

    <div className="command-heading">
      <div>
        <h1>FPL Command Centre</h1>
        <p>Planning Gameweek {nextGw??"—"} · data through GW{latestCompletedGw??"—"}</p>
      </div>
      <span className="command-kicker">DATA DRIVEN<br/>FPL DECISIONS</span>
    </div>

    <p className="freshness-strip" role="status">
      <strong>Data status</strong>
      <span>Official FPL snapshot {data?.pulse.last_updated ? new Date(data.pulse.last_updated).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "not yet available"}</span>
      <span>Results through GW{latestCompletedGw??"—"}</span>
      <span>Fixtures GW{nextGw??"—"} onward</span>
    </p>

    {eliteGw!==null&&!eliteIsCurrent&&
      <p className="freshness-note" role="status">
        Elite-manager data is from GW{eliteGw}; the latest completed gameweek is GW{latestCompletedGw??"—"}. Captaincy and template signals are hidden until that sync catches up.
      </p>}

    <div className="command-layout"><section className="command-main">
      {eliteIsCurrent&&captain
        ? <article className="captain-hero">
            <div className="captain-copy">
              <span className="eyebrow">★ ELITE CAPTAIN SIGNAL · GW{eliteGw}</span>
              <h2>Captain <em>{captain.web_name}</em></h2>
              <div className="captain-metrics">
                <div><strong>{captain.percentage.toFixed(0)}%</strong><span>captained</span></div>
                <div><strong>{captainPlayer?.total_points??"—"}</strong><span>total points</span></div>
                <div className="best-fixture"><b>♜</b><span><strong>{easiest?.team_short_name??"—"}</strong> best fixture run</span></div>
              </div>
            </div>
            {captain.image_url&&<img className="captain-image" src={captain.image_url} alt={captain.web_name}/>}
            <div className="hero-slash"/>
          </article>
        : <article className="captain-hero">
            <div className="captain-copy">
              <span className="eyebrow">▲ FORM LEADER · GW{latestCompletedGw??"—"}</span>
              <h2>In form <em>{formLeader?.web_name??(isLoading?"loading…":"—")}</em></h2>
              <div className="captain-metrics">
                <div><strong>{formLeader?formLeader.form.toFixed(1):"—"}</strong><span>form</span></div>
                <div><strong>{formLeader?.total_points??"—"}</strong><span>total points</span></div>
                <div className="best-fixture"><b>♜</b><span><strong>{easiest?.team_short_name??"—"}</strong> best fixture run</span></div>
              </div>
            </div>
            {formLeader?.image_url&&<img className="captain-image" src={formLeader.image_url} alt={formLeader.web_name}/>}
            <div className="hero-slash"/>
          </article>}

      <div className="command-middle">
        <article className="command-card outlook-card">
          <CardTitle title="Five-Week Outlook" subtitle={`${easiest?.team_name??"Best fixture run"} · fixture difficulty`}/>
          <div className="outlook-chart">{(easiest?.fixtures??Array.from({length:5},(_,i)=>({event:i,difficulty:null,opponent:"—",location:"H" as const}))).map(f=>{
            const score=f.difficulty?6-f.difficulty:1;
            return <div className="outlook-column" key={f.event}>
              <span className="outlook-score">{f.difficulty??"—"}</span>
              <div className="outlook-bar" style={{height:`${score*13}%`}}/>
              <strong>GW{f.event||"—"}</strong>
              <small>{f.opponent} ({f.location})</small>
            </div>;
          })}</div>
        </article>
        <article className="command-card fixtures-brief">
          <CardTitle title="Next Fixtures" action="View all" href="/fixtures"/>
          <div className="fixture-list">{(easiest?.fixtures.slice(0,3)??[]).map(f=>
            <div className="fixture-row" key={f.event}>
              <span className="club-chip">{easiest?.team_short_name}</span>
              <div><strong>{f.opponent}</strong><small>GW{f.event} · {f.location==="H"?"Home":"Away"}</small></div>
              <span className={`fdr-label fdr-${f.difficulty}`}>FDR {f.difficulty}</span>
            </div>)}</div>
        </article>
      </div>

      <article className="command-card watch-card">
        <CardTitle title="Players to Watch" subtitle="Best recent value scores" action="View all" href="/players"/>
        <div className="watch-table">
          <div className="watch-head"><span>Player</span><span>Team</span><span>Position</span><span>Price</span><span>Form</span><span>Value</span></div>
          {watchlist.map(p=>{
            const filled=Math.max(0,Math.min(5,Math.round(p.form)));
            return <button className="watch-row" key={p.athlete_id} onClick={()=>setModalPlayerId(p.athlete_id)}>
              <span className="watch-player">{p.image_url?<img src={p.image_url} alt=""/>:<i>{p.web_name[0]}</i>}<strong>{p.web_name}</strong></span>
              <span>{p.team_short_name}</span>
              <span>{p.position}</span>
              <span>{p.now_cost_display}</span>
              <span className="form-blocks" aria-label={`Form ${p.form}`}>{Array.from({length:5},(_,i)=><i key={i} className={i<filled?undefined:"off"}/>)}</span>
              <strong>{p.value_score.toFixed(2)}</strong>
            </button>;
          })}
        </div>
      </article>
    </section>

    <aside className="command-rail">
      <article className="command-card snapshot-card">
        <CardTitle title="Gameweek Pulse"/>
        <div className="snapshot-grid">
          <div><strong>{latestCompletedGw??"—"}</strong><span>Latest completed GW</span></div>
          <div><strong>{data?.pulse.total_points_current?.toLocaleString()??"—"}</strong><span>Points tracked</span></div>
          <div><strong>{moveCount}</strong><span>Price moves</span></div>
        </div>
      </article>

      <article className="command-card signal-card">
        <CardTitle title="Elite Signals" subtitle={eliteIsCurrent?`Top managers · GW${eliteGw}`:undefined}/>
        {eliteIsCurrent
          ? (elite?.most_captained??[]).slice(0,3).map(p=>
              <div className="signal-row" key={p.athlete_id}>
                <div><strong>{p.web_name}</strong><span>Captaincy</span></div>
                <div className="signal-track"><i style={{width:`${Math.min(100,p.percentage)}%`}}/></div>
                <b>{p.percentage.toFixed(0)}%</b>
              </div>)
          : <p className="card-empty">Awaiting a current-gameweek elite-manager sync{eliteGw!==null?` · last synced GW${eliteGw}`:""}.</p>}
      </article>

      <article className="command-card movers-card">
        <CardTitle title="Top Movers" action="View all" href="/price-monitor"/>
        {movers.map((p,i)=><MoverRow key={`${p.id}-${i}`} player={p} onClick={setModalPlayerId}/>)}
      </article>

      <article className="command-card latest-card">
        <CardTitle title="Latest News" action="Review flagged players" href="/players?status=flagged"/>
        {(data?.news??[]).slice(0,3).map(item=>
          <button className="latest-row" key={item.id} onClick={()=>setModalPlayerId(item.id)}>
            <span className="news-status">+</span>
            <div><strong>{item.web_name} ({item.team})</strong><p>{item.news}</p></div>
          </button>)}
      </article>
    </aside></div>

    {isLoading&&<div className="command-loading">Loading live intelligence…</div>}
    {modalPlayerId!==null&&<PlayerModal playerId={modalPlayerId} onClose={()=>setModalPlayerId(null)}/>}
  </main>;
}

function CardTitle({title,subtitle,action,href}:{title:string;subtitle?:string;action?:string;href?:string}){
  return <header className="command-card-title">
    <div><h3>{title}</h3>{subtitle&&<p>{subtitle}</p>}</div>
    {action&&href&&<Link to={href}>{action} ›</Link>}
  </header>;
}

function MoverRow({player,onClick}:{player:PlayerMover;onClick:(id:number)=>void}){
  const rising=player.change_label.includes("↑");
  return <button className="mover-row" onClick={()=>onClick(player.id)}>
    {player.image_url?<img src={player.image_url} alt=""/>:<span className="player-fallback">{player.first_name[0]}</span>}
    <div><strong>{player.first_name} {player.second_name}</strong><small>{player.team} · £{((player.now_cost??0)/10).toFixed(1)}m</small></div>
    <b className={rising?"positive":"negative"}>{rising?"▲":"▼"} £{Math.abs(player.value/10).toFixed(1)}m</b>
  </button>;
}
