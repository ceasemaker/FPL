import { useEffect, useState } from "react";
import { direction, usePriceChange, usePriceChanges, type PriceChange } from "../../hooks/usePriceChanges";
import "./PriceChange.css";

const pct = (v: number | null) => (v === null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}%`);

function describe(c: PriceChange): string {
  const parts = [
    `${c.label} at the next price change (FPL's estimate)`,
    `progress ${pct(c.progress)}, predicted ${pct(c.predicted)}`,
    `ownership trend ${c.trend}`,
  ];
  if (c.lockedUntil) parts.push(`price locked until ${new Date(c.lockedUntil).toLocaleString()}`);
  return parts.join(" · ");
}

// Compact badge for table rows and lists: an arrow and FPL's progress,
// coloured by FPL's own likelihood (with the label in its accessible name).
export function PriceChangeBadge({ athleteId, showHold = false }: { athleteId: number | null | undefined; showHold?: boolean }) {
  const change = usePriceChange(athleteId);
  if (!change || change.progress === null) return null;
  const dir = direction(change);
  if (dir === "hold" && !showHold) return null;
  const arrow = dir === "rise" ? "▲" : dir === "drop" ? "▼" : "•";
  return (
    <span className={`pc-badge pc-${dir}`} title={describe(change)} aria-label={describe(change)}>
      <span aria-hidden="true">{arrow}</span>{pct(change.progress)}
    </span>
  );
}

// Fuller panel for player cards and profiles: the label, progress now,
// FPL's prediction for the next three price-change runs, and a lock if any.
export function PriceChangePanel({ athleteId }: { athleteId: number | null | undefined }) {
  const change = usePriceChange(athleteId);
  const data = usePriceChanges();
  if (!change || change.progress === null) return null;
  const dir = direction(change);
  return (
    <section className={`pc-panel pc-${dir}`} aria-label="Price change">
      <div className="pc-panel-head">
        <strong>{change.label}</strong>
        <span className="pc-source" title="From FPL's own price-change tracker, updated every 15 minutes">FPL estimate</span>
      </div>
      <dl className="pc-panel-grid">
        <div><dt>Progress</dt><dd>{pct(change.progress)}</dd></div>
        {change.projections.slice(0, 3).map((p, i) => (
          <div key={p.offset}><dt>{i === 0 ? "Next change" : `+${i} day${i === 1 ? "" : "s"}`}</dt><dd>{pct(p.percent)}</dd></div>
        ))}
        <div><dt>Ownership</dt><dd>{change.trend === "up" ? "Rising" : change.trend === "down" ? "Falling" : "Flat"}</dd></div>
      </dl>
      {change.lockedUntil && <p className="pc-note">Price locked until {new Date(change.lockedUntil).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}.</p>}
      {data?.meta.deadlines[0] && <p className="pc-note">Next price change <Countdown to={data.meta.deadlines[0]} /></p>}
    </section>
  );
}

// "in 15:03:08", ticking every second until the next price-change run.
export function Countdown({ to }: { to: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const left = Math.max(0, new Date(to).getTime() - now);
  const h = Math.floor(left / 3_600_000), m = Math.floor((left % 3_600_000) / 60_000), s = Math.floor((left % 60_000) / 1000);
  const two = (n: number) => String(n).padStart(2, "0");
  return (
    <time className="pc-countdown" dateTime={to} title={new Date(to).toLocaleString()}>
      {left === 0 ? "due now" : `in ${two(h)}:${two(m)}:${two(s)}`}
    </time>
  );
}
