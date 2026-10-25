import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Crest, EventIcon } from "./icons";
import type { MatchData, Timeline } from "./matchModel";

const num = (v: unknown) => (typeof v === "number" ? v : Number(v) || 0);

// ------------------------------------------------------------------ team stats

export function TeamCompare({ data }: { data: MatchData }) {
  const S = data.teamStats, H = data.home.id, A = data.away.id;
  const v = (t: string, k: string) => num(S[t]?.[k]);
  const rows: [string, number, number, number?, string?][] = [
    ["Expected goals (xG)", v(H, "expectedGoals"), v(A, "expectedGoals"), 2],
    ["xG on target", v(H, "expectedGoalsOnTarget"), v(A, "expectedGoalsOnTarget"), 2],
    ["Shots", v(H, "totalScoringAtt"), v(A, "totalScoringAtt")],
    ["Shots on target", v(H, "ontargetScoringAtt"), v(A, "ontargetScoringAtt")],
    ["Shots inside the box", v(H, "attemptsIbox"), v(A, "attemptsIbox")],
    ["Big chances", v(H, "bigChanceCreated"), v(A, "bigChanceCreated")],
    ["Touches in the opposition box", v(H, "touchesInOppBox"), v(A, "touchesInOppBox")],
    ["Possession", v(H, "possessionPercentage"), v(A, "possessionPercentage"), 0, "%"],
    ["Passes completed", v(H, "accuratePass"), v(A, "accuratePass")],
    ["Corners won", v(H, "wonCorners"), v(A, "wonCorners")],
    ["Tackles + interceptions", v(H, "totalTackle") + v(H, "interception"), v(A, "totalTackle") + v(A, "interception")],
  ];
  return (
    <section className="mp-sheet mp-compare" aria-label="Team stats">
      <div className="mp-compare-head"><span>{data.home.short}</span><span>{data.away.short}</span></div>
      {rows.map(([label, h, a, dp = 0, suf = ""]) => {
        const fmt = (x: number) => (dp ? x.toFixed(dp) : Math.round(x)) + suf;
        const total = h + a || 1;
        return (
          <div className="mp-crow" key={label}>
            <span className={`v${h < a ? " lo" : ""}`}>{fmt(h)}</span>
            <span className="l">{label}<span className="mp-split" aria-hidden="true"><i style={{ width: `${(h / total) * 100}%` }} /><i style={{ width: `${(a / total) * 100}%` }} /></span></span>
            <span className={`v r${a < h ? " lo" : ""}`}>{fmt(a)}</span>
          </div>
        );
      })}
    </section>
  );
}

export function ShotZones({ data }: { data: MatchData }) {
  const zone = (team: string, name: string) => {
    const st = data.teamStats[team] ?? {};
    const goal = (k: string) => num(st[`attGoal${k}`]), saved = (k: string) => num(st[`attSv${k}`]);
    const onTarget = num(st.ontargetScoringAtt);
    const goals = data.goals.filter((g) => g.team === team && g.type !== "Own").length;
    const L = num(st.attBxLeft), C = num(st.attBxCentre), R = num(st.attBxRight), inBox = num(st.attemptsIbox), out = num(st.attemptsObox);
    const max = Math.max(L, C, R, out, 1);
    const heat = (n: number) => ({ "--a": ((n / max) * 0.28).toFixed(2) } as React.CSSProperties);
    const cell = (k: string) => {
      const g = goal(k), s = saved(k);
      return (
        <div key={k} title={`${g} goal${g === 1 ? "" : "s"}, ${s} saved`}>
          {g > 0 && <span className="g"><EventIcon kind="goal" size={13} />{g > 1 ? g : ""}</span>}
          {s > 0 && <span className="s">{s}</span>}
        </div>
      );
    };
    const unplaced = inBox - L - C - R;
    return (
      <div key={team}>
        <h3>{name}</h3>
        <p>{onTarget} on target: {goals} scored, {Math.max(0, onTarget - goals)} saved</p>
        <div className="mp-goalmouth" aria-label="Where shots on target went">{["HighLeft", "HighCentre", "HighRight", "LowLeft", "LowCentre", "LowRight"].map(cell)}</div>
        <div className="mp-goalline" />
        <div className="mp-box" aria-label="Where shots were taken from">
          <div className="in">
            <div className="heat" style={heat(L)}>{L}<small>left</small></div>
            <div className="heat" style={heat(C)}>{C}<small>centre</small></div>
            <div className="heat" style={heat(R)}>{R}<small>right</small></div>
          </div>
          <div className="out heat" style={heat(out)}>{out}<small>outside the box</small></div>
        </div>
        <div className="mp-zone-note">{inBox} inside the box{unplaced > 0 ? ` (${unplaced} not placed left, centre or right by Opta)` : ""}</div>
      </div>
    );
  };
  return (
    <section className="mp-sheet mp-zones" aria-label="Where the shots came from">
      {zone(data.home.id, data.home.name)}
      {zone(data.away.id, data.away.name)}
    </section>
  );
}

