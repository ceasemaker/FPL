import { useEffect, useState } from "react";
import { EventIcon } from "./icons";
import type { MatchData, MinuteState, Slot, Timeline } from "./matchModel";

// Who was on the pitch at the cursor minute, in each side's formation.
// Landscape on wide screens (home attacking left to right), portrait on
// phones (home at the bottom). A sent-off player stays as a dashed ghost.

const lastName = (n: string) => { const p = n.split(" "); return p.length > 1 ? p.slice(1).join(" ") : n; };

function usePortrait() {
  const query = "(max-width: 720px)";
  const [portrait, setPortrait] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setPortrait(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return portrait;
}

export function MatchPitch({ data, state, slotMap, timeline }: { data: MatchData; state: MinuteState; slotMap: Record<string, Slot>; timeline: Timeline }) {
  const portrait = usePortrait();
  const sizes: Record<string, Record<number, number>> = {};
  for (const p of data.lineups) if (p.starter && p.formation_row != null && p.formation_col != null) {
    sizes[p.team_id] ??= {};
    sizes[p.team_id][p.formation_row] = Math.max(sizes[p.team_id][p.formation_row] ?? 0, p.formation_col + 1);
  }
  const maxRow = (team: string) => Math.max(1, ...Object.keys(sizes[team] ?? {}).map(Number));
  const place = (team: string, s: Slot) => {
    const depth = 5 + (s.row / maxRow(team)) * 40;
    const across = ((s.col + 1) / ((sizes[team]?.[s.row] ?? 1) + 1)) * 100;
    const home = team === data.home.id;
    if (portrait) return home ? { left: 100 - across, top: 100 - depth } : { left: across, top: depth };
    return home ? { left: depth, top: 100 - across } : { left: 100 - depth, top: across };
  };
  const bench = (team: string) => data.lineups.filter((p) => p.team_id === team && !p.starter);
  const formation = (team: string) => (data.teamStats[team]?.formation as string) || "";

  return (
    <section className="mp-sheet mp-pitch-card" aria-label="Who was on the pitch">
      <div className="mp-pitch-head">
        <span><b>{data.home.short}</b> {formation(data.home.id)}</span>
        <span><b>{timeline.label(state.index)}</b> · {state.men[data.home.id]} v {state.men[data.away.id]}</span>
        <span>{formation(data.away.id)} <b>{data.away.short}</b></span>
      </div>
      {portrait && <p className="mp-edge">{data.away.short} defending this end</p>}
      <div className={`mp-pitch${portrait ? " portrait" : ""}`}>
        <svg className="mp-lines" viewBox={portrait ? "0 0 68 105" : "0 0 105 68"} preserveAspectRatio="none" aria-hidden="true">
          {portrait ? (
            <>
              <rect x="1" y="1" width="66" height="103" /><line x1="1" y1="52.5" x2="67" y2="52.5" /><circle cx="34" cy="52.5" r="9.15" />
              <rect x="13.85" y="1" width="40.3" height="16.5" /><rect x="24.85" y="1" width="18.3" height="5.5" />
              <rect x="13.85" y="87.5" width="40.3" height="16.5" /><rect x="24.85" y="98.5" width="18.3" height="5.5" />
            </>
          ) : (
            <>
              <rect x="1" y="1" width="103" height="66" /><line x1="52.5" y1="1" x2="52.5" y2="67" /><circle cx="52.5" cy="34" r="9.15" />
              <rect x="1" y="13.85" width="16.5" height="40.3" /><rect x="1" y="24.85" width="5.5" height="18.3" />
              <rect x="87.5" y="13.85" width="16.5" height="40.3" /><rect x="98.5" y="24.85" width="5.5" height="18.3" />
            </>
          )}
        </svg>
        {state.players.map((p) => {
          const s = slotMap[p.player_id];
          if (!s) return null;
          const { left, top } = place(p.team_id, s);
          return (
            <div key={p.player_id} className={`mp-tok ${p.team_id === data.home.id ? "h" : "a"}${p.sentOff ? " off" : ""}${p.fresh ? " new" : ""}`}
              style={{ left: `${left}%`, top: `${top}%` }} title={`${p.name}${p.sentOff ? " (sent off)" : ""}`}>
              <i>
                {p.shirt}
                {p.captain && <b className="mp-cap" aria-label="Captain">C</b>}
                <span className="mp-marks">
                  {p.cards.map((c, k) => <EventIcon key={`c${k}`} kind={c} size={12} />)}
                  {Array.from({ length: p.goals }, (_, k) => <EventIcon key={`g${k}`} kind="goal" size={12} />)}
                </span>
              </i>
              <span>{lastName(p.name)}</span>
            </div>
          );
        })}
      </div>
      {portrait && <p className="mp-edge">{data.home.short} defending this end</p>}
      <div className="mp-bench">
        {[data.home.id, data.away.id].map((team, side) => (
          <div key={team} className={side ? "away" : "home"}>
            <b>Bench</b>
            {bench(team).map((p) => {
              const used = p.minute_on != null && timeline.indexOf(p.minute_on) <= state.index;
              return <span key={p.player_id} className={used ? "used" : ""}>{lastName(p.name)}{p.minute_on != null && <em> {p.minute_on}′</em>}</span>;
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

const KIND_TEXT = {
  goal: "Goal", yellow: "Yellow", second_yellow: "Sent off", red: "Sent off", sub: "", var: "VAR",
} as const;

export function NowPanel({ data, state, timeline }: { data: MatchData; state: MinuteState; timeline: Timeline }) {
  const total = state.spell.home + state.spell.away;
  const share = total ? state.spell.away / total : 0.5;
  const lead = share > 0.6 ? data.away.name : share < 0.4 ? data.home.name : null;
  const pct = Math.round(Math.max(share, 1 - share) * 100);
  const short = (team: string) => (team === data.home.id ? data.home.short : data.away.short);
  return (
    <section className="mp-sheet mp-now" aria-live="polite">
      <div className="mp-now-score">
        <span className="mp-min">{timeline.label(state.index)}</span>
        <span className="mp-sc">{data.home.short} {state.score[0]}<small>–</small>{state.score[1]} {data.away.short}</span>
      </div>
      <div className="mp-men">On the pitch: <b className={state.men[data.home.id] < 11 ? "down" : ""}>{state.men[data.home.id]}</b> v <b className={state.men[data.away.id] < 11 ? "down" : ""}>{state.men[data.away.id]}</b></div>
      {total > 0 && (
        <p className="mp-spell">
          {state.index < 3 ? "Kick-off." : lead ? <><b>{lead}</b> had the stronger spell over the last ten minutes: {pct}% of the momentum.</> : "Neither side on top over the last ten minutes."}
        </p>
      )}
      <ol className="mp-events" aria-label={`Events up to ${timeline.label(state.index)}`}>
        {state.events.length === 0 && <li className="empty">Nothing yet.</li>}
        {state.events.slice().reverse().map((e, k) => (
          <li key={k}>
            <span className="m">{e.minute}′</span>
            <EventIcon kind={e.kind} size={15} />
            <span className="t">
              {e.kind === "goal" && <><b>Goal: {e.player}</b> ({short(e.team)})<small>{e.other ? `Assist ${e.other} · ` : ""}{e.home}–{e.away}</small></>}
              {e.kind === "sub" && <><b>{e.player}</b> on for {e.other} ({short(e.team)})<small>{e.detail}</small></>}
              {(e.kind === "second_yellow" || e.kind === "red") && <><b>Sent off: {e.player}</b> ({short(e.team)})<small>{e.kind === "second_yellow" ? "Second yellow" : "Straight red"}{e.detail ? ` · ${e.detail}` : ""}. {short(e.team)} down a player.</small></>}
              {e.kind === "yellow" && <><b>Yellow: {e.player}</b> ({short(e.team)})<small>{e.detail}</small></>}
              {e.kind === "var" && <><b>{KIND_TEXT.var}: {e.detail}</b> ({short(e.team)})<small>{e.player}</small></>}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
