import { useState, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { usePlayers, type Player } from "../hooks/usePlayers";
import { PlayerModal } from "../components/PlayerModal";
import { PlayerNotes, PlayersTable } from "../components/PlayersTable";
import { availability, AVAILABILITY_FILTERS, type AvailabilityFilter, matchesAvailability, splitNews } from "../components/availability";
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
  const [searchParams, setSearchParams] = useSearchParams();
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
  // Availability lives in the address (?status=flagged) so Home and old Team
  // news links open the injury list directly.
  const statusParam = searchParams.get("status") as AvailabilityFilter | null;
  const availabilityFilter: AvailabilityFilter = AVAILABILITY_FILTERS.some(([k]) => k === statusParam) ? statusParam! : "all";
  const setAvailability = (f: AvailabilityFilter) => {
    const next = new URLSearchParams(searchParams);
    if (f === "all") next.delete("status"); else next.set("status", f);
    setSearchParams(next, { replace: true });
  };
  const injuryView = !["all", "fit"].includes(availabilityFilter);

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

    const list = data.players.filter(player => {
      // Team Filter
      if (teamFilter !== "all" && player.team !== teamFilter) return false;

      // Position Filter
      if (positionFilter !== "all" && player.element_type !== Number(positionFilter)) return false;

      // FDR Filter
      if (player.avg_fdr !== null && player.avg_fdr > maxFdr) return false;

      if (!matchesAvailability(availabilityFilter, player.status, player.chance)) return false;

      // Best Value Filter
      if (minBestValue > 0) {
        const val = calculateBestValue(player);
        if (val < minBestValue) return false;
      }

      return true;
    });
    // Looking at injuries: the ones that hit the most managers first.
    return injuryView ? [...list].sort((a, b) => (b.selected_by_percent ?? 0) - (a.selected_by_percent ?? 0)) : list;
  }, [data?.players, teamFilter, positionFilter, maxFdr, availabilityFilter, minBestValue, injuryView]);

  const injurySummary = useMemo(() => {
    if (!injuryView || !filteredPlayers.length) return null;
    const top = filteredPlayers[0];
    const flag = availability(top.status, top.chance);
    const big = filteredPlayers.filter((p) => (p.selected_by_percent ?? 0) >= 5).length;
    const { detail } = splitNews(top.news);
    const state = flag?.tone === "out" ? "out" : flag?.tone === "ban" ? "suspended" : `${flag?.text.toLowerCase()} to play`;
    return `${big} of these ${filteredPlayers.length} are owned by 5% or more of managers. The most owned is ${top.web_name} (${top.team}, ${(top.selected_by_percent ?? 0).toFixed(1)}%): ${state}${detail ? `, ${detail.charAt(0).toLowerCase()}${detail.slice(1)}` : ""}.`;
  }, [filteredPlayers, injuryView]);

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

      <section className="players-filters" aria-label="Filters">
        <div className="players-filter-row">
          <label className="players-search">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true"><circle cx="7" cy="7" r="4.5" /><path d="M10.5 10.5 14 14" /></svg>
            <input
              type="search"
              placeholder="Search players"
              aria-label="Search players"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>

          <div className="aero-segmented" role="group" aria-label="Position">
            {([["all", "All"], ["1", "GK"], ["2", "DEF"], ["3", "MID"], ["4", "FWD"]] as const).map(([value, label]) => (
              <button key={value} type="button" aria-pressed={positionFilter === value} onClick={() => setPositionFilter(value)}>{label}</button>
            ))}
          </div>

          <select
            className="aero-select"
            aria-label="Team"
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
          >
            <option value="all">All teams</option>
            {teams.map(team => (
              <option key={team} value={team!}>{team}</option>
            ))}
          </select>

          <select
            className="aero-select"
            aria-label="Availability"
            value={availabilityFilter}
            onChange={(e) => setAvailability(e.target.value as AvailabilityFilter)}
          >
            {AVAILABILITY_FILTERS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </div>

        <div className="players-filter-row">
          <label className="players-range">
            <span>Fixture difficulty up to <b>{maxFdr}</b></span>
            <input
              type="range"
              min="1"
              max="5"
              step="0.1"
              value={maxFdr}
              onChange={(e) => setMaxFdr(Number(e.target.value))}
            />
          </label>

          <label className="players-range">
            <span>Value at least <b>{minBestValue}</b></span>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={minBestValue}
              onChange={(e) => setMinBestValue(Number(e.target.value))}
            />
          </label>
        </div>
      </section>

      {isLoading ? (
        <p className="aero-loading">Loading players…</p>
      ) : (
        <>
          <div className="results-bar">
            <div className="results-count">
              {filteredPlayers.length} player{filteredPlayers.length === 1 ? "" : "s"}{injuryView && ", most owned first"}
              {compareMode && " · tap a card to add it to the comparison"}
            </div>
            <div className="view-toggle aero-segmented" role="group" aria-label="View">
              <button
                className="view-btn"
                onClick={() => setViewMode("grid")}
                aria-pressed={viewMode === "grid"}
                aria-label="Grid view"
                title="Grid view"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><g fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="2" y="2" width="5" height="5" rx="1.2" /><rect x="9" y="2" width="5" height="5" rx="1.2" /><rect x="2" y="9" width="5" height="5" rx="1.2" /><rect x="9" y="9" width="5" height="5" rx="1.2" /></g></svg>
              </button>
              <button
                className="view-btn"
                onClick={() => setViewMode("table")}
                aria-pressed={viewMode === "table"}
                aria-label="Table view"
                title="Table view"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 4h11M2.5 8h11M2.5 12h11" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>
          </div>

          {injurySummary && <p className="players-summary">{injurySummary} Flags and news from FPL.</p>}

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
                          Value {bestValue.toFixed(1)}
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
                      <div className="card-notes"><PlayerNotes player={player} /></div>
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
              key={injuryView ? "injuries" : "everyone"}
              defaultSort={injuryView ? { field: "selected_by_percent", direction: "desc" } : undefined}
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
