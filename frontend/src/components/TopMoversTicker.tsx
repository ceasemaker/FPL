import { useEffect, useRef } from "react";
import anime from "animejs";
import { PlayerMover, PriceMovers } from "../types";
import { cn } from "../utils/cn";

interface TopMoversTickerProps {
  priceMovers: PriceMovers | undefined;
  pointsMovers: PlayerMover[] | undefined;
  loading: boolean;
}

export function TopMoversTicker({ priceMovers, pointsMovers, loading }: TopMoversTickerProps) {
  const stripRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!stripRef.current || !priceMovers || loading) return;

    const animation = anime({
      targets: stripRef.current,
      translateX: [0, "-50%"],
      duration: 20000,
      easing: "linear",
      loop: true,
    });

    return () => {
      animation.pause();
    };
  }, [priceMovers, loading]);

  const moverCards = createTickerItems(priceMovers, pointsMovers, loading);

  return (
    <section className="glow-card ticker">
      <div className="glow-card-content">
        <div className="section-title">Top Movers</div>
        <p className="section-subtitle">Price changes and point scorers — risers 📈, fallers 📉, and top performers ⭐</p>
        <div className="ticker-viewport">
          <div className="ticker-strip" ref={stripRef}>
            {moverCards.map((mover) => (
              <TickerCard key={mover.key} mover={mover} />
            ))}
            {moverCards.map((mover) => (
              <TickerCard key={`${mover.key}-clone`} mover={mover} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

interface TickerRenderable extends PlayerMover {
  key: string;
  badge: string;
  badgeTone: "rise" | "fall" | "points";
}

function createTickerItems(
  priceMovers: PriceMovers | undefined,
  pointsMovers: PlayerMover[] | undefined,
  loading: boolean,
): TickerRenderable[] {
  if (loading) {
    return new Array(6).fill(null).map((_, idx) => ({
      id: idx,
      key: `placeholder-${idx}`,
      first_name: "Loading",
      second_name: "",
      team: null,
      value: 0,
      now_cost: null,
      total_points: null,
      change_label: "",
      image_url: null,
      badge: "...",
      badgeTone: "points" as const,
    }));
  }

  const renderables: TickerRenderable[] = [];

  priceMovers?.risers.forEach((mover) => {
    renderables.push({
      ...mover,
      key: `price-rise-${mover.id}`,
      badge: `▲ £${(mover.value / 10).toFixed(1)}`,
      badgeTone: "rise",
    });
  });

  priceMovers?.fallers.forEach((mover) => {
    renderables.push({
      ...mover,
      key: `price-fall-${mover.id}`,
      badge: `▼ £${Math.abs(mover.value / 10).toFixed(1)}`,
      badgeTone: "fall",
    });
  });

  pointsMovers?.slice(0, 6).forEach((mover) => {
    renderables.push({
      ...mover,
      key: `points-${mover.id}`,
      badge: `+${mover.value.toFixed(0)} pts`,
      badgeTone: "points",
    });
  });

  return renderables.length > 0 ? renderables : [];
}

function TickerCard({ mover }: { mover: TickerRenderable }) {
  const { first_name, second_name, team, badgeTone, badge, change_label, image_url } = mover;
  const initials = `${first_name?.[0] ?? ""}${second_name?.[0] ?? ""}`;

  return (
    <article className={cn("ticker-card", badgeTone)}>
      <div className="ticker-avatar">
        {image_url ? <img src={image_url} alt={`${first_name} ${second_name}`} /> : <span>{initials}</span>}
      </div>
      <div className="ticker-body">
        <div className="ticker-name">{first_name} {second_name}</div>
        <div className="ticker-meta">
          <span className="ticker-team">{team ?? ""}</span>
          <span className="ticker-note">{change_label}</span>
        </div>
      </div>
      <span className="ticker-badge">{badge}</span>
    </article>
  );
}
