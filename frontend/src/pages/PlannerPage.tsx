import { track } from "@amplitude/unified";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Crest } from "../components/match/icons";
import {
  bestXI, CHIP_NAMES, chipOptions, gamesIn, HIT, MAX_PER_CLUB, money, projected, squadAt, summarise,
  type ChipKey, type Plan, type PlannerData, type PlannerPlayer, type Transfer, type WeekSummary,
} from "../components/planner/planModel";
import { PriceChangeBadge } from "../components/priceChange/PriceChange";
import { WatchStar } from "../components/WatchStar";
import { direction, usePriceChanges, type PriceChangeData } from "../hooks/usePriceChanges";
import { mergeRemoteWatchlist, readWatchlist, SYNC_KEY } from "../hooks/useWatchlist";
import "./MatchPage.css";
import "./TeamPage.css";
import "./PlannerPage.css";

// Transfer planner (/planner): import a squad by FPL manager ID, plan transfers
// and chips over the next six gameweeks with bank, free transfers and hits
// tallied, see fixtures (with cup and European games in between), projected
// points from the AeroFPL forecast (with its record), rotation risk, FPL's own
// price-change flags, optimizer suggestions and mini-league rivals. Plans are
// saved in this browser and can be synced to another device with a code (the
// same code carries the watchlist).

const PLAN_NAMES = ["A", "B", "C"];
const ORDER: Record<string, number> = { GKP: 0, DEF: 1, MID: 2, FWD: 3 };
const POS_WORD: Record<string, string> = { GKP: "Goalkeepers", DEF: "Defenders", MID: "Midfielders", FWD: "Forwards" };
const storeKey = (id: number) => `aerofpl_planner_v1_${id}`;
interface Stored { active: string; plans: Record<string, Plan> }

const safeGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const safeSet = (k: string, v: string | null) => { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch { /* storage blocked */ } };

function readPlans(id: number): Stored {
  try {
    const raw = safeGet(storeKey(id));
    if (raw) return JSON.parse(raw) as Stored;
  } catch { /* bad data: start fresh */ }
  return { active: "A", plans: { A: { name: "Plan A", transfers: [] } } };
}

