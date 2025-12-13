import { useTop100Template, useTop100Transfers } from "../hooks/useTop100Data";
import { Top100Player, TransferTrend, CaptainPick } from "../types";
import "./Top100Overview.css";

interface Top100OverviewProps {
  onPlayerClick?: (playerId: number) => void;
}

export function Top100Overview({ onPlayerClick }: Top100OverviewProps) {
  const { data: templateData, isLoading: templateLoading } = useTop100Template();
  const { data: transferData, isLoading: transferLoading } = useTop100Transfers();

  return (
    <section className="glow-card top100-overview">
      <div className="glow-card-content">
        <header className="overview-header">
          <div className="section-title">
            🏆 Top 100 Template
            {templateData && <span className="gw-badge">GW{templateData.game_week}</span>}
          </div>
          {templateData && (
            <div className="overview-stats">
              <span className="stat">
                <strong>{templateData.manager_count}</strong> managers
              </span>
              <span className="stat">
                Avg: <strong>{templateData.average_points.toFixed(1)}</strong> pts
              </span>
              <span className="stat">
                High: <strong>{templateData.highest_points}</strong> | Low: <strong>{templateData.lowest_points}</strong>
              </span>
            </div>
          )}
        </header>

        <div className="overview-grid">
          {/* Template Squad List */}
          <div className="template-list-section">
            <h4 className="list-title">Most Owned Players</h4>
            <div className="player-list">
              {templateLoading
                ? Array(15).fill(null).map((_, i) => <SkeletonPlayerRow key={i} />)
                : (templateData?.template_squad ?? []).slice(0, 15).map((player, idx) => (
                    <PlayerRow key={player.athlete_id} player={player} rank={idx + 1} onClick={onPlayerClick} />
                  ))}
            </div>
          </div>

          {/* Transfer Trends */}
          <div className="transfers-section">
            <div className="transfers-column">
              <h4 className="list-title">
                <span className="arrow-in">↑</span> Transfers In
              </h4>
              <div className="transfer-list">
                {transferLoading
                  ? Array(5).fill(null).map((_, i) => <SkeletonTransferRow key={i} />)
                  : (transferData?.transfers_in ?? []).slice(0, 5).map((t, idx) => (
                      <TransferRow key={t.athlete_id} transfer={t} rank={idx + 1} type="in" onClick={onPlayerClick} />
                    ))}
              </div>
            </div>

            <div className="transfers-column">
              <h4 className="list-title">
                <span className="arrow-out">↓</span> Transfers Out
              </h4>
              <div className="transfer-list">
                {transferLoading
                  ? Array(5).fill(null).map((_, i) => <SkeletonTransferRow key={i} />)
                  : (transferData?.transfers_out ?? []).slice(0, 5).map((t, idx) => (
                      <TransferRow key={t.athlete_id} transfer={t} rank={idx + 1} type="out" onClick={onPlayerClick} />
                    ))}
              </div>
            </div>
          </div>
        </div>

        {/* Captain & Chip Stats Row */}
        <div className="bottom-stats">
          <CaptainSection captains={templateData?.most_captained ?? []} loading={templateLoading} onPlayerClick={onPlayerClick} />
          <ChipUsageSection chips={templateData?.chip_usage ?? {}} loading={templateLoading} />
        </div>
      </div>
    </section>
  );
}

function PlayerRow({ player, rank, onClick }: { player: Top100Player; rank: number; onClick?: (playerId: number) => void }) {
  const ownershipColor =
    player.ownership_percentage >= 80
      ? "ownership-high"
      : player.ownership_percentage >= 50
      ? "ownership-medium"
      : "ownership-low";

  const positionLabels: Record<number, string> = {
    1: "GK",
    2: "DEF",
    3: "MID",
    4: "FWD",
  };

  return (
    <div 
      className={`player-row ${ownershipColor} ${onClick ? 'clickable' : ''}`}
      onClick={() => onClick?.(player.athlete_id)}
    >
      <span className="player-rank">{rank}</span>
      <div className="player-image-container">
        {player.image_url ? (
          <img src={player.image_url} alt={player.web_name} className="player-img" loading="lazy" />
        ) : (
          <div className="player-img placeholder">?</div>
        )}
      </div>
      <div className="player-details">
        <strong className="player-name">{player.web_name}</strong>
        <span className="player-meta">
          {player.team_short_name} · {positionLabels[player.element_type]}
        </span>
      </div>
      <div className="player-ownership-bar">
        <div className="ownership-fill" style={{ width: `${player.ownership_percentage}%` }} />
        <span className="ownership-text">{player.ownership_percentage.toFixed(0)}%</span>
      </div>
      <div className="player-stats">
        <span className="stat-points">{player.total_points} pts</span>
        <span className="stat-cost">£{(player.now_cost / 10).toFixed(1)}</span>
      </div>
    </div>
  );
}

