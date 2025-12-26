import { useEffect, useState } from "react";
import { RadarChart } from "./RadarChart";
import { PlayerHeatmap } from "./PlayerHeatmap";

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

interface DetailedPlayer {
  // Basic Info
  id: number;
  first_name: string;
  second_name: string;
  web_name: string;
  team: string | null;
  team_id: number | null;
  team_code: number | null;
  element_type: number;
  image_url: string | null;
  status: string | null;
  news: string | null;
  news_added: string | null;

  // Cost & Ownership
  now_cost: number;
  cost_change_event: number | null;
  cost_change_start: number | null;
  selected_by_percent: number | null;

  // Points & Form
  total_points: number;
  event_points: number | null;
  points_per_game: number | null;
  form: number | null;
  value_form: number | null;
  value_season: number | null;

  // Transfers
  transfers_in: number | null;
  transfers_in_event: number | null;
  transfers_out: number | null;
  transfers_out_event: number | null;

  // Performance Stats
  minutes: number | null;
  goals_scored: number | null;
  assists: number | null;
  clean_sheets: number | null;
  goals_conceded: number | null;
  own_goals: number | null;
  penalties_saved: number | null;
  penalties_missed: number | null;
  yellow_cards: number | null;
  red_cards: number | null;
  saves: number | null;
  bonus: number | null;
  bps: number | null;
  starts: number | null;

  // Advanced Stats (ICT)
  influence: number | null;
  creativity: number | null;
  threat: number | null;
  ict_index: number | null;

  // Expected Stats
  expected_goals: number | null;
  expected_assists: number | null;
  expected_goal_involvements: number | null;
  expected_goals_conceded: number | null;

  // Per 90 Stats
  expected_goals_per_90: number | null;
  expected_assists_per_90: number | null;
  expected_goal_involvements_per_90: number | null;
  expected_goals_conceded_per_90: number | null;
  goals_conceded_per_90: number | null;
  saves_per_90: number | null;
  starts_per_90: number | null;
  clean_sheets_per_90: number | null;

  // Rankings
  influence_rank: number | null;
  creativity_rank: number | null;
  threat_rank: number | null;
  ict_index_rank: number | null;
  now_cost_rank: number | null;
  form_rank: number | null;
  points_per_game_rank: number | null;
  selected_rank: number | null;

  // Set Pieces
  corners_and_indirect_freekicks_order: number | null;
  direct_freekicks_order: number | null;
  penalties_order: number | null;

  // Fixtures
  avg_fdr: number | null;

  // Chance of Playing
  chance_of_playing_this_round: number | null;
  chance_of_playing_next_round: number | null;
}

interface Fixture {
  event: number;
  opponent_team: string;
  opponent_team_short: string;
  is_home: boolean;
  difficulty: number;
  kickoff_time: string | null;
}

interface FixtureHistory {
  event: number;
  opponent_team: string;
  opponent_team_short: string;
  was_home: boolean;
  total_points: number;
  minutes: number;
  goals_scored: number;
  assists: number;
  kickoff_time: string | null;
}

interface EuropeanMatch {
  competition: string;
  competition_short: string;
  opponent: string;
  date: string;
  is_home: boolean;
  minutes: number;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  rating: number | null;
}

interface PlayerModalProps {
  playerId: number;
  onClose: () => void;
}

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
      return "Goalkeeper";
    case 2:
      return "Defender";
    case 3:
      return "Midfielder";
    case 4:
      return "Forward";
    default:
      return "Unknown";
  }
}

