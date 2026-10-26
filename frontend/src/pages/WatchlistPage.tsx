import { track } from "@amplitude/unified";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Crest } from "../components/match/icons";
import { PriceChangeBadge } from "../components/priceChange/PriceChange";
import { WatchStar } from "../components/WatchStar";
import { direction, usePriceChanges } from "../hooks/usePriceChanges";
import { getSyncCode, mergeRemoteWatchlist, readWatchlist, setSyncCode, useWatchlist } from "../hooks/useWatchlist";
import "./MatchPage.css";
import "./TeamPage.css";
import "./WatchlistPage.css";

// Watchlist (/watchlist): the players you're tracking, with what matters for a
// transfer decision side by side: price and FPL's price-move signal, status,
// form, projected points and the next five gameweeks of fixtures. A sync code
// (shared with the transfer planner) opens the same list on another device.

interface Cell { opp: string; home: boolean; difficulty: number | null; cleanSheet: number | null; goals: number | null }
interface W {
  id: number; name: string; team: string; teamShort: string; position: string; price: number; form: number; points: number;
  ownership: number; status: string; news: string; chance: number | null;
  projected: Record<string, number | null>; fixtures: Record<string, Cell[]>;
  rotation: { starts: number; clubGames: number; next14: number } | null;
}
interface Payload { gameweeks: number[]; players: W[]; fixtureModel: boolean }
type Sort = "added" | "projected" | "price" | "form" | "move";

const money = (t: number) => `£${(t / 10).toFixed(1)}m`;

// One colour band per fixture: clean-sheet chance for keepers and defenders,
// projected goals for midfielders and forwards, FPL difficulty without the model.
function band(c: Cell, pos: string): number {
  if ((pos === "GKP" || pos === "DEF") && c.cleanSheet != null) { const v = c.cleanSheet; return v >= 0.45 ? 1 : v >= 0.35 ? 2 : v >= 0.27 ? 3 : v >= 0.2 ? 4 : 5; }
  if ((pos === "MID" || pos === "FWD") && c.goals != null) { const v = c.goals; return v >= 2 ? 1 : v >= 1.6 ? 2 : v >= 1.3 ? 3 : v >= 1 ? 4 : 5; }
  return c.difficulty ?? 0;
}
const cellNote = (c: Cell, pos: string) => ((pos === "GKP" || pos === "DEF") && c.cleanSheet != null ? `${Math.round(c.cleanSheet * 100)}%`
  : (pos === "MID" || pos === "FWD") && c.goals != null ? c.goals.toFixed(1) : `FDR ${c.difficulty ?? "–"}`);

