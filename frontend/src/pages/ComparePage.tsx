import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { RadarChart } from "../components/RadarChart";

// Use empty string for API base URL to use relative paths (proxied through Vite)
const API_BASE_URL = "";
const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

interface FixtureHistory {
  event: number;
  opponent_team: string;
  opponent_team_short: string;
  was_home: boolean;
  total_points: number;
  minutes: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  bonus: number;
}

interface EuropeanMatch {
  event_id: string;
  date: string | null;
  competition: string;
  competition_short: string;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  minutes_played: number;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  rating: number | null;
}

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
  
  // Recent fixture history (populated separately)
  fixtureHistory?: FixtureHistory[];
  
  // European/Other competition matches (populated separately)
  europeanMatches?: EuropeanMatch[];
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

export function ComparePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [players, setPlayers] = useState<DetailedPlayer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const playerIds = searchParams.get("ids")?.split(",").map(Number) || [];

    if (playerIds.length < 2) {
      setError("Please select at least 2 players to compare");
      setIsLoading(false);
      return;
    }

    // Fetch bootstrap-static for team names, then player data + summaries
    fetch(`${API_BASE_URL}/api/fpl/bootstrap-static/`)
      .then((res) => res.json())
      .then((bootstrapData) => {
        // Create team lookup map
        const teamsMap = new Map<number, { name: string; short_name: string }>();
        (bootstrapData.teams || []).forEach((team: any) => {
          teamsMap.set(team.id, {
            name: team.name,
            short_name: team.short_name,
          });
        });

        // Fetch player details, FPL summaries, and European matches in parallel
        return Promise.all(
          playerIds.map((id) =>
            Promise.all([
              fetch(`${API_BASE_URL}/api/players/${id}/`, {
                headers: { Accept: "application/json" },
              }).then((res) => res.json()),
              fetch(`${API_BASE_URL}/api/fpl/element-summary/${id}/`)
                .then((res) => res.json())
                .catch(() => ({ history: [] })), // Handle missing summaries gracefully
              fetch(`${API_BASE_URL}/api/sofasport/player/${id}/recent-matches/?limit=10`)
                .then((res) => res.json())
                .catch(() => ({ matches: [] })), // Handle missing European data gracefully
            ]).then(([playerData, summaryData, europeanData]) => {
              // Get fixture history (last 5)
              const history = (summaryData.history || [])
                .slice(-5)
                .reverse()
                .map((h: any) => {
                  const opponentTeam = teamsMap.get(h.opponent_team);
                  return {
                    event: h.round,
                    opponent_team: opponentTeam?.name || "Unknown",
                    opponent_team_short: opponentTeam?.short_name || "UNK",
                    was_home: h.was_home,
                    total_points: h.total_points || 0,
                    minutes: h.minutes || 0,
                    goals_scored: h.goals_scored || 0,
                    assists: h.assists || 0,
                    clean_sheets: h.clean_sheets || 0,
                    bonus: h.bonus || 0,
                  };
                });

              // Filter European matches to only non-Premier League
              const europeanMatches = (europeanData.matches || [])
                .filter((m: any) => m.competition_short !== "PL")
                .slice(0, 5);

              return {
                ...playerData,
                fixtureHistory: history,
                europeanMatches: europeanMatches,
              };
            })
          )
        );
      })
      .then((playersData) => {
        setPlayers(playersData);
        setError(null);
      })
      .catch((err) => {
        console.error("Failed to load players", err);
        setError(err.message ?? "Unexpected error");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [searchParams]);

  if (isLoading) {
    return (
      <div className="page">
        <div className="compare-loading">Loading players...</div>
      </div>
    );
  }

  if (error || players.length < 2) {
    return (
      <div className="page">
        <div className="compare-error">
          <h2>Unable to Compare</h2>
          <p>{error || "Not enough players selected"}</p>
          <button className="back-btn" onClick={() => navigate("/players")}>
            Back to Players
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page compare-page">
      <div className="compare-header">
        <h1>Player Comparison</h1>
        <button className="back-btn" onClick={() => navigate("/players")}>
          ← Back to Players
        </button>
      </div>

      <div className="comparison-container">
        {/* Player Headers */}
        <div className="comparison-players-header">
          {players.map((player) => {
            const initials = `${player.first_name[0] || ""}${player.second_name[0] || ""}`;
            return (
              <div key={player.id} className="comparison-player-card">
                <div className="comparison-player-image">
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
                <h2>{player.web_name}</h2>
                <div className="player-team-info">
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
                {player.news && (
                  <div className="comparison-player-news">
                    <div className="news-icon">📰</div>
                    <div className="news-content">
                      <p>{player.news}</p>
                      {player.news_added && (
                        <span className="news-timestamp">
                          {new Date(player.news_added).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short'
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Radar Chart Comparison */}
        <div className="comparison-radar-section">
          <h3 className="section-title">Player Attributes</h3>
          <div className="comparison-radar-wrapper">
            <RadarChart 
              playerIds={players.map(p => p.id)} 
              height={500} 
              width={500} 
              showBreakdown={true}
              hideOnError={false}
            />
          </div>
        </div>

        {/* Recent Form Comparison */}
        <div className="comparison-recent-form">
          <h3 className="section-title">📊 Recent Form</h3>
          <p className="section-subtitle">Last 5 gameweeks performance comparison</p>
          <div className="recent-form-grid" style={{ gridTemplateColumns: `repeat(${players.length}, 1fr)` }}>
            {players.map((player) => (
              <div key={player.id} className="recent-form-column">
                <div className="recent-form-player-name">{player.web_name}</div>
                <div className="recent-form-list">
                  {(player.fixtureHistory || []).length > 0 ? (
                    player.fixtureHistory!.map((fixture, idx) => (
                      <div key={idx} className="recent-form-item">
                        <span className="form-gw">GW{fixture.event}</span>
                        <span className="form-opponent">
                          {fixture.was_home ? "vs" : "@"} {fixture.opponent_team_short}
                        </span>
                        <span className="form-details">
                          {fixture.minutes}'
                          {fixture.goals_scored > 0 && ` ⚽${fixture.goals_scored}`}
                          {fixture.assists > 0 && ` 🅰️${fixture.assists}`}
                          {fixture.clean_sheets > 0 && ` 🛡️`}
                          {fixture.bonus > 0 && ` +${fixture.bonus}bp`}
                        </span>
                        <span
                          className={`form-points ${
                            fixture.total_points >= 8
                              ? "excellent"
                              : fixture.total_points >= 5
                              ? "good"
                              : fixture.total_points >= 2
                              ? "ok"
                              : "poor"
                          }`}
                        >
                          {fixture.total_points}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="no-history">No recent games</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* European / Other Competitions */}
        {players.some((p) => (p.europeanMatches || []).length > 0) && (
          <div className="comparison-european-matches">
            <h3 className="section-title">🏆 European & Cup Matches</h3>
            <p className="section-subtitle">
              UCL, Europa League, Conference League, FA Cup, EFL Cup — recent non-Premier League appearances
            </p>
            <div className="european-matches-grid" style={{ gridTemplateColumns: `repeat(${players.length}, 1fr)` }}>
              {players.map((player) => (
                <div key={player.id} className="european-matches-column">
                  <div className="european-matches-player-name">{player.web_name}</div>
                  <div className="european-matches-list">
                    {(player.europeanMatches || []).length > 0 ? (
                      player.europeanMatches!.map((match, idx) => (
                        <div key={idx} className="european-match-item">
                          <div className="match-header">
                            <span className={`competition-badge ${match.competition_short.toLowerCase()}`}>
                              {match.competition_short}
                            </span>
                            {match.date && (
                              <span className="match-date">
                                {new Date(match.date).toLocaleDateString("en-GB", {
                                  day: "numeric",
                                  month: "short",
                                })}
                              </span>
                            )}
                          </div>
                          <div className="match-teams">
                            <span className="team-name">{match.home_team}</span>
                            <span className="match-score">
                              {match.home_score ?? "?"} - {match.away_score ?? "?"}
                            </span>
                            <span className="team-name">{match.away_team}</span>
                          </div>
                          <div className="match-stats">
                            <span className="stat-item">
                              {match.minutes_played}'
                            </span>
                            {match.goals > 0 && (
                              <span className="stat-item goal">⚽ {match.goals}</span>
                            )}
                            {match.assists > 0 && (
                              <span className="stat-item assist">🅰️ {match.assists}</span>
                            )}
                            {match.yellow_cards > 0 && (
                              <span className="stat-item yellow">🟨</span>
                            )}
                            {match.red_cards > 0 && (
                              <span className="stat-item red">🟥</span>
                            )}
                            {match.rating && (
                              <span className={`rating-badge ${match.rating >= 7 ? "good" : match.rating >= 6 ? "ok" : "poor"}`}>
                                {match.rating}
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="no-european-matches">No European/Cup games</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats Comparison Table */}
        <div className="comparison-stats-table">
          {/* Cost & Ownership */}
          <div className="stats-section">
            <h3 className="section-title">Cost & Ownership</h3>
            <StatRow label="Price" players={players} accessor={(p) => `£${(p.now_cost / 10).toFixed(1)}m`} />
            <StatRow label="Selected By" players={players} accessor={(p) => p.selected_by_percent !== null ? `${p.selected_by_percent}%` : "—"} />
            <StatRow label="Price Change (Event)" players={players} accessor={(p) => p.cost_change_event !== null ? (p.cost_change_event > 0 ? `+${p.cost_change_event}` : p.cost_change_event) : "—"} />
            <StatRow label="Price Change (Season)" players={players} accessor={(p) => p.cost_change_start !== null ? (p.cost_change_start > 0 ? `+${p.cost_change_start}` : p.cost_change_start) : "—"} />
          </div>

          {/* Points & Form */}
          <div className="stats-section">
            <h3 className="section-title">Points & Form</h3>
            <StatRow label="Total Points" players={players} accessor={(p) => p.total_points} highlight />
            <StatRow label="Event Points" players={players} accessor={(p) => p.event_points ?? "—"} />
            <StatRow label="Points Per Game" players={players} accessor={(p) => p.points_per_game?.toFixed(1) ?? "—"} />
            <StatRow label="Form" players={players} accessor={(p) => p.form?.toFixed(1) ?? "—"} />
            <StatRow label="Value Form" players={players} accessor={(p) => p.value_form?.toFixed(1) ?? "—"} />
            <StatRow label="Value Season" players={players} accessor={(p) => p.value_season?.toFixed(1) ?? "—"} />
          </div>

          {/* Transfers */}
          <div className="stats-section">
            <h3 className="section-title">Transfers</h3>
            <StatRow label="Transfers In (Total)" players={players} accessor={(p) => p.transfers_in?.toLocaleString() ?? "—"} />
            <StatRow label="Transfers In (Event)" players={players} accessor={(p) => p.transfers_in_event?.toLocaleString() ?? "—"} />
            <StatRow label="Transfers Out (Total)" players={players} accessor={(p) => p.transfers_out?.toLocaleString() ?? "—"} />
            <StatRow label="Transfers Out (Event)" players={players} accessor={(p) => p.transfers_out_event?.toLocaleString() ?? "—"} />
          </div>

          {/* Performance Stats */}
          <div className="stats-section">
            <h3 className="section-title">Performance</h3>
            <StatRow label="Minutes" players={players} accessor={(p) => p.minutes?.toLocaleString() ?? "—"} />
            <StatRow label="Starts" players={players} accessor={(p) => p.starts ?? "—"} />
            <StatRow label="Goals" players={players} accessor={(p) => p.goals_scored ?? "—"} highlight />
            <StatRow label="Assists" players={players} accessor={(p) => p.assists ?? "—"} highlight />
            <StatRow label="Clean Sheets" players={players} accessor={(p) => p.clean_sheets ?? "—"} />
            <StatRow label="Goals Conceded" players={players} accessor={(p) => p.goals_conceded ?? "—"} />
            <StatRow label="Own Goals" players={players} accessor={(p) => p.own_goals ?? "—"} />
            <StatRow label="Penalties Saved" players={players} accessor={(p) => p.penalties_saved ?? "—"} />
            <StatRow label="Penalties Missed" players={players} accessor={(p) => p.penalties_missed ?? "—"} />
            <StatRow label="Yellow Cards" players={players} accessor={(p) => p.yellow_cards ?? "—"} />
            <StatRow label="Red Cards" players={players} accessor={(p) => p.red_cards ?? "—"} />
            <StatRow label="Saves" players={players} accessor={(p) => p.saves ?? "—"} />
            <StatRow label="Bonus Points" players={players} accessor={(p) => p.bonus ?? "—"} />
            <StatRow label="BPS" players={players} accessor={(p) => p.bps ?? "—"} />
          </div>

          {/* ICT Index */}
          <div className="stats-section">
            <h3 className="section-title">ICT Index</h3>
            <StatRow label="Influence" players={players} accessor={(p) => p.influence?.toFixed(1) ?? "—"} />
            <StatRow label="Creativity" players={players} accessor={(p) => p.creativity?.toFixed(1) ?? "—"} />
            <StatRow label="Threat" players={players} accessor={(p) => p.threat?.toFixed(1) ?? "—"} />
            <StatRow label="ICT Index" players={players} accessor={(p) => p.ict_index?.toFixed(1) ?? "—"} highlight />
          </div>

          {/* Expected Stats */}
          <div className="stats-section">
            <h3 className="section-title">Expected Stats</h3>
            <StatRow label="xG (Expected Goals)" players={players} accessor={(p) => p.expected_goals?.toFixed(2) ?? "—"} />
            <StatRow label="xA (Expected Assists)" players={players} accessor={(p) => p.expected_assists?.toFixed(2) ?? "—"} />
            <StatRow label="xGI (Expected Goal Involvements)" players={players} accessor={(p) => p.expected_goal_involvements?.toFixed(2) ?? "—"} />
            <StatRow label="xGC (Expected Goals Conceded)" players={players} accessor={(p) => p.expected_goals_conceded?.toFixed(2) ?? "—"} />
          </div>

          {/* Per 90 Stats */}
          <div className="stats-section">
            <h3 className="section-title">Per 90 Minutes</h3>
            <StatRow label="xG per 90" players={players} accessor={(p) => p.expected_goals_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="xA per 90" players={players} accessor={(p) => p.expected_assists_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="xGI per 90" players={players} accessor={(p) => p.expected_goal_involvements_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="xGC per 90" players={players} accessor={(p) => p.expected_goals_conceded_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="Goals Conceded per 90" players={players} accessor={(p) => p.goals_conceded_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="Saves per 90" players={players} accessor={(p) => p.saves_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="Starts per 90" players={players} accessor={(p) => p.starts_per_90?.toFixed(2) ?? "—"} />
            <StatRow label="Clean Sheets per 90" players={players} accessor={(p) => p.clean_sheets_per_90?.toFixed(2) ?? "—"} />
          </div>

          {/* Rankings */}
          <div className="stats-section">
            <h3 className="section-title">Rankings</h3>
            <StatRow label="Influence Rank" players={players} accessor={(p) => p.influence_rank ?? "—"} />
            <StatRow label="Creativity Rank" players={players} accessor={(p) => p.creativity_rank ?? "—"} />
            <StatRow label="Threat Rank" players={players} accessor={(p) => p.threat_rank ?? "—"} />
            <StatRow label="ICT Index Rank" players={players} accessor={(p) => p.ict_index_rank ?? "—"} />
            <StatRow label="Form Rank" players={players} accessor={(p) => p.form_rank ?? "—"} />
            <StatRow label="Points Per Game Rank" players={players} accessor={(p) => p.points_per_game_rank ?? "—"} />
          </div>

          {/* Set Pieces */}
          <div className="stats-section">
            <h3 className="section-title">Set Pieces</h3>
            <StatRow label="Corners & Indirect FK" players={players} accessor={(p) => p.corners_and_indirect_freekicks_order ?? "—"} />
            <StatRow label="Direct Free Kicks" players={players} accessor={(p) => p.direct_freekicks_order ?? "—"} />
            <StatRow label="Penalties" players={players} accessor={(p) => p.penalties_order ?? "—"} />
          </div>

          {/* Fixtures */}
          <div className="stats-section">
            <h3 className="section-title">Fixtures</h3>
            <StatRow 
              label="FDR (Next 3)" 
              players={players} 
              accessor={(p) => p.avg_fdr !== null ? p.avg_fdr.toFixed(1) : "—"}
              renderValue={(value, player) => (
                player.avg_fdr !== null ? (
                  <span
                    className="fdr-badge-inline"
                    style={{ backgroundColor: getDifficultyColor(player.avg_fdr) }}
                  >
                    {value}
                  </span>
                ) : value
              )}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper component for stat rows
function StatRow({ 
  label, 
  players, 
  accessor,
  highlight = false,
  renderValue
}: { 
  label: string; 
  players: DetailedPlayer[]; 
  accessor: (player: DetailedPlayer) => string | number;
  highlight?: boolean;
  renderValue?: (value: string | number, player: DetailedPlayer) => React.ReactNode;
}) {
  return (
    <div className={`stat-comparison-row ${highlight ? 'highlight' : ''}`}>
      <div className="stat-label">{label}</div>
      {players.map((player) => {
        const value = accessor(player);
        return (
          <div key={player.id} className="stat-value">
            {renderValue ? renderValue(value, player) : value}
          </div>
        );
      })}
    </div>
  );
}
