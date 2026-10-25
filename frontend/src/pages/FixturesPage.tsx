import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { usePriceChanges } from "../hooks/usePriceChanges";
import "./FixturesPage.css";
import "./MatchesPage.css";

// Fixture planner (/fixtures): every club's run of league fixtures, three ways.
// Ticker: difficulty, clean-sheet chance and projected goals per fixture, over
// 3–10 gameweeks anywhere in the season. Runs: each club's best and worst
// stretch. Rotation: pairs of clubs whose fixtures cover each other. Clean
// sheets and goals come from the AeroFPL fixture model, shown with its record.

interface Fixture {
  event: number; fixture_id?: number; opponent: string | null; location: "H" | "A"; difficulty: number | null;
  win_probability: number | null; odds_difficulty: number | null;
  clean_sheet: number | null; goals_for: number | null; goals_against: number | null;
}
interface TeamRow {
  team_id: number; team_name: string; team_short_name: string; fixtures: Fixture[]; avg_difficulty: number | null;
  expected_market_wins: number | null; probability_win_all: number | null; probability_at_least_one: number | null; market_fixture_count: number;
  expected_clean_sheets: number | null; expected_goals_for: number | null; expected_goals_against: number | null;
}
interface Side { model: number; rule: number; gain: number; low: number; high: number }
interface ModelRecord {
  matches: number; seasons: string[];
  cleanSheets: { vsLeagueAverage: Side; vsSeasonTable: Side }; goals: { vsLeagueAverage: Side; vsSeasonTable: Side };
  calibration: { band: string; predicted: number; actual: number; n: number }[];
}
interface FixtureMatrix {
  current_gameweek: number; start_gameweek: number; end_gameweek: number; horizon: number;
  model: { available: boolean; record: ModelRecord | null };
  market: { available: boolean; snapshot_date: string | null; source: string | null; priced_fixture_count: number; total_fixture_count: number; type: string; includes_clean_sheet_odds: boolean; note: string };
  teams: TeamRow[];
}
type Basis = "cs" | "goals" | "fdr" | "odds";
type View = "ticker" | "runs" | "rotation";

const BASES: [Basis, string][] = [["cs", "Clean sheet %"], ["goals", "Projected goals"], ["fdr", "FPL difficulty"], ["odds", "Win odds"]];
const HORIZONS = [3, 4, 5, 6, 8, 10];

// One number per club-gameweek: higher is better for the club (doubles add, blanks are 0).
function weekValue(fx: Fixture[], basis: Basis): number | null {
  if (!fx.length) return 0;
  if (basis === "cs") return fx.every((f) => f.clean_sheet == null) ? null : fx.reduce((s, f) => s + (f.clean_sheet ?? 0), 0);
  if (basis === "goals") return fx.every((f) => f.goals_for == null) ? null : fx.reduce((s, f) => s + (f.goals_for ?? 0), 0);
  if (basis === "odds") return fx.every((f) => f.win_probability == null) ? null : fx.reduce((s, f) => s + (f.win_probability ?? 0), 0);
  return fx.every((f) => f.difficulty == null) ? null : fx.reduce((s, f) => s + (6 - (f.difficulty ?? 3)), 0);
}

// Colour band 1 (best) .. 5 (worst) for one fixture.
function band(f: Fixture, basis: Basis): number {
  if (basis === "fdr") return f.difficulty ?? 0;
  if (basis === "odds") return f.odds_difficulty ?? 0;
  if (basis === "cs") { const v = f.clean_sheet; return v == null ? 0 : v >= 0.45 ? 1 : v >= 0.35 ? 2 : v >= 0.27 ? 3 : v >= 0.2 ? 4 : 5; }
  const v = f.goals_for; return v == null ? 0 : v >= 2.0 ? 1 : v >= 1.6 ? 2 : v >= 1.3 ? 3 : v >= 1.0 ? 4 : 5;
}

