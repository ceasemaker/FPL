import { useEffect, useMemo, useState } from "react";
import "./OptimizeTeamPage.css";

interface OptimizedPlayer {
  id: number;
  web_name: string;
  team_short_name: string | null;
  position: string;
  now_cost: number;
  predicted_points: number;
  starter: boolean;
  image_url: string | null;
}

interface OptimizedTeamResponse {
  budget: number;
  budget_remaining: number;
  horizon: number;
  current_gameweek: number;
  start_gameweek: number;
  end_gameweek: number;
  max_per_team: number;
  formation: string;
  total_cost: number;
  total_predicted_points: number;
  players: OptimizedPlayer[];
}

const BUDGET_STORAGE_KEY = "optimizer_budget";
const HORIZON_STORAGE_KEY = "optimizer_horizon";
const INCLUDE_UNAVAILABLE_KEY = "optimizer_include_unavailable";
const MANAGER_ID_KEY = "optimizer_manager_id";
const USE_MANAGER_KEY = "optimizer_use_manager_squad";

const formatCost = (cost: number) => (cost / 10).toFixed(1);

export function OptimizeTeamPage() {
  const [budget, setBudget] = useState<string>("100.0");
  const [horizon, setHorizon] = useState<string>("3");
  const [includeUnavailable, setIncludeUnavailable] = useState<boolean>(false);
  const [managerId, setManagerId] = useState<string>("");
  const [useManagerSquad, setUseManagerSquad] = useState<boolean>(false);
  const [team, setTeam] = useState<OptimizedTeamResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedBudget = localStorage.getItem(BUDGET_STORAGE_KEY);
    const storedHorizon = localStorage.getItem(HORIZON_STORAGE_KEY);
    const storedInclude = localStorage.getItem(INCLUDE_UNAVAILABLE_KEY);
    const storedManager = localStorage.getItem(MANAGER_ID_KEY);
    const storedUseManager = localStorage.getItem(USE_MANAGER_KEY);

    if (storedBudget) setBudget(storedBudget);
    if (storedHorizon) setHorizon(storedHorizon);
    if (storedInclude) setIncludeUnavailable(storedInclude === "true");
    if (storedManager) setManagerId(storedManager);
    if (storedUseManager) setUseManagerSquad(storedUseManager === "true");
  }, []);

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

  const handleSolve = async () => {
    const numericBudget = Number(budget);
    const numericHorizon = Number(horizon);

    if (Number.isNaN(numericBudget) || numericBudget <= 0) {
      setError("Enter a valid budget (e.g., 100.0).");
      return;
    }
    if (Number.isNaN(numericHorizon) || numericHorizon < 1 || numericHorizon > 5) {
      setError("Horizon must be between 1 and 5 gameweeks.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let budgetValue = Math.round(numericBudget * 10);

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
        `/api/optimize-team/?budget=${budgetValue}&horizon=${numericHorizon}&include_unavailable=${includeUnavailable}${managerParam}`
      );

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload?.error || "Failed to optimize team.");
      }

      const data = (await response.json()) as OptimizedTeamResponse;
      setTeam(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to optimize team.");
    } finally {
      setLoading(false);
    }
  };

  const grouped = useMemo(() => {
    if (!team) return null;
    const starters = team.players.filter((p) => p.starter);
    const bench = team.players.filter((p) => !p.starter);
    const groupBy = (players: OptimizedPlayer[]) =>
      players.reduce<Record<string, OptimizedPlayer[]>>((acc, player) => {
        acc[player.position] = acc[player.position] || [];
        acc[player.position].push(player);
        return acc;
      }, {});
    return {
      starters: groupBy(starters),
      bench: groupBy(bench),
    };
  }, [team]);

  return (
    <div className="page">
      <section className="glow-card optimizer-hero">
        <div className="glow-card-content">
          <div className="optimizer-header">
            <div>
              <div className="section-title">🧠 Team Optimizer</div>
          <p className="section-subtitle">
            Build a best-guess squad using predicted points for upcoming gameweeks. Toggle your manager ID to optimize
            your current squad or leave it off for the best overall wildcard suggestion.
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
              <span>Projection Horizon (GW)</span>
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
              <span>Manager ID (optional)</span>
              <input
                type="text"
                value={managerId}
                onChange={(event) => setManagerId(event.target.value)}
                placeholder="e.g. 123456"
              />
            </label>
            <label className="optimizer-toggle">
              <input
                type="checkbox"
                checked={includeUnavailable}
                onChange={(event) => setIncludeUnavailable(event.target.checked)}
              />
              <span>Include flagged/injured players</span>
            </label>
            <label className="optimizer-toggle">
              <input
                type="checkbox"
                checked={useManagerSquad}
                onChange={(event) => setUseManagerSquad(event.target.checked)}
              />
              <span>Use my current squad only</span>
            </label>
          </div>

          {error && <div className="optimizer-error">{error}</div>}
        </div>
      </section>

      {team && grouped && (
        <section className="glow-card optimizer-results">
          <div className="glow-card-content">
            <div className="optimizer-summary">
              <div>
                <div className="section-title">Optimized Squad</div>
                <p className="section-subtitle">
                  GW {team.start_gameweek} → {team.end_gameweek} projection • Formation {team.formation}
                </p>
              </div>
              <div className="summary-metrics">
                <div>
                  <span>Total xPts</span>
                  <strong>{team.total_predicted_points.toFixed(1)}</strong>
                </div>
                <div>
                  <span>Total Cost</span>
                  <strong>£{formatCost(team.total_cost)}m</strong>
                </div>
                <div>
                  <span>Remaining</span>
                  <strong>£{formatCost(team.budget_remaining)}m</strong>
                </div>
              </div>
            </div>

            <div className="optimizer-lineup">
              <div>
                <h3>Starters</h3>
                {Object.entries(grouped.starters).map(([position, players]) => (
                  <div key={position} className="optimizer-position">
                    <h4>{position}</h4>
                    <div className="optimizer-grid">
                      {players.map((player) => (
                        <article key={player.id} className="optimizer-card starter">
                          <img src={player.image_url || ""} alt={player.web_name} />
                          <div>
                            <div className="optimizer-name">{player.web_name}</div>
                            <div className="optimizer-meta">
                              {player.team_short_name || "—"} • £{formatCost(player.now_cost)}m
                            </div>
                          </div>
                          <div className="optimizer-points">{player.predicted_points.toFixed(1)} xPts</div>
                        </article>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <h3>Bench</h3>
                {Object.entries(grouped.bench).map(([position, players]) => (
                  <div key={position} className="optimizer-position">
                    <h4>{position}</h4>
                    <div className="optimizer-grid">
                      {players.map((player) => (
                        <article key={player.id} className="optimizer-card bench">
                          <img src={player.image_url || ""} alt={player.web_name} />
                          <div>
                            <div className="optimizer-name">{player.web_name}</div>
                            <div className="optimizer-meta">
                              {player.team_short_name || "—"} • £{formatCost(player.now_cost)}m
                            </div>
                          </div>
                          <div className="optimizer-points">{player.predicted_points.toFixed(1)} xPts</div>
                        </article>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
