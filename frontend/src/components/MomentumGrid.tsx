import { useEffect } from "react";
import anime from "animejs";
import { PlayerMover } from "../types";

interface MomentumGridProps {
  movers: PlayerMover[] | undefined;
  loading: boolean;
  onPlayerClick?: (playerId: number) => void;
}

export function MomentumGrid({ movers, loading, onPlayerClick }: MomentumGridProps) {
  useEffect(() => {
    if (!movers || loading) return;

    anime({
      targets: ".momentum-bar-fill",
      width: ["0%", (el: HTMLElement) => el.dataset.target ?? "100%"],
      easing: "easeOutQuad",
      duration: 1000,
      delay: anime.stagger(120),
    });
  }, [movers, loading]);

  const subset = movers?.slice(0, 6) ?? [];

  return (
    <section className="glow-card momentum">
      <div className="glow-card-content">
        <div className="section-title">Momentum Leaders</div>
        <p className="section-subtitle">Players scoring the most points in recent gameweeks — who's in form right now</p>
        <div className="momentum-grid">
          {(loading ? new Array(6).fill(null) : subset).map((mover, idx) => (
            <MomentumCard key={mover?.id ?? idx} mover={mover} loading={loading} onClick={onPlayerClick} />
          ))}
        </div>
      </div>
    </section>
  );
}

function MomentumCard({ mover, loading, onClick }: { mover: PlayerMover | null | undefined; loading: boolean; onClick?: (playerId: number) => void }) {
  if (!mover || loading) {
    return (
      <article className="momentum-card skeleton">
        <div className="skeleton-thumbnail" />
        <div className="skeleton-lines">
          <div />
          <div />
        </div>
      </article>
    );
  }

  const targetWidth = Math.min(Math.abs(mover.value) * 8, 100);

  return (
    <article 
      className={`momentum-card ${onClick ? 'clickable' : ''}`}
      onClick={() => onClick?.(mover.id)}
    >
      <header>
        <div className="momentum-name">
          <strong>
            {mover.first_name} {mover.second_name}
          </strong>
          <span>{mover.team ?? ""}</span>
        </div>
        <span className="momentum-delta">+{mover.value.toFixed(0)} pts</span>
      </header>
      <div className="momentum-bar">
        <div className="momentum-bar-fill" data-target={`${targetWidth}%`} />
      </div>
      <footer>
        <span>Now cost £{((mover.now_cost ?? 0) / 10).toFixed(1)}</span>
        <span>{(mover.total_points ?? 0).toLocaleString()} pts total</span>
      </footer>
    </article>
  );
}
