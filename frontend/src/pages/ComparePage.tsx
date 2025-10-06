import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { RadarChart } from "../components/RadarChart";

// Use empty string for API base URL to use relative paths (proxied through Vite)
const API_BASE_URL = "";
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

    // Fetch detailed data for each player
    Promise.all(
      playerIds.map((id) =>
        fetch(`${API_BASE_URL}/api/players/${id}/`, {
          headers: { Accept: "application/json" },
        }).then((res) => res.json())
      )
    )
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
