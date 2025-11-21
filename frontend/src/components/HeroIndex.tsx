import { useEffect, useRef } from "react";
import anime from "animejs";
import { PulseResponse } from "../types";

interface HeroIndexProps {
  data: PulseResponse | undefined;
  loading: boolean;
  error: string | null;
}

const shimmerGradient = {
  background:
    "linear-gradient(135deg, rgba(79, 70, 229, 0.65), rgba(22, 242, 255, 0.5))",
};

export function HeroIndex({ data, loading, error }: HeroIndexProps) {
  const valueRef = useRef<HTMLDivElement | null>(null);
  const meterFillRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!data || !valueRef.current) return;

    const counter = { value: 0 };
    const animation = anime({
      targets: counter,
      value: data.value,
      easing: "easeOutExpo",
      duration: 1600,
      update: () => {
        if (valueRef.current) {
          valueRef.current.textContent = counter.value.toFixed(2);
        }
      },
    });

    return () => {
      animation.pause();
    };
  }, [data]);

  // Animate meter fill
  useEffect(() => {
    if (!data || !meterFillRef.current) return;

    const maxPulse = 150000; // Max expected pulse value
    const percentage = Math.min((data.value / maxPulse) * 100, 100);

    anime({
      targets: meterFillRef.current,
      width: `${percentage}%`,
      easing: "easeOutExpo",
      duration: 1600,
    });
  }, [data]);

  const getPulseLevel = (value: number): { label: string; color: string } => {
    if (value < 10000) return { label: "Quiet", color: "#6b7280" };
    if (value < 50000) return { label: "Moderate", color: "#3b82f6" };
    if (value < 100000) return { label: "Active", color: "#f59e0b" };
    return { label: "Peak", color: "#ef4444" };
  };

  const pulseLevel = getPulseLevel(data?.value ?? 0);

  const subtitle = loading
    ? "Streaming match data..."
    : error
    ? "We couldn't reach the data service."
    : `ETL heartbeat captured ${data?.snapshot_counts?.["event-live"] ?? 0} live updates.`;

  return (
    <header className="glow-card hero">
      <div className="glow-card-content">
        <div className="hero-headline">
          <span className="badge" style={shimmerGradient}>
            AeroFPL Index
          </span>
          <h1>Feel the Premier League data heartbeat.</h1>
          <p>{subtitle}</p>
        </div>
        <div className="hero-metric" style={shimmerGradient}>
          <div className="metric-label">Pulse value</div>
          <div className="metric-value" ref={valueRef}>
            {loading ? "--" : data?.value.toFixed(2) ?? "0.00"}
          </div>
          
          {/* Pulse Meter */}
          <div className="pulse-meter-container">
            <div className="pulse-meter-track">
              <div 
                className="pulse-meter-fill" 
                ref={meterFillRef}
                style={{ backgroundColor: pulseLevel.color }}
              ></div>
            </div>
            <div className="pulse-meter-labels">
              <span className="pulse-level-label" style={{ color: pulseLevel.color }}>
                {pulseLevel.label}
              </span>
              <span className="pulse-meter-scale">0 — 50k — 100k — 150k+</span>
            </div>
          </div>
          
          <div className="metric-footnote">
            {data?.last_updated
              ? `Last sync ${new Date(data.last_updated).toLocaleString()}`
              : "Powered by the Django ETL loop"}
          </div>
        </div>
        <div className="hero-pills">
          <HeroPill
            label="This GW points"
            value={data?.total_points_current ?? 0}
          />
          <HeroPill
            label="Transfers in"
            value={data?.total_transfers_in_event ?? 0}
          />
          <HeroPill
            label="Snapshots processed"
            value={Object.values(data?.snapshot_counts ?? {}).reduce(
              (acc, count) => acc + count,
              0,
            )}
          />
        </div>
      </div>
    </header>
  );
}

interface HeroPillProps {
  label: string;
  value: number;
}

function HeroPill({ label, value }: HeroPillProps) {
  return (
    <div className="hero-pill">
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}
