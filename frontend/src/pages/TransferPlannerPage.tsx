import { useEffect, useMemo, useState } from "react";
import "./TransferPlannerPage.css";

interface PlayerIndex {
  id: number;
  web_name: string;
  team: string | null;
  now_cost: number;
  element_type: number;
  ep_next: number | null;
}

interface TransferPlan {
  outId: number;
  inId: number;
}

interface BootstrapEvent {
  id: number;
  is_current: boolean;
}

interface BootstrapResponse {
  events: BootstrapEvent[];
}

interface ManagerPicksResponse {
  picks: Array<{ element: number }>;
}

const MANAGER_ID_KEY = "transfer_planner_manager_id";
const HORIZON_KEY = "transfer_planner_horizon";

const positionOrder = (elementType: number) => {
  switch (elementType) {
    case 1:
      return 1;
    case 2:
      return 2;
    case 3:
      return 3;
    case 4:
      return 4;
    default:
      return 5;
  }
};

const formatCost = (cost: number) => `£${(cost / 10).toFixed(1)}m`;

export function TransferPlannerPage() {
  const [managerId, setManagerId] = useState("");
  const [activeManagerId, setActiveManagerId] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(3);
  const [currentGw, setCurrentGw] = useState<number | null>(null);
  const [players, setPlayers] = useState<Map<number, PlayerIndex>>(new Map());
  const [baseSquad, setBaseSquad] = useState<number[]>([]);
  const [transfers, setTransfers] = useState<Record<number, TransferPlan[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedManager = localStorage.getItem(MANAGER_ID_KEY);
    const storedHorizon = localStorage.getItem(HORIZON_KEY);
    if (storedManager) {
      setManagerId(storedManager);
      setActiveManagerId(storedManager);
    }
    if (storedHorizon) {
      const parsed = Number(storedHorizon);
      if (!Number.isNaN(parsed)) setHorizon(parsed);
    }
  }, []);

  useEffect(() => {
    if (activeManagerId) {
      localStorage.setItem(MANAGER_ID_KEY, activeManagerId);
    }
  }, [activeManagerId]);

  useEffect(() => {
    localStorage.setItem(HORIZON_KEY, String(horizon));
  }, [horizon]);

  useEffect(() => {
    if (!activeManagerId) return;
    const key = `transfer_planner_transfers_${activeManagerId}`;
    const stored = localStorage.getItem(key);
    if (stored) {
      setTransfers(JSON.parse(stored) as Record<number, TransferPlan[]>);
    } else {
      setTransfers({});
    }
  }, [activeManagerId]);

  useEffect(() => {
    if (!activeManagerId) return;
    const key = `transfer_planner_transfers_${activeManagerId}`;
    localStorage.setItem(key, JSON.stringify(transfers));
  }, [transfers, activeManagerId]);

  const loadSquad = async () => {
    if (!managerId.trim()) {
      setError("Enter a manager ID first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [bootstrapRes, playersRes] = await Promise.all([
        fetch("/api/fpl/bootstrap-static/"),
        fetch("/api/players/?page=1&page_size=1000"),
      ]);

      if (!bootstrapRes.ok) throw new Error("Failed to fetch FPL bootstrap data.");
      if (!playersRes.ok) throw new Error("Failed to fetch player list.");

      const bootstrap = (await bootstrapRes.json()) as BootstrapResponse;
      const playersPayload = await playersRes.json();

      const currentEvent = bootstrap.events.find((event) => event.is_current) || bootstrap.events[0];
      if (!currentEvent) throw new Error("Unable to detect current gameweek.");

      const picksRes = await fetch(`/api/fpl/entry/${managerId.trim()}/event/${currentEvent.id}/picks/`);
      if (!picksRes.ok) throw new Error("Failed to fetch manager picks.");

      const picks = (await picksRes.json()) as ManagerPicksResponse;

      const playersMap = new Map<number, PlayerIndex>();
      (playersPayload.players as PlayerIndex[]).forEach((player) => {
        playersMap.set(player.id, player);
      });

      const squadIds = picks.picks.map((pick) => pick.element);

      setPlayers(playersMap);
      setCurrentGw(currentEvent.id);
      setBaseSquad(squadIds);
      setActiveManagerId(managerId.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load planner data.");
    } finally {
      setLoading(false);
    }
  };

  const gameweeks = useMemo(() => {
    if (!currentGw) return [];
    return Array.from({ length: horizon }, (_, idx) => currentGw + idx + 1);
  }, [currentGw, horizon]);

  const applyTransfers = (squad: number[], transferList: TransferPlan[]) => {
    let next = [...squad];
    transferList.forEach((transfer) => {
      const outIdx = next.indexOf(transfer.outId);
      if (outIdx === -1 || next.includes(transfer.inId)) return;
      next[outIdx] = transfer.inId;
    });
    return next;
  };

  const plannedSquads = useMemo(() => {
    if (!baseSquad.length) return [];
    const squads: Array<{ gw: number; squad: number[] }> = [];
    let previous = [...baseSquad];

    gameweeks.forEach((gw) => {
      const planned = applyTransfers(previous, transfers[gw] || []);
      squads.push({ gw, squad: planned });
      previous = planned;
    });

    return squads;
  }, [baseSquad, gameweeks, transfers]);

  const addTransfer = (gw: number, outId: number, inId: number) => {
    if (!outId || !inId || outId === inId) return;
    setTransfers((prev) => {
      const next = { ...prev };
      const list = [...(next[gw] || [])];
      list.push({ outId, inId });
      next[gw] = list;
      return next;
    });
  };

  const removeTransfer = (gw: number, index: number) => {
    setTransfers((prev) => {
      const next = { ...prev };
      const list = [...(next[gw] || [])];
      list.splice(index, 1);
      next[gw] = list;
      return next;
    });
  };

  return (
    <div className="page">
      <section className="glow-card planner-hero">
        <div className="glow-card-content">
          <div className="section-title">🧭 Transfer Planner</div>
          <p className="section-subtitle">
            Map out transfers across the next few gameweeks. We keep your manager ID in local storage so the planner
            stays ready even after weeks away.
          </p>

          <div className="planner-controls">
            <label>
              Manager ID
              <input
                value={managerId}
                onChange={(event) => setManagerId(event.target.value)}
                placeholder="e.g. 123456"
              />
            </label>
            <label>
              Horizon (GW)
              <input
                type="number"
                min="1"
                max="5"
                value={horizon}
                onChange={(event) => setHorizon(Number(event.target.value))}
              />
            </label>
            <button onClick={loadSquad} disabled={loading}>
              {loading ? "Loading..." : "Load Squad"}
            </button>
          </div>

          {error && <div className="planner-error">{error}</div>}
        </div>
      </section>

      {currentGw && baseSquad.length > 0 && (
        <section className="glow-card planner-board">
          <div className="glow-card-content">
            <div className="planner-grid">
              {plannedSquads.map(({ gw, squad }) => {
                const outOptions = squad.map((id) => players.get(id)).filter(Boolean) as PlayerIndex[];
                return (
                  <div key={gw} className="planner-column">
                    <h3>GW {gw}</h3>
                    <div className="planner-transfer-row">
                      <select id={`out-${gw}`}>
                        <option value="">Transfer out</option>
                        {outOptions.map((player) => (
                          <option key={player.id} value={player.id}>
                            {player.web_name} ({formatCost(player.now_cost)})
                          </option>
                        ))}
                      </select>
                      <select id={`in-${gw}`}>
                        <option value="">Transfer in</option>
                        {[...players.values()]
                          .sort((a, b) => a.web_name.localeCompare(b.web_name))
                          .map((player) => (
                            <option key={player.id} value={player.id}>
                              {player.web_name} ({formatCost(player.now_cost)})
                            </option>
                          ))}
                      </select>
                      <button
                        onClick={() => {
                          const outSelect = document.getElementById(`out-${gw}`) as HTMLSelectElement | null;
                          const inSelect = document.getElementById(`in-${gw}`) as HTMLSelectElement | null;
                          if (!outSelect || !inSelect) return;
                          addTransfer(gw, Number(outSelect.value), Number(inSelect.value));
                          outSelect.value = "";
                          inSelect.value = "";
                        }}
                      >
                        Add
                      </button>
                    </div>

                    <div className="planner-transfer-list">
                      {(transfers[gw] || []).map((transfer, index) => {
                        const outPlayer = players.get(transfer.outId);
                        const inPlayer = players.get(transfer.inId);
                        return (
                          <div key={`${transfer.outId}-${transfer.inId}-${index}`}>
                            <span>{outPlayer?.web_name || "?"}</span>
                            <span>→</span>
                            <span>{inPlayer?.web_name || "?"}</span>
                            <button onClick={() => removeTransfer(gw, index)}>Remove</button>
                          </div>
                        );
                      })}
                    </div>

                    <div className="planner-squad">
                      {squad
                        .map((id) => players.get(id))
                        .filter(Boolean)
                        .sort((a, b) => positionOrder(a!.element_type) - positionOrder(b!.element_type))
                        .map((player) => (
                          <article key={player!.id} className="planner-player">
                            <div>
                              <strong>{player!.web_name}</strong>
                              <span>{player!.team || "—"}</span>
                            </div>
                            <div className="planner-meta">
                              <span>{formatCost(player!.now_cost)}</span>
                              <span>{player!.ep_next ? `${player!.ep_next.toFixed(1)} xPts` : "—"}</span>
                            </div>
                          </article>
                        ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
