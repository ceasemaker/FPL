import { useEffect, useMemo, useState } from "react";
import "./FixturesPage.css";

interface Fixture { event: number; opponent: string | null; location: "H" | "A"; difficulty: number | null; win_probability: number | null; odds_difficulty: number | null }
interface TeamRow { team_id: number; team_name: string; team_short_name: string; fixtures: Fixture[]; avg_difficulty: number | null; expected_market_wins: number | null; probability_win_all: number | null; probability_at_least_one: number | null; market_fixture_count: number }
interface FixtureMatrix { current_gameweek: number; start_gameweek: number; end_gameweek: number; horizon: number; market: { available: boolean; snapshot_date: string | null; type: string; includes_clean_sheet_odds: boolean; note: string }; teams: TeamRow[] }

export function FixturesPage() {
  const [data, setData] = useState<FixtureMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<"easiest" | "team">("easiest");
  const [basis, setBasis] = useState<"fdr" | "market" | "blend">("fdr");

  const load = () => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch("/api/fixtures/ticker/?horizon=5", { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Fixtures could not be loaded.");
        return body as FixtureMatrix;
      })
      .then(setData)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  };

  useEffect(load, []);

  const teams = useMemo(() => {
    const rows = [...(data?.teams ?? [])];
    if (sort === "team") return rows.sort((a, b) => a.team_name.localeCompare(b.team_name));
    if (basis === "market") return rows.sort((a, b) => (b.expected_market_wins ?? -1) - (a.expected_market_wins ?? -1));
    if (basis === "fdr") return rows.sort((a, b) => (a.avg_difficulty ?? 9) - (b.avg_difficulty ?? 9));

    const percentile = (team: TeamRow, metric: (row: TeamRow) => number | null, higherIsBetter: boolean) => {
      const value = metric(team);
      const available = rows.map(metric).filter((item): item is number => item !== null).sort((a, b) => a - b);
      if (value === null || available.length < 2) return null;
      const below = available.filter(item => item < value).length;
      const equal = available.filter(item => item === value).length;
      const rank = (below + (equal - 1) / 2) / (available.length - 1);
      return higherIsBetter ? rank : 1 - rank;
    };
    const blendedScore = (team: TeamRow) => {
      const odds = percentile(team, row => row.market_fixture_count ? (row.expected_market_wins ?? 0) / row.market_fixture_count : null, true);
      const fdr = percentile(team, row => row.avg_difficulty, false);
      if (odds === null) return fdr ?? -1;
      if (fdr === null) return odds;
      return odds * .7 + fdr * .3;
    };
    return rows.sort((a, b) => blendedScore(b) - blendedScore(a));
  }, [data, sort, basis]);
  const gameweeks = data ? Array.from({ length: data.horizon }, (_, index) => data.start_gameweek + index) : [];
  const pricedFixtureCount = Math.max(0, ...(data?.teams.map(team => team.market_fixture_count) ?? []));
  const winAllLabel = pricedFixtureCount === 2 ? "Win both" : "Win all";

  return <main className="aero-page fixtures-page">
    <header className="aero-header fixtures-heading">
      <div><span className="fixtures-eyebrow">Official FPL schedule</span><h1>Fixture planner</h1><p>{data ? `Planning GW${data.start_gameweek}–GW${data.end_gameweek} · results complete through GW${data.current_gameweek}` : "The next five gameweeks for every club."}</p></div>
      <div className="fixtures-actions"><div className="fixture-basis" aria-label="Fixture difficulty basis"><button className={basis === "fdr" ? "active" : ""} onClick={() => setBasis("fdr")}>Official FDR</button><button className={basis === "market" ? "active" : ""} onClick={() => setBasis("market")} disabled={!data?.market.available}>Win odds</button><button className={basis === "blend" ? "active" : ""} onClick={() => setBasis("blend")} disabled={!data?.market.available}>70% odds + 30% FDR</button></div><label className="fixtures-sort"><span>Order</span><select className="aero-select" value={sort} onChange={(event) => setSort(event.target.value as "easiest" | "team")}><option value="easiest">Easiest run first</option><option value="team">Team A–Z</option></select></label></div>
    </header>
    <p className="aero-note fixtures-context">{basis === "market" ? `${data?.market.type ?? "1X2 match-result odds"} · snapshot ${data?.market.snapshot_date ?? "unavailable"}. Higher win probability means an easier fixture. “${winAllLabel}” and “Win 1+” assume fixture results are independent. These are not clean-sheet odds.` : basis === "blend" ? `Combined order uses percentile ranks: 70% current average win probability and 30% official average FDR. “${winAllLabel}” and “Win 1+” assume fixture results are independent. Missing market odds fall back to FDR.` : "FDR is the official 1–5 fixture difficulty rating. Venue is shown as H or A. Lower average FDR means the easier five-match run."}</p>
    {loading && <div className="aero-loading">Loading the current fixture schedule…</div>}
    {error && <div className="aero-error fixtures-error"><strong>Fixtures are unavailable.</strong><span>{error}</span><button className="aero-button" onClick={load}>Try again</button></div>}
    {!loading && !error && data && <section className="fixture-matrix-card" aria-label="Five gameweek fixture difficulty matrix"><div className="fixture-matrix-scroll">
              <div className={`fixture-matrix fixture-matrix-head ${basis !== "fdr" ? "with-probabilities" : ""}`}><span>Club</span>{gameweeks.map(gameweek => <span key={gameweek}>GW{gameweek}</span>)}{basis === "fdr" ? <span>Avg</span> : <><span>xW</span><span>{winAllLabel}</span><span>Win 1+</span></>}</div>
      {teams.map(team => <div className={`fixture-matrix fixture-team-row ${basis !== "fdr" ? "with-probabilities" : ""}`} key={team.team_id}>
        <div className="fixture-team"><b>{team.team_short_name}</b><span>{team.team_name}</span></div>
        {gameweeks.map(gameweek => { const fixture = team.fixtures.find(item => item.event === gameweek); const level = basis === "fdr" ? fixture?.difficulty : fixture?.odds_difficulty; return fixture ? <div className={`fixture-cell fdr-${level ?? 0}`} key={gameweek}><strong>{fixture.opponent}</strong><span>{basis === "fdr" ? `${fixture.location} · FDR ${fixture.difficulty ?? "—"}` : fixture.win_probability == null ? `${fixture.location} · Market unavailable · FDR ${fixture.difficulty ?? "—"}` : basis === "blend" ? `${fixture.location} · ${(fixture.win_probability * 100).toFixed(0)}% win · FDR ${fixture.difficulty ?? "—"}` : `${fixture.location} · ${(fixture.win_probability * 100).toFixed(0)}% win`}</span></div> : <div className="fixture-cell blank" key={gameweek}>—</div>; })}
        {basis === "fdr" ? <strong className="fixture-average">{team.avg_difficulty?.toFixed(1) ?? "—"}</strong> : <><strong className="fixture-average">{team.expected_market_wins == null ? "—" : <><span>{team.expected_market_wins.toFixed(2)}</span><small>{team.market_fixture_count} priced</small></>}</strong><strong className="fixture-average">{team.probability_win_all == null ? "—" : <span>{(team.probability_win_all * 100).toFixed(0)}%</span>}</strong><strong className="fixture-average">{team.probability_at_least_one == null ? "—" : <span>{(team.probability_at_least_one * 100).toFixed(0)}%</span>}</strong></>}
      </div>)}
    </div></section>}
  </main>;
}
