import { useEffect, useState } from "react";
import "./OptimizeTeamPage.css";

interface SolverPlayer {
  id: number;
  web_name: string;
  position: string;
  now_cost: number;
  predicted_points: number;
  predicted_sd: number;
  ownership_proxy: number;
  image_url: string | null;
}

interface TransferInfo {
  in: SolverPlayer[];
  out: SolverPlayer[];
  count: number;
  free_transfers: number;
  paid_transfers: number;
}

interface GWResult {
  gameweek: number;
  chips: string[];
  transfers: TransferInfo;
  squad: {
    starters: SolverPlayer[];
    bench: SolverPlayer[];
  };
  captain: { id: number; web_name: string } | null;
  total_predicted_points: number;
  bank: number;
}

interface MILPResult {
  meta: {
    budget: number;
    start_gameweek: number;
    end_gameweek: number;
    horizon: number;
    objective_value: number;
    solver: string;
    risk_profile: "protect" | "balanced" | "chase";
    personalized: boolean;
    manager_id: number | null;
    /** Where the points the solver maximised came from. */
    projection_source?: "stored_model" | "official_ep_next";
    projection_note?: string;
  };
  gameweeks: GWResult[];
}

const BUDGET_STORAGE_KEY = "optimizer_budget";
const HORIZON_STORAGE_KEY = "optimizer_horizon";
const INCLUDE_UNAVAILABLE_KEY = "optimizer_include_unavailable";
const MANAGER_ID_KEY = "optimizer_manager_id";
const USE_MANAGER_KEY = "optimizer_use_manager_squad";
const FREE_TRANSFERS_KEY = "optimizer_free_transfers";
const RISK_PROFILE_KEY = "optimizer_risk_profile";

const formatCost = (cost: number) => (cost / 10).toFixed(1);

/**
 * MILP squad optimiser. Rendered inside Decision Lab as its advanced
 * "Build optimal squad" mode rather than as a standalone route.
 */
