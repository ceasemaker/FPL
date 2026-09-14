import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SquadOptimizer } from "./OptimizeTeamPage";
import "./DecisionDashboardPage.css";
import "./OptimizeTeamPage.css";

type RiskProfile = "protect" | "balanced" | "chase";

interface PlayerSignal {
  id: number;
  name: string;
  position: string;
  current_price: number;
  ownership: number;
  next_xp: number;
  horizon_xp: number;
  xp_per_m: number;
  rank_exposure: number;
  rank_risk: number;
  role: "shield" | "differential" | "balanced";
}

interface TransferSignal {
  out: string;
  in: string;
  position: string;
  expected_points_gain: number;
  objective_gain: number;
  incoming_ownership: number;
  bank_after: number;
}

interface SeasonResult {
  season: string;
  player_gameweeks: number;
  base_mae: number;
  odds_mae: number;
  mae_improvement_pct: number;
  base_top5_points: number;
  odds_top5_points: number;
}

interface TeamReplay {
  season: string;
  start_gameweek: number;
  end_gameweek: number;
  manager_count: number;
  results: {
    scoring_view?: string;
    mean_delta: number;
    median_delta: number;
    teams_model_beat: number;
    teams_tied: number;
    teams_model_lost: number;
    best_delta: number;
    worst_delta: number;
  };
  chip_excluded_results?: {
    mean_delta: number;
    median_delta: number;
    teams_model_beat: number;
  };
  transfer_value_results?: {
    benchmark: string;
    mean_delta: number;
    median_delta: number;
    paths_transfers_added_value: number;
    paths_tied: number;
    paths_transfers_destroyed_value: number;
    best_delta: number;
    worst_delta: number;
  };
  weekly_mean: Array<{
    gameweek: number;
    human_points: number;
    model_points: number;
    cumulative_delta: number;
  }>;
}

interface DashboardPayload {
  meta: {
    manager_id: number;
    generated_at: string;
    risk_profile: RiskProfile;
    projection_warning: string;
    public_squad_warning: string;
    /** Gameweek the saved analysis was built for. */
    saved_for_gameweek: number | null;
    /** Next gameweek according to the refreshed database. */
    live_next_gameweek: number | null;
    is_stale: boolean;
  };
  manager: {
    name: string;
    overall_points: number;
    overall_rank: number;
    bank: number;
    team_value: number;
  };
  gameweek: {
    current: number;
    next: number;
    deadline: string;
    horizon: number;
    next_xp: number;
    captain: PlayerSignal | null;
  };
  decision: {
    recommended_action: "roll_transfer" | "make_one_transfer";
    hold_expected_points: number;
    minimum_gain_to_spend_transfer: number;
    transfers: TransferSignal[];
  };
  squad: PlayerSignal[];
  signals: {
    shields: PlayerSignal[];
    differentials: PlayerSignal[];
    weak_spots: PlayerSignal[];
  };
  backtest: {
    odds: {
      overall: {
        player_gameweeks: number;
        base_mae: number;
        odds_mae: number;
        mae_improvement_pct: number;
        base_top5_points: number;
        odds_top5_points: number;
      };
      season_results: SeasonResult[];
      method: { price_snapshot: string };
    };
    team_replay: TeamReplay | null;
    team_replays: TeamReplay[];
  };
  accepted_forecast?: {
    model: string;
    accepted_for_mean_forecast: boolean;
    accepted_for_optimizer: boolean;
    accepted_for_transfer_horizon: boolean;
    evidence: {
      mae_gain_vs_odds_ridge?: number;
      mae_gain_ci95?: [number, number];
      correlation_gain_ci95?: [number, number];
      top5_weekly_diff_ci95?: [number, number];
      horizon_correlation_gain_ci95?: [number, number];
    };
    caveat: string;
  } | null;
  research: {
    report_url: string;
    data: {
      seasons: string[];
      odds: string;
      timing: string;
    };
    layers: Array<{
      name: string;
      status: "working" | "research" | "prototype";
      detail: string;
    }>;
    pipeline: Array<{ label: string; detail: string }>;
    evidence: {
      mae_gain?: number;
      mae_gain_ci95?: [number, number];
      top5_difference?: number;
      top5_ci95?: [number, number];
      horizon_utility_difference?: number;
      horizon_utility_ci95?: [number, number];
      horizon_correlation_ci95?: [number, number];
    };
    replay_evidence: Array<{
      start_gameweek: number;
      manager_count: number;
      median_transfer_value?: number;
      mean_transfer_value?: number;
      paths_positive?: number;
    }>;
    limitations: string[];
  };
}

