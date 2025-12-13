import { useTop100Transfers, useTop100Differentials } from "../hooks/useTop100Data";
import { TransferTrend, DifferentialPlayer } from "../types";
import "./Top100Extras.css";

export function Top100Extras() {
  return (
    <div className="top100-extras">
      <TransferTrendsSection />
      <DifferentialsSection />
    </div>
  );
}

function TransferTrendsSection() {
  const { data, isLoading, error } = useTop100Transfers();

  if (error) {
    return (
      <section className="glow-card extras-section">
        <div className="glow-card-content">
          <div className="section-title">🔄 Transfer Trends</div>
          <p className="error-message">Failed to load data</p>
        </div>
      </section>
    );
  }

  return (
    <section className="glow-card extras-section transfers-section">
      <div className="glow-card-content">
        <header className="extras-header">
          <div className="section-title">
            🔄 Transfer Trends
            {data && <span className="gw-badge">GW{data.game_week}</span>}
          </div>
          <p className="extras-subtitle">What the top 100 managers are buying and selling</p>
        </header>

        <div className="transfers-grid">
          <div className="transfers-column in">
            <h4 className="column-title">
              <span className="arrow-in">↑</span> Most Transferred In
            </h4>
            <div className="transfer-list">
              {isLoading
                ? [1, 2, 3, 4, 5].map((i) => <SkeletonTransfer key={i} />)
                : (data?.transfers_in ?? []).slice(0, 5).map((t, idx) => (
                    <TransferItem key={t.athlete_id} transfer={t} rank={idx + 1} type="in" />
                  ))}
            </div>
          </div>

          <div className="transfers-column out">
            <h4 className="column-title">
              <span className="arrow-out">↓</span> Most Transferred Out
            </h4>
            <div className="transfer-list">
              {isLoading
                ? [1, 2, 3, 4, 5].map((i) => <SkeletonTransfer key={i} />)
                : (data?.transfers_out ?? []).slice(0, 5).map((t, idx) => (
                    <TransferItem key={t.athlete_id} transfer={t} rank={idx + 1} type="out" />
                  ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function TransferItem({
  transfer,
  rank,
  type,
}: {
  transfer: TransferTrend;
  rank: number;
  type: "in" | "out";
}) {
  return (
    <div className={`transfer-item ${type}`}>
      <span className="transfer-rank">{rank}</span>
      <div className="transfer-image">
        {transfer.image_url ? (
          <img src={transfer.image_url} alt={transfer.web_name} loading="lazy" />
        ) : (
          <div className="placeholder-image">?</div>
        )}
      </div>
      <div className="transfer-info">
        <strong>{transfer.web_name}</strong>
        <span className="transfer-team">{transfer.team_short_name}</span>
      </div>
      <div className="transfer-stats">
        <span className="transfer-count">{transfer.count} transfers</span>
        <span className="transfer-cost">£{transfer.now_cost_display}</span>
      </div>
    </div>
  );
}

function DifferentialsSection() {
  const { data, isLoading, error } = useTop100Differentials();

  if (error) {
    return (
      <section className="glow-card extras-section">
        <div className="glow-card-content">
          <div className="section-title">🎲 Differentials</div>
          <p className="error-message">Failed to load data</p>
        </div>
      </section>
    );
  }

  return (
    <section className="glow-card extras-section differentials-section">
      <div className="glow-card-content">
        <header className="extras-header">
          <div className="section-title">
            🎲 Differential Picks
            {data && <span className="gw-badge">GW{data.game_week}</span>}
          </div>
          <p className="extras-subtitle">
            Low-owned players ({`<${data?.max_ownership ?? 15}%`}) among the elite
          </p>
        </header>

        <div className="differentials-list">
          {isLoading
            ? [1, 2, 3, 4, 5].map((i) => <SkeletonDifferential key={i} />)
            : (data?.differentials ?? []).slice(0, 8).map((d, idx) => (
                <DifferentialItem key={d.athlete_id} player={d} rank={idx + 1} />
              ))}
        </div>
      </div>
    </section>
  );
}

function DifferentialItem({
  player,
  rank,
}: {
  player: DifferentialPlayer;
  rank: number;
}) {
  const positionColors: Record<string, string> = {
    GK: "#eab308",
    DEF: "#22c55e",
    MID: "#3b82f6",
    FWD: "#ef4444",
  };

  return (
    <div className="differential-item">
      <span className="differential-rank">{rank}</span>
      <div className="differential-image">
        {player.image_url ? (
          <img src={player.image_url} alt={player.web_name} loading="lazy" />
        ) : (
          <div className="placeholder-image">?</div>
        )}
      </div>
      <div className="differential-info">
        <div className="differential-name">
          <strong>{player.web_name}</strong>
          <span
            className="differential-position"
            style={{ backgroundColor: positionColors[player.position] || "#6366f1" }}
          >
            {player.position}
          </span>
        </div>
        <span className="differential-team">{player.team_short_name}</span>
      </div>
      <div className="differential-stats">
        <span className="differential-ownership">
          {player.ownership_percentage.toFixed(1)}%
        </span>
        <span className="differential-points">{player.total_points} pts</span>
        <span className="differential-cost">£{player.now_cost_display}</span>
      </div>
    </div>
  );
}

function SkeletonTransfer() {
  return (
    <div className="transfer-item skeleton">
      <div className="skeleton-rank" />
      <div className="skeleton-image" />
      <div className="skeleton-info">
        <div className="skeleton-text wide" />
        <div className="skeleton-text narrow" />
      </div>
    </div>
  );
}

function SkeletonDifferential() {
  return (
    <div className="differential-item skeleton">
      <div className="skeleton-rank" />
      <div className="skeleton-image" />
      <div className="skeleton-info">
        <div className="skeleton-text wide" />
        <div className="skeleton-text narrow" />
      </div>
    </div>
  );
}