export function PlayerModal({ playerId, onClose }: PlayerModalProps) {
  const [player, setPlayer] = useState<DetailedPlayer | null>(null);
  const [upcomingFixtures, setUpcomingFixtures] = useState<Fixture[]>([]);
  const [fixtureHistory, setFixtureHistory] = useState<FixtureHistory[]>([]);
  const [europeanMatches, setEuropeanMatches] = useState<EuropeanMatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [selectedHeatmapGw, setSelectedHeatmapGw] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      // Fetch player details from our API
      fetch(`/api/players/${playerId}/`, {
        headers: { Accept: "application/json" },
      }).then(res => {
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`);
        return res.json();
      }),
      // Fetch bootstrap-static to get team names
      fetch(`/api/fpl/bootstrap-static/`)
        .then(res => res.json()),
      // Fetch player summary from FPL (includes fixtures and history)
      fetch(`/api/fpl/element-summary/${playerId}/`)
        .then(res => res.json()),
      // Fetch European/cup matches from SofaScore
      fetch(`/api/sofasport/player/${playerId}/recent-matches/`)
        .then(res => res.ok ? res.json() : { matches: [] })
        .catch(() => ({ matches: [] }))
    ])
      .then(([playerData, bootstrapData, summaryData, europeanData]) => {
        // Create team lookup map
        const teamsMap = new Map();
        (bootstrapData.teams || []).forEach((team: any) => {
          teamsMap.set(team.id, {
            name: team.name,
            short_name: team.short_name,
          });
        });

        // Get upcoming fixtures (next 5)
        const upcoming = (summaryData.fixtures || [])
          .filter((fix: any) => !fix.finished)
          .slice(0, 5)
          .map((fix: any) => {
            const opponentTeamId = fix.is_home ? fix.team_a : fix.team_h;
            const opponentTeam = teamsMap.get(opponentTeamId);
            return {
              event: fix.event,
              opponent_team: opponentTeam?.name || 'Unknown',
              opponent_team_short: opponentTeam?.short_name || 'UNK',
              is_home: fix.is_home,
              difficulty: fix.difficulty,
              kickoff_time: fix.kickoff_time,
            };
          });

        // Get fixture history (last 5)
        const history = (summaryData.history || [])
          .slice(-5)
          .reverse()
          .map((h: any) => {
            const opponentTeam = teamsMap.get(h.opponent_team);
            return {
              event: h.round,
              opponent_team: opponentTeam?.name || 'Unknown',
              opponent_team_short: opponentTeam?.short_name || 'UNK',
              was_home: h.was_home,
              total_points: h.total_points || 0,
              minutes: h.minutes || 0,
              goals_scored: h.goals_scored || 0,
              assists: h.assists || 0,
              kickoff_time: h.kickoff_time,
            };
          });

        // Process European/cup matches (filter out Premier League since that's in Recent Form)
        const euroMatches: EuropeanMatch[] = (europeanData.matches || [])
          .filter((m: any) => m.competition !== "Premier League" && m.competition_short !== "PL")
          .slice(0, 5)
          .map((m: any) => {
            // Determine opponent based on home/away (we need to know player's team)
            // For now, use home/away team names and let user see the full match
            const playerTeamName = playerData.team || "";
            const isHome = m.home_team?.toLowerCase().includes(playerTeamName.toLowerCase().split(" ")[0]) ||
              m.home_team === playerTeamName;
            const opponent = isHome ? m.away_team : m.home_team;

            return {
              competition: m.competition || "Unknown",
              competition_short: m.competition_short || "CUP",
              opponent: opponent || "Unknown",
              date: m.date || "",
              is_home: isHome,
              minutes: m.minutes_played || 0,
              goals: m.goals || 0,
              assists: m.assists || 0,
              yellow_cards: m.yellow_cards || 0,
              red_cards: m.red_cards || 0,
              rating: m.rating || null,
            };
          });

        setPlayer(playerData);
        setUpcomingFixtures(upcoming);
        setFixtureHistory(history);
        setEuropeanMatches(euroMatches);

        // Default heatmap to latest played gameweek from history
        if (history.length > 0) {
          setSelectedHeatmapGw(history[0].event);
        } else if (upcoming.length > 0) {
          // If no history, maybe no heatmap, but set to something safe
          setSelectedHeatmapGw(upcoming[0].event - 1);
        }

        setError(null);
      })
      .catch((err) => {
        console.error("Failed to load player", err);
        setError(err.message ?? "Unexpected error");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [playerId]);

  // Close modal on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  if (isLoading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-loading">Loading player details...</div>
        </div>
      </div>
    );
  }

  if (error || !player) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-error">
            <p>Failed to load player details</p>
            <button className="modal-close-btn" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  const initials = `${player.first_name[0] || ""}${player.second_name[0] || ""}`;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-x" onClick={onClose}>
          ×
        </button>

        {/* Player Header */}
        <div className="modal-player-header">
          <div className="modal-player-image">
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
          <div className="modal-player-info">
            <h2>{player.web_name}</h2>
            <p className="modal-player-full-name">
              {player.first_name} {player.second_name}
            </p>
            <div className="modal-player-meta">
              <span className="position-badge">
                {getPositionLabel(player.element_type)}
              </span>
              {player.team && player.team_code && (
                <div className="team-info">
                  <img
                    src={getTeamBadgeUrl(player.team_code)!}
                    alt={player.team}
                    className="team-badge-medium"
                  />
                  <span>{player.team}</span>
                </div>
              )}
            </div>
          </div>
          <div className="modal-radar-header">
            <RadarChart playerIds={[player.id]} height={360} width={360} showBreakdown={false} hideOnError={true} />

            {selectedHeatmapGw && (
              <div className="modal-heatmap-section">
                <div className="heatmap-controls">
                  <label>GW:</label>
                  <select
                    value={selectedHeatmapGw}
                    onChange={(e) => setSelectedHeatmapGw(Number(e.target.value))}
                    className="heatmap-gw-select"
                  >
                    {fixtureHistory.map(h => (
                      <option key={h.event} value={h.event}>GW{h.event} vs {h.opponent_team_short}</option>
                    ))}
                  </select>
                </div>
                <PlayerHeatmap playerId={player.id} gameweek={selectedHeatmapGw} />
              </div>
            )}
          </div>
        </div>

        {/* Player News */}
        {player.news && (
          <div className="modal-news-section">
            <div className="modal-news-icon">📰</div>
            <div className="modal-news-content">
              <p className="modal-news-text">{player.news}</p>
              {player.news_added && (
                <span className="modal-news-time">
                  {new Date(player.news_added).toLocaleString('en-GB', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Basic Stats */}
        <div className="modal-basic-stats">
          <div className="modal-stat-card">
            <span className="modal-stat-label">Price</span>
            <span className="modal-stat-value price-highlight">
              £{(player.now_cost / 10).toFixed(1)}m
            </span>
          </div>
          <div className="modal-stat-card">
            <span className="modal-stat-label">Total Points</span>
            <span className="modal-stat-value">{player.total_points}</span>
          </div>
          <div className="modal-stat-card">
            <span className="modal-stat-label">Form</span>
            <span className="modal-stat-value">
              {player.form?.toFixed(1) ?? "—"}
            </span>
          </div>
          <div className="modal-stat-card">
            <span className="modal-stat-label">PPG</span>
            <span className="modal-stat-value">
              {player.points_per_game?.toFixed(1) ?? "—"}
            </span>
          </div>
          <div className="modal-stat-card">
            <span className="modal-stat-label">Selected By</span>
            <span className="modal-stat-value">
              {player.selected_by_percent !== null
                ? `${player.selected_by_percent}%`
                : "—"}
            </span>
          </div>
          <div className="modal-stat-card">
            <span className="modal-stat-label">FDR</span>
            <span
              className="modal-stat-value fdr-badge-inline"
              style={{
                backgroundColor:
                  player.avg_fdr !== null
                    ? getDifficultyColor(player.avg_fdr)
                    : "#666",
              }}
            >
              {player.avg_fdr?.toFixed(1) ?? "—"}
            </span>
          </div>
        </div>

        {/* Upcoming Fixtures */}
        {upcomingFixtures.length > 0 && (
          <div className="modal-fixtures-section">
            <h3>📅 Upcoming Fixtures</h3>
            <div className="fixtures-list">
              {upcomingFixtures.map((fixture, idx) => (
                <div key={idx} className="fixture-item">
                  <span className="fixture-gw">GW{fixture.event}</span>
                  <span className="fixture-opponent">
                    {fixture.is_home ? 'vs' : '@'} {fixture.opponent_team_short}
                  </span>
                  <span
                    className="fixture-difficulty"
                    style={{ backgroundColor: getDifficultyColor(fixture.difficulty) }}
                  >
                    {fixture.difficulty}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fixture History */}
        {fixtureHistory.length > 0 && (
          <div className="modal-fixtures-section">
            <h3>📊 Recent Form</h3>
            <div className="fixtures-history-list">
              {fixtureHistory.map((fixture, idx) => (
                <div key={idx} className="fixture-history-item">
                  <span className="fixture-gw">GW{fixture.event}</span>
                  <span className="fixture-opponent">
                    {fixture.was_home ? 'vs' : '@'} {fixture.opponent_team_short}
                  </span>
                  <span className="fixture-performance">
                    {fixture.minutes}'
                    {fixture.goals_scored > 0 && ` ⚽${fixture.goals_scored}`}
                    {fixture.assists > 0 && ` 🅰️${fixture.assists}`}
                  </span>
                  <span
                    className={`fixture-points ${fixture.total_points >= 6 ? 'good' : fixture.total_points >= 3 ? 'ok' : 'poor'}`}
                  >
                    {fixture.total_points} pts
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* European/Cup Matches */}
        {europeanMatches.length > 0 && (
          <div className="modal-fixtures-section european-section">
            <h3>🏆 European & Cup Matches</h3>
            <p className="european-subtitle">Recent non-Premier League appearances</p>
            <div className="fixtures-history-list">
              {europeanMatches.map((match, idx) => (
                <div key={idx} className="fixture-history-item european-match">
                  <span className="fixture-competition" title={match.competition}>
                    {match.competition_short}
                  </span>
                  <span className="fixture-opponent">
                    {match.is_home ? 'vs' : '@'} {match.opponent}
                  </span>
                  <span className="fixture-performance">
                    {match.minutes}'
                    {match.goals > 0 && ` ⚽${match.goals}`}
                    {match.assists > 0 && ` 🅰️${match.assists}`}
                    {match.yellow_cards > 0 && ` 🟨`}
                    {match.red_cards > 0 && ` 🟥`}
                  </span>
                  {match.rating && (
                    <span className={`fixture-rating ${match.rating >= 7.5 ? 'good' : match.rating >= 6.5 ? 'ok' : 'poor'}`}>
                      {match.rating.toFixed(1)}
                    </span>
                  )}
                  <span className="fixture-date">
                    {new Date(match.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* See More Button */}
        {!expanded && (
          <button
            className="modal-see-more-btn"
            onClick={() => setExpanded(true)}
          >
            See More Stats ↓
          </button>
        )}

        {/* Expanded Stats */}
        {expanded && (
          <div className="modal-expanded-stats">
            {/* Cost & Ownership */}
            <div className="modal-stats-section">
              <h3>Cost & Ownership</h3>
              <div className="modal-stats-grid">
                <StatItem label="Price Change (Event)" value={player.cost_change_event !== null ? (player.cost_change_event > 0 ? `+${player.cost_change_event}` : player.cost_change_event) : "—"} />
                <StatItem label="Price Change (Season)" value={player.cost_change_start !== null ? (player.cost_change_start > 0 ? `+${player.cost_change_start}` : player.cost_change_start) : "—"} />
              </div>
            </div>

            {/* Points & Form */}
            <div className="modal-stats-section">
              <h3>Points & Form</h3>
              <div className="modal-stats-grid">
                <StatItem label="Event Points" value={player.event_points ?? "—"} />
                <StatItem label="Value Form" value={player.value_form?.toFixed(1) ?? "—"} />
                <StatItem label="Value Season" value={player.value_season?.toFixed(1) ?? "—"} />
              </div>
            </div>

            {/* Transfers */}
            <div className="modal-stats-section">
              <h3>Transfers</h3>
              <div className="modal-stats-grid">
                <StatItem label="Transfers In (Total)" value={player.transfers_in?.toLocaleString() ?? "—"} />
                <StatItem label="Transfers In (Event)" value={player.transfers_in_event?.toLocaleString() ?? "—"} />
                <StatItem label="Transfers Out (Total)" value={player.transfers_out?.toLocaleString() ?? "—"} />
                <StatItem label="Transfers Out (Event)" value={player.transfers_out_event?.toLocaleString() ?? "—"} />
              </div>
            </div>

            {/* Performance Stats */}
            <div className="modal-stats-section">
              <h3>Performance</h3>
              <div className="modal-stats-grid">
                <StatItem label="Minutes" value={player.minutes?.toLocaleString() ?? "—"} />
                <StatItem label="Starts" value={player.starts ?? "—"} />
                <StatItem label="Goals" value={player.goals_scored ?? "—"} highlight />
                <StatItem label="Assists" value={player.assists ?? "—"} highlight />
                <StatItem label="Clean Sheets" value={player.clean_sheets ?? "—"} />
                <StatItem label="Goals Conceded" value={player.goals_conceded ?? "—"} />
                <StatItem label="Saves" value={player.saves ?? "—"} />
                <StatItem label="Bonus" value={player.bonus ?? "—"} />
                <StatItem label="BPS" value={player.bps ?? "—"} />
                <StatItem label="Yellow Cards" value={player.yellow_cards ?? "—"} />
                <StatItem label="Red Cards" value={player.red_cards ?? "—"} />
              </div>
            </div>

            {/* ICT Index */}
            <div className="modal-stats-section">
              <h3>ICT Index</h3>
              <div className="modal-stats-grid">
                <StatItem label="Influence" value={player.influence?.toFixed(1) ?? "—"} />
                <StatItem label="Creativity" value={player.creativity?.toFixed(1) ?? "—"} />
                <StatItem label="Threat" value={player.threat?.toFixed(1) ?? "—"} />
                <StatItem label="ICT Index" value={player.ict_index?.toFixed(1) ?? "—"} highlight />
              </div>
            </div>

            {/* Expected Stats */}
            <div className="modal-stats-section">
              <h3>Expected Stats</h3>
              <div className="modal-stats-grid">
                <StatItem label="xG" value={player.expected_goals?.toFixed(2) ?? "—"} />
                <StatItem label="xA" value={player.expected_assists?.toFixed(2) ?? "—"} />
                <StatItem label="xGI" value={player.expected_goal_involvements?.toFixed(2) ?? "—"} />
                <StatItem label="xGC" value={player.expected_goals_conceded?.toFixed(2) ?? "—"} />
              </div>
            </div>

            {/* Per 90 Stats */}
            <div className="modal-stats-section">
              <h3>Per 90 Minutes</h3>
              <div className="modal-stats-grid">
                <StatItem label="xG per 90" value={player.expected_goals_per_90?.toFixed(2) ?? "—"} />
                <StatItem label="xA per 90" value={player.expected_assists_per_90?.toFixed(2) ?? "—"} />
                <StatItem label="xGI per 90" value={player.expected_goal_involvements_per_90?.toFixed(2) ?? "—"} />
                <StatItem label="xGC per 90" value={player.expected_goals_conceded_per_90?.toFixed(2) ?? "—"} />
                <StatItem label="GC per 90" value={player.goals_conceded_per_90?.toFixed(2) ?? "—"} />
                <StatItem label="Saves per 90" value={player.saves_per_90?.toFixed(2) ?? "—"} />
              </div>
            </div>

            {/* Rankings */}
            <div className="modal-stats-section">
              <h3>Rankings</h3>
              <div className="modal-stats-grid">
                <StatItem label="Influence Rank" value={player.influence_rank ?? "—"} />
                <StatItem label="Creativity Rank" value={player.creativity_rank ?? "—"} />
                <StatItem label="Threat Rank" value={player.threat_rank ?? "—"} />
                <StatItem label="ICT Index Rank" value={player.ict_index_rank ?? "—"} />
                <StatItem label="Form Rank" value={player.form_rank ?? "—"} />
                <StatItem label="PPG Rank" value={player.points_per_game_rank ?? "—"} />
              </div>
            </div>

            {/* Set Pieces */}
            <div className="modal-stats-section">
              <h3>Set Pieces</h3>
              <div className="modal-stats-grid">
                <StatItem label="Corners & Indirect FK" value={player.corners_and_indirect_freekicks_order ?? "—"} />
                <StatItem label="Direct Free Kicks" value={player.direct_freekicks_order ?? "—"} />
                <StatItem label="Penalties" value={player.penalties_order ?? "—"} />
              </div>
            </div>

            <button
              className="modal-collapse-btn"
              onClick={() => setExpanded(false)}
            >
              Show Less ↑
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper component for stat items
function StatItem({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div className={`modal-stat-item ${highlight ? "highlight" : ""}`}>
      <span className="modal-stat-item-label">{label}</span>
      <span className="modal-stat-item-value">{value}</span>
    </div>
  );
}
