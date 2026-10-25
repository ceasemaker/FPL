import { track } from "@amplitude/unified";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Crest } from "../components/match/icons";
import {
  HIT, MAX_PER_CLUB, money, squadAt, summarise,
  type Plan, type PlannerData, type PlannerPlayer, type Transfer, type WeekSummary,
} from "../components/planner/planModel";
import { PriceChangeBadge } from "../components/priceChange/PriceChange";
import { direction, usePriceChanges, type PriceChangeData } from "../hooks/usePriceChanges";
import "./MatchPage.css";
import "./PlannerPage.css";

// Transfer planner (/planner): import a squad by FPL manager ID, plan transfers
// over the next six gameweeks with bank, free transfers and hits tallied, see
// every player's fixtures (with cup and European games in between) and FPL's
// own price-change flags. Plans are saved in this browser.

const PLAN_NAMES = ["A", "B", "C"];
const ORDER: Record<string, number> = { GKP: 0, DEF: 1, MID: 2, FWD: 3 };
const POS_WORD: Record<string, string> = { GKP: "Goalkeepers", DEF: "Defenders", MID: "Midfielders", FWD: "Forwards" };
const storeKey = (id: number) => `aerofpl_planner_v1_${id}`;
interface Stored { active: string; plans: Record<string, Plan> }

function readPlans(id: number): Stored {
  try {
    const raw = localStorage.getItem(storeKey(id));
    if (raw) return JSON.parse(raw) as Stored;
  } catch { /* private window or bad data: start fresh */ }
  return { active: "A", plans: { A: { name: "Plan A", transfers: [] } } };
}
function writePlans(id: number, s: Stored) {
  try { localStorage.setItem(storeKey(id), JSON.stringify(s)); } catch { /* storage blocked: plans last this visit */ }
}

