import { useEffect, useId, useMemo, useState } from "react";
import "./PriceChangePredictorPage.css";
import { PlayerModal } from "../components/PlayerModal";

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

interface PriceHistoryPoint {
  timestamp: string;
  value: number;
}

interface PriceHistorySeries {
  player_id: number;
  web_name: string;
  team: string | null;
  direction: "in" | "out";
  metric: "transfers" | "ownership";
  points: PriceHistoryPoint[];
}

interface PriceHistoryResponse {
  snapshot_count: number;
  latest_snapshot: string;
  series: PriceHistorySeries[];
}

interface PlayerSearchResult {
  id: number;
  web_name: string;
  team: string | null;
  now_cost: number;
  image_url: string | null;
}

const formatCost = (cost: number) => `£${(cost / 10).toFixed(1)}m`;

function Sparkline({
  series,
  accent,
}: {
  series: PriceHistorySeries;
  accent: "rise" | "fall";
}) {
  const gradientId = useId();
  const width = 180;
  const height = 70;
  const padding = 6;
  const values = series.points.map((p) => p.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const range = max - min || 1;

  const points = series.points.map((point, index) => {
    const x = padding + (index / Math.max(1, values.length - 1)) * (width - padding * 2);
    const y = padding + ((max - point.value) / range) * (height - padding * 2);
    return [x, y];
  });

  const linePath = points.length
    ? `M ${points.map((p) => p.join(",")).join(" L ")}`
    : "";
  const areaPath = points.length
    ? `${linePath} L ${width - padding},${height - padding} L ${padding},${height - padding} Z`
    : "";

  return (
    <svg className={`sparkline ${accent}`} viewBox={`0 0 ${width} ${height}`} role="img">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={accent === "rise" ? "#22c55e" : "#ef4444"} stopOpacity="0.55" />
          <stop offset="100%" stopColor={accent === "rise" ? "#22c55e" : "#ef4444"} stopOpacity="0.05" />
        </linearGradient>
      </defs>
      {areaPath && <path d={areaPath} fill={`url(#${gradientId})`} />}
      {linePath && (
        <path
          d={linePath}
          fill="none"
          stroke={accent === "rise" ? "#22c55e" : "#ef4444"}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

function MultiLineChart({
  series,
  yLabel,
  valueFormatter,
}: {
  series: PriceHistorySeries[];
  yLabel: string;
  valueFormatter?: (value: number) => string;
}) {
  const width = 720;
  const height = 280;
  const padding = 44;
  const rightPadding = 56;
  const palette = ["#38bdf8", "#60a5fa", "#a78bfa", "#f97316", "#22c55e"];
  const formatValue = valueFormatter ?? ((value: number) => value.toFixed(1));

  const allValues = series.flatMap((item) => item.points.map((point) => point.value));
  const min = Math.min(...allValues, 0);
  const max = Math.max(...allValues, 1);
  const range = max - min || 1;
  const pointCount = Math.max(...series.map((item) => item.points.length), 2);
  const chartWidth = width - padding - rightPadding;
  const chartHeight = height - padding * 2;

  const xFor = (index: number) => padding + (index / (pointCount - 1)) * chartWidth;
  const yFor = (value: number) => padding + ((max - value) / range) * chartHeight;
  const xLabels = series[0]?.points.length ? [0, Math.floor((pointCount - 1) / 2), pointCount - 1] : [];
  const yTicks = 4;
  const yLabels = Array.from({ length: yTicks + 1 }, (_, idx) => max - (range * idx) / yTicks);

  return (
    <div className="ownership-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <defs>
          <linearGradient id="ownership-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#050914" />
            <stop offset="100%" stopColor="#0b1226" />
          </linearGradient>
          {palette.map((color, idx) => (
            <linearGradient key={color} id={`line-${idx}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={color} stopOpacity="0.5" />
              <stop offset="60%" stopColor={color} stopOpacity="1" />
              <stop offset="100%" stopColor={color} stopOpacity="0.6" />
            </linearGradient>
          ))}
        </defs>
        <rect x="0" y="0" width={width} height={height} fill="url(#ownership-bg)" />
        <g className="ownership-grid">
          {Array.from({ length: yTicks + 1 }).map((_, idx) => {
            const y = padding + (idx / yTicks) * chartHeight;
            return (
              <line
                key={`y-${idx}`}
                x1={padding}
                x2={width - rightPadding}
                y1={y}
                y2={y}
              />
            );
          })}
          {Array.from({ length: 5 }).map((_, idx) => {
            const x = padding + (idx / 4) * chartWidth;
            return (
              <line
                key={`x-${idx}`}
                x1={x}
                x2={x}
                y1={padding}
                y2={height - padding}
              />
            );
          })}
        </g>
        <g className="ownership-axis">
          {yLabels.map((value, idx) => {
            const y = yFor(value);
            return (
              <g key={`y-${idx}`}>
                <text x={padding - 8} y={y + 4} textAnchor="end">
                  {formatValue(Math.max(0, value))}
                </text>
              </g>
            );
          })}
          {xLabels.map((index) => {
            const point = series[0]?.points[index];
            if (!point) return null;
            const date = new Date(point.timestamp);
            const label = date.toLocaleDateString("en-GB", { month: "short", day: "numeric" });
            const x = xFor(index);
            return (
              <text key={`x-${index}`} x={x} y={height - 8} textAnchor="middle">{label}</text>
            );
          })}
          <text x={padding} y={padding - 10} className="ownership-axis-label">{yLabel}</text>
          <text x={width / 2} y={height - 2} textAnchor="middle" className="ownership-axis-label">Date</text>
        </g>
        {series.map((item, idx) => {
          const color = palette[idx % palette.length];
          const points = item.points.map((point, index) => [xFor(index), yFor(point.value)]);
          const path = points.length ? `M ${points.map((p) => p.join(",")).join(" L ")}` : "";
          const lastPoint = points[points.length - 1];
          return (
            <g key={item.player_id}>
              <path
                d={path}
                fill="none"
                stroke={`url(#line-${idx % palette.length})`}
                strokeWidth="2.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ filter: `drop-shadow(0 0 6px ${color})` }}
              />
              {lastPoint && (
                <circle
                  cx={lastPoint[0]}
                  cy={lastPoint[1]}
                  r="4.5"
                  fill={color}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                />
              )}
            </g>
          );
        })}
      </svg>
      <div className="ownership-legend">
        {series.map((item, idx) => (
          <div key={item.player_id} className="ownership-legend-item">
            <span className="legend-dot" style={{ background: palette[idx % palette.length] }} />
            <span>
              {item.web_name} {item.team ? `(${item.team})` : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PriceChangePredictorPage() {
  const [data, setData] = useState<PredictorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalPlayerId, setModalPlayerId] = useState<number | null>(null);

  const [historySeries, setHistorySeries] = useState<PriceHistorySeries[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [pulseSeries, setPulseSeries] = useState<PriceHistorySeries[]>([]);
  const [pulseLoading, setPulseLoading] = useState(false);
  const [pulseDirection, setPulseDirection] = useState<"in" | "out">("in");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchDirection, setSearchDirection] = useState<"in" | "out">("in");
  const [trackedPlayers, setTrackedPlayers] = useState<
    Array<{ id: number; web_name: string; team: string | null; direction: "in" | "out" }>
  >([]);
  const [customSeries, setCustomSeries] = useState<PriceHistorySeries[]>([]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/price-predictor/?limit=10");
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

  useEffect(() => {
    const loadHistory = async () => {
      setHistoryLoading(true);
      try {
        const response = await fetch("/api/price-predictor/history/?top=5&limit=30");
        if (!response.ok) throw new Error("Failed to load transfer history.");
        const payload = (await response.json()) as PriceHistoryResponse;
        setHistorySeries(payload.series || []);
      } catch (err) {
        console.warn(err);
      } finally {
        setHistoryLoading(false);
      }
    };
    loadHistory();
  }, []);

  useEffect(() => {
    const loadPulse = async () => {
      setPulseLoading(true);
      try {
        const response = await fetch(
          `/api/price-predictor/history/?top=5&limit=30&direction=${pulseDirection}`
        );
        if (!response.ok) throw new Error("Failed to load transfer pulse.");
        const payload = (await response.json()) as PriceHistoryResponse;
        setPulseSeries(payload.series || []);
      } catch (err) {
        console.warn(err);
      } finally {
        setPulseLoading(false);
      }
    };
    loadPulse();
  }, [pulseDirection]);

  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    const handle = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const response = await fetch(`/api/players/?search=${encodeURIComponent(searchQuery)}&page=1&page_size=8`);
        if (!response.ok) throw new Error("Search failed.");
        const payload = await response.json();
        setSearchResults(payload.players as PlayerSearchResult[]);
      } catch (err) {
        console.warn(err);
      } finally {
        setSearchLoading(false);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [searchQuery]);

  useEffect(() => {
    if (trackedPlayers.length === 0) {
      setCustomSeries([]);
      return;
    }
    const ids = trackedPlayers.map((player) => player.id).join(",");
    const directions = trackedPlayers.map((player) => player.direction).join(",");
    const loadCustom = async () => {
      try {
        const response = await fetch(
          `/api/price-predictor/history/?player_ids=${ids}&directions=${directions}&limit=30`
        );
        if (!response.ok) throw new Error("Failed to load player history.");
        const payload = (await response.json()) as PriceHistoryResponse;
        setCustomSeries(payload.series || []);
      } catch (err) {
        console.warn(err);
      }
    };
    loadCustom();
  }, [trackedPlayers]);

  const topIn = useMemo(() => historySeries.filter((series) => series.direction === "in"), [historySeries]);
  const topOut = useMemo(() => historySeries.filter((series) => series.direction === "out"), [historySeries]);

  const addTrackedPlayer = (player: PlayerSearchResult) => {
    const alreadyAdded = trackedPlayers.some(
      (tracked) => tracked.id === player.id && tracked.direction === searchDirection
    );
    if (alreadyAdded) return;
    setTrackedPlayers((prev) => [
      ...prev,
      { id: player.id, web_name: player.web_name, team: player.team, direction: searchDirection },
    ]);
    setSearchQuery("");
    setSearchResults([]);
  };

  const removeTrackedPlayer = (playerId: number, direction: "in" | "out") => {
    setTrackedPlayers((prev) => prev.filter((player) => !(player.id === playerId && player.direction === direction)));
  };

  const renderSeriesCards = (seriesList: PriceHistorySeries[]) => {
    return seriesList.map((series) => {
      const values = series.points.map((p) => p.value);
      const delta = values.length ? values[values.length - 1] - values[0] : 0;
      const accent = series.direction === "in" ? "rise" : "fall";
      return (
        <article
          key={`${series.player_id}-${series.direction}`}
          className={`predictor-graph-card ${accent} clickable`}
          onClick={() => setModalPlayerId(series.player_id)}
        >
          <div>
            <div className="predictor-name">{series.web_name}</div>
            <div className="predictor-meta">
              {series.team || "—"} • {series.direction === "in" ? "Transfers In" : "Transfers Out"}
            </div>
            <div className={`predictor-delta ${delta >= 0 ? "positive" : "negative"}`}>
              {delta >= 0 ? "+" : ""}
              {delta.toLocaleString()}
            </div>
          </div>
          <Sparkline series={series} accent={accent} />
        </article>
      );
    });
  };

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

      <section className="glow-card predictor-transfer">
        <div className="glow-card-content">
          <div className="predictor-chart-header">
            <div>
              <div className="section-title">Transfer Pulse</div>
              <p className="section-subtitle">Top 5 transfer momentum trends from recent snapshots.</p>
            </div>
            <label className="predictor-filter">
              <span>Show</span>
              <select value={pulseDirection} onChange={(event) => setPulseDirection(event.target.value as "in" | "out")}>
                <option value="in">Most transferred in</option>
                <option value="out">Most transferred out</option>
              </select>
            </label>
            {pulseLoading && <div className="predictor-loading">Loading pulse...</div>}
          </div>
          {pulseSeries.length > 0 && (
            <MultiLineChart
              series={pulseSeries}
              yLabel="Transfers"
              valueFormatter={(value) => Math.round(value).toLocaleString()}
            />
          )}
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
                    <article
                      key={player.id}
                      className="predictor-card rise clickable"
                      onClick={() => setModalPlayerId(player.id)}
                    >
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
                    <article
                      key={player.id}
                      className="predictor-card fall clickable"
                      onClick={() => setModalPlayerId(player.id)}
                    >
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

      <section className="glow-card predictor-charts">
        <div className="glow-card-content">
          <div className="predictor-chart-header">
            <div>
              <div className="section-title">Transfer Momentum</div>
              <p className="section-subtitle">Top 5 movers with stock-style momentum charts.</p>
            </div>
            {historyLoading && <div className="predictor-loading">Loading charts...</div>}
          </div>
          <div className="predictor-chart-grid">
            <div>
              <h3>Top 5 In</h3>
              <div className="predictor-chart-list">{renderSeriesCards(topIn)}</div>
            </div>
            <div>
              <h3>Top 5 Out</h3>
              <div className="predictor-chart-list">{renderSeriesCards(topOut)}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="glow-card predictor-custom">
        <div className="glow-card-content">
          <div className="section-title">Track Players</div>
          <p className="section-subtitle">Search, click, and add players to plot their transfer trend lines.</p>
          <div className="predictor-search">
            <div className="predictor-search-input">
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search player..."
              />
              {searchLoading && <span className="predictor-search-loading">Searching...</span>}
              {searchResults.length > 0 && (
                <div className="predictor-search-results">
                  {searchResults.map((player) => (
                    <button
                      key={player.id}
                      type="button"
                      onClick={() => addTrackedPlayer(player)}
                    >
                      <span>{player.web_name}</span>
                      <span className="predictor-search-meta">{player.team || "—"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <label className="predictor-search-direction">
              Direction
              <select value={searchDirection} onChange={(event) => setSearchDirection(event.target.value as "in" | "out")}>
                <option value="in">Transfers In</option>
                <option value="out">Transfers Out</option>
              </select>
            </label>
          </div>

          {trackedPlayers.length === 0 && <div className="predictor-empty">No players tracked yet.</div>}
          {trackedPlayers.length > 0 && (
            <div className="predictor-chart-list">
              {customSeries.map((series) => (
                <article
                  key={`${series.player_id}-${series.direction}`}
                  className={`predictor-graph-card ${series.direction === "in" ? "rise" : "fall"} clickable`}
                  onClick={() => setModalPlayerId(series.player_id)}
                >
                  <div>
                    <div className="predictor-name">{series.web_name}</div>
                    <div className="predictor-meta">
                      {series.team || "—"} • {series.direction === "in" ? "Transfers In" : "Transfers Out"}
                    </div>
                    <button
                      className="predictor-remove"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        removeTrackedPlayer(series.player_id, series.direction);
                      }}
                    >
                      Remove
                    </button>
                  </div>
                  <Sparkline series={series} accent={series.direction === "in" ? "rise" : "fall"} />
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {modalPlayerId !== null && (
        <PlayerModal
          playerId={modalPlayerId}
          onClose={() => setModalPlayerId(null)}
        />
      )}
    </div>
  );
}
