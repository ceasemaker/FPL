import { useMemo, useState } from "react";
import { direction, usePriceChanges, type PriceChange } from "../../hooks/usePriceChanges";
import { Countdown, TrendArrow } from "./PriceChange";
import "./PriceChange.css";

type Filter = "all" | "rise" | "drop";
const pct = (v: number | null) => (v === null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}%`);
const PAGE = 30;

// FPL's own price-change tracker as a sortable list: who is close to rising
// or falling at the next price-change run, by FPL's own numbers.
export function PriceTracker({ onOpen }: { onOpen?: (id: number) => void }) {
  const data = usePriceChanges();
  const [filter, setFilter] = useState<Filter>("all");
  const [limit, setLimit] = useState(PAGE);
  const rows = useMemo(() => (data?.players ?? []).filter((p) => filter === "all" || direction(p) === filter), [data, filter]);
  const next = data?.meta.deadlines[0];

  return (
    <section className="aero-card pc-tracker">
      <header className="pc-tracker-head">
        <div>
          <h2>Next price change {next ? <Countdown to={next} /> : null}</h2>
          <p>
            {next && <>At {new Date(next).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} your time. </>}
            FPL's own tracker{data?.meta.lastUpdated && <>, last updated {new Date(data.meta.lastUpdated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</>} (it updates every 15 minutes).
          </p>
        </div>
        <span className="pc-source" title="Progress, predictions and likelihood all come from FPL's own price-change tracker">FPL estimate</span>
      </header>
      <div className="pc-filter" role="tablist" aria-label="Show">
        {([["all", "All"], ["rise", "Likely to rise"], ["drop", "Likely to drop"]] as [Filter, string][]).map(([key, text]) => (
          <button key={key} role="tab" aria-selected={filter === key} className={filter === key ? "active" : ""} onClick={() => { setFilter(key); setLimit(PAGE); }}>{text}</button>
        ))}
      </div>
      {!data ? <p className="pc-note">Loading FPL's price tracker…</p> : rows.length === 0 ? <p className="pc-note">Nobody in this group right now.</p> : (
        <div className="pc-table-wrap">
          <table className="pc-table">
            <thead>
              <tr><th scope="col">Player</th><th scope="col">Status</th><th scope="col" className="num">Progress</th><th scope="col" className="num">Predicted</th><th scope="col">Ownership</th><th scope="col" className="num">Price</th></tr>
            </thead>
            <tbody>
              {rows.slice(0, limit).map((p: PriceChange) => {
                const dir = direction(p);
                return (
                  <tr key={p.id}>
                    <th scope="row">
                      <button className="pc-player" onClick={() => onOpen?.(p.id)}>
                        <strong>{p.name}</strong><span>{p.team} {p.position}</span>
                      </button>
                    </th>
                    <td><span className={`pc-status pc-${dir}`}>{p.label}</span>{p.lockedUntil && <span className="pc-locked" title={`Locked until ${new Date(p.lockedUntil).toLocaleString()}`}>Locked</span>}</td>
                    <td className="num">{pct(p.progress)}</td>
                    <td className="num">{pct(p.predicted)}</td>
                    <td className={`pc-trend t-${p.trend}`}>{p.trend === "up" ? <><TrendArrow dir="rise" />Rising</> : p.trend === "down" ? <><TrendArrow dir="drop" />Falling</> : "Flat"}</td>
                    <td className="num">£{p.price.toFixed(1)}m</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length > limit && <button className="pc-more" onClick={() => setLimit((n) => n + PAGE)}>Show {Math.min(PAGE, rows.length - limit)} more of {rows.length - limit}</button>}
        </div>
      )}
    </section>
  );
}