export function PlannerPage() {
  const [params, setParams] = useSearchParams();
  const initialId = params.get("manager") ?? (() => { try { return localStorage.getItem("fpl_manager_id") ?? ""; } catch { return ""; } })();
  const [draft, setDraft] = useState(initialId);
  const [managerId, setManagerId] = useState<number | null>(initialId && /^\d+$/.test(initialId) ? Number(initialId) : null);
  const [data, setData] = useState<PlannerData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stored, setStored] = useState<Stored | null>(null);
  const [gw, setGw] = useState<number | null>(null);
  const [selling, setSelling] = useState<number | null>(null);
  const prices = usePriceChanges();

  useEffect(() => { document.title = "Transfer planner · AeroFPL"; }, []);
  // On narrow screens the replacement list sits below the squad: bring it into view.
  useEffect(() => {
    if (selling != null && window.innerWidth < 1100) document.querySelector(".pl-pick")?.scrollIntoView({ block: "start" });
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
        try { localStorage.setItem("fpl_manager_id", String(d.managerId)); } catch { /* ignore */ }
        track("Planner Team Imported");
      })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [managerId]);

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

  const savePlan = (p: Plan) => {
    if (!data || !stored) return;
    const next = { ...stored, plans: { ...stored.plans, [stored.active]: p } };
    setStored(next); writePlans(data.managerId, next);
  };
  const switchPlan = (name: string) => {
    if (!data || !stored) return;
    const next = { active: name, plans: { ...stored.plans, [name]: stored.plans[name] ?? { name: `Plan ${name}`, transfers: [] } } };
    setStored(next); writePlans(data.managerId, next);
  };
  const copyPlan = () => {
    if (!data || !stored || !plan) return;
    const free = PLAN_NAMES.find((n) => !stored.plans[n]);
    if (!free) return;
    const next = { active: free, plans: { ...stored.plans, [free]: { ...plan, name: `Plan ${free}` } } };
    setStored(next); writePlans(data.managerId, next);
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

  if (!data || !plan || gw == null) {
    return (
      <main className="aero-page mp-page pl-page">
        <header className="pl-head"><div><h1>Transfer planner</h1><p>Load your FPL team, plan transfers for the next six gameweeks, and see who's about to change price.</p></div></header>
        <ImportForm draft={draft} setDraft={setDraft} onSubmit={load} loading={loading} />
        {error && <p className="mp-error" role="alert">{error}</p>}
        {loading && <div className="mp-skeleton tall" aria-busy="true" />}
        {!loading && !error && <p className="pl-help">Your manager ID is the number in the address of your team's Points page on the FPL site: fantasy.premierleague.com/entry/<b>576154</b>/event/8. No login needed.</p>}
      </main>
    );
  }

  const week: WeekSummary | undefined = weeks.find((w) => w.gw === gw) ?? weeks[0];
  const squad = squadAt(data, plan, gw).map((h) => ({ ...h, p: byId.get(h.id) })).filter((h) => h.p)
    .sort((a, b) => ORDER[a.p!.position] - ORDER[b.p!.position] || b.p!.price - a.p!.price);
  const totalHits = weeks.reduce((s, w) => s + w.cost, 0);
  const checks = planChecks(data, plan, weeks, byId, prices, gw);

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
          <button type="button" className="pl-ghost" onClick={copyPlan} disabled={PLAN_NAMES.every((n) => stored!.plans[n])}>Copy to a new plan</button>
        </div>
      </header>

      <section className="pl-facts" aria-label="Team facts">
        <div><dt>Bank</dt><dd>{money(plan.bank ?? data.bank)}</dd></div>
        <div>
          <dt>Free transfers for GW{data.nextGameweek} <span title="Worked out from your history; FPL doesn't publish it. Correct it if it's wrong.">(estimate)</span></dt>
          <dd className="pl-step">
            <button type="button" aria-label="One fewer" onClick={() => savePlan({ ...plan, freeTransfers: Math.max(0, (plan.freeTransfers ?? data.freeTransfers) - 1) })}>−</button>
            {plan.freeTransfers ?? data.freeTransfers}
            <button type="button" aria-label="One more" onClick={() => savePlan({ ...plan, freeTransfers: Math.min(5, (plan.freeTransfers ?? data.freeTransfers) + 1) })}>+</button>
          </dd>
        </div>
        <div><dt>Team value</dt><dd>{data.teamValue != null ? money(data.teamValue) : "–"}</dd></div>
        <div><dt>Chips left this half</dt><dd className="pl-chips">{data.chips.filter((c) => c.available).map((c) => <span key={c.key}>{c.name}</span>)}{data.chips.every((c) => !c.available) && "None"}</dd></div>
        <div><dt>Hits in this plan</dt><dd className={totalHits ? "neg" : ""}>{totalHits ? `−${totalHits} pts` : "None"}</dd></div>
      </section>

      <nav className="pl-weeks" aria-label="Gameweeks">
        {weeks.map((w) => (
          <button key={w.gw} type="button" aria-pressed={w.gw === gw} onClick={() => { setGw(w.gw); setSelling(null); }}
            className={w.overBudget || w.clubsOver.length ? "bad" : ""}>
            <b>GW{w.gw}</b>
            <small>{w.transfers.length ? `${w.transfers.length} transfer${w.transfers.length === 1 ? "" : "s"}${w.hits ? ` · −${w.cost}` : ""}` : `${w.free} free`}</small>
          </button>
        ))}
      </nav>

      <div className="pl-grid">
        <section className="mp-sheet pl-squad" aria-label={`Squad for gameweek ${gw}`}>
          <div className="pl-squad-head">
            <span>Your squad for GW{gw}</span>
            <span className="pl-fx-head">{data.gameweeks.map((g) => <b key={g.gameweek} className={g.gameweek === gw ? "on" : ""}>GW{g.gameweek}</b>)}</span>
          </div>
          {(["GKP", "DEF", "MID", "FWD"] as const).map((pos) => (
            <div key={pos} className="pl-pos">
              <h3>{POS_WORD[pos]}</h3>
              {squad.filter((h) => h.p!.position === pos).map((h) => (
                <SquadRow key={h.id} player={h.p!} selling={h.selling} data={data} gw={gw}
                  isNew={plan.transfers.some((t) => t.in === h.id && t.gw <= gw)}
                  active={selling === h.id} onSell={() => setSelling(selling === h.id ? null : h.id)} />
              ))}
            </div>
          ))}
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
                <h2>GW{gw}</h2>
                {week && week.transfers.length === 0 && <p className="mp-note">No transfers planned. Choose Sell on a player to plan one.</p>}
                {week?.transfers.map((t, i) => (
                  <div key={i} className="pl-move">
                    <span className="out">{byId.get(t.out)?.name}<small>{money(t.sell)}</small></span>
                    <svg width="14" height="14" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11m-4-4 4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    <span className="in">{byId.get(t.in)?.name}<small>{money(t.buy)}</small></span>
                    <button type="button" className="pl-x" aria-label="Undo this transfer" onClick={() => removeTransfer(t)}>Undo</button>
                  </div>
                ))}
                {week && (
                  <dl className="pl-tally">
                    <div><dt>Free transfers</dt><dd>{week.free}</dd></div>
                    <div><dt>Hits</dt><dd className={week.cost ? "neg" : ""}>{week.cost ? `−${week.cost} pts (${week.hits} × ${HIT})` : "None"}</dd></div>
                    <div><dt>Bank after</dt><dd className={week.overBudget ? "neg" : ""}>{money(week.bankAfter)}</dd></div>
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
      <p className="mp-foot">Squad, bank and chips from FPL; free transfers worked out from your history. Selling prices follow FPL's rule (you keep half of any rise). Price flags are FPL's own tracker, about two days ahead. Plans are saved in this browser only.</p>
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

function SquadRow({ player, selling, data, gw, isNew, active, onSell }: {
  player: PlannerPlayer; selling: number; data: PlannerData; gw: number; isNew: boolean; active: boolean; onSell: () => void;
}) {
  const flagged = player.status !== "a";
  return (
    <div className={`pl-row${active ? " active" : ""}${isNew ? " new" : ""}`}>
      <Crest team={player.team} />
      <span className="nm">
        <Link to={`/players/${player.id}`}>{player.name}</Link>
        {flagged && <span className={`pl-status s-${player.status}`} title={player.news || "Flagged"}>{player.chance != null ? `${player.chance}%` : player.status === "i" ? "Injured" : player.status === "s" ? "Suspended" : "Doubt"}</span>}
        {isNew && <span className="pl-new">New</span>}
        <small>{player.teamShort} · {money(player.price)}{selling !== player.price ? ` · sells for ${money(selling)}` : ""} <PriceChangeBadge athleteId={player.id} /></small>
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
  const [sort, setSort] = useState<"form" | "points" | "price" | "rising">("form");
  const prices = usePriceChanges();
  const budget = bank + selling;
  const rows = data.players
    .filter((p) => p.position === out.position && !squadIds.has(p.id))
    .filter((p) => !q || `${p.name} ${p.fullName} ${p.teamShort}`.toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => sort === "price" ? b.price - a.price : sort === "points" ? b.points - a.points
      : sort === "rising" ? (prices?.byId.get(b.id)?.progress ?? -999) - (prices?.byId.get(a.id)?.progress ?? -999)
      : b.form - a.form)
    .slice(0, 60);
  return (
    <section className="mp-sheet pl-pick" aria-label={`Replace ${out.name}`}>
      <div className="pl-pick-head">
        <h2>Replace {out.name}</h2>
        <button type="button" className="pl-x" onClick={onClose}>Close</button>
      </div>
      <p className="mp-note">Up to {money(budget)} to spend in GW{gw}: {money(selling)} from selling {out.name} plus {money(bank)} in the bank.</p>
      <div className="pl-pick-tools">
        <input className="aero-input" placeholder="Search players or clubs" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search players" />
        <select className="aero-select" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort by">
          <option value="form">Form</option><option value="points">Points</option><option value="price">Price</option><option value="rising">Closest to a price rise</option>
        </select>
      </div>
      <ul className="pl-pick-list">
        {rows.map((p) => {
          const club = (counts.get(p.team) ?? 0) - (p.team === out.team ? 1 : 0);
          const reason = p.price > budget ? `${money(p.price - budget)} short` : club >= MAX_PER_CLUB ? `Already ${MAX_PER_CLUB} from ${p.teamShort}` : null;
          return (
            <li key={p.id}>
              <button type="button" disabled={!!reason} onClick={() => onPick(p)}>
                <Crest team={p.team} />
                <span className="nm"><b>{p.name}</b>{p.status !== "a" && <span className={`pl-status s-${p.status}`} title={p.news}>{p.chance != null ? `${p.chance}%` : "Flag"}</span>}<small>{p.teamShort} · {money(p.price)} · form {p.form.toFixed(1)} · {p.points} pts <PriceChangeBadge athleteId={p.id} /></small></span>
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

interface Check { level: "bad" | "warn" | "tip"; text: string }

// Plain-language checks on the whole plan: rules first, then price timing
// (from FPL's own tracker), then players who may not play.
function planChecks(data: PlannerData, plan: Plan, weeks: WeekSummary[], byId: Map<number, PlannerPlayer>, prices: PriceChangeData | null, gw: number): Check[] {
  const out: Check[] = [];
  for (const w of weeks) {
    if (w.overBudget) out.push({ level: "bad", text: `GW${w.gw}: you'd be ${money(-w.bankAfter)} over budget.` });
    for (const c of w.clubsOver) out.push({ level: "bad", text: `GW${w.gw}: more than ${MAX_PER_CLUB} players from ${c}.` });
    if (w.hits) out.push({ level: "warn", text: `GW${w.gw}: ${w.hits} transfer${w.hits === 1 ? "" : "s"} beyond your free ones cost ${w.cost} points.` });
  }
  const next = data.nextGameweek;
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
    if (direction(prices?.byId.get(p.id) ?? null) === "drop" && !plan.transfers.some((t) => t.out === p.id)) out.push({ level: "tip", text: `${p.name} (in your GW${gw} squad) is likely to drop in price.` });
  }
  return out;
}
