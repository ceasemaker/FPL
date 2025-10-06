import { useEffect, useRef, useState } from "react";

interface RadarAttributes {
  attacking: number | null;
  technical: number | null;
  tactical: number | null;
  defending: number | null;
  creativity: number | null;
}

interface PlayerRadarData {
  player_id: number;
  player_name: string;
  full_name: string;
  position: string;
  attributes: RadarAttributes;
  is_average: boolean;
  year_shift: number;
}

interface RadarChartProps {
  playerIds: number[];  // Support multiple players for comparison
  height?: number;
  width?: number;
  showBreakdown?: boolean;  // Show horizontal bars below chart
  hideOnError?: boolean;  // Hide component instead of showing error message
}

const ATTRIBUTE_LABELS = [
  "Attacking",
  "Technical",
  "Tactical",
  "Defending",
  "Creativity"
];

const ATTRIBUTE_KEYS: (keyof RadarAttributes)[] = [
  "attacking",
  "technical",
  "tactical",
  "defending",
  "creativity"
];

// Colors for up to 4 players
const PLAYER_COLORS = [
  { fill: "rgba(79, 70, 229, 0.3)", stroke: "rgba(79, 70, 229, 0.9)", name: "#4f46e5" },     // Primary purple
  { fill: "rgba(251, 111, 187, 0.3)", stroke: "rgba(251, 111, 187, 0.9)", name: "#fb6fbb" },  // Pink
  { fill: "rgba(34, 211, 238, 0.3)", stroke: "rgba(34, 211, 238, 0.9)", name: "#22d3ee" },    // Cyan
  { fill: "rgba(251, 146, 60, 0.3)", stroke: "rgba(251, 146, 60, 0.9)", name: "#fb923c" },    // Orange
];