function cellText(f: Fixture, basis: Basis): string {
  if (basis === "cs") return f.clean_sheet == null ? "–" : `${Math.round(f.clean_sheet * 100)}%`;
  if (basis === "goals") return f.goals_for == null ? "–" : f.goals_for.toFixed(1);
  if (basis === "odds") return f.win_probability == null ? `FDR ${f.difficulty ?? "–"}` : `${Math.round(f.win_probability * 100)}% win`;
  return `FDR ${f.difficulty ?? "–"}`;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

export function FixturesPage() {
  const [params, setParams] = useSearchParams();
  const view = (params.get("view") ?? "ticker") as View;
  const basis = (params.get("basis") ?? "cs") as Basis;
  const horizon = Number(params.get("weeks") ?? 6);
  const startParam = params.get("from");
  const [data, setData] = useState<FixtureMatrix | null>(null);
  const [season, setSeason] = useState<FixtureMatrix | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<"best" | "worst" | "az" | number>("best");
  const [hidden, setHidden] = useState<Set<number>>(new Set());
  const [partner, setPartner] = useState<number | null>(null);
  const set = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (v == null) next.delete(k); else next.set(k, v); }
    setParams(next, { replace: true });
  };

  useEffect(() => { document.title = "Fixture planner · AeroFPL"; }, []);
  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    fetch(`/api/fixtures/ticker/?horizon=${horizon}${startParam ? `&start=${startParam}` : ""}`, { signal: controller.signal })
      .then(async (r) => { const body = await r.json(); if (!r.ok) throw new Error(body.error || "Fixtures could not be loaded."); return body as FixtureMatrix; })
      .then(setData)
      .catch((e) => { if (e.name !== "AbortError") setError(e.message); });
    return () => controller.abort();
  }, [horizon, startParam]);
  // The rest of the season, for runs and rotation.
  useEffect(() => {
    if (view === "ticker" || season) return;
    fetch("/api/fixtures/ticker/?horizon=38").then((r) => r.json()).then(setSeason).catch(() => undefined);
  }, [view, season]);

  const modelOn = !!data?.model.available;
  const effectiveBasis: Basis = !modelOn && (basis === "cs" || basis === "goals") ? "fdr" : basis;
  const gameweeks = data ? Array.from({ length: data.horizon }, (_, i) => data.start_gameweek + i) : [];

  const rows = useMemo(() => {
    if (!data) return [];
    const score = (t: TeamRow, gws: number[]) => gws.reduce((s, g) => s + (weekValue(t.fixtures.filter((f) => f.event === g), effectiveBasis) ?? 0), 0);
    const visible = data.teams.filter((t) => !hidden.has(t.team_id));
    if (partner != null) {
      const anchor = data.teams.find((t) => t.team_id === partner);
      if (anchor) {
        const pairScore = (t: TeamRow) => gameweeks.reduce((s, g) => s + Math.max(
          weekValue(anchor.fixtures.filter((f) => f.event === g), effectiveBasis) ?? 0,
          weekValue(t.fixtures.filter((f) => f.event === g), effectiveBasis) ?? 0), 0);
        return [anchor, ...visible.filter((t) => t.team_id !== partner).sort((a, b) => pairScore(b) - pairScore(a))];
      }
    }
    if (sort === "az") return [...visible].sort((a, b) => a.team_name.localeCompare(b.team_name));
    if (typeof sort === "number") return [...visible].sort((a, b) => score(b, [sort]) - score(a, [sort]));
    const s = [...visible].sort((a, b) => score(b, gameweeks) - score(a, gameweeks));
    return sort === "worst" ? s.reverse() : s;
  }, [data, sort, effectiveBasis, hidden, partner, gameweeks.join()]);

  const total = (t: TeamRow) => {
    if (effectiveBasis === "cs") return t.expected_clean_sheets == null ? "–" : t.expected_clean_sheets.toFixed(1);
    if (effectiveBasis === "goals") return t.expected_goals_for == null ? "–" : t.expected_goals_for.toFixed(1);
    if (effectiveBasis === "odds") return t.expected_market_wins == null ? "–" : t.expected_market_wins.toFixed(1);
    return t.avg_difficulty?.toFixed(1) ?? "–";
  };
  const totalLabel = effectiveBasis === "cs" ? "Clean sheets" : effectiveBasis === "goals" ? "Goals" : effectiveBasis === "odds" ? "Wins" : "Avg FDR";
  const start = data?.start_gameweek ?? 0;
  const first = data ? data.current_gameweek + 1 : 0;

  return (
    <main className="aero-page fx-page ms-page">
      <header className="ms-head">
        <div>
          <h1>Fixture planner</h1>
          <p>Every club's league fixtures: clean-sheet chances, projected goals and difficulty, the best and worst runs, and rotation pairs.</p>
        </div>
        <nav className="ms-switch" aria-label="Matches views"><Link to="/matches">Calendar</Link><span aria-current="page">Fixture planner</span></nav>
      </header>

      <div className="ms-tools">
        <div className="ms-seg" role="group" aria-label="View">
          {([["ticker", "Ticker"], ["runs", "Best & worst runs"], ["rotation", "Rotation pairs"]] as [View, string][]).map(([k, l]) =>
            <button key={k} type="button" aria-pressed={view === k} onClick={() => set({ view: k === "ticker" ? null : k })}>{l}</button>)}
        </div>
        <div className="ms-seg" role="group" aria-label="Measure">
          {BASES.filter(([k]) => modelOn || (k !== "cs" && k !== "goals")).map(([k, l]) =>
            <button key={k} type="button" aria-pressed={effectiveBasis === k} onClick={() => set({ basis: k })}>{l}</button>)}
        </div>
      </div>

      {error && <div className="ms-error" role="alert">{error}</div>}
      {!data && !error && <div className="ms-skeleton" aria-busy="true" />}

      {data && view === "ticker" && (
        <>
          <div className="ms-tools fx-window">
            <div className="ms-range" role="group" aria-label="Gameweeks">
              <button type="button" disabled={start <= first} onClick={() => set({ from: String(Math.max(first, start - 1)) })} aria-label="One gameweek earlier"><Chevron dir="left" /></button>
              <button type="button" className="today" onClick={() => set({ from: null })}>Next gameweek</button>
              <button type="button" disabled={data.end_gameweek >= 38} onClick={() => set({ from: String(start + 1) })} aria-label="One gameweek later"><Chevron dir="right" /></button>
              <span>GW{data.start_gameweek}–GW{data.end_gameweek}</span>
            </div>
            <label className="fx-label">Show
              <select className="aero-select" value={horizon} onChange={(e) => set({ weeks: e.target.value })}>{HORIZONS.map((h) => <option key={h} value={h}>{h} gameweeks</option>)}</select>
            </label>
            <label className="fx-label">Order
              <select className="aero-select" value={partner != null ? `p${partner}` : String(sort)} onChange={(e) => {
                const v = e.target.value;
                if (v.startsWith("p")) { setPartner(Number(v.slice(1))); return; }
                setPartner(null); setSort(v === "best" || v === "worst" || v === "az" ? v : Number(v));
              }}>
                <option value="best">Best run first</option><option value="worst">Toughest run first</option><option value="az">Club A–Z</option>
                <optgroup label="Best rotation partner for…">{data.teams.slice().sort((a, b) => a.team_name.localeCompare(b.team_name)).map((t) => <option key={t.team_id} value={`p${t.team_id}`}>{t.team_name}</option>)}</optgroup>
              </select>
            </label>
            {hidden.size > 0 && <button type="button" className="fx-reset" onClick={() => setHidden(new Set())}>Show {hidden.size} hidden club{hidden.size === 1 ? "" : "s"}</button>}
          </div>
          {partner != null && <p className="fx-note">Rotation partners for {data.teams.find((t) => t.team_id === partner)?.team_name}: ranked by the better of the two clubs each gameweek, added up.</p>}

          <section className="fx-grid-wrap" aria-label="Fixture ticker">
            <table className="fx-grid">
              <thead>
                <tr>
                  <th scope="col" className="club">Club</th>
                  {gameweeks.map((g) => <th key={g} scope="col"><button type="button" className={sort === g ? "on" : ""} onClick={() => { setPartner(null); setSort(sort === g ? "best" : g); }} title={`Order by GW${g}`}>GW{g}</button></th>)}
                  <th scope="col" className="tot">{totalLabel}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((t) => (
                  <tr key={t.team_id} className={partner === t.team_id ? "anchor" : ""}>
                    <th scope="row" className="club">
                      <b>{t.team_short_name}</b><span>{t.team_name}</span>
                      <button type="button" className="fx-hide" aria-label={`Hide ${t.team_name}`} onClick={() => setHidden(new Set([...hidden, t.team_id]))}>×</button>
                    </th>
                    {gameweeks.map((g) => {
                      const fx = t.fixtures.filter((f) => f.event === g);
                      return (
                        <td key={g}>
                          {fx.length === 0 && <span className="fx-cell blank">Blank</span>}
                          {fx.map((f, i) => (
                            <Link key={i} to={f.fixture_id ? `/matches/fixture/${f.fixture_id}` : "#"} className={`fx-cell b-${band(f, effectiveBasis)}${fx.length > 1 ? " dbl" : ""}`}
                              title={`${t.team_short_name} ${f.location === "H" ? "v" : "at"} ${f.opponent}: FDR ${f.difficulty ?? "–"}${f.clean_sheet != null ? `, clean sheet ${pct(f.clean_sheet)}, projected ${f.goals_for?.toFixed(2)}–${f.goals_against?.toFixed(2)}` : ""}${f.win_probability != null ? `, ${pct(f.win_probability)} win` : ""}`}>
                              <strong>{f.location === "H" ? f.opponent : f.opponent?.toLowerCase()}</strong>
                              <small>{cellText(f, effectiveBasis)}</small>
                            </Link>
                          ))}
                        </td>
                      );
                    })}
                    <td className="tot">{total(t)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <Legend basis={effectiveBasis} />
          {modelOn && data.model.record && <ModelNote record={data.model.record} />}
          {effectiveBasis === "odds" && <p className="fx-note">{data.market.priced_fixture_count}/{data.market.total_fixture_count} fixtures priced ({data.market.type}). Odds are collected for the next few days only; unpriced fixtures show FPL's difficulty.</p>}
        </>
      )}

      {view === "runs" && (season ? <Runs data={season} basis={effectiveBasis} /> : <div className="ms-skeleton" aria-busy="true" />)}
      {view === "rotation" && (season ? <Rotation data={season} basis={effectiveBasis} /> : <div className="ms-skeleton" aria-busy="true" />)}
    </main>
  );
}

function Legend({ basis }: { basis: Basis }) {
  const labels = basis === "cs" ? ["45%+", "35–45%", "27–35%", "20–27%", "under 20%"] : basis === "goals" ? ["2.0+", "1.6–2.0", "1.3–1.6", "1.0–1.3", "under 1.0"] : ["1 easiest", "2", "3", "4", "5 hardest"];
  return (
    <div className="fx-legend">
      <span>{basis === "cs" ? "Chance of a clean sheet" : basis === "goals" ? "Projected goals scored" : basis === "odds" ? "Win chance (bookmakers)" : "FPL difficulty"}:</span>
      {labels.map((l, i) => <span key={l}><i className={`fx-swatch b-${i + 1}`} />{l}</span>)}
      <span>Capitals: home · lower case: away</span>
    </div>
  );
}

function ModelNote({ record }: { record: ModelRecord }) {
  const c = record.cleanSheets, g = record.goals;
  return (
    <details className="fx-model">
      <summary>Where clean sheets and projected goals come from</summary>
      <p>
        The AeroFPL fixture model rates every club's attack and defence from recent league matches (expected goals, with a little of actual goals), weighted towards recent games, then projects each fixture. Tested match by match on {record.matches.toLocaleString()} matches in {record.seasons.join(", ")}, using only games played before each kick-off, it beat the league average and a season-to-date table for both clean sheets
        (Brier score {c.vsLeagueAverage.model.toFixed(3)} against {c.vsLeagueAverage.rule.toFixed(3)} and {c.vsSeasonTable.rule.toFixed(3)}; lower is better) and goals.
      </p>
      <table>
        <thead><tr><th scope="col">Clean-sheet chance it gave</th><th scope="col">On average</th><th scope="col">How often it happened</th><th scope="col">Sides</th></tr></thead>
        <tbody>{record.calibration.map((b) => <tr key={b.band}><td>{b.band}</td><td>{pct(b.predicted)}</td><td>{pct(b.actual)}</td><td>{b.n}</td></tr>)}</tbody>
      </table>
      <p>Its highest chances run a little optimistic, so treat anything above about 45% as a strong rather than exact call. Goals for the projected-goals view use the same model.</p>
    </details>
  );
}

// Each club's best and worst stretch of N gameweeks in the rest of the season.
function Runs({ data, basis }: { data: FixtureMatrix; basis: Basis }) {
  const [length, setLength] = useState(4);
  const gws = Array.from({ length: data.horizon }, (_, i) => data.start_gameweek + i);
  const rows = data.teams.map((t) => {
    const per = gws.map((g) => weekValue(t.fixtures.filter((f) => f.event === g), basis) ?? 0);
    const windows = gws.slice(0, Math.max(0, gws.length - length + 1)).map((g, i) => ({ from: g, to: g + length - 1, score: per.slice(i, i + length).reduce((a, b) => a + b, 0) }));
    const best = windows.reduce((a, b) => (b.score > a.score ? b : a), windows[0]);
    const worst = windows.reduce((a, b) => (b.score < a.score ? b : a), windows[0]);
    const next = windows[0];
    return { t, best, worst, next };
  }).filter((r) => r.best).sort((a, b) => b.best.score - a.best.score);
  const unit = basis === "cs" ? "clean sheets" : basis === "goals" ? "goals" : basis === "odds" ? "wins" : "ease points";
  const fmt = (v: number) => (basis === "fdr" ? v.toFixed(0) : v.toFixed(1));
  return (
    <>
      <div className="ms-tools fx-window">
        <label className="fx-label">Run length
          <select className="aero-select" value={length} onChange={(e) => setLength(Number(e.target.value))}>{[3, 4, 5, 6, 8].map((n) => <option key={n} value={n}>{n} gameweeks</option>)}</select>
        </label>
        <p className="fx-note">GW{data.start_gameweek}–GW{data.end_gameweek}. The best run is when to own a club; the worst is when to be out. Measured in expected {unit} over the run.</p>
      </div>
      <div className="mp-sheet fx-runs">
        <table>
          <thead><tr><th scope="col">Club</th><th scope="col">Next {length}</th><th scope="col">Best run</th><th scope="col">Worst run</th></tr></thead>
          <tbody>
            {rows.map(({ t, best, worst, next }) => (
              <tr key={t.team_id}>
                <th scope="row"><b>{t.team_short_name}</b> <span>{t.team_name}</span></th>
                <td>{fmt(next.score)}</td>
                <td className="good">GW{best.from}–{best.to}<small> {fmt(best.score)}{best.from === next.from ? " · starts now" : ""}</small></td>
                <td className="bad">GW{worst.from}–{worst.to}<small> {fmt(worst.score)}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// Pairs of clubs whose fixtures cover each other, with the cheapest players
// who give you each half of the pair.
function Rotation({ data, basis }: { data: FixtureMatrix; basis: Basis }) {
  const [position, setPosition] = useState<"GKP" | "DEF" | "MID" | "FWD">("GKP");
  const [weeks, setWeeks] = useState(6);
  const [without, setWithout] = useState<number | null>(null);
  const prices = usePriceChanges();
  const useBasis: Basis = basis === "fdr" || basis === "odds" ? basis : position === "GKP" || position === "DEF" ? "cs" : "goals";
  const gws = Array.from({ length: Math.min(weeks, data.horizon) }, (_, i) => data.start_gameweek + i);
  const per = new Map(data.teams.map((t) => [t.team_id, gws.map((g) => weekValue(t.fixtures.filter((f) => f.event === g), useBasis) ?? 0)]));
  const pairs: { a: TeamRow; b: TeamRow; score: number; picks: string }[] = [];
  const pool = data.teams.filter((t) => t.team_id !== without);
  for (let i = 0; i < pool.length; i++) for (let j = i + 1; j < pool.length; j++) {
    const a = pool[i], b = pool[j];
    const pa = per.get(a.team_id)!, pb = per.get(b.team_id)!;
    const picks = gws.map((_, k) => (pa[k] >= pb[k] ? a.team_short_name : b.team_short_name));
    pairs.push({ a, b, score: gws.reduce((s, _, k) => s + Math.max(pa[k], pb[k]), 0), picks: picks.join(" · ") });
  }
  pairs.sort((x, y) => y.score - x.score);
  const cheapest = (team: string) => (prices?.players ?? []).filter((p) => p.team === team && p.position === position && p.status === "a")
    .sort((x, y) => x.price - y.price).slice(0, 2).map((p) => `${p.name} £${p.price.toFixed(1)}m`).join(", ");
  return (
    <>
      <div className="ms-tools fx-window">
        <div className="ms-seg" role="group" aria-label="Position">
          {(["GKP", "DEF", "MID", "FWD"] as const).map((p) => <button key={p} type="button" aria-pressed={position === p} onClick={() => setPosition(p)}>{p === "GKP" ? "Goalkeepers" : p === "DEF" ? "Defenders" : p === "MID" ? "Midfielders" : "Forwards"}</button>)}
        </div>
        <label className="fx-label">Over
          <select className="aero-select" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>{[4, 6, 8, 10].map((n) => <option key={n} value={n}>{n} gameweeks</option>)}</select>
        </label>
        <label className="fx-label">Leave out
          <select className="aero-select" value={without ?? ""} onChange={(e) => setWithout(e.target.value ? Number(e.target.value) : null)}>
            <option value="">No club</option>
            {data.teams.slice().sort((a, b) => a.team_name.localeCompare(b.team_name)).map((t) => <option key={t.team_id} value={t.team_id}>{t.team_name}</option>)}
          </select>
        </label>
        <p className="fx-note">Each pair scores the better of the two clubs every gameweek (by {useBasis === "cs" ? "clean-sheet chance" : useBasis === "goals" ? "projected goals" : useBasis === "odds" ? "win chance" : "FPL difficulty"}), added up over GW{gws[0]}–GW{gws[gws.length - 1]}. "Play" says which club to start each week.</p>
      </div>
      <div className="mp-sheet fx-runs">
        <table>
          <thead><tr><th scope="col">#</th><th scope="col">Pair</th><th scope="col">Score</th><th scope="col">Play</th><th scope="col">Cheapest options</th></tr></thead>
          <tbody>
            {pairs.slice(0, 12).map((p, i) => (
              <tr key={`${p.a.team_id}-${p.b.team_id}`}>
                <td>{i + 1}</td>
                <th scope="row"><b>{p.a.team_short_name}</b> + <b>{p.b.team_short_name}</b></th>
                <td>{p.score.toFixed(1)}</td>
                <td className="play">{p.picks}</td>
                <td className="cheap"><span>{cheapest(p.a.team_short_name) || "–"}</span><span>{cheapest(p.b.team_short_name) || "–"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Chevron({ dir }: { dir: "left" | "right" }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" aria-hidden="true"><path d={dir === "left" ? "M12.5 4.5 7 10l5.5 5.5" : "M7.5 4.5 13 10l-5.5 5.5"} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