export function PlannerPage() {
  const [params, setParams] = useSearchParams();
  const initialId = params.get("manager") ?? safeGet("fpl_manager_id") ?? "";
  const [draft, setDraft] = useState(initialId);
  const [managerId, setManagerId] = useState<number | null>(initialId && /^\d+$/.test(initialId) ? Number(initialId) : null);
  const [data, setData] = useState<PlannerData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stored, setStored] = useState<Stored | null>(null);
  const [gw, setGw] = useState<number | null>(null);
  const [selling, setSelling] = useState<number | null>(null);
  const [syncCode, setSyncCode] = useState<string | null>(safeGet(SYNC_KEY));
  const [panel, setPanel] = useState<"sync" | null>(null);
  const prices = usePriceChanges();

  useEffect(() => { document.title = "Transfer planner · AeroFPL"; }, []);
  // On narrow screens the replacement list sits below the squad: bring it into view.
  useEffect(() => {
    if (selling != null && window.innerWidth <= 1200) document.querySelector(".pl-pick")?.scrollIntoView({ block: "start" });
  }, [selling]);

  useEffect(() => {
    if (!managerId) return;
    let alive = true;
    setLoading(true); setError(null);
    fetch(`/api/planner/${managerId}/`)
      .then(async (r) => {
        if (!r.ok) throw new Error(r.status === 404 ? "We couldn't find that FPL manager ID. It's the number in your team's points page address." : "Something went wrong loading your team. Try again in a minute.");
        return r.json() as Promise<PlannerData>;
      })
      .then((d) => {
        if (!alive) return;
        setData(d); setStored(readPlans(d.managerId)); setGw(d.nextGameweek); setSelling(null);
        safeSet("fpl_manager_id", String(d.managerId));
        track("Planner Team Imported");
      })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [managerId]);

  // Push saved plans to the sync code a moment after each change.
  const pushTimer = useRef<number | null>(null);
  const persist = (next: Stored) => {
    if (!data) return;
    setStored(next);
    safeSet(storeKey(data.managerId), JSON.stringify(next));
    if (syncCode) {
      if (pushTimer.current) window.clearTimeout(pushTimer.current);
      pushTimer.current = window.setTimeout(() => {
        fetch(`/api/planner/sync/${syncCode}/`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ managerId: data.managerId, plans: next }) }).catch(() => undefined);
      }, 800);
    }
  };

  const byId = useMemo(() => new Map((data?.players ?? []).map((p) => [p.id, p])), [data]);
  const plan = stored ? stored.plans[stored.active] : null;
  const weeks = useMemo(() => (data && plan ? summarise(data, plan, byId) : []), [data, plan, byId]);

  const load = (e: FormEvent) => {
    e.preventDefault();
    const id = draft.trim();
    if (!/^\d+$/.test(id)) { setError("Enter the number in your FPL team's address, e.g. 576154."); return; }
    setManagerId(Number(id));
    const next = new URLSearchParams(params); next.set("manager", id); setParams(next, { replace: true });
  };

  const savePlan = (p: Plan) => { if (stored) persist({ ...stored, plans: { ...stored.plans, [stored.active]: p } }); };
  const switchPlan = (name: string) => {
    if (!stored) return;
    persist({ active: name, plans: { ...stored.plans, [name]: stored.plans[name] ?? { name: `Plan ${name}`, transfers: [] } } });
  };
  const freeSlot = stored ? PLAN_NAMES.find((n) => n !== stored.active && (!stored.plans[n] || (!stored.plans[n].transfers.length && !Object.keys(stored.plans[n].chips ?? {}).length))) : undefined;
  const copyPlan = () => {
    if (!stored || !plan || !freeSlot) return;
    persist({ active: freeSlot, plans: { ...stored.plans, [freeSlot]: { ...plan, name: `Plan ${freeSlot}` } } });
  };

  const addTransfer = (outId: number, inPlayer: PlannerPlayer) => {
    if (!data || !plan || gw == null) return;
    const holding = squadAt(data, plan, gw).find((h) => h.id === outId);
    if (!holding) return;
    savePlan({ ...plan, transfers: [...plan.transfers, { gw, out: outId, in: inPlayer.id, sell: holding.selling, buy: inPlayer.price }] });
    setSelling(null);
    track("Transfer Planned");
  };
  // Undoing a transfer also undoes later ones that moved the player it brought in.
  const removeTransfer = (t: Transfer) => {
    if (!plan) return;
    let drop = new Set<Transfer>([t]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const x of plan.transfers) {
        if (!drop.has(x) && [...drop].some((d) => x.gw >= d.gw && x.out === d.in)) { drop = new Set([...drop, x]); changed = true; }
      }
    }
    savePlan({ ...plan, transfers: plan.transfers.filter((x) => !drop.has(x)) });
  };
  const setChip = (week: number, chip: ChipKey | "") => {
    if (!plan) return;
    const chips = { ...(plan.chips ?? {}) };
    if (chip) chips[String(week)] = chip; else delete chips[String(week)];
    savePlan({ ...plan, chips });
    if (chip) track("Chip Planned", { chip });
  };

  if (!data || !plan || gw == null) {
    return (
      <main className="aero-page mp-page pl-page">
        <header className="pl-head"><div><h1>Transfer planner</h1><p>Load your FPL team, plan transfers and chips for the next six gameweeks, and see who's about to change price.</p></div></header>
        <ImportForm draft={draft} setDraft={setDraft} onSubmit={load} loading={loading} />
        {error && <p className="mp-error" role="alert">{error}</p>}
        {loading && <div className="mp-skeleton tall" aria-busy="true" />}
        {!loading && !error && <p className="pl-help">Your manager ID is the number in the address of your team's Points page on the FPL site: fantasy.premierleague.com/entry/<b>576154</b>/event/8. No login needed.</p>}
        <SyncLoad onLoaded={(code, d) => { setSyncCode(code); safeSet(SYNC_KEY, code); mergeRemoteWatchlist(d.watchlist, code); if (d.managerId && d.plans?.plans) { safeSet(storeKey(d.managerId), JSON.stringify(d.plans)); setDraft(String(d.managerId)); setManagerId(d.managerId); } }} />
      </main>
    );
  }

  const week: WeekSummary | undefined = weeks.find((w) => w.gw === gw) ?? weeks[0];
  const squad = squadAt(data, plan, gw).map((h) => ({ ...h, p: byId.get(h.id) })).filter((h) => h.p)
    .sort((a, b) => ORDER[a.p!.position] - ORDER[b.p!.position] || b.p!.price - a.p!.price);
  const totalHits = weeks.reduce((s, w) => s + w.cost, 0);
  const checks = planChecks(data, plan, weeks, byId, prices, gw);
  const xiByWeek = new Map(weeks.map((w) => {
    const ids = squadAt(data, plan, w.gw).map((h) => h.id);
    const best = bestXI(data, ids, byId, w.gw);
    const total = best.points + best.captainPts * (w.chip === "3xc" ? 2 : 1) + (w.chip === "bboost" ? best.benchPts : 0) - w.cost;
    return [w.gw, { ...best, total }];
  }));
  const thisXI = xiByWeek.get(gw);
  const record = data.projections.record;

  return (
    <main className="aero-page mp-page pl-page">
      <header className="pl-head">
        <div>
          <h1>Transfer planner</h1>
          <p><b>{data.teamName}</b> · {data.name}{data.overallRank ? ` · rank ${data.overallRank.toLocaleString()}` : ""} · <button type="button" className="pl-link" onClick={() => { setData(null); setManagerId(null); }}>Load another team</button></p>
        </div>
        <div className="pl-plans" role="group" aria-label="Plans">
          {PLAN_NAMES.map((n) => (
            <button key={n} type="button" aria-pressed={stored!.active === n} onClick={() => switchPlan(n)} className={stored!.plans[n] ? "" : "empty"}>
              Plan {n}{stored!.plans[n]?.transfers.length ? <small>{stored!.plans[n].transfers.length}</small> : null}
            </button>
          ))}
          <button type="button" className="pl-ghost" onClick={copyPlan} disabled={!freeSlot}>Copy to a new plan</button>
          <button type="button" className={`pl-ghost${syncCode ? " on" : ""}`} aria-pressed={panel === "sync"} onClick={() => setPanel(panel === "sync" ? null : "sync")}>{syncCode ? "Synced" : "Sync to another device"}</button>
        </div>
      </header>

      {panel === "sync" && <SyncPanel code={syncCode} managerId={data.managerId} stored={stored!} onLinked={(c) => { setSyncCode(c); safeSet(SYNC_KEY, c); }}
        onUnlinked={() => { setSyncCode(null); safeSet(SYNC_KEY, null); }} onPulled={(s) => persist(s)} />}

      <section className="pl-facts" aria-label="Team facts">
        <div><dt>Bank</dt><dd>{money(plan.bank ?? data.bank)}</dd></div>
        <div>
          <dt>Free transfers for GW{data.nextGameweek} <span title="Worked out from your history; FPL doesn't publish it. Correct it if it's wrong.">(estimate)</span></dt>
          <dd className="pl-step">
            <button type="button" aria-label="One fewer" onClick={() => savePlan({ ...plan, freeTransfers: Math.max(0, (plan.freeTransfers ?? data.freeTransfers) - 1) })}><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6h7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg></button>
            {plan.freeTransfers ?? data.freeTransfers}
            <button type="button" aria-label="One more" onClick={() => savePlan({ ...plan, freeTransfers: Math.min(5, (plan.freeTransfers ?? data.freeTransfers) + 1) })}><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6h7M6 2.5v7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg></button>
          </dd>
        </div>
        <div><dt>Team value</dt><dd>{data.teamValue != null ? money(data.teamValue) : "–"}</dd></div>
        <div><dt>Chips left this half</dt><dd className="pl-chips">{data.chips.filter((c) => c.available).map((c) => <span key={c.key}>{c.name}</span>)}{data.chips.every((c) => !c.available) && "None"}</dd></div>
        <div><dt>Hits in this plan</dt><dd className={totalHits ? "neg" : ""}>{totalHits ? `−${totalHits} pts` : "None"}</dd></div>
        <Suggest data={data} plan={plan} freeSlot={freeSlot} onPlan={(name, p) => persist({ active: name, plans: { ...stored!.plans, [name]: p } })} />
      </section>

      <nav className="pl-weeks" aria-label="Gameweeks">
        {weeks.map((w) => {
          const ids = squadAt(data, plan, w.gw).map((h) => h.id);
          const blanks = ids.filter((id) => gamesIn(data, byId.get(id)?.team ?? "", w.gw) === 0).length;
          const doubles = ids.filter((id) => gamesIn(data, byId.get(id)?.team ?? "", w.gw) > 1).length;
          return (
            <button key={w.gw} type="button" aria-pressed={w.gw === gw} onClick={() => { setGw(w.gw); setSelling(null); }}
              className={w.overBudget || w.clubsOver.length ? "bad" : ""}>
              <b>GW{w.gw}{w.chip && <span className="pl-chip-tag">{CHIP_NAMES[w.chip]}</span>}</b>
              <small>{w.transfers.length ? `${w.transfers.length} transfer${w.transfers.length === 1 ? "" : "s"}${w.cost ? ` · −${w.cost}` : ""}` : `${w.free} free`}</small>
              <small className="xp">{xiByWeek.get(w.gw)!.available ? `${xiByWeek.get(w.gw)!.total.toFixed(1)} projected` : "No projection yet"}</small>
              {(blanks > 0 || doubles > 0) && <small className="bd">{doubles ? `${doubles} double` : ""}{doubles && blanks ? " · " : ""}{blanks ? `${blanks} blank` : ""}</small>}
            </button>
          );
        })}
      </nav>

      <div className="pl-grid">
        <section className="mp-sheet pl-squad" aria-label={`Squad for gameweek ${gw}`}>
          <div className="pl-squad-head">
            <span>Your squad for GW{gw} <span className="pl-xp-key">· projected points this week</span></span>
            <span className="pl-fx-head">{data.gameweeks.map((g) => <b key={g.gameweek} className={g.gameweek === gw ? "on" : ""}>GW{g.gameweek}</b>)}</span>
          </div>
          {(["GKP", "DEF", "MID", "FWD"] as const).map((pos) => (
            <div key={pos} className="pl-pos">
              <h3>{POS_WORD[pos]}</h3>
              {squad.filter((h) => h.p!.position === pos).map((h) => (
                <SquadRow key={h.id} player={h.p!} selling={h.selling} data={data} gw={gw}
                  isNew={plan.transfers.some((t) => t.in === h.id && t.gw <= gw)}
                  inXI={thisXI?.xi.includes(h.id) ?? true} captain={thisXI?.captain === h.id}
                  active={selling === h.id} onSell={() => setSelling(selling === h.id ? null : h.id)} />
              ))}
            </div>
          ))}
          {record && (
            <p className="pl-record">Projected points come from the AeroFPL forecast. Tested on {record.playerWeeks.toLocaleString()} player-weeks across {record.seasons.join(", ")}, it was off by {record.modelError.toFixed(2)} points a week on average, against {record.formError.toFixed(2)} for a guess from form alone. It is a guide, not a promise.{data.projections.fplOnly.length ? " Players it has no history for show FPL's own expected points for the next gameweek only." : ""} Faded rows are the projected bench.</p>
          )}
        </section>

        <aside className="pl-side">
          {selling != null && byId.get(selling) ? (
            <Replacements out={byId.get(selling)!} selling={squad.find((h) => h.id === selling)?.selling ?? 0}
              bank={week?.bankAfter ?? data.bank} squadIds={new Set(squad.map((h) => h.id))}
              clubCounts={clubCounts(squad.map((h) => h.p!))} data={data} gw={gw}
              onPick={(p) => addTransfer(selling, p)} onClose={() => setSelling(null)} />
          ) : (
            <>
              <section className="mp-sheet pl-week">
                <div className="pl-week-head">
                  <h2>GW{gw}</h2>
                  <label>Chip
                    <select className="aero-select" value={plan.chips?.[String(gw)] ?? ""} onChange={(e) => setChip(gw, e.target.value as ChipKey | "")}>
                      <option value="">None</option>
                      {chipOptions(data, plan, gw).map((c) => <option key={c} value={c}>{CHIP_NAMES[c]}</option>)}
                    </select>
                  </label>
                </div>
                {week?.chip === "wildcard" && <p className="mp-note">Wildcard: unlimited free transfers this week, and they stay.</p>}
                {week?.chip === "freehit" && <p className="mp-note">Free Hit: unlimited free transfers for this week only. Your squad and bank go back afterwards.</p>}
                {week && week.transfers.length === 0 && <p className="mp-note">No transfers planned. Choose Sell on a player to plan one.</p>}
                {week?.transfers.map((t, i) => (
                  <div key={i} className="pl-move">
                    <span className="out">{byId.get(t.out)?.name}<small>{money(t.sell)}</small></span>
                    <svg width="14" height="14" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11m-4-4 4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    <span className="in">{byId.get(t.in)?.name}<small>{money(t.buy)}</small></span>
                    <button type="button" className="pl-x" aria-label="Undo this transfer" onClick={() => removeTransfer(t)}>Undo</button>
                  </div>
                ))}
                {week && thisXI && (
                  <dl className="pl-tally">
                    <div><dt>Free transfers</dt><dd>{week.chip === "wildcard" || week.chip === "freehit" ? "Unlimited" : week.free}</dd></div>
                    <div><dt>Hits</dt><dd className={week.cost ? "neg" : ""}>{week.cost ? `−${week.cost} pts (${week.hits} × ${HIT})` : "None"}</dd></div>
                    <div><dt>Bank after</dt><dd className={week.overBudget ? "neg" : ""}>{money(week.bankAfter)}</dd></div>
                    <div><dt>Projected points</dt><dd>{thisXI.available ? thisXI.total.toFixed(1) : "Not yet"}</dd></div>
                    <div className="sub"><dt>Best XI {thisXI.points.toFixed(1)} · captain {byId.get(thisXI.captain ?? 0)?.name ?? "–"} +{(thisXI.captainPts * (week.chip === "3xc" ? 2 : 1)).toFixed(1)}{week.chip === "bboost" ? ` · bench +${thisXI.benchPts.toFixed(1)}` : ""}{week.cost ? ` · hits −${week.cost}` : ""}</dt></div>
                  </dl>
                )}
              </section>
              <section className="mp-sheet pl-checks">
                <h2>Plan checks</h2>
                {checks.length === 0 ? <p className="mp-note">Nothing to flag.</p> : (
                  <ul>{checks.map((c, i) => <li key={i} className={c.level}>{c.text}</li>)}</ul>
                )}
              </section>
            </>
          )}
        </aside>
      </div>

      <MiniLeagues managerId={data.managerId} />

      <p className="mp-foot">Squad, bank and chips from FPL; free transfers worked out from your history. Selling prices follow FPL's rule (you keep half of any rise). Price flags are FPL's own tracker, about two days ahead. Plans are saved in this browser{syncCode ? " and under your sync code" : ""}.</p>
    </main>
  );
}