function TransferRow({
  transfer,
  rank,
  type,
  onClick,
}: {
  transfer: TransferTrend;
  rank: number;
  type: "in" | "out";
  onClick?: (playerId: number) => void;
}) {
  return (
    <div 
      className={`transfer-row ${type} ${onClick ? 'clickable' : ''}`}
      onClick={() => onClick?.(transfer.athlete_id)}
    >
      <span className="transfer-rank">{rank}</span>
      <div className="transfer-image-container">
        {transfer.image_url ? (
          <img src={transfer.image_url} alt={transfer.web_name} loading="lazy" />
        ) : (
          <div className="placeholder">?</div>
        )}
      </div>
      <div className="transfer-details">
        <strong>{transfer.web_name}</strong>
        <span className="transfer-meta">{transfer.team_short_name}</span>
      </div>
      <div className="transfer-count-badge">
        {transfer.count}
      </div>
    </div>
  );
}

function CaptainSection({ captains, loading, onPlayerClick }: { captains: CaptainPick[]; loading: boolean; onPlayerClick?: (playerId: number) => void }) {
  if (loading) {
    return (
      <div className="captain-stats">
        <h4>👑 Most Captained</h4>
        <div className="captain-list">
          {[1, 2, 3].map((i) => (
            <div key={i} className="captain-item skeleton">
              <div className="skeleton-circle" />
              <div className="skeleton-text" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="captain-stats">
      <h4>👑 Most Captained</h4>
      <div className="captain-list">
        {captains.slice(0, 3).map((c, idx) => (
          <div 
            key={c.athlete_id} 
            className={`captain-item ${onPlayerClick ? 'clickable' : ''}`}
            onClick={() => onPlayerClick?.(c.athlete_id)}
          >
            <span className="captain-rank">{idx + 1}</span>
            {c.image_url && <img src={c.image_url} alt={c.web_name} className="captain-img" />}
            <span className="captain-name">{c.web_name}</span>
            <span className="captain-pct">{c.percentage.toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChipUsageSection({ chips, loading }: { chips: Record<string, number>; loading: boolean }) {
  const chipLabels: Record<string, string> = {
    wildcard: "🃏 WC",
    freehit: "🎯 FH",
    bboost: "📈 BB",
    "3xc": "3️⃣ TC",
  };

  const activeChips = Object.entries(chips).filter(([_, count]) => count > 0);

  if (loading) {
    return (
      <div className="chip-stats">
        <h4>🎮 Chips Used</h4>
        <div className="chip-list skeleton">
          <div className="skeleton-text" />
        </div>
      </div>
    );
  }

  return (
    <div className="chip-stats">
      <h4>🎮 Chips Used</h4>
      <div className="chip-list">
        {activeChips.length === 0 ? (
          <span className="no-chips">None this week</span>
        ) : (
          activeChips.map(([chip, count]) => (
            <div key={chip} className="chip-badge">
              <span className="chip-label">{chipLabels[chip] ?? chip}</span>
              <span className="chip-count">{count}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SkeletonPlayerRow() {
  return (
    <div className="player-row skeleton">
      <span className="player-rank skeleton-box" />
      <div className="player-image-container skeleton-circle" />
      <div className="player-details">
        <div className="skeleton-text" />
        <div className="skeleton-text short" />
      </div>
      <div className="player-ownership-bar skeleton-bar" />
      <div className="player-stats skeleton-stats" />
    </div>
  );
}

function SkeletonTransferRow() {
  return (
    <div className="transfer-row skeleton">
      <span className="transfer-rank skeleton-box" />
      <div className="transfer-image-container skeleton-circle" />
      <div className="transfer-details">
        <div className="skeleton-text" />
      </div>
      <div className="transfer-count-badge skeleton-box" />
    </div>
  );
}