interface PlayerCatalogueItem {
  id: number;
  name: string;
  label: string;
  team: string;
  position: string;
  price_m: number;
  ownership: number;
}

interface PlayerCataloguePayload {
  snapshot_date: string;
  generated_at: string;
  available_gameweeks: number[];
  players: PlayerCatalogueItem[];
}

interface PlayerAnalysisRow {
  fixture_id?: number | null;
  fixture_count?: number;
  matches?: PlayerAnalysisRow[];
  gameweek: number;
  opponent: string;
  venue: string;
  expected_points: number;
  expected_minutes: number;
  ownership: number;
  price_m: number;
  team_lambda: number;
  opponent_lambda: number;
  goal_lambda: number;
  assist_lambda: number;
  return_probability: number;
  attacking_blank_probability: number;
  multiple_return_probability: number;
  clean_sheet_probability: number;
  xp_per_m: number;
  differential_upside: number;
  omission_risk: number;
  non_start_probability: number;
  data_basis: "market" | "fdr_proxy" | "mixed";
  congested: boolean;
  days_previous_europe: number | null;
  days_next_europe: number | null;
  components: Record<string, number>;
}

interface PlayerAnalysisResult {
  id: number;
  name: string;
  team: string;
  position: string;
  role: "shield" | "differential" | "balanced";
  focus_rank: number;
  weighted_horizon_xp: number;
  captain_total_xp: number;
  triple_captain_total_xp: number;
  triple_captain_increment: number;
  focus: PlayerAnalysisRow;
  fixtures: PlayerAnalysisRow[];
}

interface PlayerAnalysisPayload {
  meta: {
    snapshot_date: string;
    focus_gameweek: number;
    horizon: number;
    gameweeks: number[];
    player_count: number;
    data_policy: string;
    authority: string;
  };
  players: PlayerAnalysisResult[];
  limitations: string[];
}

const formatRank = (rank: number) => new Intl.NumberFormat("en-GB").format(rank);
const formatOwnership = (ownership: number) => `${Math.round(ownership * 100)}%`;
const roleLabel = (role: PlayerSignal["role"]) =>
  role === "shield" ? "Rank shield" : role === "differential" ? "Differential" : "Balanced";
const formatSigned = (value?: number, digits = 3) => value == null ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
const formatInterval = (interval?: [number, number]) =>
  interval ? `[${formatSigned(interval[0])}, ${formatSigned(interval[1])}]` : "—";

type LabMode = "players" | "decisions" | "optimizer";