export function RadarChart({ playerIds, height = 400, width = 400, showBreakdown = true, hideOnError = false }: RadarChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [playersData, setPlayersData] = useState<PlayerRadarData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch radar data for all players
  useEffect(() => {
    if (!playerIds || playerIds.length === 0) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    // If single player, fetch individually; if multiple, use compare endpoint
    const fetchPromise = playerIds.length === 1
      ? fetch(`/api/sofasport/player/${playerIds[0]}/radar/`)
          .then(res => res.json())
          .then(data => {
            // Handle error response from single player endpoint
            if (data.error) {
              return { error: data.error };
            }
            return { players: [data] };
          })
      : fetch(`/api/sofasport/compare/radar/?player_ids=${playerIds.join(',')}`)
          .then(res => res.json());

    fetchPromise
      .then(data => {
        if (data.error) {
          setError(data.error);
          setPlayersData([]);
        } else {
          // Filter out any undefined or null players
          const validPlayers = (data.players || []).filter(
            (p: PlayerRadarData) => p && p.attributes && typeof p.attributes === 'object'
          );
          setPlayersData(validPlayers);
        }
      })
      .catch(err => {
        console.error("Failed to fetch radar data:", err);
        setError("Failed to load radar chart data");
        setPlayersData([]);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [playerIds]);

  // Draw radar chart
  useEffect(() => {
    if (!canvasRef.current || playersData.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // High DPI support
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Chart dimensions
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 60;
    const numAxes = ATTRIBUTE_LABELS.length;
    const angleStep = (Math.PI * 2) / numAxes;

    // Draw background circles (scale lines)
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 1;
    for (let scale = 20; scale <= 100; scale += 20) {
      ctx.beginPath();
      ctx.arc(centerX, centerY, (radius * scale) / 100, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Draw axes and labels
    ctx.strokeStyle = "rgba(255, 255, 255, 0.2)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#a5b4fc";
    ctx.font = "600 12px system-ui, -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    ATTRIBUTE_LABELS.forEach((label, i) => {
      const angle = angleStep * i - Math.PI / 2; // Start from top
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;

      // Draw axis line
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.stroke();

      // Draw label
      const labelX = centerX + Math.cos(angle) * (radius + 30);
      const labelY = centerY + Math.sin(angle) * (radius + 30);
      ctx.fillText(label, labelX, labelY);

      // Draw scale values (0, 50, 100)
      ctx.font = "500 10px system-ui";
      ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
      
      // Only show on first axis to avoid clutter
      if (i === 0) {
        [50, 100].forEach(value => {
          const scaleX = centerX + Math.cos(angle) * ((radius * value) / 100);
          const scaleY = centerY + Math.sin(angle) * ((radius * value) / 100) - 10;
          ctx.fillText(value.toString(), scaleX, scaleY);
        });
      }
    });

    // Draw each player's data
    playersData.forEach((player, playerIndex) => {
      const color = PLAYER_COLORS[playerIndex % PLAYER_COLORS.length];
      const values = ATTRIBUTE_KEYS.map(key => player.attributes[key] ?? 0);

      // Draw filled area
      ctx.beginPath();
      values.forEach((value, i) => {
        const angle = angleStep * i - Math.PI / 2;
        const distance = (radius * value) / 100;
        const x = centerX + Math.cos(angle) * distance;
        const y = centerY + Math.sin(angle) * distance;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.closePath();
      ctx.fillStyle = color.fill;
      ctx.fill();

      // Draw border
      ctx.strokeStyle = color.stroke;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Draw data points with values
      values.forEach((value, i) => {
        const angle = angleStep * i - Math.PI / 2;
        const distance = (radius * value) / 100;
        const x = centerX + Math.cos(angle) * distance;
        const y = centerY + Math.sin(angle) * distance;

        // Draw point
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = color.stroke;
        ctx.fill();
        ctx.strokeStyle = "rgba(14, 18, 49, 0.9)";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw value text on the point
        if (value > 0) {
          ctx.font = "700 13px system-ui, -apple-system, sans-serif";
          ctx.fillStyle = "#ffffff";
          ctx.strokeStyle = "rgba(14, 18, 49, 0.8)";
          ctx.lineWidth = 3;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          
          // Position text slightly outside the data point
          const textDistance = distance + 15;
          const textX = centerX + Math.cos(angle) * textDistance;
          const textY = centerY + Math.sin(angle) * textDistance;
          
          // Draw text with stroke for better visibility
          ctx.strokeText(value.toString(), textX, textY);
          ctx.fillText(value.toString(), textX, textY);
        }
      });
    });
  }, [playersData, width, height]);

  if (loading) {
    if (hideOnError) return null;
    return (
      <div className="radar-chart-container" style={{ height, width }}>
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (error) {
    if (hideOnError) return null;
    return (
      <div className="radar-chart-container" style={{ height, width }}>
        <div className="radar-chart-error">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (playersData.length === 0) {
    if (hideOnError) return null;
    return (
      <div className="radar-chart-container" style={{ height, width }}>
        <div className="radar-chart-error">
          <p>No radar chart data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="radar-chart-wrapper">
      <canvas
        ref={canvasRef}
        className="radar-chart-canvas"
        style={{ width, height }}
      />
      
      {/* Legend */}
      <div className="radar-chart-legend">
        {playersData.map((player, index) => (
          <div key={player.player_id} className="radar-legend-item">
            <div
              className="radar-legend-color"
              style={{ backgroundColor: PLAYER_COLORS[index % PLAYER_COLORS.length].name }}
            />
            <span className="radar-legend-name">
              {player.player_name}
              {player.is_average && <span className="radar-legend-note"> (Career Avg)</span>}
            </span>
          </div>
        ))}
      </div>

      {/* Attribute breakdown */}
      {showBreakdown && playersData.length === 1 && (
        <div className="radar-attribute-breakdown">
          {ATTRIBUTE_LABELS.map((label, index) => {
            const key = ATTRIBUTE_KEYS[index];
            const value = playersData[0].attributes[key];
            return (
              <div key={label} className="radar-attribute-item">
                <span className="radar-attribute-label">{label}</span>
                <div className="radar-attribute-bar">
                  <div
                    className="radar-attribute-bar-fill"
                    style={{
                      width: `${value ?? 0}%`,
                      backgroundColor: PLAYER_COLORS[0].name
                    }}
                  />
                </div>
                <span className="radar-attribute-value">{value ?? "—"}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