function ImportForm({ draft, setDraft, onSubmit, loading }: { draft: string; setDraft: (v: string) => void; onSubmit: (e: FormEvent) => void; loading: boolean }) {
  return (
    <form className="pl-import" onSubmit={onSubmit}>
      <label htmlFor="pl-id">FPL manager ID</label>
      <input id="pl-id" className="aero-input" inputMode="numeric" placeholder="e.g. 576154" value={draft} onChange={(e) => setDraft(e.target.value)} />
      <button type="submit" className="aero-button primary" disabled={loading}>{loading ? "Loading…" : "Load my team"}</button>
    </form>
  );
}

function clubCounts(players: PlannerPlayer[]) {
  const m = new Map<string, number>();
  for (const p of players) m.set(p.team, (m.get(p.team) ?? 0) + 1);
  return m;
}

const sum6 = (data: PlannerData, id: number, from: number) =>
  data.gameweeks.filter((g) => g.gameweek >= from).reduce((s, g) => s + (projected(data, id, g.gameweek) ?? 0), 0);

function rotationNote(data: PlannerData, id: number): { text: string; risky: boolean } | null {
  const r = data.rotation[String(id)];
  if (!r || !r.clubGames) return null;
  return { text: `started ${r.starts} of ${r.clubGames}${r.next14 >= 4 ? ` · ${r.next14} games in 14 days` : ""}`, risky: r.clubGames >= 4 && r.starts <= 2 };
}