// ------------------------------------------------------------------ players

// Numeric column value by key (the row type mixes strings and numbers).
const val = (p: object, k: string) => (p as Record<string, unknown>)[k] as number | null | undefined;

// Short competition tags for form chips and meetings.
const COMP_TAG: Record<string, string> = {
  "Premier League": "PL", "League Cup": "EFL", "English League Cup": "EFL", "FA Cup": "FAC", "English FA Cup": "FAC",
  "UEFA Champions League": "UCL", "Champions League": "UCL", "UEFA Europa League": "UEL", "Europa League": "UEL",
  "UEFA Conference League": "UECL", "Conference League": "UECL", "English Community Shield": "CS", "UEFA Super Cup": "USC",
};
export const compTag = (name: string) => COMP_TAG[name] ?? name.split(" ").map((w) => w[0]).join("").slice(0, 4).toUpperCase();

const COLS: [string, string][] = [
  ["fpl", "FPL pts"], ["minutes", "Mins"], ["goals", "Goals"], ["assists", "Assists"], ["shots", "Shots"], ["boxShots", "In box"],
  ["bigChances", "Big chances"], ["chances", "Chances created"], ["boxTouches", "Box touches"], ["defence", "Tackles + int"],
  ["passPct", "Pass %"], ["passes", "Passes"],
];

// Cup and European matches have no Opta player sheets yet: minutes come from
// the lineups, plus goals and assists.
const LINEUP_COLS: [string, string][] = [["minutes", "Mins"], ["goals", "Goals"], ["assists", "Assists"]];

