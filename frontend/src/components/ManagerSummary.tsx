import { useEffect, useState } from "react";

interface ManagerData {
  id: number;
  player_first_name: string;
  player_last_name: string;
  name: string; // Team name
  summary_overall_points: number;
  summary_overall_rank: number;
  summary_event_points: number;
  summary_event_rank: number;
  last_deadline_value: number;
  last_deadline_bank: number;
  favourite_team: number | null;
  current_event: number;
  started_event: number;
}

interface ManagerSummaryProps {
  managerId: string;
}

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

const ManagerSummary: React.FC<ManagerSummaryProps> = ({ managerId }) => {
  const [manager, setManager] = useState<ManagerData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!managerId) return;

    setLoading(true);
    setError(null);

    fetch(`/api/fpl/entry/${managerId}/`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Manager not found (${res.status})`);
        }
        return res.json();
      })
      .then((data: ManagerData) => {
        setManager(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [managerId]);

  if (loading) {
    return (
      <div className="manager-summary-card">
        <div className="manager-summary-loading">
          <div className="loading-spinner"></div>
          <p>Loading manager...</p>
        </div>
      </div>
    );
  }

  if (error || !manager) {
    return (
      <div className="manager-summary-card error">
        <div className="error-icon">⚠️</div>
        <h3>Manager Not Found</h3>
        <p>{error || "Unable to load manager data"}</p>
      </div>
    );
  }

  const teamValue = (manager.last_deadline_value / 10).toFixed(1);
  const bank = (manager.last_deadline_bank / 10).toFixed(1);

  return (
    <div className="manager-summary-card">
      <div className="manager-summary-header">
        <h3 className="manager-summary-title">🏆 Manager Info</h3>
        {manager.favourite_team && (
          <img
            src={`${TEAM_BADGE_BASE}${manager.favourite_team}.svg`}
            alt="Favourite team"
            className="manager-favorite-badge"
            onError={(e) => {
              // `favourite_team` is a team id and the badge set is keyed on
              // team code, so this can legitimately miss.
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        )}
      </div>

      <div className="manager-info-section">
        <div className="manager-name">
          {manager.player_first_name} {manager.player_last_name}
        </div>
        <div className="team-name">{manager.name}</div>
      </div>

      <div className="manager-stats-grid">
        <div className="stat-box highlight">
          <span className="stat-label">Overall Rank</span>
          <span className="stat-value">
            {manager.summary_overall_rank.toLocaleString()}
          </span>
        </div>

        <div className="stat-box highlight">
          <span className="stat-label">Total Points</span>
          <span className="stat-value">{manager.summary_overall_points}</span>
        </div>

        <div className="stat-box">
          <span className="stat-label">GW{manager.current_event} Rank</span>
          <span className="stat-value">
            {manager.summary_event_rank?.toLocaleString() || "—"}
          </span>
        </div>

        <div className="stat-box">
          <span className="stat-label">GW{manager.current_event} Points</span>
          <span className="stat-value">{manager.summary_event_points || 0}</span>
        </div>

        <div className="stat-box">
          <span className="stat-label">Team Value</span>
          <span className="stat-value team-value">£{teamValue}m</span>
        </div>

        <div className="stat-box">
          <span className="stat-label">Bank</span>
          <span className="stat-value bank">£{bank}m</span>
        </div>
      </div>

      <div className="manager-meta">
        <p className="meta-item">
          <span className="meta-label">Joined:</span> Gameweek {manager.started_event}
        </p>
        <p className="meta-item">
          <span className="meta-label">Manager ID:</span> {manager.id}
        </p>
      </div>
    </div>
  );
};

export default ManagerSummary;