function FixtureStrip({ data, team, from, count, gw }: { data: PlannerData; team: string; from: number; count: number; gw?: number }) {
  const weeks = data.gameweeks.map((g) => g.gameweek).filter((g) => g >= from).slice(0, count);
  return (
    <span className="pl-fx">
      {weeks.map((g) => {
        const cell = data.fixtures[team]?.[String(g)];
        const fx = cell?.fixtures ?? [];
        const before = cell?.before ?? [];
        return (
          <span key={g} className={`pl-fx-cell${g === gw ? " on" : ""}`}
            title={`GW${g}: ${fx.length ? fx.map((f) => `${f.home ? "v" : "at"} ${f.opp} (difficulty ${f.difficulty ?? "–"})`).join(", ") : "no league game (blank)"}${before.length ? `. Before it: ${before.map((b) => `${b.competition} ${b.home ? "v" : "at"} ${b.opp}`).join(", ")}` : ""}`}>
            {fx.length === 0 && <i className="blank">—</i>}
            {fx.map((f, k) => <i key={k} className={`fdr-${f.difficulty ?? 0}`}>{f.home ? f.opp : f.opp.toLowerCase()}</i>)}
            {before.length > 0 && <em>{before.map((b) => b.competition).join("+")}</em>}
          </span>
        );
      })}
    </span>
  );
}