export function WatchlistPage() {
  const { ids } = useWatchlist();
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>("added");
  const [pos, setPos] = useState("all");
  const [q, setQ] = useState("");
  const prices = usePriceChanges();
  const key = ids.join(",");

  useEffect(() => { document.title = "Watchlist · AeroFPL"; }, []);
  useEffect(() => {
    if (!ids.length) { setData({ gameweeks: [], players: [], fixtureModel: false }); return; }
    let alive = true;
    fetch(`/api/watchlist/?ids=${key}`).then((r) => (r.ok ? r.json() : Promise.reject())).then((d) => { if (alive) setData(d); })
      .catch(() => { if (alive) setError("Your watchlist couldn't be loaded. Try again in a minute."); });
    return () => { alive = false; };
  }, [key]);

  const gws = data?.gameweeks ?? [];
  const next3 = (p: W) => gws.slice(0, 3).reduce((s, g) => s + (p.projected[String(g)] ?? 0), 0);
  const rows = useMemo(() => {
    const list = (data?.players ?? []).filter((p) => ids.includes(p.id) && (pos === "all" || p.position === pos));
    const move = (p: W) => prices?.byId.get(p.id)?.progress ?? -999;
    if (sort === "projected") return [...list].sort((a, b) => next3(b) - next3(a));
    if (sort === "price") return [...list].sort((a, b) => b.price - a.price);
    if (sort === "form") return [...list].sort((a, b) => b.form - a.form);
    if (sort === "move") return [...list].sort((a, b) => move(b) - move(a));
    return [...list].sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
  }, [data, ids, pos, sort, prices]);

  const rising = rows.filter((p) => direction(prices?.byId.get(p.id) ?? null) === "rise");
  const flagged = rows.filter((p) => p.status !== "a");
  const search = q.trim().length >= 2 ? (prices?.players ?? []).filter((p) => !ids.includes(p.id) && `${p.name} ${p.team}`.toLowerCase().includes(q.toLowerCase())).slice(0, 8) : [];

  return (
    <main className="aero-page mp-page tp-page wl-page">
      <header className="tp-index-head">
        <h1>Watchlist</h1>
        <p>The players you're tracking. Star a player anywhere on the site to add him here: his page, the Players list, the planner, DEFCON or the Stats Explorer.</p>
      </header>

      <div className="wl-add">
        <input className="aero-input" placeholder="Add a player: type a name" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Find a player to add" />
        {search.length > 0 && (
          <ul className="wl-results">
            {search.map((p) => <li key={p.id}><WatchStar id={p.id} name={p.name} /><span><b>{p.name}</b> {p.team} · {p.position} · £{p.price.toFixed(1)}m</span></li>)}
          </ul>
        )}
      </div>

      {error && <p className="mp-error" role="alert">{error}</p>}
      {!data && !error && <div className="mp-skeleton tall" aria-busy="true" />}
      {data && ids.length === 0 && (
        <div className="wl-empty">
          <p><b>Nothing on your watchlist yet.</b> Search above, or tap the star next to a player wherever you see one.</p>
        </div>
      )}
      {data && rows.length > 0 && (
        <>
          <p className="tp-summary">
            {ids.length} player{ids.length === 1 ? "" : "s"} on your watchlist.
            {rising.length > 0 && <> {rising.map((p) => p.name).join(", ")} {rising.length === 1 ? "is" : "are"} likely to rise in price soon.</>}
            {flagged.length > 0 && <> {flagged.map((p) => p.name).join(", ")} {flagged.length === 1 ? "is" : "are"} flagged by FPL.</>}
          </p>
          <div className="tp-filters">
            <div className="tp-seg" role="group" aria-label="Position">
              {["all", "GKP", "DEF", "MID", "FWD"].map((p) => <button key={p} type="button" aria-pressed={pos === p} onClick={() => setPos(p)}>{p === "all" ? "Everyone" : p}</button>)}
            </div>
            <label className="wl-label">Order
              <select className="aero-select" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                <option value="added">As added</option><option value="projected">Projected, next 3</option><option value="move">Closest to a price rise</option><option value="form">Form</option><option value="price">Price</option>
              </select>
            </label>
          </div>
          <div className="mp-sheet wl-table">
            <table>
              <thead>
                <tr>
                  <th scope="col"><span className="sr-only">Watch</span></th><th scope="col">Player</th><th scope="col" className="n">Price</th><th scope="col" className="n">Form</th>
                  <th scope="col" className="n" title="AeroFPL forecast where it has the player, FPL's expected points otherwise">Projected</th>
                  <th scope="col">Next {gws.length}</th><th scope="col" className="n hide-s">Starts</th><th scope="col" className="n hide-s">Owned</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td className="star"><WatchStar id={p.id} name={p.name} /></td>
                    <th scope="row">
                      <Link to={`/players/${p.id}`}><Crest team={p.team} /><span>{p.name}</span></Link>
                      <small>{p.teamShort} · {p.position}{p.status !== "a" && <span className={`wl-flag s-${p.status}`} title={p.news}>{p.chance != null && p.status === "d" ? `${p.chance}%` : p.status === "s" ? "Suspended" : "Out"}</span>}</small>
                    </th>
                    <td className="n">{money(p.price)}<span className="wl-move"><PriceChangeBadge athleteId={p.id} /></span></td>
                    <td className="n">{p.form.toFixed(1)}</td>
                    <td className="n"><b>{p.projected[String(gws[0])] != null ? p.projected[String(gws[0])]!.toFixed(1) : "–"}</b><small> {next3(p).toFixed(1)} in 3</small></td>
                    <td>
                      <span className="wl-fx">
                        {gws.map((g) => {
                          const cells = p.fixtures[String(g)] ?? [];
                          return (
                            <span key={g} className="wl-fx-cell" title={`GW${g}: ${cells.length ? cells.map((c) => `${c.home ? "v" : "at"} ${c.opp} (${cellNote(c, p.position)})`).join(", ") : "no game"}`}>
                              {cells.length === 0 && <i className="blank">—</i>}
                              {cells.map((c, k) => <i key={k} className={`b-${band(c, p.position)}`}>{c.home ? c.opp : c.opp.toLowerCase()}</i>)}
                            </span>
                          );
                        })}
                      </span>
                    </td>
                    <td className="n hide-s">{p.rotation?.clubGames ? `${p.rotation.starts}/${p.rotation.clubGames}` : "–"}</td>
                    <td className="n hide-s">{p.ownership.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mp-foot">Fixture colours: {data.fixtureModel ? "clean-sheet chance for goalkeepers and defenders, projected goals for midfielders and forwards (AeroFPL fixture model)" : "FPL's difficulty rating"}. Capitals are home games. Starts: in the club's last games, every competition.</p>
        </>
      )}
      <WatchlistSync />
    </main>
  );
}

// Same code as the transfer planner's: one code carries plans and watchlist.
function WatchlistSync() {
  const [code, setCode] = useState<string | null>(getSyncCode);
  const [entry, setEntry] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    const r = await fetch("/api/planner/sync/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ watchlist: readWatchlist() }) }).catch(() => null);
    setBusy(false);
    if (!r?.ok) { setMsg("Couldn't create a code. Try again."); return; }
    const d = await r.json();
    setSyncCode(d.code); setCode(d.code); setMsg(null); track("Planner Sync Created", { from: "watchlist" });
  };
  const join = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const r = await fetch(`/api/planner/sync/${entry.trim().toLowerCase()}/`).catch(() => null);
    setBusy(false);
    if (!r?.ok) { setMsg("Nothing is saved under that code."); return; }
    const d = await r.json();
    setSyncCode(d.code); setCode(d.code); mergeRemoteWatchlist(d.watchlist, d.code);
    setMsg("Synced. Players from both devices are on your list.");
  };

  return (
    <section className="wl-sync" aria-label="Sync">
      {code ? (
        <p>Synced under <b className="wl-code">{code}</b>. Enter the code on another device, here or in the transfer planner, to see the same list. Changes save as you make them.
          <button type="button" className="wl-x" onClick={() => navigator.clipboard?.writeText(code).then(() => setMsg("Copied."))}>Copy</button>
          <button type="button" className="wl-x" onClick={() => { setSyncCode(null); setCode(null); setMsg("This device has stopped syncing. Your list stays here."); }}>Stop syncing here</button>
        </p>
      ) : (
        <form onSubmit={join}>
          <p>Saved in this browser only. To keep the same list on your phone and laptop, create a sync code, or enter one you made here or in the transfer planner. No account needed; anyone with the code can see and change the list.</p>
          <div className="wl-sync-row">
            <button type="button" className="aero-button primary" onClick={create} disabled={busy}>Create a sync code</button>
            <span>or</span>
            <input className="aero-input" placeholder="Enter a code" value={entry} onChange={(e) => setEntry(e.target.value)} aria-label="Sync code" />
            <button type="submit" className="aero-button" disabled={busy || entry.trim().length < 6}>Use code</button>
          </div>
        </form>
      )}
      {msg && <p className="mp-note" role="status">{msg}</p>}
    </section>
  );
}