export function MatchPlayers({ data }: { data: MatchData }) {
  const sheets = data.players.some((p) => p.shots != null);
  const cols = sheets ? COLS : LINEUP_COLS;
  const [team, setTeam] = useState<string>("all");
  const [sort, setSort] = useState(sheets ? "fpl" : "minutes");
  const onMinute = useMemo(() => Object.fromEntries(data.lineups.map((p) => [p.player_id, p.minute_on])), [data]);
  const rows = useMemo(() => data.players
    .map((p) => ({ ...p, passPct: p.passes ? Math.round(((p.accuratePasses ?? 0) / p.passes) * 100) : null }))
    .filter((p) => team === "all" || p.team === team)
    .sort((a, b) => (val(b, sort) ?? -1) - (val(a, sort) ?? -1) || (b.fpl ?? 0) - (a.fpl ?? 0)), [data, team, sort]);
  const best = Math.max(...rows.map((p) => p.fpl ?? 0));
  const top = Object.fromEntries(cols.map(([k]) => [k, Math.max(...rows.map((p) => val(p, k) ?? 0))]));
  const short = (t: string) => (t === data.home.id ? data.home.short : data.away.short);

  if (!data.players.length) return <p className="mp-note">Player match sheets for this match aren't loaded yet.</p>;
  return (
    <>
      <div className="mp-tools" role="group" aria-label="Team">
        {[["all", "Both teams"], [data.home.id, data.home.name], [data.away.id, data.away.name]].map(([k, l]) => (
          <button key={k} type="button" aria-pressed={team === k} onClick={() => setTeam(k)}>{l}</button>
        ))}
      </div>
      {!sheets && <p className="mp-note">Opta player sheets are loaded for Premier League matches; here minutes come from the lineups (who started, who came on or off when).</p>}
      {data.fplDouble.length > 0 && <p className="mp-note">FPL points for {data.fplDouble.map(short).join(" and ")} players cover both of their matches in this double gameweek.</p>}
      <div className="mp-tbl-wrap">
        <table className="mp-table">
          <thead>
            <tr>
              <th scope="col">Player</th>
              {cols.map(([k, l]) => (
                <th key={k} scope="col" aria-sort={k === sort ? "descending" : "none"} className={k === sort ? "sorted" : ""}>
                  <button type="button" onClick={() => setSort(k)}>{l}</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <th scope="row"><span className="mp-pl"><Crest team={p.team} alt={short(p.team)} />{p.name} <small>{p.position}</small></span></th>
                {cols.map(([k]) => {
                  const x = val(p, k) ?? null;
                  const shown = x == null ? "–" : k === "passPct" ? `${x}%` : x;
                  const cls = k === "fpl" ? `fpl${x === best && best > 0 ? " best" : ""}` : x && x === top[k] && k !== "minutes" && k !== "passes" ? "top" : "";
                  return <td key={k} className={cls}>{shown}{k === "minutes" && onMinute[p.id] != null && <span className="on">on {onMinute[p.id]}′</span>}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ context

export function MatchContext({ data }: { data: MatchData }) {
  const formRow = (team: string, short: string, name: string, list: MatchData["form"]["home"]) => (
    <div className="mp-form-row">
      <Crest team={team} /><span className="code">{short}</span>
      <div className="chips">
        {list === null && <span className="mp-note">We store {name}'s games against Premier League clubs only.</span>}
        {list?.slice().reverse().map((f) => (
          <Link key={f.matchId} to={`/matches/${f.matchId}`} className={`chip ${f.res}${f.league ? "" : " cup"}`}
            title={`${f.competition}: ${f.home ? "v" : "at"} ${f.opp} ${f.gf}–${f.ga}`}>
            {f.res}<br />{f.gf}-{f.ga}{!f.league && <em>{compTag(f.competition)}</em>}
          </Link>
        ))}
        {list?.length === 0 && <span className="mp-note">No earlier games stored.</span>}
      </div>
    </div>
  );
  const pts = data.players.filter((p) => p.fpl != null).sort((a, b) => (b.fpl ?? 0) - (a.fpl ?? 0)).slice(0, 6);
  const short = (t: string) => (t === data.home.id ? data.home.short : data.away.short);
  return (
    <div className={`mp-ctx${data.status === "finished" && data.competitionId !== 8 ? " two" : ""}`}>
      <section className="mp-sheet"><h3>Last five games</h3><div className="mp-form">{formRow(data.home.id, data.home.short, data.home.name, data.form.home)}{formRow(data.away.id, data.away.short, data.away.name, data.form.away)}</div></section>
      <section className="mp-sheet">
        <h3>Last meetings</h3>
        {data.h2h.length === 0 ? <p className="mp-note">No earlier meetings stored (we hold matches from 2021/22).</p> : (
          <ul className="mp-h2h">
            {data.h2h.map((h) => (
              <li key={h.matchId}><Link to={`/matches/${h.matchId}`}>
                <span className="d">{h.date ? new Date(h.date).toLocaleDateString([], { day: "numeric", month: "short", year: "2-digit" }) : ""}</span>
                <span className="r">{h.home}</span><span className="s">{h.hs}–{h.as}</span><span>{h.away}{h.competition !== "Premier League" && <em className="comp">{compTag(h.competition)}</em>}</span>
              </Link></li>
            ))}
          </ul>
        )}
      </section>
      {data.status === "finished" ? (data.competitionId === 8 && (
        <section className="mp-sheet">
          <h3>FPL points from this match</h3>
          {pts.length === 0 ? <p className="mp-note">No FPL points stored for this match.</p> : (
            <ul className="mp-fplist">{pts.map((p) => <li key={p.id}><span>{p.name}<small>{short(p.team)}</small></span><b>{p.fpl}</b></li>)}</ul>
          )}
        </section>
      )) : (
        <OddsCard data={data} />
      )}
    </div>
  );
}

function OddsCard({ data }: { data: MatchData }) {
  const o = data.odds;
  return (
    <section className="mp-sheet">
      <h3>What the bookmakers expect <span className="mp-badge" title="Bookmaker odds via SofaScore, with the margin removed">Odds</span></h3>
      {!o?.chances ? <p className="mp-note">Odds are collected in the three days before kick-off.</p> : (
        <>
          <div className="mp-odds">
            {[[data.home.short, o.chances[0], o.home], ["Draw", o.chances[1], o.draw], [data.away.short, o.chances[2], o.away]].map(([label, pct, price]) => (
              <div key={String(label)}><strong>{Number(pct).toFixed(0)}%</strong><span>{label}</span><small>{price ? Number(price).toFixed(2) : "–"}</small></div>
            ))}
          </div>
          {o.updated && <p className="mp-note">Updated {new Date(o.updated).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}.</p>}
        </>
      )}
    </section>
  );
}

export function UpcomingTimelineNote({ data, timeline }: { data: MatchData; timeline: Timeline }) {
  void timeline;
  return (
    <section className="mp-sheet mp-upcoming">
      <p>
        Kick-off {data.kickoff ? new Date(data.kickoff).toLocaleString([], { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }) : "time to be confirmed"}.
        The timeline, lineups and match stats appear here once the match has been played.
      </p>
    </section>
  );
}
