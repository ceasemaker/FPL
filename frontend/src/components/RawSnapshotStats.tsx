import anime, { type AnimeInstance } from "animejs";
import { useEffect, useRef } from "react";
import { PulseResponse } from "../types";

interface RawSnapshotStatsProps {
  pulse: PulseResponse | undefined;
  loading: boolean;
  error: string | null;
}

export function RawSnapshotStats({ pulse, loading, error }: RawSnapshotStatsProps) {
  const countersRef = useRef<Array<HTMLSpanElement | null>>([]);

  useEffect(() => {
    if (!pulse || loading) return;

    const animations = countersRef.current
      .map((el: HTMLSpanElement | null, index: number) => {
        if (!el) return null;
        const target = Number(el.dataset.target ?? 0);
        const counter = { value: 0 };
        return anime({
          targets: counter,
          value: target,
          duration: 1200,
          easing: "easeOutExpo",
          delay: 120 * index,
          update: () => {
            el.textContent = Math.round(counter.value).toLocaleString();
          },
        });
      })
      .filter((animation): animation is AnimeInstance => Boolean(animation));

    return () => {
      animations.forEach((animation: AnimeInstance) => animation.pause());
    };
  }, [pulse, loading]);

  const snapshotEntries = Object.entries(pulse?.snapshot_counts ?? {});

  return (
    <section className="glow-card raw-stats">
      <div className="glow-card-content">
        <div className="section-title">Raw snapshots</div>
        {loading ? (
          <p className="muted">Collecting the latest data...</p>
        ) : error ? (
          <p className="error">{error}</p>
        ) : (
          <div className="raw-grid">
            {snapshotEntries.map(([endpoint, count], idx) => (
              <article key={endpoint} className="raw-card">
                <header>{endpoint}</header>
                <span
                  ref={(el: HTMLSpanElement | null) => {
                    countersRef.current[idx] = el;
                  }}
                  data-target={count}
                  className="raw-count"
                >
                  {count.toLocaleString()}
                </span>
                <footer>payloads captured</footer>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
