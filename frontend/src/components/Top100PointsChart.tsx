import { useState, useRef, useEffect } from "react";
import { useTop100Chart } from "../hooks/useTop100Data";
import { ChartDataPoint } from "../types";
import "./Top100PointsChart.css";

export function Top100PointsChart() {
  const [entryId, setEntryId] = useState<number | undefined>();
  const [inputValue, setInputValue] = useState("");
  const { data, isLoading, error, refetch } = useTop100Chart(entryId);

  const handleAddTeam = () => {
    const id = parseInt(inputValue, 10);
    if (!isNaN(id) && id > 0) {
      setEntryId(id);
      refetch(id);
    }
  };

  const handleClearTeam = () => {
    setEntryId(undefined);
    setInputValue("");
    refetch(undefined);
  };

  return (
    <section className="glow-card points-chart-section">
      <div className="glow-card-content">
        <header className="chart-header">
          <div className="section-title">📈 Performance Tracker</div>
          <p className="chart-subtitle">
            Compare Top 100 Template vs Average Points per Gameweek
          </p>
        </header>

        {/* User Team Input */}
        <div className="team-input-container">
          <div className="team-input-group">
            <input
              type="text"
              placeholder="Enter your FPL Team ID"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddTeam()}
              className="team-input"
            />
            <button onClick={handleAddTeam} className="btn-add-team">
              Add My Team
            </button>
            {entryId && (
              <button onClick={handleClearTeam} className="btn-clear-team">
                ✕
              </button>
            )}
          </div>
          {data?.user_info && (
            <div className="user-info-badge">
              <span className="user-name">{data.user_info.player_name}</span>
              <span className="user-team-name">{data.user_info.entry_name}</span>
              <span className="user-rank">
                Rank: {data.user_info.overall_rank?.toLocaleString()}
              </span>
            </div>
          )}
        </div>

        {/* Chart */}
        {error ? (
          <p className="error-message">Failed to load chart data</p>
        ) : isLoading ? (
          <div className="chart-skeleton" />
        ) : data?.chart_data && data.chart_data.length > 0 ? (
          <TradingChart
            data={data.chart_data}
            showUserLine={!!entryId}
          />
        ) : (
          <p className="no-data-message">
            No chart data available. Run the Top 100 sync first.
          </p>
        )}

        {/* Legend */}
        <div className="chart-legend">
          <div className="legend-item">
            <span className="legend-color template" />
            <span>Template Team Points</span>
          </div>
          <div className="legend-item">
            <span className="legend-color average" />
            <span>Top 100 Average</span>
          </div>
          {entryId && (
            <div className="legend-item">
              <span className="legend-color user" />
              <span>Your Team</span>
            </div>
          )}
          <div className="legend-item">
            <span className="legend-color range" />
            <span>High/Low Range</span>
          </div>
        </div>
      </div>
    </section>
  );
}

interface TradingChartProps {
  data: ChartDataPoint[];
  showUserLine: boolean;
}