function SquadRow({ player, selling, data, gw, isNew, inXI, captain, active, onSell }: {
  player: PlannerPlayer; selling: number; data: PlannerData; gw: number; isNew: boolean; inXI: boolean; captain: boolean; active: boolean; onSell: () => void;
}) {
  const flagged = player.status !== "a";
  const rot = rotationNote(data, player.id);
  const xp = projected(data, player.id, gw);
  const six = sum6(data, player.id, data.nextGameweek);
  return (
    <div className={`pl-row${active ? " active" : ""}${isNew ? " new" : ""}${inXI ? "" : " bench"}`}>
      <Crest team={player.team} />
      <span className="nm">
        <Link to={`/players/${player.id}`}>{player.name}</Link>
        <WatchStar id={player.id} name={player.name} size={14} />
        {captain && <span className="pl-cap" title="Projected captain">C</span>}
        {flagged && <span className={`pl-status s-${player.status}`} title={player.news || "Flagged"}>{player.chance != null ? `${player.chance}%` : player.status === "i" ? "Injured" : player.status === "s" ? "Suspended" : "Doubt"}</span>}
        {isNew && <span className="pl-new">New</span>}
        {data.priceForecast?.chances[String(player.id)] != null && <span className="pl-rise" title={`AeroFPL forecast: ${Math.round(data.priceForecast.chances[String(player.id)] * 100)}% chance of a price rise within 7 days. In testing, ${Math.round(data.priceForecast.record.precision * 100)}% of players it flagged did rise.`}>Rise likely this week</span>}
        <small>
          {player.teamShort} · {money(player.price)}{selling !== player.price ? ` · sells for ${money(selling)}` : ""} <PriceChangeBadge athleteId={player.id} />
          {rot && <span className={rot.risky ? "pl-rot risky" : "pl-rot"}> · {rot.text}</span>}
        </small>
      </span>
      <span className="pl-xp" title={`Projected points: ${xp?.toFixed(1) ?? "–"} in GW${gw}, ${six.toFixed(1)} over the six weeks`}>
        <b>{xp != null ? xp.toFixed(1) : "–"}</b><small>{six.toFixed(0)} in 6</small>
      </span>
      <FixtureStrip data={data} team={player.team} from={data.nextGameweek} count={6} gw={gw} />
      <button type="button" className="pl-sell" aria-pressed={active} onClick={onSell}>{active ? "Cancel" : "Sell"}</button>
    </div>
  );
}

function Replacements({ out, selling, bank, squadIds, clubCounts: counts, data, gw, onPick, onClose }: {
  out: PlannerPlayer; selling: number; bank: number; squadIds: Set<number>; clubCounts: Map<string, number>;
  data: PlannerData; gw: number; onPick: (p: PlannerPlayer) => void; onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<"projected" | "form" | "points" | "price" | "rising">("projected");
  const [compare, setCompare] = useState<number[]>([]);
  const prices = usePriceChanges();
  const budget = bank + selling;
  const rows = data.players
    .filter((p) => p.position === out.position && !squadIds.has(p.id))
    .filter((p) => !q || `${p.name} ${p.fullName} ${p.teamShort}`.toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => sort === "price" ? b.price - a.price : sort === "points" ? b.points - a.points
      : sort === "rising" ? (prices?.byId.get(b.id)?.progress ?? -999) - (prices?.byId.get(a.id)?.progress ?? -999)
      : sort === "form" ? b.form - a.form : sum6(data, b.id, gw) - sum6(data, a.id, gw))
    .slice(0, 60);
  const byId = new Map(data.players.map((p) => [p.id, p]));
  const toggle = (id: number) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 3 ? c : [...c, id]));
  const lastGw = data.gameweeks[data.gameweeks.length - 1]?.gameweek;
  return (
    <section className="mp-sheet pl-pick" aria-label={`Replace ${out.name}`}>
      <div className="pl-pick-head">
        <h2>Replace {out.name}</h2>
        <button type="button" className="pl-x" onClick={onClose}>Close</button>
      </div>
      <p className="mp-note">Up to {money(budget)} to spend in GW{gw}: {money(selling)} from selling {out.name} plus {money(bank)} in the bank. Tick up to three players to compare them with {out.name}.</p>
      {compare.length > 0 && <CompareTable data={data} gw={gw} players={[out, ...compare.map((id) => byId.get(id)).filter((p): p is PlannerPlayer => Boolean(p))]} onPick={onPick} budget={budget} outId={out.id} onClear={() => setCompare([])} />}
      <div className="pl-pick-tools">
        <input className="aero-input" placeholder="Search players or clubs" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search players" />
        <select className="aero-select" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort by">
          <option value="projected">Projected, GW{gw}–{lastGw}</option><option value="form">Form</option><option value="points">Points</option><option value="price">Price</option><option value="rising">Closest to a price rise</option>
        </select>
      </div>
      <ul className="pl-pick-list">
        {rows.map((p) => {
          const club = (counts.get(p.team) ?? 0) - (p.team === out.team ? 1 : 0);
          const reason = p.price > budget ? `${money(p.price - budget)} short` : club >= MAX_PER_CLUB ? `Already ${MAX_PER_CLUB} from ${p.teamShort}` : null;
          const rot = rotationNote(data, p.id);
          return (
            <li key={p.id} className="pl-pick-item">
              <input type="checkbox" aria-label={`Compare ${p.name}`} checked={compare.includes(p.id)} onChange={() => toggle(p.id)} disabled={!compare.includes(p.id) && compare.length >= 3} />
              <button type="button" disabled={!!reason} onClick={() => onPick(p)}>
                <Crest team={p.team} />
                <span className="nm"><b>{p.name}</b><WatchStar id={p.id} name={p.name} size={14} />{p.status !== "a" && <span className={`pl-status s-${p.status}`} title={p.news}>{p.chance != null ? `${p.chance}%` : "Flag"}</span>}<small>{p.teamShort} · {money(p.price)} · {sum6(data, p.id, gw).toFixed(1)} projected · form {p.form.toFixed(1)}{rot?.risky ? ` · ${rot.text}` : ""} <PriceChangeBadge athleteId={p.id} /></small></span>
                <FixtureStrip data={data} team={p.team} from={gw} count={3} />
                <span className="why">{reason ?? "Buy"}</span>
              </button>
            </li>
          );
        })}
        {rows.length === 0 && <li className="mp-note">No players match.</li>}
      </ul>
    </section>
  );
}

