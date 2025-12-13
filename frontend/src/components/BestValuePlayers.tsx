import { useBestValuePlayers } from "../hooks/useTop100Data";
import { ValuePlayer } from "../types";
import "./BestValuePlayers.css";

interface BestValuePlayersProps {
  onPlayerClick?: (playerId: number) => void;
}

export function BestValuePlayers({ onPlayerClick }: BestValuePlayersProps) {
  const { data, isLoading, error } = useBestValuePlayers();

  if (error) {
    return (
      <section className="glow-card best-value">
        <div className="glow-card-content">
          <div className="section-title">💎 Best Value Players</div>
          <p className="error-message">Failed to load data</p>
        </div>
      </section>
    );
  }

  return (
    <section className="glow-card best-value">
      <div className="glow-card-content">
        <header className="value-header">
          <div className="section-title">
            💎 Best Value Players
            {data && <span className="gw-badge">GW{data.current_gameweek}</span>}
          </div>
          <p className="value-subtitle">
            Points per 90 (last 3 GWs) ÷ Cost • Excludes injured players
          </p>
        </header>

        <div className="value-grid">
          <PositionSection
            title="Goalkeepers"
            emoji="🧤"
            players={data?.goalkeepers ?? []}
            loading={isLoading}
            count={3}
            onPlayerClick={onPlayerClick}
          />
          <PositionSection
            title="Defenders"
            emoji="🛡️"
            players={data?.defenders ?? []}
            loading={isLoading}
            count={5}
            onPlayerClick={onPlayerClick}
          />
          <PositionSection
            title="Midfielders"
            emoji="⚽"
            players={data?.midfielders ?? []}
            loading={isLoading}
            count={5}
            onPlayerClick={onPlayerClick}
          />
          <PositionSection
            title="Forwards"
            emoji="🎯"
            players={data?.forwards ?? []}
            loading={isLoading}
            count={5}
            onPlayerClick={onPlayerClick}
          />
        </div>
      </div>
    </section>
  );
}

interface PositionSectionProps {
  title: string;
  emoji: string;
  players: ValuePlayer[];
  loading: boolean;
  count: number;
  onPlayerClick?: (playerId: number) => void;
}

function PositionSection({
  title,
  emoji,
  players,
  loading,
  count,
  onPlayerClick,
}: PositionSectionProps) {
  return (
    <div className="position-section">
      <h3 className="position-title">
        {emoji} {title}
      </h3>
      <div className="value-list">
        {loading
          ? Array(count)
              .fill(null)
              .map((_, i) => <SkeletonValueCard key={i} />)
          : players.map((player, idx) => (
              <ValuePlayerCard key={player.athlete_id} player={player} rank={idx + 1} onClick={onPlayerClick} />
            ))}
      </div>
    </div>
  );
}

interface ValuePlayerCardProps {
  player: ValuePlayer;
  rank: number;
  onClick?: (playerId: number) => void;
}

function ValuePlayerCard({ player, rank, onClick }: ValuePlayerCardProps) {
  const valueColor =
    player.value_score >= 2.0
      ? "value-excellent"
      : player.value_score >= 1.5
      ? "value-good"
      : "value-decent";

  return (
    <article 
      className={`value-card ${valueColor} ${onClick ? 'clickable' : ''}`}
      onClick={() => onClick?.(player.athlete_id)}
    >
      <div className="value-rank">{rank}</div>
      
      <div className="value-player-image">
        {player.image_url ? (
          <img src={player.image_url} alt={player.web_name} loading="lazy" />
        ) : (
          <div className="placeholder-image">?</div>
        )}
      </div>

      <div className="value-player-info">
        <div className="value-player-name">
          <strong>{player.web_name}</strong>
          <span className="value-player-team">{player.team_short_name}</span>
        </div>
        <div className="value-player-stats">
          <span className="value-cost">£{player.now_cost_display}</span>
          <span className="value-separator">•</span>
          <span className="value-points">{player.total_points} pts</span>
        </div>
      </div>

      <div className="value-metrics">
        <div className="value-score-container">
          <span className="value-score-label">Value</span>
          <span className="value-score">{player.value_score.toFixed(2)}</span>
        </div>
        <div className="value-last3">
          <span className="last3-label">Last 3 GWs</span>
          <span className="last3-points">{player.points_last_3} pts</span>
          <span className="last3-minutes">({player.minutes_last_3} min)</span>
        </div>
      </div>

      <div className="value-form">
        <span className="form-label">Form</span>
        <span className="form-value">{player.form.toFixed(1)}</span>
      </div>
    </article>
  );
}

function SkeletonValueCard() {
  return (
    <article className="value-card skeleton">
      <div className="skeleton-rank" />
      <div className="skeleton-image" />
      <div className="skeleton-info">
        <div className="skeleton-text wide" />
        <div className="skeleton-text narrow" />
      </div>
      <div className="skeleton-metrics" />
    </article>
  );
}