function TradingChart({ data, showUserLine }: TradingChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    data: ChartDataPoint;
  } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size
    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = 300 * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = "300px";
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = 300;
    const padding = { top: 20, right: 20, bottom: 40, left: 50 };

    // Calculate ranges
    const allValues = data.flatMap((d) => [
      d.template_points,
      d.average_points,
      d.highest_points ?? 0,
      d.lowest_points ?? 0,
      d.user_points ?? 0,
    ].filter(v => v > 0));
    
    const minVal = Math.min(...allValues) * 0.9;
    const maxVal = Math.max(...allValues) * 1.05;

    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Helper functions
    const xScale = (i: number) =>
      padding.left + (i / (data.length - 1)) * chartWidth;
    const yScale = (v: number) =>
      padding.top + (1 - (v - minVal) / (maxVal - minVal)) * chartHeight;

    // Clear canvas
    ctx.fillStyle = "#0d0d1a";
    ctx.fillRect(0, 0, width, height);

    // Draw grid
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 1;

    // Horizontal grid lines
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (i / gridLines) * chartHeight;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      // Y-axis labels
      const value = maxVal - (i / gridLines) * (maxVal - minVal);
      ctx.fillStyle = "#a1a1aa";
      ctx.font = "11px Inter, sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(Math.round(value).toString(), padding.left - 8, y + 4);
    }

    // Draw high/low range area
    if (data[0].highest_points !== null) {
      ctx.fillStyle = "rgba(99, 102, 241, 0.1)";
      ctx.beginPath();
      ctx.moveTo(xScale(0), yScale(data[0].highest_points ?? 0));
      
      // Upper line (highest)
      data.forEach((d, i) => {
        if (d.highest_points !== null) {
          ctx.lineTo(xScale(i), yScale(d.highest_points));
        }
      });
      
      // Lower line (lowest) - reverse
      for (let i = data.length - 1; i >= 0; i--) {
        if (data[i].lowest_points !== null) {
          ctx.lineTo(xScale(i), yScale(data[i].lowest_points!));
        }
      }
      
      ctx.closePath();
      ctx.fill();
    }

    // Draw template line
    ctx.strokeStyle = "#22c55e";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    data.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.template_points);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw average line
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    data.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.average_points);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw user line if present
    if (showUserLine) {
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 2;
      ctx.beginPath();
      let started = false;
      data.forEach((d, i) => {
        if (d.user_points !== null) {
          const x = xScale(i);
          const y = yScale(d.user_points);
          if (!started) {
            ctx.moveTo(x, y);
            started = true;
          } else {
            ctx.lineTo(x, y);
          }
        }
      });
      ctx.stroke();
    }

    // Draw data points
    data.forEach((d, i) => {
      const x = xScale(i);

      // Template point
      ctx.fillStyle = "#22c55e";
      ctx.beginPath();
      ctx.arc(x, yScale(d.template_points), 4, 0, Math.PI * 2);
      ctx.fill();

      // Average point
      ctx.fillStyle = "#6366f1";
      ctx.beginPath();
      ctx.arc(x, yScale(d.average_points), 3, 0, Math.PI * 2);
      ctx.fill();

      // User point
      if (d.user_points !== null && showUserLine) {
        ctx.fillStyle = "#f59e0b";
        ctx.beginPath();
        ctx.arc(x, yScale(d.user_points), 4, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // X-axis labels (gameweeks)
    ctx.fillStyle = "#a1a1aa";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "center";
    
    const labelEvery = data.length > 20 ? 3 : data.length > 10 ? 2 : 1;
    data.forEach((d, i) => {
      if (i % labelEvery === 0 || i === data.length - 1) {
        ctx.fillText(`GW${d.game_week}`, xScale(i), height - 10);
      }
    });

    // Mouse interaction
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      
      // Find closest data point
      let closestIdx = 0;
      let closestDist = Infinity;
      data.forEach((_, i) => {
        const dist = Math.abs(x - xScale(i));
        if (dist < closestDist) {
          closestDist = dist;
          closestIdx = i;
        }
      });

      if (closestDist < 30) {
        setTooltip({
          x: xScale(closestIdx),
          y: e.clientY - rect.top,
          data: data[closestIdx],
        });
      } else {
        setTooltip(null);
      }
    };

    const handleMouseLeave = () => setTooltip(null);

    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [data, showUserLine]);

  return (
    <div className="trading-chart-container" ref={containerRef}>
      <canvas ref={canvasRef} className="trading-chart" />
      {tooltip && (
        <div
          className="chart-tooltip"
          style={{
            left: tooltip.x,
            top: Math.max(10, tooltip.y - 80),
          }}
        >
          <div className="tooltip-header">GW{tooltip.data.game_week}</div>
          <div className="tooltip-row template">
            <span>Template:</span>
            <strong>{tooltip.data.template_points} pts</strong>
          </div>
          <div className="tooltip-row average">
            <span>Average:</span>
            <strong>{tooltip.data.average_points.toFixed(1)} pts</strong>
          </div>
          {tooltip.data.user_points !== null && (
            <div className="tooltip-row user">
              <span>Your Team:</span>
              <strong>{tooltip.data.user_points} pts</strong>
            </div>
          )}
          {tooltip.data.highest_points !== null && (
            <div className="tooltip-row range">
              <span>Range:</span>
              <strong>
                {tooltip.data.lowest_points}-{tooltip.data.highest_points}
              </strong>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
