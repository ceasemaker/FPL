import { useEffect, useRef, useState } from "react";
import { EventIcon } from "./icons";
import type { MatchData, Timeline } from "./matchModel";

// The match as a timeline you can drag: Opta momentum per minute (home above
// the line, away below), events pinned on it, and a lime cursor. Pointer drag,
// arrow keys, pins and the jump buttons all move the same cursor.

const W = 1000, PAD_L = 44, PAD_R = 8, GAP = 14, MID = 95, AMP = 62;
const KIND_LABEL: Record<string, string> = { goal: "Goal", yellow: "Yellow card", second_yellow: "Second yellow", red: "Red card", sub: "Substitution", var: "VAR" };

export function MomentumScrubber({ data, timeline, cursor, onCursor, hasMomentum }: {
  data: MatchData; timeline: Timeline; cursor: number; onCursor: (i: number) => void; hasMomentum: boolean;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);
  const playing = useRef<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const { moments, end, halfIndex, events, label, indexOf } = timeline;
  const usable = W - PAD_L - PAD_R - GAP;
  const xAt = (i: number) => PAD_L + (i / end) * usable + (i >= halfIndex ? GAP : 0);
  const barW = Math.max(1, usable / end - 1.2);
  const maxM = Math.max(...moments.map((m) => Math.max(m.h, m.a)), 0.0001);

  const stop = () => {
    if (playing.current !== null) cancelAnimationFrame(playing.current);
    playing.current = null;
    setIsPlaying(false);
  };
  useEffect(() => stop, []);

  const fromPointer = (clientX: number) => {
    const r = svgRef.current!.getBoundingClientRect();
    const x = ((clientX - r.left) / r.width) * W;
    let best = 0, d = Infinity;
    for (let i = 0; i < end; i++) { const dd = Math.abs(xAt(i) + barW / 2 - x); if (dd < d) { d = dd; best = i; } }
    return best;
  };
  const move = (i: number) => { stop(); onCursor(Math.max(0, Math.min(end - 1, i))); };

  const play = () => {
    if (playing.current !== null) { stop(); return; }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { onCursor(end - 1); return; }
    const from = cursor >= end - 1 ? 0 : cursor;
    const duration = 9000 * (1 - from / end);
    let start: number | null = null;
    const tick = (t: number) => {
      start ??= t;
      const k = Math.min(1, (t - start) / duration);
      onCursor(Math.round(from + (end - 1 - from) * k));
      if (k < 1) playing.current = requestAnimationFrame(tick); else stop();
    };
    setIsPlaying(true);
    playing.current = requestAnimationFrame(tick);
  };

  const red = events.find((e) => e.kind === "second_yellow" || e.kind === "red");
  const jumps: [string, number][] = [["Kick-off", 0], ["Half-time", halfIndex - 1], ...(red ? [[`Red card ${red.minute}′`, red.idx] as [string, number]] : []), ["Full time", end - 1]];
  const extraTime = moments.some((m) => m.period === 3);
  const ticks: [number, string][] = [[0, "0′"], [indexOf(15, 1), "15′"], [indexOf(30, 1), "30′"], [halfIndex, "HT"], [indexOf(60, 2), "60′"], [indexOf(75, 2), "75′"],
    ...(extraTime ? [[indexOf(91, 3), "90′"] as [number, string]] : []), [end - 1, extraTime ? "AET" : "FT"]];
  const cx = xAt(cursor) + barW / 2, tag = label(cursor);
  // Without momentum (cup and European matches) the band is a slim events strip.
  const H = hasMomentum ? 170 : 96, mid = hasMomentum ? MID : 48, awayPin = H - 24;
  const pct = (x: number, total: number) => `${(x / total) * 100}%`;
  const score = events.filter((e) => e.kind === "goal" && e.idx <= cursor).reduce<[number, number]>((s, g) => [g.home ?? s[0], g.away ?? s[1]], [0, 0]);

  return (
    <section className="mp-sheet mp-scrub" aria-labelledby="mp-scrub-title">
      <div className="mp-scrub-top">
        <h2 id="mp-scrub-title">Drag through the match {hasMomentum && <span className="mp-badge" title="Opta's momentum: each side's chance of scoring in that minute">Opta momentum</span>}</h2>
        <div className="mp-jumps">
          <button type="button" className="mp-play" onClick={play} aria-pressed={isPlaying}>
            <EventIcon kind={isPlaying ? "pause" : "play"} size={12} />{isPlaying ? "Pause" : "Replay the match"}
          </button>
          {jumps.map(([text, i]) => <button type="button" key={text} onClick={() => move(i)}>{text}</button>)}
        </div>
      </div>
      {!hasMomentum && <p className="mp-nomom"><span className="mp-badge">No momentum</span> Opta publishes momentum for Premier League games only; goals, cards and substitutions are below.</p>}
      <div className="mp-band-wrap">
      {/* Labels are HTML over the SVG so they stay readable when the band scales down on phones. */}
      <span className="mp-side-label" style={{ top: pct(mid - 26, H) }}>{data.home.short}</span>
      <span className="mp-side-label" style={{ top: pct(mid + 8, H) }}>{data.away.short}</span>
      <span className="mp-cursor-tag" style={{ left: pct(cx, W), top: pct(mid, H) }}>{tag}</span>
      <svg
        ref={svgRef}
        className="mp-band"
        viewBox={`0 0 ${W} ${H}`}
        role="slider"
        tabIndex={0}
        aria-label="Match minute"
        aria-valuemin={0}
        aria-valuemax={end - 1}
        aria-valuenow={cursor}
        aria-valuetext={`${tag}, ${data.home.short} ${score[0]}, ${data.away.short} ${score[1]}`}
        onPointerDown={(ev) => {
          const pin = (ev.target as Element).closest("[data-pin]");
          if (pin) { move(Number(pin.getAttribute("data-pin"))); return; }
          dragging.current = true;
          (ev.currentTarget as SVGSVGElement).setPointerCapture(ev.pointerId);
          move(fromPointer(ev.clientX));
        }}
        onPointerMove={(ev) => { if (dragging.current) move(fromPointer(ev.clientX)); }}
        onPointerUp={() => { dragging.current = false; }}
        onKeyDown={(ev) => {
          const step = ({ ArrowRight: 1, ArrowLeft: -1, PageUp: 5, PageDown: -5 } as Record<string, number>)[ev.key];
          if (step) { move(cursor + step); ev.preventDefault(); }
          if (ev.key === "Home") { move(0); ev.preventDefault(); }
          if (ev.key === "End") { move(end - 1); ev.preventDefault(); }
        }}
      >
        <line className="mp-axis" x1={PAD_L} x2={W - PAD_R} y1={mid} y2={mid} />
        {hasMomentum && moments.map((m, i) => {
          const x = xAt(i), hh = (m.h / maxM) * AMP, ha = (m.a / maxM) * AMP, future = i > cursor ? " future" : "";
          return (
            <g key={i}>
              <rect className={`mp-bar-h${future}`} x={x} y={MID - hh} width={barW} height={Math.max(hh, 0.6)} rx="1" />
              <rect className={`mp-bar-a${future}`} x={x} y={MID} width={barW} height={Math.max(ha, 0.6)} rx="1" />
            </g>
          );
        })}
        {events.map((e, k) => (
          <g key={k} className="mp-pin" data-pin={e.idx} transform={`translate(${xAt(e.idx) + barW / 2 - 9},${e.team === data.home.id ? 6 : awayPin})`}>
            <title>{`${e.minute}′ ${KIND_LABEL[e.kind] ?? e.kind}: ${e.player}`}</title>
            <rect className="mp-pin-bg" width="18" height="18" rx="4" />
            <EventIcon kind={e.kind} size={18} />
          </g>
        ))}
        <line className="mp-cursor" x1={cx} x2={cx} y1="24" y2={awayPin} />
      </svg>
      <div className="mp-ticks" aria-hidden="true">{ticks.map(([i, t]) => <span key={t} style={{ left: pct(xAt(i), W) }}>{t}</span>)}</div>
      </div>
      <div className="mp-legend">
        {hasMomentum && <><span><i className="mp-swatch home" />{data.home.short} momentum (above the line)</span>
        <span><i className="mp-swatch away" />{data.away.short} momentum (below)</span></>}
        {!hasMomentum && <span>{data.home.short} events above the line, {data.away.short} below</span>}
        <span><EventIcon kind="goal" size={13} />Goal</span>
        <span><EventIcon kind="yellow" size={13} />Yellow</span>
        <span><EventIcon kind="second_yellow" size={13} />Second yellow</span>
        <span><EventIcon kind="sub" size={13} />Substitution</span>
      </div>
    </section>
  );
}
