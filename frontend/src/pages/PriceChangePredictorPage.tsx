import { useEffect, useState } from "react";
import "./PriceChangePredictorPage.css";

interface PriceSignalPlayer {
  id: number;
  web_name: string;
  team: string | null;
  now_cost: number;
  transfer_delta: number;
  signal: number;
  selected_by_percent: number | null;
  cost_change_event: number | null;
  status: string | null;
  image_url: string | null;
}

interface PredictorResponse {
  risers: PriceSignalPlayer[];
  fallers: PriceSignalPlayer[];
  limit: number;
}

const formatCost = (cost: number) => `£${(cost / 10).toFixed(1)}m`;

export function PriceChangePredictorPage() {
  const [data, setData] = useState<PredictorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/price-predictor/");
        if (!response.ok) throw new Error("Failed to load price predictors.");
        const payload = (await response.json()) as PredictorResponse;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load price predictors.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="page">
      <section className="glow-card predictor-hero">
        <div className="glow-card-content">
          <div className="section-title">📈 Price Change Predictor</div>
          <p className="section-subtitle">
            This is a momentum-based signal from transfers in/out. It is not an official FPL price predictor, but it
            highlights who is trending toward rises or drops.
          </p>
          {error && <div className="predictor-error">{error}</div>}
        </div>
      </section>

      <section className="glow-card predictor-board">
        <div className="glow-card-content">
          {loading && <div className="predictor-loading">Loading signals...</div>}
          {!loading && data && (
            <div className="predictor-grid">
              <div>
                <h3>Potential Risers</h3>
                <div className="predictor-list">
                  {data.risers.map((player) => (
                    <article key={player.id} className="predictor-card rise">
                      <img src={player.image_url || ""} alt={player.web_name} />
                      <div>
                        <div className="predictor-name">{player.web_name}</div>
                        <div className="predictor-meta">
                          {player.team || "—"} • {formatCost(player.now_cost)}
                        </div>
                      </div>
                      <div className="predictor-signal">
                        <span>Net {player.transfer_delta.toLocaleString()}</span>
                        <small>Momentum {player.signal}%</small>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
              <div>
                <h3>Potential Fallers</h3>
                <div className="predictor-list">
                  {data.fallers.map((player) => (
                    <article key={player.id} className="predictor-card fall">
                      <img src={player.image_url || ""} alt={player.web_name} />
                      <div>
                        <div className="predictor-name">{player.web_name}</div>
                        <div className="predictor-meta">
                          {player.team || "—"} • {formatCost(player.now_cost)}
                        </div>
                      </div>
                      <div className="predictor-signal">
                        <span>Net {player.transfer_delta.toLocaleString()}</span>
                        <small>Momentum {player.signal}%</small>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
