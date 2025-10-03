import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlayers, type Player } from "../hooks/usePlayers";
import { PlayerModal } from "../components/PlayerModal";

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

function getTeamBadgeUrl(teamCode: number | null): string | null {
  if (!teamCode) return null;
  return `${TEAM_BADGE_BASE}${teamCode}.svg`;
}

function getDifficultyColor(difficulty: number | null): string {
  if (difficulty === null) return "#666";
  if (difficulty <= 1.5) return "#22c55e";
  if (difficulty <= 2.5) return "#84cc16";
  if (difficulty <= 3.5) return "#eab308";
  if (difficulty <= 4.5) return "#f97316";
  return "#ef4444";
}

function getPositionLabel(elementType: number): string {
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
}

export function PlayersPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [compareMode, setCompareMode] = useState(false);
  const [selectedPlayers, setSelectedPlayers] = useState<Set<number>>(new Set());
  const [modalPlayerId, setModalPlayerId] = useState<number | null>(null);

  const { data, isLoading, error } = usePlayers(search);

  const togglePlayerSelection = (playerId: number) => {
    setSelectedPlayers((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(playerId)) {
        newSet.delete(playerId);
      } else {
        newSet.add(playerId);
      }
      return newSet;
    });
  };

  const handlePlayerClick = (player: Player) => {
    if (compareMode) {
      togglePlayerSelection(player.id);
    } else {
      // Open player detail modal
      setModalPlayerId(player.id);
    }
  };

  const handleCompare = () => {
    if (selectedPlayers.size < 2) {
      alert("Please select at least 2 players to compare");
      return;
    }
    // Navigate to comparison view with selected player IDs
    const playerIds = Array.from(selectedPlayers).join(",");
    navigate(`/compare?ids=${playerIds}`);
  };

  if (error) {
    return (
      <div className="page">
        <div className="players-error">
          <h2>Error loading players</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page players-page">
      <div className="players-header">
        <h1>Players</h1>
        <div className="players-controls">
          <input
            type="text"
            className="players-search"
            placeholder="Search players..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button
            className={`compare-toggle ${compareMode ? "active" : ""}`}
            onClick={() => {
              setCompareMode(!compareMode);
              setSelectedPlayers(new Set());
            }}
          >
            {compareMode ? "Cancel Compare" : "Compare"}
          </button>
          {compareMode && selectedPlayers.size > 0 && (
            <button className="compare-btn" onClick={handleCompare}>
              Compare ({selectedPlayers.size})
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="players-loading">Loading players...</div>
      ) : (
        <div className="players-grid">
          {data?.players.map((player) => {
            const isSelected = selectedPlayers.has(player.id);
            const initials = `${player.first_name[0] || ""}${player.second_name[0] || ""}`;

            return (
              <div
                key={player.id}
                className={`player-card ${compareMode ? "compare-mode" : ""} ${
                  isSelected ? "selected" : ""
                }`}
                onClick={() => handlePlayerClick(player)}
              >
                {compareMode && (
                  <div className="player-checkbox">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => togglePlayerSelection(player.id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )}
                <div className="player-image">
                  <img
                    src={player.image_url || `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-220.webp`}
                    alt={player.web_name}
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      if (target.src !== `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-220.webp`) {
                        target.onerror = null;
                        target.src = `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-220.webp`;
                      }
                    }}
                  />
                </div>
                <div className="player-info">
                  <div className="player-name">{player.web_name}</div>
                  <div className="player-meta">
                    <span className="player-position">
                      {getPositionLabel(player.element_type)}
                    </span>
                    {player.team && (
                      <>
                        <span className="meta-sep">•</span>
                        {player.team_code && (
                          <img 
                            src={getTeamBadgeUrl(player.team_code)!}
                            alt={player.team}
                            className="team-badge-small"
                          />
                        )}
                        <span className="player-team">{player.team}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="player-stats">
                  <div className="stat-item">
                    <span className="stat-label">Price</span>
                    <span className="stat-value">
                      £{(player.now_cost / 10).toFixed(1)}m
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Points</span>
                    <span className="stat-value">{player.total_points}</span>
                  </div>
                  {player.avg_fdr !== null && (
                    <div className="stat-item">
                      <span className="stat-label">FDR</span>
                      <span
                        className="stat-value fdr-badge"
                        style={{
                          backgroundColor: getDifficultyColor(player.avg_fdr),
                        }}
                      >
                        {player.avg_fdr.toFixed(1)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Player Detail Modal */}
      {modalPlayerId !== null && (
        <PlayerModal
          playerId={modalPlayerId}
          onClose={() => setModalPlayerId(null)}
        />
      )}
    </div>
  );
}
