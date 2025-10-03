import { useEffect, useState } from "react";

interface PlayerGameweekModalProps {
  playerId: number;
  playerName: string;
  playerTeam: number;
  playerPosition: number;
  gameweek: number;
  onClose: () => void;
}

interface PlayerStats {
  minutes: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  goals_conceded: number;
  own_goals: number;
  penalties_saved: number;
  penalties_missed: number;
  yellow_cards: number;
  red_cards: number;
  saves: number;
  bonus: number;
  bps: number;
  influence: string;
  creativity: string;
  threat: string;
  ict_index: string;
  total_points: number;
}

interface PlayerExplain {
  fixture: number;
  stats: Array<{
    identifier: string;
    points: number;
    value: number;
  }>;
}

const PlayerGameweekModal: React.FC<PlayerGameweekModalProps> = ({
  playerId,
  playerName,
  playerTeam,
  playerPosition,
  gameweek,
  onClose,
}) => {
  const [stats, setStats] = useState<PlayerStats | null>(null);
  const [explain, setExplain] = useState<PlayerExplain[]>([]);
  const [loading, setLoading] = useState(true);

  const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

  const getPositionLabel = (elementType: number): string => {
    switch (elementType) {
      case 1:
        return "GKP";
      case 2:
        return "DEF";
      case 3:
        return "MID";
      case 4:
        return "FWD";
      default:
        return "—";
    }
  };

  useEffect(() => {
    fetch(`/api/fpl/event/${gameweek}/live/`)
      .then((res) => res.json())
      .then((data) => {
        const playerData = data.elements.find((el: any) => el.id === playerId);
        if (playerData) {
          setStats(playerData.stats);
          setExplain(playerData.explain || []);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load player gameweek stats:", err);
        setLoading(false);
      });
  }, [playerId, gameweek]);

  const formatStat = (value: number | string): string => {
    if (typeof value === "string") {
      return parseFloat(value).toFixed(1);
    }
    return value.toString();
  };

  const getStatLabel = (identifier: string): string => {
    const labels: Record<string, string> = {
      minutes: "Minutes played",
      goals_scored: "Goals",
      assists: "Assists",
      clean_sheets: "Clean sheet",
      goals_conceded: "Goals conceded",
      own_goals: "Own goals",
      penalties_saved: "Penalties saved",
      penalties_missed: "Penalties missed",
      yellow_cards: "Yellow card",
      red_cards: "Red card",
      saves: "Saves",
      bonus: "Bonus points",
      bps: "BPS",
    };
    return labels[identifier] || identifier;
  };

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content gw-stats-modal" onClick={(e) => e.stopPropagation()}>
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content gw-stats-modal" onClick={(e) => e.stopPropagation()}>
          <button className="modal-close-x" onClick={onClose}>
            ×
          </button>
          <p>No data available for this gameweek.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content gw-stats-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-x" onClick={onClose}>
          ×
        </button>

        <div className="gw-modal-header">
          <h2>{playerName}</h2>
          <p className="gw-modal-subtitle">
            <span className="gw-position-badge">{getPositionLabel(playerPosition)}</span>
            <img
              src={`${TEAM_BADGE_BASE}t${playerTeam}.svg`}
              alt="Team"
              className="gw-team-badge"
            />
            <span className="gw-separator">•</span>
            Gameweek {gameweek} Performance
          </p>
        </div>

        <div className="gw-total-points">
          <div className="gw-points-label">Total Points</div>
          <div className="gw-points-value">{stats.total_points}</div>
        </div>

        {explain.length > 0 && (
          <div className="gw-points-breakdown">
            <h3>Points Breakdown</h3>
            {explain.map((fixture, idx) => (
              <div key={idx} className="gw-fixture-breakdown">
                {explain.length > 1 && (
                  <div className="gw-fixture-label">Fixture {idx + 1}</div>
                )}
                <div className="gw-breakdown-list">
                  {fixture.stats.map((stat, statIdx) => (
                    <div key={statIdx} className="gw-breakdown-item">
                      <span className="gw-breakdown-stat">
                        {getStatLabel(stat.identifier)}
                        {stat.value > 0 && ` (${stat.value})`}
                      </span>
                      <span className={`gw-breakdown-points ${stat.points > 0 ? 'positive' : stat.points < 0 ? 'negative' : ''}`}>
                        {stat.points > 0 ? '+' : ''}{stat.points}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="gw-stats-grid">
          <div className="gw-stat-card">
            <div className="gw-stat-label">Minutes</div>
            <div className="gw-stat-value">{stats.minutes}</div>
          </div>
          
          <div className="gw-stat-card">
            <div className="gw-stat-label">Goals</div>
            <div className="gw-stat-value">{stats.goals_scored}</div>
          </div>
          
          <div className="gw-stat-card">
            <div className="gw-stat-label">Assists</div>
            <div className="gw-stat-value">{stats.assists}</div>
          </div>
          
          <div className="gw-stat-card">
            <div className="gw-stat-label">Bonus</div>
            <div className="gw-stat-value">{stats.bonus}</div>
          </div>
          
          {stats.clean_sheets > 0 && (
            <div className="gw-stat-card">
              <div className="gw-stat-label">Clean Sheet</div>
              <div className="gw-stat-value">✓</div>
            </div>
          )}
          
          {stats.saves > 0 && (
            <div className="gw-stat-card">
              <div className="gw-stat-label">Saves</div>
              <div className="gw-stat-value">{stats.saves}</div>
            </div>
          )}
          
          {stats.goals_conceded > 0 && (
            <div className="gw-stat-card">
              <div className="gw-stat-label">Goals Conceded</div>
              <div className="gw-stat-value">{stats.goals_conceded}</div>
            </div>
          )}
          
          {stats.yellow_cards > 0 && (
            <div className="gw-stat-card warning">
              <div className="gw-stat-label">Yellow Cards</div>
              <div className="gw-stat-value">{stats.yellow_cards}</div>
            </div>
          )}
          
          {stats.red_cards > 0 && (
            <div className="gw-stat-card danger">
              <div className="gw-stat-label">Red Cards</div>
              <div className="gw-stat-value">{stats.red_cards}</div>
            </div>
          )}
          
          {stats.penalties_saved > 0 && (
            <div className="gw-stat-card">
              <div className="gw-stat-label">Penalties Saved</div>
              <div className="gw-stat-value">{stats.penalties_saved}</div>
            </div>
          )}
          
          {stats.penalties_missed > 0 && (
            <div className="gw-stat-card danger">
              <div className="gw-stat-label">Penalties Missed</div>
              <div className="gw-stat-value">{stats.penalties_missed}</div>
            </div>
          )}
          
          {stats.own_goals > 0 && (
            <div className="gw-stat-card danger">
              <div className="gw-stat-label">Own Goals</div>
              <div className="gw-stat-value">{stats.own_goals}</div>
            </div>
          )}
        </div>

        <div className="gw-advanced-stats">
          <h3>Advanced Stats</h3>
          <div className="gw-advanced-grid">
            <div className="gw-advanced-item">
              <span className="gw-advanced-label">BPS</span>
              <span className="gw-advanced-value">{stats.bps}</span>
            </div>
            <div className="gw-advanced-item">
              <span className="gw-advanced-label">Influence</span>
              <span className="gw-advanced-value">{formatStat(stats.influence)}</span>
            </div>
            <div className="gw-advanced-item">
              <span className="gw-advanced-label">Creativity</span>
              <span className="gw-advanced-value">{formatStat(stats.creativity)}</span>
            </div>
            <div className="gw-advanced-item">
              <span className="gw-advanced-label">Threat</span>
              <span className="gw-advanced-value">{formatStat(stats.threat)}</span>
            </div>
            <div className="gw-advanced-item">
              <span className="gw-advanced-label">ICT Index</span>
              <span className="gw-advanced-value">{formatStat(stats.ict_index)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlayerGameweekModal;
