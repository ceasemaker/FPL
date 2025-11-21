import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { PulseResponse } from "../types";
import { Heartbeat } from "./Heartbeat";

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
  const navigate = useNavigate();

  const subtitle = loading
    ? "Streaming match data..."
    : error
      ? "We couldn't reach the data service."
      : `ETL heartbeat captured ${data?.snapshot_counts?.["event-live"] ?? 0} live updates.`;

  return (
    <header className="glow-card hero relative overflow-hidden">
      <div className="glow-card-content relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="hero-headline flex-1">
          <span className="badge mb-4" style={shimmerGradient}>
            AeroFPL Index
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight">
            Feel the Premier League <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500">
              data heartbeat.
            </span>
          </h1>
          <p className="text-lg text-gray-400 mb-8 max-w-lg">{subtitle}</p>

          <button
            onClick={() => navigate("/analyze")}
            className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl font-bold text-lg hover:scale-105 transition-transform shadow-lg shadow-indigo-500/30"
          >
            Analyze Your Team →
          </button>
        </div>

        <div className="hero-visual flex-1 flex justify-center items-center">
          <div className="relative">
            <div className="absolute inset-0 bg-cyan-500/20 blur-3xl rounded-full"></div>
            <Heartbeat value={data?.value ?? 0} width={400} height={200} />
            <div className="text-center mt-4">
              <div className="text-sm text-gray-500 uppercase tracking-widest">Pulse Value</div>
            </div>
          </div>
        </div>
      </div>

      {/* Background Elements */}
      <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-indigo-900/20 to-transparent pointer-events-none"></div>
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