function CompareTable({ data, gw, players, onPick, budget, outId, onClear }: {
  data: PlannerData; gw: number; players: PlannerPlayer[]; onPick: (p: PlannerPlayer) => void; budget: number; outId: number; onClear: () => void;
}) {
  const prices = usePriceChanges();
  const rows: [string, (p: PlannerPlayer) => string][] = [
    ["Price", (p) => money(p.price)],
    [`Projected, GW${gw}`, (p) => projected(data, p.id, gw)?.toFixed(1) ?? "–"],
    ["Projected, to the end of the plan", (p) => sum6(data, p.id, gw).toFixed(1)],
    ["Points this season", (p) => String(p.points)],
    ["Form", (p) => p.form.toFixed(1)],
    ["Starts, recent games", (p) => { const r = data.rotation[String(p.id)]; return r?.clubGames ? `${r.starts} of ${r.clubGames}` : "–"; }],
    ["Price move", (p) => { const d = direction(prices?.byId.get(p.id) ?? null); return d === "rise" ? "Likely to rise" : d === "drop" ? "Likely to drop" : "None expected"; }],
    ["Owned by", (p) => `${p.ownership.toFixed(1)}%`],
  ];
  return (
    <div className="pl-compare">
      <div className="pl-compare-head"><b>Side by side</b><button type="button" className="pl-x" onClick={onClear}>Clear</button></div>
      <div className="pl-compare-scroll">
        <table>
          <thead><tr><th scope="col"><span className="sr-only">Stat</span></th>{players.map((p) => <th key={p.id} scope="col"><Link to={`/players/${p.id}`}>{p.name}</Link><small>{p.id === outId ? "selling" : p.teamShort}</small></th>)}</tr></thead>
          <tbody>
            {rows.map(([label, f]) => <tr key={label}><th scope="row">{label}</th>{players.map((p) => <td key={p.id}>{f(p)}</td>)}</tr>)}
            <tr><th scope="row">Next three</th>{players.map((p) => <td key={p.id}><FixtureStrip data={data} team={p.team} from={gw} count={3} /></td>)}</tr>
            <tr><th scope="row"><span className="sr-only">Action</span></th>{players.map((p) => <td key={p.id}>{p.id !== outId && <button type="button" className="pl-sell" disabled={p.price > budget} onClick={() => onPick(p)}>{p.price > budget ? "Too dear" : "Buy"}</button>}</td>)}</tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Optimizer suggestions, loaded into a free plan so they never overwrite yours.
function Suggest({ data, plan, freeSlot, onPlan }: { data: PlannerData; plan: Plan; freeSlot?: string; onPlan: (name: string, p: Plan) => void }) {
  const [state, setState] = useState<"idle" | "busy" | "error" | "none">("idle");
  const run = async () => {
    if (!freeSlot) return;
    setState("busy");
    try {
      // Three weeks ahead where the forecast reaches; one week if it can't solve that.
      let r: Response | null = null;
      for (const horizon of [3, 1]) {
        r = await fetch(`/api/optimize-team/?manager_id=${data.managerId}&horizon=${horizon}&free_transfers=${plan.freeTransfers ?? data.freeTransfers}`);
        if (r.ok) break;
      }
      if (!r || !r.ok) throw new Error();
      const body = await r.json() as { gameweeks: { gameweek: number; transfers: { in: { id: number; position: string; now_cost: number }[]; out: { id: number; position: string }[] } }[] };
      const draft: Plan = { name: `Plan ${freeSlot}`, transfers: [] };
      for (const w of body.gameweeks ?? []) {
        const ins = [...w.transfers.in];
        for (const o of w.transfers.out) {
          const k = ins.findIndex((i) => i.position === o.position);
          if (k < 0) continue;
          const i = ins.splice(k, 1)[0];
          const holding = squadAt(data, draft, w.gameweek).find((h) => h.id === o.id);
          if (!holding) continue;
          draft.transfers.push({ gw: w.gameweek, out: o.id, in: i.id, sell: holding.selling, buy: i.now_cost });
        }
      }
      if (!draft.transfers.length) { setState("none"); return; }
      onPlan(freeSlot, draft);
      track("Optimizer Plan Loaded");
      setState("idle");
    } catch {
      setState("error");
    }
  };
  return (
    <div className="pl-suggest">
      <dt>Optimiser</dt>
      <dd>
        <button type="button" className="pl-ghost-btn" onClick={run} disabled={!freeSlot || state === "busy"} title={freeSlot ? `Loads into Plan ${freeSlot}` : "Clear a plan first: suggestions go into a free plan"}>
          {state === "busy" ? "Working it out…" : "Suggest transfers"}
        </button>
        {state === "error" && <small className="neg">The optimiser couldn't finish. Try again.</small>}
        {state === "none" && <small>It suggests no transfers: rolling your free transfer is best.</small>}
      </dd>
    </div>
  );
}

interface LeagueRow { id: number; name: string; team: string; owners: number; share: number }
interface LeagueView {
  league: { id: number; name: string }; gameweek: number; rivals: number;
  managers: { entry: number; manager: string; team: string; rank: number; total: number; gw: number }[];
  theyHave: LeagueRow[]; onlyYou: LeagueRow[]; captains: LeagueRow[];
}

function MiniLeagues({ managerId }: { managerId: number }) {
  const [leagues, setLeagues] = useState<{ id: number; name: string; rank: number | null }[] | null>(null);
  const [league, setLeague] = useState<number | null>(null);
  const [view, setView] = useState<LeagueView | null>(null);
  const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  const pick = (id: number) => {
    setLeague(id); setView(null); setState("busy");
    fetch(`/api/planner/league/${id}/?manager=${managerId}`).then((r) => (r.ok ? r.json() : Promise.reject())).then((d) => { setView(d); setState("idle"); track("Mini-league Viewed"); })
      .catch(() => setState("error"));
  };
  const open = () => {
    setState("busy");
    fetch(`/api/planner/${managerId}/leagues/`).then((r) => r.json()).then((d) => { setLeagues(d.leagues ?? []); setState("idle"); if (d.leagues?.[0]) pick(d.leagues[0].id); })
      .catch(() => setState("error"));
  };
  return (
    <section className="pl-league">
      <div className="mp-sec-title"><div><h2>Your mini-leagues</h2><p>What your rivals own that you don't, what only you have, and who they captained this gameweek.</p></div></div>
      {!leagues && <button type="button" className="aero-button" onClick={open} disabled={state === "busy"}>{state === "busy" ? "Loading…" : "Show my mini-leagues"}</button>}
      {state === "error" && <p className="mp-note">That couldn't be loaded from FPL. Try again in a minute.</p>}
      {leagues && leagues.length === 0 && <p className="mp-note">You're not in any private mini-leagues.</p>}
      {leagues && leagues.length > 0 && (
        <div className="pl-league-tools"><select className="aero-select" value={league ?? ""} onChange={(e) => pick(Number(e.target.value))} aria-label="Mini-league">
          {leagues.map((l) => <option key={l.id} value={l.id}>{l.name}{l.rank ? ` (you're ${l.rank})` : ""}</option>)}
        </select></div>
      )}
      {league && !view && state === "busy" && <div className="mp-skeleton" aria-busy="true" />}
      {view && (
        <div className="pl-league-grid">
          <div className="mp-sheet tp-squad pl-league-table">
            <table>
              <thead><tr><th scope="col">#</th><th scope="col">Team</th><th scope="col" className="n">GW{view.gameweek}</th><th scope="col" className="n">Total</th></tr></thead>
              <tbody>{view.managers.map((m) => <tr key={m.entry} className={m.entry === managerId ? "me" : ""}><td>{m.rank}</td><th scope="row">{m.team}<small> {m.manager}</small></th><td className="n">{m.gw}</td><td className="n">{m.total}</td></tr>)}</tbody>
            </table>
            {view.managers.length >= 20 && <p className="mp-note">The top 20 only.</p>}
          </div>
          <LeagueList title={`Your rivals own, you don't (of ${view.rivals})`} rows={view.theyHave} empty="Nothing: you own all their popular picks." />
          <LeagueList title="Only you (or few rivals) own" rows={view.onlyYou} empty="No differentials: your squad looks like theirs." />
          <LeagueList title={`Their captains, GW${view.gameweek}`} rows={view.captains} empty="No captains found." />
        </div>
      )}
    </section>
  );
}

function LeagueList({ title, rows, empty }: { title: string; rows: LeagueRow[]; empty: string }) {
  return (
    <div className="mp-sheet pl-league-list">
      <h3>{title}</h3>
      {rows.length === 0 ? <p className="mp-note">{empty}</p> : (
        <ul>{rows.map((r) => <li key={r.id}><Link to={`/players/${r.id}`}>{r.name}</Link><small>{r.team}</small><span className="bar" aria-hidden="true"><i style={{ width: `${r.share}%` }} /></span><b>{r.share}%</b></li>)}</ul>
      )}
    </div>
  );
}

function SyncPanel({ code, managerId, stored, onLinked, onUnlinked, onPulled }: {
  code: string | null; managerId: number; stored: Stored; onLinked: (c: string) => void; onUnlinked: () => void; onPulled: (s: Stored) => void;
}) {
  const [entry, setEntry] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const create = async () => {
    const r = await fetch("/api/planner/sync/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ managerId, plans: stored, watchlist: readWatchlist() }) });
    if (!r.ok) { setMsg("Couldn't create a code. Try again."); return; }
    const d = await r.json(); onLinked(d.code); setMsg(null); track("Planner Sync Created");
  };
  const join = async () => {
    const r = await fetch(`/api/planner/sync/${entry.trim().toLowerCase()}/`);
    if (!r.ok) { setMsg("No plans under that code."); return; }
    const d = await r.json();
    if (d.managerId && d.managerId !== managerId) { setMsg(`That code holds plans for manager ${d.managerId}. Load that team first.`); return; }
    mergeRemoteWatchlist(d.watchlist, d.code);
    onLinked(d.code);
    if (d.plans?.plans) { onPulled(d.plans as Stored); setMsg("Plans loaded from your other device."); return; }
    // A code made on the Watchlist page holds no plans yet: send this device's.
    fetch(`/api/planner/sync/${d.code}/`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ managerId, plans: stored }) }).catch(() => undefined);
    setMsg("Synced. Your plans now save under this code too.");
  };
  return (
    <section className="mp-sheet pl-sync">
      {code ? (
        <>
          <p>Your plans and watchlist sync under this code. Enter it in the planner or on the Watchlist page on another device to open them there.</p>
          <div className="pl-code"><b>{code}</b><button type="button" className="pl-x" onClick={() => navigator.clipboard?.writeText(code).then(() => setMsg("Copied."))}>Copy</button><button type="button" className="pl-x" onClick={onUnlinked}>Stop syncing here</button></div>
        </>
      ) : (
        <>
          <p>No account needed: create a code, then enter it on your phone or laptop to open the same plans and watchlist. Anyone with the code can see and change them, so keep it to yourself.</p>
          <div className="pl-code">
            <button type="button" className="aero-button primary" onClick={create}>Create a sync code</button>
            <span>or</span>
            <input className="aero-input" placeholder="Enter a code" value={entry} onChange={(e) => setEntry(e.target.value)} aria-label="Sync code" />
            <button type="button" className="aero-button" onClick={join} disabled={entry.trim().length < 6}>Use code</button>
          </div>
        </>
      )}
      {msg && <p className="mp-note">{msg}</p>}
    </section>
  );
}

// Before a team is loaded: open plans from another device by their code.
function SyncLoad({ onLoaded }: { onLoaded: (code: string, d: { managerId: number | null; plans: Stored; watchlist: number[] | null }) => void }) {
  const [entry, setEntry] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const go = async (e: FormEvent) => {
    e.preventDefault();
    const r = await fetch(`/api/planner/sync/${entry.trim().toLowerCase()}/`);
    if (!r.ok) { setMsg("No plans under that code."); return; }
    const d = await r.json();
    onLoaded(d.code, { managerId: d.managerId, plans: d.plans, watchlist: d.watchlist });
  };
  return (
    <form className="pl-import pl-syncload" onSubmit={go}>
      <label htmlFor="pl-sync">Have a sync code?</label>
      <input id="pl-sync" className="aero-input" placeholder="e.g. k7m2p9qx3d" value={entry} onChange={(e) => setEntry(e.target.value)} />
      <button type="submit" className="aero-button" disabled={entry.trim().length < 6}>Open my plans</button>
      {msg && <span className="mp-note">{msg}</span>}
    </form>
  );
}

interface Check { level: "bad" | "warn" | "tip"; text: string }

const names = (ps: (PlannerPlayer | undefined)[]) => {
  const n = ps.filter(Boolean).map((p) => p!.name);
  return n.length <= 3 ? n.join(", ") : `${n.slice(0, 3).join(", ")} and ${n.length - 3} more`;
};

// Plain-language checks on the whole plan: rules first, then blanks and
// doubles, chips, price timing (FPL's own tracker), then who may not play.
function planChecks(data: PlannerData, plan: Plan, weeks: WeekSummary[], byId: Map<number, PlannerPlayer>, prices: PriceChangeData | null, gw: number): Check[] {
  const out: Check[] = [];
  for (const w of weeks) {
    if (w.overBudget) out.push({ level: "bad", text: `GW${w.gw}: you'd be ${money(-w.bankAfter)} over budget.` });
    for (const c of w.clubsOver) out.push({ level: "bad", text: `GW${w.gw}: more than ${MAX_PER_CLUB} players from ${c}.` });
    if (w.hits) out.push({ level: "warn", text: `GW${w.gw}: ${w.hits} transfer${w.hits === 1 ? "" : "s"} beyond your free ones cost ${w.cost} points.` });
    const ids = squadAt(data, plan, w.gw).map((h) => h.id);
    const blank = ids.filter((id) => gamesIn(data, byId.get(id)?.team ?? "", w.gw) === 0).map((id) => byId.get(id));
    const double = ids.filter((id) => gamesIn(data, byId.get(id)?.team ?? "", w.gw) > 1).map((id) => byId.get(id));
    if (blank.length >= 3) out.push({ level: "warn", text: `GW${w.gw}: ${blank.length} of your players have no league game (${names(blank)}).${w.chip === "freehit" ? "" : " A Free Hit week?"}` });
    else if (blank.length) out.push({ level: "tip", text: `GW${w.gw}: ${names(blank)} ${blank.length === 1 ? "has" : "have"} no league game.` });
    if (double.length >= 3 && !w.chip) out.push({ level: "tip", text: `GW${w.gw}: ${double.length} of your players play twice (${names(double)}). A Bench Boost or Triple Captain week?` });
    if (w.chip === "bboost") {
      const best = bestXI(data, ids, byId, w.gw);
      const weak = best.bench.map((id) => byId.get(id)).filter((p) => p && (p.status !== "a" || gamesIn(data, p.team, w.gw) === 0));
      if (weak.length) out.push({ level: "warn", text: `GW${w.gw} Bench Boost: ${names(weak)} on your bench may not play.` });
    }
  }
  const next = data.nextGameweek;
  if (data.priceForecast) {
    const soon = plan.transfers.filter((t) => t.gw > next && data.priceForecast!.chances[String(t.in)] != null && direction(prices?.byId.get(t.in) ?? null) !== "rise");
    for (const t of soon) {
      const p = byId.get(t.in);
      if (p) out.push({ level: "tip", text: `${p.name} may rise within a week (AeroFPL forecast, right ${Math.round(data.priceForecast.record.precision * 100)}% of the time in testing): buying before GW${t.gw} could save money.` });
    }
  }
  for (const t of plan.transfers) {
    const dirIn = direction(prices?.byId.get(t.in) ?? null), dirOut = direction(prices?.byId.get(t.out) ?? null);
    const pin = byId.get(t.in), pout = byId.get(t.out);
    if (dirIn === "rise" && pin) out.push({ level: "tip", text: `${pin.name} is likely to rise in price soon${t.gw > next ? `: buying in GW${next} instead of GW${t.gw} would save money` : ": buy before the next price update"}.` });
    if (dirOut === "drop" && pout) out.push({ level: "tip", text: `${pout.name} is likely to drop in price soon${t.gw > next ? `: selling in GW${next} rather than GW${t.gw} keeps more value` : ": sell before the next price update"}.` });
  }
  for (const h of squadAt(data, plan, gw)) {
    const p = byId.get(h.id);
    if (!p) continue;
    if (p.status !== "a") out.push({ level: "warn", text: `${p.name}: ${p.news || "flagged by FPL"}.` });
    const rot = rotationNote(data, p.id);
    if (rot?.risky && p.status === "a" && bestXI(data, squadAt(data, plan, gw).map((x) => x.id), byId, gw).xi.includes(p.id)) out.push({ level: "warn", text: `${p.name} ${rot.text}: a rotation risk.` });
    if (direction(prices?.byId.get(p.id) ?? null) === "drop" && !plan.transfers.some((t) => t.out === p.id)) out.push({ level: "tip", text: `${p.name} (in your GW${gw} squad) is likely to drop in price.` });
  }
  return out;
}
