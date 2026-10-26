import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { projected, swapPlayers, type ChipKey, type Lineup, type PlannerData, type PlannerPlayer } from "./planModel";
import "./PlannerPitch.css";

// The planner's squad on a pitch, laid out like FPL's Pick Team: the XI in
// formation rows, the bench underneath in substitution order. Tap a player for
// their options; "Substitute" then highlights who they can legally swap with.

const SHIRT = "https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_";
const ROWS = ["GKP", "DEF", "MID", "FWD"] as const;

interface Props {
  data: PlannerData;
  gw: number;
  sheet: Lineup;
  byId: Map<number, PlannerPlayer>;
  chip?: ChipKey;
  newIds: Set<number>;
  selling: number | null;
  onChange: (sheet: Lineup) => void;
  onSell: (id: number) => void;
}

export function PlannerPitch({ data, gw, sheet, byId, chip, newIds, selling, onChange, onSell }: Props) {
  const [menu, setMenu] = useState<number | null>(null);
  const [subbing, setSubbing] = useState<number | null>(null);
  const root = useRef<HTMLDivElement>(null);

  // Escape or a tap outside the pitch closes the menu and cancels a substitution.
  useEffect(() => {
    const close = () => { setMenu(null); setSubbing(null); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    const onDown = (e: PointerEvent) => { if (root.current && !root.current.contains(e.target as Node)) close(); };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => { document.removeEventListener("keydown", onKey); document.removeEventListener("pointerdown", onDown); };
  }, []);
  useEffect(() => { setMenu(null); setSubbing(null); }, [gw]);

  const tap = (id: number) => {
    if (subbing != null) {
      const next = swapPlayers(sheet, subbing, id, byId);
      if (next) onChange(next);
      setSubbing(null);
      setMenu(null);
      return;
    }
    setMenu(menu === id ? null : id);
  };

  const card = (id: number, benchSlot?: string) => {
    const p = byId.get(id);
    if (!p) return null;
    const target = subbing != null && subbing !== id && swapPlayers(sheet, subbing, id, byId) != null;
    const dimmed = subbing != null && subbing !== id && !target;
    const flagged = p.status !== "a";
    const pts = projected(data, id, gw);
    const fixtures = data.fixtures[p.team]?.[String(gw)]?.fixtures ?? [];
    const opp = fixtures.length ? fixtures.map((f) => `${f.opp} (${f.home ? "H" : "A"})`).join(", ") : "No game";
    const cls = ["pp-card", newIds.has(id) && "is-new", subbing === id && "subbing", target && "target", dimmed && "dimmed", selling === id && "selling"].filter(Boolean).join(" ");
    return (
      <div className="pp-slot" key={id}>
        {benchSlot && <span className="pp-bench-label">{benchSlot}</span>}
        <button type="button" className={cls} onClick={() => tap(id)} aria-haspopup="menu" aria-expanded={menu === id}
          aria-label={`${p.name}, ${p.teamShort}, ${opp}${pts != null ? `, ${pts.toFixed(1)} projected` : ""}${sheet.captain === id ? ", captain" : sheet.vice === id ? ", vice-captain" : ""}`}>
          {sheet.captain === id && <span className="pp-arm c" title={chip === "3xc" ? "Triple captain" : "Captain"}>{chip === "3xc" ? "3×" : "C"}</span>}
          {sheet.vice === id && <span className="pp-arm v" title="Vice-captain">V</span>}
          {flagged && <span className={`pp-flag s-${p.status}`} title={p.news || "Flagged by FPL"}>{p.chance != null ? `${p.chance}%` : "Out"}</span>}
          <img className="pp-shirt" src={`${SHIRT}${p.team}${p.position === "GKP" ? "_1" : ""}-110.webp`} alt="" width={56} height={56} loading="lazy" />
          <span className="pp-name">{p.name}{newIds.has(id) && <i className="pp-new">New</i>}</span>
          <span className="pp-info"><span className="pp-opp">{opp}</span><b>{pts != null ? pts.toFixed(1) : "–"}</b></span>
        </button>
        {menu === id && (
          <div className="pp-menu" role="menu">
            <button type="button" role="menuitem" onClick={() => { setSubbing(id); setMenu(null); }}>Substitute</button>
            <button type="button" role="menuitem" onClick={() => { onSell(id); setMenu(null); }}>{selling === id ? "Cancel sale" : "Sell"}</button>
            {sheet.xi.includes(id) && sheet.captain !== id && (
              <button type="button" role="menuitem" onClick={() => { onChange({ ...sheet, captain: id, vice: sheet.vice === id ? sheet.captain : sheet.vice }); setMenu(null); }}>Make captain</button>
            )}
            {sheet.xi.includes(id) && sheet.vice !== id && (
              <button type="button" role="menuitem" onClick={() => { onChange({ ...sheet, vice: id, captain: sheet.captain === id ? sheet.vice : sheet.captain }); setMenu(null); }}>Make vice-captain</button>
            )}
            <Link role="menuitem" to={`/players/${id}`}>Player page</Link>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="pp" ref={root}>
      {subbing != null && (
        <p className="pp-hint" role="status">Choose who {byId.get(subbing)?.name} swaps with. <button type="button" onClick={() => setSubbing(null)}>Cancel</button></p>
      )}
      <div className="pp-pitch">
        <svg className="pp-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <rect x="1" y="1" width="98" height="98" />
          <rect x="22" y="1" width="56" height="17" />
          <rect x="37" y="1" width="26" height="6" />
          <path d="M40 18a10 6 0 0 0 20 0" />
          <path d="M1 99h98" />
          <path d="M38 99a12 9 0 0 1 24 0" />
        </svg>
        {ROWS.map((pos) => (
          <div className="pp-row" key={pos}>{sheet.xi.filter((id) => byId.get(id)?.position === pos).map((id) => card(id))}</div>
        ))}
      </div>
      <div className={`pp-bench${chip === "bboost" ? " boosted" : ""}`} aria-label="Bench">
        <span className="pp-bench-title">{chip === "bboost" ? "Bench (Bench Boost: these score too)" : "Bench"}</span>
        <div className="pp-row">{sheet.bench.map((id, i) => card(id, i === 0 ? "GK" : String(i)))}</div>
      </div>
    </div>
  );
}
