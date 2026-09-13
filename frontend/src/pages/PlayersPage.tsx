import { useState, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { usePlayers, type Player } from "../hooks/usePlayers";
import { PlayerModal } from "../components/PlayerModal";
import { PlayersTable } from "../components/PlayersTable";
import "./PlayersPage.css";

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

function getTeamBadgeUrl(teamCode: number | null): string | null {
  if (!teamCode) return null;
  return `${TEAM_BADGE_BASE}${teamCode}.svg`;
}

function getPositionLabel(elementType: number): string {
  switch (elementType) {
    case 1: return "GKP";
    case 2: return "DEF";
    case 3: return "MID";
    case 4: return "FWD";
    default: return "—";
  }
}

function calculateBestValue(player: Player): number {
  if (player.now_cost === 0 || player.minutes_last_3 === 0) return 0;
  const pointsPer90 = (player.points_last_3 / player.minutes_last_3) * 90;
  const costInMillions = player.now_cost / 10;
  return pointsPer90 / costInMillions;
}

export function PlayersPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [compareMode, setCompareMode] = useState(false);
  const [selectedPlayers, setSelectedPlayers] = useState<Set<number>>(new Set());
  const [modalPlayerId, setModalPlayerId] = useState<number | null>(null);

  // View State
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // Filter State
  const [teamFilter, setTeamFilter] = useState<string>("all");
  const [positionFilter, setPositionFilter] = useState<string>("all");
  const [maxFdr, setMaxFdr] = useState<number>(5);
  const [minBestValue, setMinBestValue] = useState<number>(0);
  const [excludeInjured, setExcludeInjured] = useState<boolean>(false);
  const flaggedOnly = searchParams.get("status") === "flagged";

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
      setModalPlayerId(player.id);
    }
  };

  const handleCompare = () => {
    if (selectedPlayers.size < 2) return;
    const playerIds = Array.from(selectedPlayers).join(",");
    navigate(`/compare?ids=${playerIds}`);
  };

  // Derived Data
  const teams = useMemo(() => {
    if (!data?.players) return [];
    const uniqueTeams = Array.from(new Set(data.players.map(p => p.team).filter(Boolean)));
    return uniqueTeams.sort();
  }, [data?.players]);

  const filteredPlayers = useMemo(() => {
    if (!data?.players) return [];

    return data.players.filter(player => {
      // Team Filter
      if (teamFilter !== "all" && player.team !== teamFilter) return false;

      // Position Filter
      if (positionFilter !== "all" && player.element_type !== Number(positionFilter)) return false;

      // FDR Filter
      if (player.avg_fdr !== null && player.avg_fdr > maxFdr) return false;

      // Exclude Injured
      if (excludeInjured && (player.status === "i" || player.status === "u")) return false;
      if (flaggedOnly && (!player.status || player.status === "a")) return false;

      // Best Value Filter
      if (minBestValue > 0) {
        const val = calculateBestValue(player);
        if (val < minBestValue) return false;
      }

      return true;
    });
  }, [data?.players, teamFilter, positionFilter, maxFdr, excludeInjured, minBestValue, flaggedOnly]);

  if (error) {
    return (
      <main className="aero-page players-page">
        <div className="aero-header">
          <div><h1>Players</h1></div>
        </div>
        <p className="aero-error">{error}</p>
      </main>
    );
  }

  return (
    <main className="aero-page players-page">
      <div className="aero-header">
        <div>
          <h1>Players</h1>
          <p>
            Browse the squad pool, then pick two or more players to compare them
            side by side.
          </p>
        </div>
        <button
          className={`aero-button ${compareMode ? "" : "primary"}`}
          onClick={() => {
            setCompareMode(!compareMode);
            setSelectedPlayers(new Set());
          }}
        >
          {compareMode ? "Cancel selection" : "Select to compare"}
        </button>
      </div>

      <section className="players-filters aero-card">
        {flaggedOnly && <div className="aero-note" role="status">Showing players with an injury, suspension or availability flag. <button className="players-clear-filter" onClick={() => navigate("/players")}>Show everyone</button></div>}
        <label className="aero-field players-search-field">
          <span>Search</span>
          <input
            type="text"
            className="aero-input"
            placeholder="Search players…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>

        <label className="aero-field">
          <span>Team</span>
          <select
            className="aero-select"
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
          >
            <option value="all">All teams</option>
            {teams.map(team => (
              <option key={team} value={team!}>{team}</option>
            ))}
          </select>
        </label>

        <label className="aero-field">
          <span>Position</span>
          <select
            className="aero-select"
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
          >
            <option value="all">All positions</option>
            <option value="1">Goalkeepers</option>
            <option value="2">Defenders</option>
            <option value="3">Midfielders</option>
            <option value="4">Forwards</option>
          </select>
        </label>

        <label className="aero-field players-range">
          <span>Max FDR · {maxFdr}</span>
          <input
            type="range"
            min="1"
            max="5"
            step="0.1"
            value={maxFdr}
            onChange={(e) => setMaxFdr(Number(e.target.value))}
          />
        </label>

        <label className="aero-field players-range">
          <span>Min value · {minBestValue}</span>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={minBestValue}
            onChange={(e) => setMinBestValue(Number(e.target.value))}
          />
        </label>

        <label className="aero-field players-check">
          <span>Availability</span>
          <span className="players-check-row">
            <input
              type="checkbox"
              checked={excludeInjured}
              onChange={(e) => setExcludeInjured(e.target.checked)}
            />
            Exclude injured
          </span>
        </label>
      </section>

      {isLoading ? (
        <p className="aero-loading">Loading players…</p>
      ) : (
        <>
          <div className="results-bar">
            <div className="results-count">
              {filteredPlayers.length} player{filteredPlayers.length === 1 ? "" : "s"}
              {compareMode && " · tap a card to add it to the comparison"}
            </div>
            <div className="view-toggle">
              <button
                className={`view-btn ${viewMode === "grid" ? "active" : ""}`}
                onClick={() => setViewMode("grid")}
                aria-pressed={viewMode === "grid"}
                title="Grid view"
              >
                ⊞
              </button>
              <button
                className={`view-btn ${viewMode === "table" ? "active" : ""}`}
                onClick={() => setViewMode("table")}
                aria-pressed={viewMode === "table"}
                title="Table view"
              >
                ≡
              </button>
            </div>
          </div>

          {viewMode === "grid" ? (
            <div className="players-grid">
              {filteredPlayers.map((player) => {
                const isSelected = selectedPlayers.has(player.id);
                const bestValue = calculateBestValue(player);

                return (
                  <div
                    key={player.id}
                    className={`player-card ${compareMode ? "compare-mode" : ""} ${isSelected ? "selected" : ""
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
                      {bestValue >= 1.0 && (
                        <div className="value-badge" title="Best Value Rating">
                          💎 {bestValue.toFixed(1)}
                        </div>
                      )}
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
                            className="stat-value aero-fdr"
                            data-fdr={Math.round(player.avg_fdr)}
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
          ) : (
            <PlayersTable
              players={filteredPlayers}
              onPlayerClick={handlePlayerClick}
              selectedPlayers={selectedPlayers}
              compareMode={compareMode}
              onToggleSelection={togglePlayerSelection}
            />
          )}
        </>
      )}

      {/* Selection tray — keeps the compare action in reach while scrolling. */}
      {compareMode && (
        <div className="compare-tray" role="region" aria-label="Comparison selection">
          <div className="compare-tray-players">
            {selectedPlayers.size === 0 ? (
              <span className="compare-tray-hint">Select at least two players.</span>
            ) : (
              Array.from(selectedPlayers).map((id) => {
                const player = data?.players.find((p) => p.id === id);
                return (
                  <button
                    key={id}
                    type="button"
                    className="compare-tray-chip"
                    onClick={() => togglePlayerSelection(id)}
                    aria-label={`Remove ${player?.web_name ?? "player"} from comparison`}
                  >
                    {player?.web_name ?? `#${id}`} <b>×</b>
                  </button>
                );
              })
            )}
          </div>
          <button
            className="aero-button primary"
            onClick={handleCompare}
            disabled={selectedPlayers.size < 2}
          >
            Compare {selectedPlayers.size > 0 ? `(${selectedPlayers.size})` : ""}
          </button>
        </div>
      )}

      {/* Player Detail Modal */}
      {modalPlayerId !== null && (
        <PlayerModal
          playerId={modalPlayerId}
          onClose={() => setModalPlayerId(null)}
        />
      )}
    </main>
  );
}