export function SquadOptimizer({ defaultManagerId = "" }: { defaultManagerId?: string }) {
  const [budget, setBudget] = useState<string>("100.0");
  const [horizon, setHorizon] = useState<string>("3");
  const [includeUnavailable, setIncludeUnavailable] = useState<boolean>(false);
  const [managerId, setManagerId] = useState<string>("");
  const [useManagerSquad, setUseManagerSquad] = useState<boolean>(false);
  const [freeTransfers, setFreeTransfers] = useState<string>("1");
  const [riskProfile, setRiskProfile] = useState<"protect" | "balanced" | "chase">("balanced");
  const [result, setResult] = useState<MILPResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeGWTab, setActiveGWTab] = useState<number>(0);

  // Load from localStorage
  useEffect(() => {
    const storedBudget = localStorage.getItem(BUDGET_STORAGE_KEY);
    const storedHorizon = localStorage.getItem(HORIZON_STORAGE_KEY);
    const storedInclude = localStorage.getItem(INCLUDE_UNAVAILABLE_KEY);
    const storedManager = localStorage.getItem(MANAGER_ID_KEY);
    const storedUseManager = localStorage.getItem(USE_MANAGER_KEY);
    const storedFreeTransfers = localStorage.getItem(FREE_TRANSFERS_KEY);
    const storedRiskProfile = localStorage.getItem(RISK_PROFILE_KEY);

    if (storedBudget) setBudget(storedBudget);
    if (storedHorizon) setHorizon(storedHorizon);
    if (storedInclude) setIncludeUnavailable(storedInclude === "true");
    if (defaultManagerId) {
      setManagerId(defaultManagerId);
      setUseManagerSquad(true);
    } else if (storedManager) {
      setManagerId(storedManager);
    }
    if (!defaultManagerId && storedUseManager) setUseManagerSquad(storedUseManager === "true");
    if (storedFreeTransfers) setFreeTransfers(storedFreeTransfers);
    if (storedRiskProfile === "protect" || storedRiskProfile === "balanced" || storedRiskProfile === "chase") {
      setRiskProfile(storedRiskProfile);
    }
  }, [defaultManagerId]);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem(BUDGET_STORAGE_KEY, budget);
  }, [budget]);

  useEffect(() => {
    localStorage.setItem(HORIZON_STORAGE_KEY, horizon);
  }, [horizon]);

  useEffect(() => {
    localStorage.setItem(INCLUDE_UNAVAILABLE_KEY, String(includeUnavailable));
  }, [includeUnavailable]);

  useEffect(() => {
    localStorage.setItem(MANAGER_ID_KEY, managerId);
  }, [managerId]);

  useEffect(() => {
    localStorage.setItem(USE_MANAGER_KEY, String(useManagerSquad));
  }, [useManagerSquad]);

  useEffect(() => {
    localStorage.setItem(FREE_TRANSFERS_KEY, freeTransfers);
  }, [freeTransfers]);

  useEffect(() => {
    localStorage.setItem(RISK_PROFILE_KEY, riskProfile);
  }, [riskProfile]);

  const handleSolve = async () => {
    const numericBudget = Number(budget);
    const numericHorizon = Number(horizon);
    const numericFreeTransfers = Number(freeTransfers);

    if (Number.isNaN(numericBudget) || numericBudget <= 0) {
      setError("Enter a valid budget (e.g., 100.0).");
      return;
    }
    if (Number.isNaN(numericHorizon) || numericHorizon < 1 || numericHorizon > 5) {
      setError("Horizon must be between 1 and 5 gameweeks.");
      return;
    }
    if (Number.isNaN(numericFreeTransfers) || numericFreeTransfers < 0 || numericFreeTransfers > 5) {
      setError("Free transfers must be between 0 and 5.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let budgetValue = Math.round(numericBudget * 10);

      // If using manager squad, try to load their current budget
      if (useManagerSquad && managerId.trim()) {
        try {
          const summaryResponse = await fetch(`/api/fpl/entry/${managerId.trim()}/`);
          if (summaryResponse.ok) {
            const summary = await summaryResponse.json();
            const value = summary.last_deadline_value ?? 1000;
            const bank = summary.last_deadline_bank ?? 0;
            budgetValue = value + bank;
            setBudget((budgetValue / 10).toFixed(1));
          }
        } catch (err) {
          console.warn("Failed to load manager budget:", err);
        }
      }

      const managerParam =
        useManagerSquad && managerId.trim()
          ? `&manager_id=${encodeURIComponent(managerId.trim())}`
          : "";

      const response = await fetch(
        `/api/optimize-team/?budget=${budgetValue}&horizon=${numericHorizon}&include_unavailable=${includeUnavailable}&free_transfers=${numericFreeTransfers}&risk_profile=${riskProfile}${managerParam}`
      );

      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        // A 502/503 HTML page means the API instance restarted or ran out of
        // memory mid-solve; say so instead of surfacing a JSON parse error.
        throw new Error(
          response.ok
            ? "The optimizer returned an unexpected response. Please try again."
            : `The optimizer service is unavailable (HTTP ${response.status}). It may have restarted — try again in a moment, or shorten the horizon.`
        );
      }

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload?.error || "Failed to optimize team.");
      }

      const data = (await response.json()) as MILPResult;
      setResult(data);
      setActiveGWTab(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to optimize team.");
    } finally {
      setLoading(false);
    }
  };

  const currentGW = result ? result.gameweeks[activeGWTab] : null;

  return (
    <div className="optimizer-panel">
      <section className="glow-card optimizer-hero">
        <div className="glow-card-content">
          <div className="optimizer-header">
            <div>
              <div className="section-title">Build optimal squad</div>
              <p className="section-subtitle">
                Mixed-integer linear programming over your horizon: plans transfers, captain
                picks and chip timing against budget, formation and club limits.
              </p>
            </div>
            <button className="optimizer-action" onClick={handleSolve} disabled={loading}>
              {loading ? "Solving..." : "Solve Team"}
            </button>
          </div>

          <div className="optimizer-controls">
            <label className="optimizer-field">
              <span>Budget (£m)</span>
              <input
                type="number"
                min="80"
                max="120"
                step="0.1"
                value={budget}
                onChange={(event) => setBudget(event.target.value)}
              />
            </label>
            <label className="optimizer-field">
              <span>Horizon (GW)</span>
              <input
                type="number"
                min="1"
                max="5"
                step="1"
                value={horizon}
                onChange={(event) => setHorizon(event.target.value)}
              />
            </label>
            <label className="optimizer-field">
              <span>Free Transfers</span>
              <input
                type="number"
                min="0"
                max="5"
                step="1"
                value={freeTransfers}
                onChange={(event) => setFreeTransfers(event.target.value)}
              />
            </label>
            <label className="optimizer-field">
              <span>Manager ID (optional)</span>
              <input
                type="text"
                value={managerId}
                onChange={(event) => setManagerId(event.target.value)}
                placeholder="e.g. 123456"
              />
            </label>
            <label className="optimizer-field">
              <span>Rank strategy</span>
              <select
                value={riskProfile}
                onChange={(event) => setRiskProfile(event.target.value as "protect" | "balanced" | "chase")}
              >
                <option value="protect">Protect rank</option>
                <option value="balanced">Balanced</option>
                <option value="chase">Chase upside</option>
              </select>
            </label>
            <label className="optimizer-toggle">
              <input
                type="checkbox"
                checked={includeUnavailable}
                onChange={(event) => setIncludeUnavailable(event.target.checked)}
              />
              <span>Include flagged/injured</span>
            </label>
            <label className="optimizer-toggle">
              <input
                type="checkbox"
                checked={useManagerSquad}
                onChange={(event) => setUseManagerSquad(event.target.checked)}
              />
              <span>Use my squad</span>
            </label>
          </div>

          {error && <div className="optimizer-error">{error}</div>}
        </div>
      </section>

      {result && (
        <section className="glow-card optimizer-results">
          <div className="glow-card-content">
            {result.meta.projection_note && (
              <p className="aero-note optimizer-provenance">{result.meta.projection_note}</p>
            )}
            <div className="optimizer-summary">
              <div>
                <div className="section-title">MILP Solution</div>
                <p className="section-subtitle">
                  GW {result.meta.start_gameweek} → {result.meta.end_gameweek} • Objective: {result.meta.objective_value}
                  {result.meta.personalized ? ` • Team ${result.meta.manager_id}` : ""}
                </p>
              </div>
              <div className="summary-metrics">
                <div>
                  <span>Objective</span>
                  <strong>{result.meta.objective_value}</strong>
                </div>
                <div>
                  <span>Horizon</span>
                  <strong>{result.meta.horizon} GW</strong>
                </div>
                <div>
                  <span>Risk mode</span>
                  <strong>{result.meta.risk_profile}</strong>
                </div>
                <div>
                  <span>Budget</span>
                  <strong>£{formatCost(result.meta.budget)}m</strong>
                </div>
              </div>
            </div>

            {/* GW Tabs */}
            <div className="gw-tabs">
              {result.gameweeks.map((gw, idx) => (
                <button
                  key={gw.gameweek}
                  className={`gw-tab ${activeGWTab === idx ? "active" : ""}`}
                  onClick={() => setActiveGWTab(idx)}
                >
                  GW {gw.gameweek}
                </button>
              ))}
            </div>

            {currentGW && (
              <div className="gw-panel">
                {/* Chip Badges */}
                {currentGW.chips.length > 0 && (
                  <div className="chip-badges">
                    {currentGW.chips.map((chip) => (
                      <span key={chip} className="chip-badge">
                        {chip.toUpperCase()}
                      </span>
                    ))}
                  </div>
                )}

                {/* Transfer Panel */}
                <div className="transfer-panel">
                  <div className="transfer-section">
                    <h3>OUT</h3>
                    {currentGW.transfers.out.length > 0 ? (
                      <div className="transfer-grid">
                        {currentGW.transfers.out.map((player) => (
                          <div key={player.id} className="transfer-out">
                            <img src={player.image_url || ""} alt={player.web_name} />
                            <div className="transfer-info">
                              <div className="transfer-name">{player.web_name}</div>
                              <div className="transfer-cost">£{formatCost(player.now_cost)}m</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="no-transfers">No transfers out</p>
                    )}
                  </div>

                  <div className="transfer-arrow">→</div>

                  <div className="transfer-section">
                    <h3>IN</h3>
                    {currentGW.transfers.in.length > 0 ? (
                      <div className="transfer-grid">
                        {currentGW.transfers.in.map((player) => (
                          <div key={player.id} className="transfer-in">
                            <img src={player.image_url || ""} alt={player.web_name} />
                            <div className="transfer-info">
                              <div className="transfer-name">{player.web_name}</div>
                              <div className="transfer-cost">£{formatCost(player.now_cost)}m</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="no-transfers">No transfers in</p>
                    )}
                  </div>
                </div>

                {/* Transfer Summary */}
                <div className="transfer-summary">
                  <span>
                    {currentGW.transfers.count} transfer
                    {currentGW.transfers.count !== 1 ? "s" : ""} •{" "}
                    {currentGW.transfers.free_transfers} free •{" "}
                    {currentGW.transfers.paid_transfers} paid
                  </span>
                  {currentGW.transfers.paid_transfers > 0 && (
                    <span className="paid-transfer-warning">
                      -4 pts per paid transfer
                    </span>
                  )}
                </div>

                {/* Squad Grid */}
                <div className="squad-section">
                  <h3>Starters ({currentGW.squad.starters.length})</h3>
                  <div className="squad-grid">
                    {currentGW.squad.starters.map((player) => (
                      <div key={player.id} className="squad-card">
                        <div className="card-image">
                          <img src={player.image_url || ""} alt={player.web_name} />
                          {currentGW.captain?.id === player.id && (
                            <div className="captain-crown">👑</div>
                          )}
                        </div>
                        <div className="card-info">
                          <div className="card-name">{player.web_name}</div>
                          <div className="card-meta">{player.position}</div>
                          <div className="card-cost">£{formatCost(player.now_cost)}m</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="squad-section">
                  <h3>Bench ({currentGW.squad.bench.length})</h3>
                  <div className="squad-grid">
                    {currentGW.squad.bench.map((player) => (
                      <div key={player.id} className="squad-card bench">
                        <div className="card-image">
                          <img src={player.image_url || ""} alt={player.web_name} />
                        </div>
                        <div className="card-info">
                          <div className="card-name">{player.web_name}</div>
                          <div className="card-meta">{player.position}</div>
                          <div className="card-cost">£{formatCost(player.now_cost)}m</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