export function DecisionDashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [managerId, setManagerId] = useState(() =>
    searchParams.get("manager_id") || localStorage.getItem("fpl_manager_id") || "576154"
  );
  const [managerDraft, setManagerDraft] = useState(managerId);
  const mode: LabMode = searchParams.get("mode") === "optimizer" ? "optimizer" : searchParams.get("mode") === "decisions" ? "decisions" : "players";
  const setMode = (next: LabMode) => {
    const params = new URLSearchParams(searchParams);
    if (next === "players") params.delete("mode");
    else params.set("mode", next);
    setSearchParams(params, { replace: true });
  };
  const [profile, setProfile] = useState<RiskProfile>("balanced");
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [catalogue, setCatalogue] = useState<PlayerCataloguePayload | null>(null);
  const [playerA, setPlayerA] = useState("411");
  const [playerB, setPlayerB] = useState("426");
  const [analysisGameweek, setAnalysisGameweek] = useState(3);
  const [analysisHorizon, setAnalysisHorizon] = useState(3);
  const [playerAnalysis, setPlayerAnalysis] = useState<PlayerAnalysisPayload | null>(null);
  const [playerAnalysisError, setPlayerAnalysisError] = useState<string | null>(null);
  const [playerAnalysisLoading, setPlayerAnalysisLoading] = useState(true);

  const loadManager = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextManagerId = managerDraft.trim();
    if (!/^\d+$/.test(nextManagerId)) {
      setError("Enter the numeric manager ID shown in your FPL team URL.");
      return;
    }
    localStorage.setItem("fpl_manager_id", nextManagerId);
    localStorage.setItem("optimizer_manager_id", nextManagerId);
    setManagerId(nextManagerId);
    const params = new URLSearchParams(searchParams);
    params.set("manager_id", nextManagerId);
    setSearchParams(params, { replace: true });
  };

  useEffect(() => {
    if (mode !== "decisions") return;
    const controller = new AbortController();
    setError(null);
    setData(null);
    fetch(`/api/decision-dashboard/?manager_id=${encodeURIComponent(managerId)}&risk_profile=${profile}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Could not load the decision dashboard.");
        return body as DashboardPayload;
      })
      .then(setData)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      });
    return () => controller.abort();
  }, [managerId, profile, mode]);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/decision-dashboard/players/", { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Could not load the player model.");
        return body as PlayerCataloguePayload;
      })
      .then((body) => {
        setCatalogue(body);
        const ids = new Set(body.players.map((player) => String(player.id)));
        if (!ids.has(playerA) && body.players[0]) setPlayerA(String(body.players[0].id));
        if (!ids.has(playerB) && body.players[1]) setPlayerB(String(body.players[1].id));
        if (!body.available_gameweeks.includes(analysisGameweek) && body.available_gameweeks[0]) {
          setAnalysisGameweek(body.available_gameweeks[0]);
        }
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setPlayerAnalysisError(requestError.message);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!catalogue || !playerA) return;
    const controller = new AbortController();
    const ids = playerB && playerB !== playerA ? `${playerA},${playerB}` : playerA;
    const params = new URLSearchParams({
      player_ids: ids,
      gameweek: String(analysisGameweek),
      horizon: String(analysisHorizon),
    });
    setPlayerAnalysisLoading(true);
    setPlayerAnalysisError(null);
    fetch(`/api/decision-dashboard/player-analysis/?${params}`, { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Could not calculate player analysis.");
        return body as PlayerAnalysisPayload;
      })
      .then(setPlayerAnalysis)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setPlayerAnalysisError(requestError.message);
      })
      .finally(() => setPlayerAnalysisLoading(false));
    return () => controller.abort();
  }, [catalogue, playerA, playerB, analysisGameweek, analysisHorizon]);

  const weakestIds = useMemo(
    () => new Set(data?.signals.weak_spots.map((player) => player.id) ?? []),
    [data],
  );

  const reportParams = new URLSearchParams({
    player_ids: playerB && playerB !== playerA ? `${playerA},${playerB}` : playerA,
    gameweek: String(analysisGameweek),
    horizon: String(analysisHorizon),
  });
  const renderPlayerWorkbench = () => (
<section className="decision-panel player-lab" id="player-lab">
        <div className="research-heading">
          <div>
            <span className="decision-label">Player workbench</span>
            <h2>Analyse anyone, without hiding the maths</h2>
            <p>{playerAnalysis?.meta.data_policy ?? "Loading the latest saved pre-deadline snapshot..."}</p>
          </div>
          <div className="player-report-actions">
            <a className="report-link" href={`/api/decision-dashboard/player-report/?${reportParams}`} target="_blank" rel="noreferrer">
              Open dynamic report <span aria-hidden="true">↗</span>
            </a>
            <span className="report-format-note">Print the HTML report to save a PDF</span>
          </div>
        </div>

        <div className="player-lab-controls">
          <label htmlFor="player-analysis-a">
            <span>Player A</span>
            <select id="player-analysis-a" value={playerA} onChange={(event) => setPlayerA(event.target.value)}>
              {catalogue?.players.map((player) => <option key={player.id} value={player.id}>{player.label}</option>)}
            </select>
          </label>
          <label htmlFor="player-analysis-b">
            <span>Player B</span>
            <select id="player-analysis-b" value={playerB} onChange={(event) => setPlayerB(event.target.value)}>
              {catalogue?.players.map((player) => <option key={player.id} value={player.id}>{player.label}</option>)}
            </select>
          </label>
          <label htmlFor="player-analysis-gameweek">
            <span>Focus gameweek</span>
            <select id="player-analysis-gameweek" value={analysisGameweek} onChange={(event) => setAnalysisGameweek(Number(event.target.value))}>
              {catalogue?.available_gameweeks.map((gameweek) => <option key={gameweek} value={gameweek}>GW{gameweek}</option>)}
            </select>
          </label>
          <label htmlFor="player-analysis-horizon">
            <span>Horizon</span>
            <select id="player-analysis-horizon" value={analysisHorizon} onChange={(event) => setAnalysisHorizon(Number(event.target.value))}>
              {[1, 2, 3].map((horizon) => <option key={horizon} value={horizon}>{horizon} GW{horizon > 1 ? "s" : ""}</option>)}
            </select>
          </label>
        </div>

        {playerAnalysisError && <div className="decision-error">{playerAnalysisError}</div>}
        {playerAnalysisLoading && <div className="decision-loading">Calculating minutes, Poisson events, value, and rank exposure...</div>}

        {!playerAnalysisLoading && playerAnalysis && (
          <>
            <div className="player-analysis-grid">
              {playerAnalysis.players.map((player) => {
                const focus = player.focus;
                const maxComponent = Math.max(...Object.values(focus.components).map((value) => Math.abs(value)), 0.01);
                return (
                  <article className="player-analysis-card" key={player.id}>
                    <div className="player-analysis-title">
                      <div>
                        <span>{player.position} · {player.team} · #{player.focus_rank} model rank</span>
                        <h3>{player.name}</h3>
                      </div>
                      <strong>{focus.expected_points.toFixed(2)} <small>xP</small></strong>
                    </div>

                    <div className="player-analysis-kpis">
                      <div><span>Expected minutes</span><strong>{focus.expected_minutes.toFixed(1)}</strong><small>{Math.round(focus.non_start_probability * 100)}% chance of no starts this GW</small></div>
                      <div><span>Return probability</span><strong>{Math.round(focus.return_probability * 100)}%</strong><small>{Math.round(focus.multiple_return_probability * 100)}% multi-return</small></div>
                      <div><span>{playerAnalysis.meta.horizon}-GW value</span><strong>{player.weighted_horizon_xp.toFixed(2)}</strong><small>weighted xP</small></div>
                      <div><span>Budget value</span><strong>{focus.xp_per_m.toFixed(3)}</strong><small>xP per £m</small></div>
                      <div><span>Differential upside</span><strong>{focus.differential_upside.toFixed(2)}</strong><small>xP × unowned</small></div>
                      <div><span>Omission risk</span><strong>{focus.omission_risk.toFixed(2)}</strong><small>xP × owned</small></div>
                    </div>

                    <div className="component-list" aria-label={`${player.name} expected-points components`}>
                      {Object.entries(focus.components).map(([name, value]) => (
                        <div className="component-row" key={name}>
                          <span>{name.replaceAll("_", " ")}</span>
                          <i><b className={value < 0 ? "negative" : ""} style={{ width: `${Math.max(2, Math.abs(value) / maxComponent * 100)}%` }}></b></i>
                          <strong>{value >= 0 ? "+" : ""}{value.toFixed(2)}</strong>
                        </div>
                      ))}
                    </div>

                    <div className="fixture-path">
                      {player.fixtures.flatMap((week) => week.matches ?? [week]).map((fixture) => (
                        <div key={`${fixture.gameweek}-${fixture.fixture_id ?? "single"}`}>
                          <span>GW{fixture.gameweek}</span>
                          <strong>{fixture.opponent} <small>{fixture.venue}</small></strong>
                          <b>{fixture.expected_points.toFixed(2)} xP</b>
                          <small className={fixture.data_basis === "market" ? "market-basis" : "proxy-basis"}>
                            {fixture.opponent === "Blank" ? "No fixture" : fixture.data_basis === "market" ? "market" : "FDR proxy"}
                          </small>
                        </div>
                      ))}
                    </div>

                    <details className="model-detail">
                      <summary>Inspect the probability model</summary>
                      {(focus.fixture_count ?? 1) > 1 && <p>Points and minutes cover all matches this gameweek. Weekly probabilities assume independent matches, including availability.</p>}
                      <dl>
                        <div><dt>Team goal mean</dt><dd>{focus.team_lambda.toFixed(3)}</dd></div>
                        <div><dt>Opponent goal mean</dt><dd>{focus.opponent_lambda.toFixed(3)}</dd></div>
                        <div><dt>Player goal mean</dt><dd>{focus.goal_lambda.toFixed(3)}</dd></div>
                        <div><dt>Player assist mean</dt><dd>{focus.assist_lambda.toFixed(3)}</dd></div>
                        <div><dt>Attacking blank</dt><dd>{Math.round(focus.attacking_blank_probability * 100)}%</dd></div>
                        <div><dt>{(focus.fixture_count ?? 1) > 1 ? "At least one team clean sheet" : "Team clean sheet"}</dt><dd>{Math.round(focus.clean_sheet_probability * 100)}%</dd></div>
                        <div><dt>Captain total</dt><dd>{player.captain_total_xp.toFixed(2)}</dd></div>
                        <div><dt>TC total</dt><dd>{player.triple_captain_total_xp.toFixed(2)}</dd></div>
                      </dl>
                    </details>
                  </article>
                );
              })}
            </div>
            <div className="player-lab-footnote">
              <strong>Authority:</strong> {playerAnalysis.meta.authority}
              <span>Snapshot {playerAnalysis.meta.snapshot_date} · {playerAnalysis.meta.player_count} players</span>
            </div>
          </>
        )}
      </section>
  );

  if (mode === "players") {
    return (
      <main className="page decision-page">
        <LabModeSwitch mode={mode} onChange={setMode} />
        <header className="decision-public-header">
          <span className="decision-kicker">All-player intelligence</span>
          <h1>Transfer Decision Lab</h1>
          <p>Compare every FPL player across expected minutes, scoring probabilities, fixtures, value, ownership risk, and multi-gameweek projections.</p>
        </header>
        {renderPlayerWorkbench()}
      </main>
    );
  }

  if (mode === "optimizer") {
    return (
      <main className="page decision-page">
        <ManagerPicker value={managerDraft} onChange={setManagerDraft} onSubmit={loadManager} />
        <LabModeSwitch mode={mode} onChange={setMode} />
        <SquadOptimizer defaultManagerId={managerId} />
      </main>
    );
  }
  if (error) {
    return (
      <main className="page decision-page">
        <ManagerPicker value={managerDraft} onChange={setManagerDraft} onSubmit={loadManager} />
        <LabModeSwitch mode={mode} onChange={setMode} />
        <div className="decision-error">
          <strong>We could not load Decision Lab for manager {managerId}.</strong>
          <span>{error}</span>
          <a href="/analyze">Open Analyse Manager</a>
        </div>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="page decision-page">
        <ManagerPicker value={managerDraft} onChange={setManagerDraft} onSubmit={loadManager} />
        <LabModeSwitch mode={mode} onChange={setMode} />
        <div className="decision-loading">Building your decision room…</div>
      </main>
    );
  }

  const odds = data.backtest.odds.overall;
  const replay = data.backtest.team_replay;
  const replays = data.backtest.team_replays?.length ? data.backtest.team_replays : (replay ? [replay] : []);
  const action = data.decision.recommended_action === "roll_transfer" ? "Roll the transfer" : "Make one transfer";

  return (
    <main className="page decision-page">
      <ManagerPicker value={managerDraft} onChange={setManagerDraft} onSubmit={loadManager} />
      <LabModeSwitch mode={mode} onChange={setMode} />

      {data.meta.is_stale && (
        <p className="aero-note decision-stale" role="status">
          This analysis was built for Gameweek {data.meta.saved_for_gameweek ?? "—"} but the
          next gameweek is now {data.meta.live_next_gameweek ?? "—"}. Treat every number
          below as historical until the analysis is re-run.
        </p>
      )}

      <section className="decision-hero">
        <div>
          <span className="decision-kicker">Manager {data.meta.manager_id} · GW{data.gameweek.next}</span>
          <h1>{data.manager.name} decision room</h1>
          <p>True value, ownership exposure and transfer risk—grounded in four archived seasons and an explicit research gate.</p>
        </div>
        <div className="profile-switch" aria-label="Rank strategy">
          {(["protect", "balanced", "chase"] as RiskProfile[]).map((option) => (
            <button key={option} className={profile === option ? "active" : ""} onClick={() => setProfile(option)}>
              {option}
            </button>
          ))}
        </div>
      </section>

      <section className="decision-callout prototype-callout">
        <div>
          <span className="decision-label">Prototype suggestion · manager remains the authority</span>
          <strong>{action}</strong>
          <p>
            {data.decision.recommended_action === "roll_transfer"
              ? `In the current restricted search, no move clears the ${data.decision.minimum_gain_to_spend_transfer.toFixed(1)} point confidence buffer.`
              : "The current restricted search found a move above its confidence buffer. Treat it as a shortlist, not an instruction."}
          </p>
        </div>
        <div className="captain-call">
          <span>Captain</span>
          <strong>{data.gameweek.captain?.name ?? "—"}</strong>
          <small>{data.gameweek.captain?.next_xp.toFixed(1) ?? "0.0"} xP before doubling</small>
        </div>
      </section>

      <section className="decision-kpis" aria-label="Manager overview">
        <article><span>Overall rank</span><strong>{formatRank(data.manager.overall_rank)}</strong><small>{data.manager.overall_points} points</small></article>
        <article><span>Next-GW xP</span><strong>{data.gameweek.next_xp.toFixed(1)}</strong><small>starting XI + captain</small></article>
        <article><span>Squad value</span><strong>£{data.manager.team_value.toFixed(1)}m</strong><small>£{data.manager.bank.toFixed(1)}m bank</small></article>
        <article><span>Odds lift</span><strong>+{odds.mae_improvement_pct.toFixed(1)}%</strong><small>{formatRank(odds.player_gameweeks)} tested player-weeks</small></article>
      </section>

      {data.accepted_forecast && (
        <section className="decision-callout" aria-label="Forecast audit">
          <div>
            <span className="decision-label">
              Forecast audit{data.accepted_forecast.accepted_for_optimizer ? " · optimizer approved" : " · optimizer not approved"}
            </span>
            <strong>{data.accepted_forecast.model}</strong>
            <p>{data.accepted_forecast.caveat}</p>
          </div>
          <div className="captain-call">
            <span>MAE gain vs odds ridge</span>
            <strong>
              {data.accepted_forecast.evidence.mae_gain_vs_odds_ridge != null
                ? `+${data.accepted_forecast.evidence.mae_gain_vs_odds_ridge.toFixed(3)}`
                : "—"}
            </strong>
            <small>
              {data.accepted_forecast.evidence.mae_gain_ci95
                ? `95% CI [${data.accepted_forecast.evidence.mae_gain_ci95[0].toFixed(3)}, ${data.accepted_forecast.evidence.mae_gain_ci95[1].toFixed(3)}]`
                : "untouched test season"}
            </small>
          </div>
        </section>
      )}

      <section className="decision-panel research-panel" id="research">
        <div className="research-heading">
          <div>
            <span className="decision-label">Research status</span>
            <h2>What is working—and what is still only a hypothesis</h2>
            <p>{data.research.data.timing}</p>
          </div>
          <a className="report-link" href={data.research.report_url} target="_blank" rel="noreferrer">
            Read the full mathematics <span aria-hidden="true">↗</span>
          </a>
        </div>

        <div className="research-status-grid">
          {data.research.layers.map((layer) => (
            <article key={layer.name} className={`research-status ${layer.status}`}>
              <span>{layer.status === "working" ? "Working" : layer.status === "research" ? "Research" : "Prototype"}</span>
              <strong>{layer.name}</strong>
              <p>{layer.detail}</p>
            </article>
          ))}
        </div>

        <div className="model-pipeline" aria-label="Forecast calculation pipeline">
          {data.research.pipeline.map((step, index) => (
            <div className="pipeline-step" key={step.label}>
              <small>0{index + 1}</small>
              <strong>{step.label}</strong>
              <span>{step.detail}</span>
            </div>
          ))}
        </div>

        <div className="research-evidence-grid">
          <article>
            <span>Mean forecast</span>
            <strong>{formatSigned(data.research.evidence.mae_gain)} MAE gain</strong>
            <small>95% CI {formatInterval(data.research.evidence.mae_gain_ci95)} · supported</small>
          </article>
          <article>
            <span>Weekly top five</span>
            <strong>{formatSigned(data.research.evidence.top5_difference)} pts</strong>
            <small>95% CI {formatInterval(data.research.evidence.top5_ci95)} · unresolved</small>
          </article>
          <article>
            <span>Three-week utility</span>
            <strong>{formatSigned(data.research.evidence.horizon_utility_difference)} pts</strong>
            <small>Utility CI {formatInterval(data.research.evidence.horizon_utility_ci95)}</small>
          </article>
          <article>
            <span>Three-week correlation</span>
            <strong>Not promoted</strong>
            <small>Gain CI {formatInterval(data.research.evidence.horizon_correlation_ci95)}</small>
          </article>
        </div>

        <details className="research-limitations">
          <summary>Known data and model limitations</summary>
          <ul>{data.research.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </details>
      </section>

      {renderPlayerWorkbench()}

      <section className="decision-grid">
        <div className="decision-panel squad-panel">
          <div className="panel-heading">
            <div><span className="decision-label">Your 15</span><h2>Value and rank exposure</h2></div>
            <span className="freshness">Updated {new Date(data.meta.generated_at).toLocaleString()}</span>
          </div>
          <div className="squad-table" role="table">
            <div className="squad-row squad-header" role="row">
              <span>Player</span><span>GW xP</span><span>3GW xP</span><span>Owned</span><span>Value</span>
            </div>
            {data.squad.map((player) => (
              <div className={`squad-row ${weakestIds.has(player.id) ? "weak" : ""}`} role="row" key={player.id}>
                <div className="player-cell">
                  <span className={`role-dot ${player.role}`}></span>
                  <div><strong>{player.name}</strong><small>{player.position} · {roleLabel(player.role)}</small></div>
                </div>
                <strong>{player.next_xp.toFixed(1)}</strong>
                <span>{player.horizon_xp.toFixed(1)}</span>
                <span>{formatOwnership(player.ownership)}</span>
                <span>{player.xp_per_m.toFixed(2)} <small>xP/£m</small></span>
              </div>
            ))}
          </div>
        </div>

        <aside className="decision-side">
          <div className="decision-panel">
            <span className="decision-label">Exposure map</span>
            <h2>What moves your rank</h2>
            <div className="signal-group">
              <span>Shields you own</span>
              {data.signals.shields.map((player) => <strong key={player.id}>{player.name} <small>{formatOwnership(player.ownership)}</small></strong>)}
            </div>
            <div className="signal-group">
              <span>Your differentials</span>
              {data.signals.differentials.length
                ? data.signals.differentials.map((player) => <strong key={player.id}>{player.name} <small>{formatOwnership(player.ownership)}</small></strong>)
                : <small>No sub-10% players in the saved squad.</small>}
            </div>
          </div>

          <div className="decision-panel">
            <span className="decision-label">Prototype shortlist</span>
            <h2>Moves worth investigating</h2>
            <div className="transfer-list">
              {data.decision.transfers.slice(0, 3).map((move) => (
                <div className="transfer-row" key={`${move.out}-${move.in}`}>
                  <div><small>{move.out}</small><strong>→ {move.in}</strong></div>
                  <span className={move.objective_gain >= data.decision.minimum_gain_to_spend_transfer ? "clears" : ""}>
                    +{move.objective_gain.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </section>

      <section className="decision-panel evidence-panel">
        <div className="panel-heading">
          <div><span className="decision-label">Historical proof</span><h2>Did bookmaker context improve selection?</h2></div>
          <p>Opening average odds only · no closing-price lookahead</p>
        </div>
        <div className="season-results">
          {data.backtest.odds.season_results.map((season) => {
            const maxPoints = Math.max(season.base_top5_points, season.odds_top5_points);
            return (
              <article key={season.season}>
                <div className="season-title"><strong>{season.season}</strong><span>{season.mae_improvement_pct.toFixed(1)}% lower MAE</span></div>
                <div className="bar-label"><span>Player model</span><strong>{season.base_top5_points.toFixed(2)} pts</strong></div>
                <div className="result-track"><i style={{ width: `${(season.base_top5_points / maxPoints) * 100}%` }}></i></div>
                <div className="bar-label"><span>Player + odds</span><strong>{season.odds_top5_points.toFixed(2)} pts</strong></div>
                <div className="result-track market"><i style={{ width: `${(season.odds_top5_points / maxPoints) * 100}%` }}></i></div>
              </article>
            );
          })}
        </div>
        <p className="evidence-note">
          Odds added a modest forecasting improvement, while the top-five weekly screen rose from {odds.base_top5_points.toFixed(2)} to {odds.odds_top5_points.toFixed(2)} points per player. This supports using the market as a fixture calibration layer, not as the whole model.
        </p>
      </section>

      {replay && (
        <section className="decision-panel replay-panel">
          <div className="panel-heading">
            <div><span className="decision-label">Team-path replay</span><h2>Did transfers add value versus holding?</h2></div>
            <p>{replay.season} · decisions from GW{replay.start_gameweek + 1}</p>
          </div>
          <div className="replay-scorecard">
            <article>
              <span>Median transfer value</span>
              <strong className={(replay.transfer_value_results?.median_delta ?? 0) >= 0 ? "positive" : "negative"}>
                {formatSigned(replay.transfer_value_results?.median_delta, 1)} pts
              </strong>
              <small>model path minus holding the same starting squad</small>
            </article>
            <article><span>Transfers added value</span><strong>{replay.transfer_value_results?.paths_transfers_added_value ?? 0}/{replay.manager_count}</strong><small>paired internal squad paths</small></article>
            <article><span>Best path</span><strong className="positive">{formatSigned(replay.transfer_value_results?.best_delta, 0)}</strong><small>points versus holding</small></article>
            <article><span>Worst path</span><strong className="negative">{formatSigned(replay.transfer_value_results?.worst_delta, 0)}</strong><small>points versus holding</small></article>
          </div>
          {replays.length > 1 && (
            <div className="replay-runs">
              {replays.map((run) => (
                <article key={run.start_gameweek}>
                  <div><span>Start after GW{run.start_gameweek}</span><small>{run.manager_count} squad paths</small></div>
                  <strong className={(run.transfer_value_results?.median_delta ?? 0) >= 0 ? "positive" : "negative"}>
                    {formatSigned(run.transfer_value_results?.median_delta, 1)} median
                  </strong>
                  <small>
                    {run.transfer_value_results?.paths_transfers_added_value ?? 0}/{run.manager_count} paths above hold
                  </small>
                </article>
              ))}
            </div>
          )}
          <div className="replay-trend" aria-label="Average cumulative model advantage by gameweek">
            {replay.weekly_mean.map((week) => {
              const scale = Math.min(100, Math.abs(week.cumulative_delta) / 4);
              return (
                <div className="replay-week" key={week.gameweek} title={`GW${week.gameweek}: ${week.cumulative_delta > 0 ? "+" : ""}${week.cumulative_delta} points`}>
                  <i className={week.cumulative_delta >= 0 ? "positive" : "negative"} style={{ height: `${Math.max(3, scale)}%` }}></i>
                  <span>{week.gameweek}</span>
                </div>
              );
            })}
          </div>
          <p className="evidence-note">
            This is a paired internal hold benchmark, not a representative-manager experiment. Both paths begin with the same squad and use normal XI, autosubs and one captain. The starting cohort was selected ex post from eventual top-100 finishers, and historical prices are reconstructed.
          </p>
        </section>
      )}

      <p className="decision-warning">{data.meta.projection_warning} {data.meta.public_squad_warning}</p>
    </main>
  );
}

function ManagerPicker({
  value,
  onChange,
  onSubmit,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="manager-picker" onSubmit={onSubmit}>
      <label htmlFor="decision-manager-id">FPL manager</label>
      <input
        id="decision-manager-id"
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Manager ID"
        aria-label="FPL manager ID"
      />
      <button type="submit">Load team</button>
    </form>
  );
}

/** Decision Lab has two modes: read the room, or let the solver build a squad. */
function LabModeSwitch({ mode, onChange }: { mode: LabMode; onChange: (mode: LabMode) => void }) {
  return (
    <nav className="lab-mode-switch" aria-label="Decision Lab mode">
      <button
        type="button"
        className={mode === "players" ? "active" : ""}
        onClick={() => onChange("players")}
      >
        All players
      </button>
      <button
        type="button"
        className={mode === "decisions" ? "active" : ""}
        onClick={() => onChange("decisions")}
      >
        My team
      </button>
      <button
        type="button"
        className={mode === "optimizer" ? "active" : ""}
        onClick={() => onChange("optimizer")}
      >
        Build optimal squad
      </button>
    </nav>
  );
}
