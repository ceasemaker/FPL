import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { RadarChart } from "../components/RadarChart";
import "./ComparePage.css";

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

interface UpcomingFixture {
  event: number;
  opponent: string | null;
  is_home: boolean;
  difficulty: number | null;
}

interface UpcomingPrediction {
  game_week: number;
  predicted_points: number;
  clean_sheet_prob: number | null;
  goal_prob: number | null;
  assist_prob: number | null;
  bonus_prob: number | null;
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
  /** Official FPL expected points for the current and next gameweek. */
  ep_this: number | null;
  ep_next: number | null;
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
  upcoming_fixtures?: UpcomingFixture[];
  next_gameweek?: number;

  // Predicted points for the next gameweeks
  upcoming_predictions?: UpcomingPrediction[];
  
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

const POSITION_SHORT: Record<number, string> = { 1: "GK", 2: "DEF", 3: "MID", 4: "FWD" };

function formatPrice(nowCost: number | null): string {
  if (nowCost === null || nowCost === undefined) return "—";
  return `£${(nowCost / 10).toFixed(1)}m`;
}

function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(digits);
}

/** Sum of predicted points across the horizon we hold predictions for. */
function projectedTotal(player: DetailedPlayer): number | null {
  const predictions = player.upcoming_predictions ?? [];
  if (!predictions.length) return null;
  return predictions.reduce((total, p) => total + p.predicted_points, 0);
}

function nextGameweekProjection(player: DetailedPlayer): number | null {
  return player.upcoming_predictions?.[0]?.predicted_points ?? null;
}

/** Share of available minutes played, as a rough start-security signal. */
function minutesShare(player: DetailedPlayer): number | null {
  const minutes = player.minutes ?? 0;
  const starts = player.starts ?? 0;
  if (!minutes && !starts) return null;
  return starts > 0 ? minutes / (starts * 90) : 0;
}

function availabilityLabel(player: DetailedPlayer): { text: string; tone: "ok" | "warn" | "risk" } {
  const chance = player.chance_of_playing_next_round;
  if (player.status === "u") return { text: "Unavailable", tone: "risk" };
  if (chance !== null && chance !== undefined && chance < 100) {
    return { text: `${chance}% chance`, tone: chance <= 50 ? "risk" : "warn" };
  }
  if (player.status && player.status !== "a") return { text: "Flagged", tone: "warn" };
  return { text: "Available", tone: "ok" };
}

/**
 * Indexes of the players holding the best value for a metric, so the winner of
 * each decision row can be highlighted. Ties highlight every tied player.
 */
function bestIndexes(
  players: DetailedPlayer[],
  accessor: (player: DetailedPlayer) => number | null,
  higherIsBetter = true,
): Set<number> {
  const values = players.map(accessor);
  const present = values.filter((v): v is number => v !== null && Number.isFinite(v));
  if (present.length < 2) return new Set();
  const best = higherIsBetter ? Math.max(...present) : Math.min(...present);
  const winners = new Set<number>();
  values.forEach((value, index) => {
    if (value !== null && value === best) winners.add(index);
  });
  return winners;
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

  const columns = useMemo(
    () => ({ "--compare-players": players.length }) as CSSProperties,
    [players.length],
  );
  const nextGameweek = players.find((p) => p.next_gameweek)?.next_gameweek ?? null;
  const hasPredictions = players.some((p) => (p.upcoming_predictions ?? []).length > 0);
  const hasOfficialExpected = players.some((p) => p.ep_next !== null && p.ep_next !== undefined);
  const horizon = Math.max(0, ...players.map((p) => (p.upcoming_predictions ?? []).length));

  if (isLoading) {
    return (
      <main className="aero-page compare-page">
        <p className="aero-loading">Loading players…</p>
      </main>
    );
  }

  if (error || players.length < 2) {
    return (
      <main className="aero-page compare-page">
        <div className="aero-header">
          <div>
            <h1>Compare players</h1>
            <p>Pick at least two players from the Players page to see them side by side.</p>
          </div>
        </div>
        <p className="aero-error">{error || "Not enough players selected"}</p>
        <button className="aero-button primary" onClick={() => navigate("/players")}>
          Back to players
        </button>
      </main>
    );
  }

  return (
    <main className="aero-page compare-page">
      <div className="aero-header">
        <div>
          <h1>Compare players</h1>
          <p>
            {nextGameweek
              ? `Decision view for Gameweek ${nextGameweek} and the run that follows.`
              : "Side-by-side decision view."}
          </p>
        </div>
        <button className="aero-button ghost" onClick={() => navigate("/players")}>
          ← Back to players
        </button>
      </div>

      {/* Player identity row — stays at the top of every comparison. */}
      <section className="compare-identity" style={columns}>
        <div className="compare-row-label" />
        {players.map((player) => {
          const badge = getTeamBadgeUrl(player.team_code);
          const availability = availabilityLabel(player);
          return (
            <article key={player.id} className="compare-player">
              <div className="compare-player-face">
                <img
                  src={
                    player.image_url ||
                    `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-220.webp`
                  }
                  alt={player.web_name}
                  loading="lazy"
                />
              </div>
              <h2>{player.web_name}</h2>
              <p className="compare-player-meta">
                {badge && <img className="compare-badge" src={badge} alt="" />}
                <span>{player.team ?? "—"}</span>
                <span className="aero-chip">{POSITION_SHORT[player.element_type] ?? "?"}</span>
              </p>
              <p className="compare-player-price">
                <strong>{formatPrice(player.now_cost)}</strong>
                <span>{formatNumber(player.selected_by_percent, 1)}% owned</span>
              </p>
              <span className={`compare-availability ${availability.tone}`}>{availability.text}</span>
            </article>
          );
        })}
      </section>

      {/* The decision itself: the handful of numbers that actually pick a player. */}
      <section className="aero-card compare-block">
        <header className="aero-card-title">
          <div>
            <h3>Decision snapshot</h3>
            <p>Best value in each row is highlighted.</p>
          </div>
        </header>
        <div className="compare-grid" style={columns}>
          {hasOfficialExpected && (
            <DecisionRow
              label={nextGameweek ? `Expected points GW${nextGameweek}` : "Expected points"}
              players={players}
              value={(p) => p.ep_next}
              format={(v) => formatNumber(v, 1)}
              hint="Official FPL projection"
              columns={columns}
            />
          )}
          {hasPredictions && (
            <>
              <DecisionRow
                label={nextGameweek ? `Model projection GW${nextGameweek}` : "Model projection"}
                players={players}
                value={nextGameweekProjection}
                format={(v) => formatNumber(v, 1)}
                hint="Stored model output"
                columns={columns}
              />
              <DecisionRow
                label={horizon > 1 ? `Model projection, next ${horizon} GWs` : "Model projection total"}
                players={players}
                value={projectedTotal}
                format={(v) => formatNumber(v, 1)}
                columns={columns}
              />
            </>
          )}
          <DecisionRow
            label="Form"
            players={players}
            value={(p) => p.form}
            format={(v) => formatNumber(v, 1)}
            columns={columns}
          />
          <DecisionRow
            label="Points per game"
            players={players}
            value={(p) => p.points_per_game}
            format={(v) => formatNumber(v, 1)}
            columns={columns}
          />
          <DecisionRow
            label="Total points"
            players={players}
            value={(p) => p.total_points}
            format={(v) => (v === null ? "—" : String(v))}
            columns={columns}
          />
          <DecisionRow
            label="Price"
            players={players}
            value={(p) => p.now_cost}
            format={formatPrice}
            higherIsBetter={false}
            columns={columns}
          />
          <DecisionRow
            label="Ownership"
            players={players}
            value={(p) => p.selected_by_percent}
            format={(v) => (v === null ? "—" : `${v.toFixed(1)}%`)}
            higherIsBetter={false}
            hint="Lower ownership is the differential play"
            columns={columns}
          />
          <DecisionRow
            label="Next 3 fixture difficulty"
            players={players}
            value={(p) => p.avg_fdr}
            format={(v) => formatNumber(v, 1)}
            higherIsBetter={false}
            columns={columns}
          />
        </div>
        {!hasPredictions && (
          <p className="aero-note compare-note">
            Expected points above come from the official FPL projection. No stored model
            projection exists for these players yet, so none is shown rather than a guess.
          </p>
        )}
      </section>

      {/* Fixtures: who they actually face, not just an averaged number. */}
      <section className="aero-card compare-block">
        <header className="aero-card-title">
          <div>
            <h3>Upcoming fixtures</h3>
            <p>Next five matches with difficulty rating.</p>
          </div>
        </header>
        <div className="compare-grid" style={columns}>
          <div className="compare-row" style={columns}>
            <div className="compare-row-label">Schedule</div>
            {players.map((player) => (
              <div key={player.id} className="compare-cell">
                <div className="compare-fixtures">
                  {(player.upcoming_fixtures ?? []).length > 0 ? (
                    player.upcoming_fixtures!.map((fixture) => (
                      <span key={`${player.id}-${fixture.event}`} className="compare-fixture">
                        <span className="aero-fdr" data-fdr={fixture.difficulty ?? ""}>
                          {fixture.difficulty ?? "—"}
                        </span>
                        <b>{fixture.opponent ?? "—"}</b>
                        <small>
                          GW{fixture.event} · {fixture.is_home ? "H" : "A"}
                        </small>
                      </span>
                    ))
                  ) : (
                    <p className="aero-empty">No scheduled fixtures.</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Minutes risk and role — the two things that most often break a pick. */}
      <div className="compare-split">
        <section className="aero-card compare-block">
          <header className="aero-card-title">
            <div>
              <h3>Minutes &amp; start risk</h3>
              <p>Will they actually play?</p>
            </div>
          </header>
          <div className="compare-grid" style={columns}>
            <DecisionRow
              label="Starts"
              players={players}
              value={(p) => p.starts}
              format={(v) => (v === null ? "—" : String(v))}
              columns={columns}
            />
            <DecisionRow
              label="Minutes"
              players={players}
              value={(p) => p.minutes}
              format={(v) => (v === null ? "—" : v.toLocaleString())}
              columns={columns}
            />
            <DecisionRow
              label="Minutes per start"
              players={players}
              value={(p) => {
                const share = minutesShare(p);
                return share === null ? null : Math.round(share * 90);
              }}
              format={(v) => (v === null ? "—" : `${v}'`)}
              columns={columns}
            />
            <div className="compare-row" style={columns}>
              <div className="compare-row-label">Availability</div>
              {players.map((player) => {
                const availability = availabilityLabel(player);
                return (
                  <div key={player.id} className="compare-cell">
                    <span className={`compare-availability ${availability.tone}`}>
                      {availability.text}
                    </span>
                    {player.news && <small className="compare-news">{player.news}</small>}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="aero-card compare-block">
          <header className="aero-card-title">
            <div>
              <h3>Set-piece role</h3>
              <p>Order in the queue (1 is first choice).</p>
            </div>
          </header>
          <div className="compare-grid" style={columns}>
            <DecisionRow
              label="Penalties"
              players={players}
              value={(p) => p.penalties_order}
              format={(v) => (v === null ? "—" : `#${v}`)}
              higherIsBetter={false}
              columns={columns}
            />
            <DecisionRow
              label="Direct free kicks"
              players={players}
              value={(p) => p.direct_freekicks_order}
              format={(v) => (v === null ? "—" : `#${v}`)}
              higherIsBetter={false}
              columns={columns}
            />
            <DecisionRow
              label="Corners"
              players={players}
              value={(p) => p.corners_and_indirect_freekicks_order}
              format={(v) => (v === null ? "—" : `#${v}`)}
              higherIsBetter={false}
              columns={columns}
            />
          </div>
        </section>
      </div>

      {/* Recent form */}
      <section className="aero-card compare-block">
        <header className="aero-card-title">
          <div>
            <h3>Recent form</h3>
            <p>Last five gameweeks.</p>
          </div>
        </header>
        <div className="compare-columns" style={columns}>
          {players.map((player) => (
            <div key={player.id} className="compare-form-column">
              <h4>{player.web_name}</h4>
              {(player.fixtureHistory ?? []).length > 0 ? (
                player.fixtureHistory!.map((fixture, index) => (
                  <div key={index} className="compare-form-row">
                    <span className="compare-form-gw">GW{fixture.event}</span>
                    <span className="compare-form-opponent">
                      {fixture.opponent_team_short} ({fixture.was_home ? "H" : "A"})
                    </span>
                    <span className="compare-form-detail">
                      {fixture.minutes}&apos;
                      {fixture.goals_scored > 0 && ` · ${fixture.goals_scored}G`}
                      {fixture.assists > 0 && ` · ${fixture.assists}A`}
                      {fixture.bonus > 0 && ` · ${fixture.bonus}B`}
                    </span>
                    <span
                      className={`compare-form-points ${
                        fixture.total_points >= 10
                          ? "great"
                          : fixture.total_points >= 6
                            ? "good"
                            : fixture.total_points >= 3
                              ? "ok"
                              : "poor"
                      }`}
                    >
                      {fixture.total_points}
                    </span>
                  </div>
                ))
              ) : (
                <p className="aero-empty">No recent games.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Attribute radar */}
      <section className="aero-card compare-block">
        <header className="aero-card-title">
          <div>
            <h3>Player attributes</h3>
            <p>Relative strengths across the profile.</p>
          </div>
        </header>
        <div className="compare-radar">
          <RadarChart
            playerIds={players.map((p) => p.id)}
            height={460}
            width={460}
            showBreakdown
            hideOnError={false}
          />
        </div>
      </section>

      {/* Everything else stays available, just out of the decision path. */}
      <details className="aero-card compare-block compare-details">
        <summary>All statistics</summary>

        <StatGroup title="Points &amp; value" columns={columns}>
          <StatRow label="Event points" players={players} columns={columns} accessor={(p) => p.event_points ?? "—"} />
          <StatRow label="Value (form)" players={players} columns={columns} accessor={(p) => p.value_form ?? "—"} />
          <StatRow label="Value (season)" players={players} columns={columns} accessor={(p) => p.value_season ?? "—"} />
          <StatRow label="Price change (GW)" players={players} columns={columns} accessor={(p) => formatPrice(p.cost_change_event)} />
          <StatRow label="Price change (season)" players={players} columns={columns} accessor={(p) => formatPrice(p.cost_change_start)} />
        </StatGroup>

        <StatGroup title="Transfers" columns={columns}>
          <StatRow label="In (GW)" players={players} columns={columns} accessor={(p) => (p.transfers_in_event ?? 0).toLocaleString()} />
          <StatRow label="Out (GW)" players={players} columns={columns} accessor={(p) => (p.transfers_out_event ?? 0).toLocaleString()} />
          <StatRow label="In (season)" players={players} columns={columns} accessor={(p) => (p.transfers_in ?? 0).toLocaleString()} />
          <StatRow label="Out (season)" players={players} columns={columns} accessor={(p) => (p.transfers_out ?? 0).toLocaleString()} />
        </StatGroup>

        <StatGroup title="Attacking &amp; defending" columns={columns}>
          <StatRow label="Goals" players={players} columns={columns} accessor={(p) => p.goals_scored ?? 0} />
          <StatRow label="Assists" players={players} columns={columns} accessor={(p) => p.assists ?? 0} />
          <StatRow label="Clean sheets" players={players} columns={columns} accessor={(p) => p.clean_sheets ?? 0} />
          <StatRow label="Goals conceded" players={players} columns={columns} accessor={(p) => p.goals_conceded ?? 0} />
          <StatRow label="Saves" players={players} columns={columns} accessor={(p) => p.saves ?? 0} />
          <StatRow label="Bonus" players={players} columns={columns} accessor={(p) => p.bonus ?? 0} />
          <StatRow label="BPS" players={players} columns={columns} accessor={(p) => p.bps ?? 0} />
          <StatRow label="Yellow cards" players={players} columns={columns} accessor={(p) => p.yellow_cards ?? 0} />
          <StatRow label="Red cards" players={players} columns={columns} accessor={(p) => p.red_cards ?? 0} />
        </StatGroup>

        <StatGroup title="ICT index" columns={columns}>
          <StatRow label="Influence" players={players} columns={columns} accessor={(p) => formatNumber(p.influence, 1)} />
          <StatRow label="Creativity" players={players} columns={columns} accessor={(p) => formatNumber(p.creativity, 1)} />
          <StatRow label="Threat" players={players} columns={columns} accessor={(p) => formatNumber(p.threat, 1)} />
          <StatRow label="ICT index" players={players} columns={columns} accessor={(p) => formatNumber(p.ict_index, 1)} />
        </StatGroup>

        <StatGroup title="Expected stats" columns={columns}>
          <StatRow label="xG" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_goals, 2)} />
          <StatRow label="xA" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_assists, 2)} />
          <StatRow label="xGI" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_goal_involvements, 2)} />
          <StatRow label="xGC" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_goals_conceded, 2)} />
          <StatRow label="xG per 90" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_goals_per_90, 2)} />
          <StatRow label="xA per 90" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_assists_per_90, 2)} />
          <StatRow label="xGI per 90" players={players} columns={columns} accessor={(p) => formatNumber(p.expected_goal_involvements_per_90, 2)} />
          <StatRow label="Clean sheets per 90" players={players} columns={columns} accessor={(p) => formatNumber(p.clean_sheets_per_90, 2)} />
        </StatGroup>

        <StatGroup title="Rankings" columns={columns}>
          <StatRow label="Form rank" players={players} columns={columns} accessor={(p) => p.form_rank ?? "—"} />
          <StatRow label="Points per game rank" players={players} columns={columns} accessor={(p) => p.points_per_game_rank ?? "—"} />
          <StatRow label="ICT rank" players={players} columns={columns} accessor={(p) => p.ict_index_rank ?? "—"} />
          <StatRow label="Threat rank" players={players} columns={columns} accessor={(p) => p.threat_rank ?? "—"} />
          <StatRow label="Creativity rank" players={players} columns={columns} accessor={(p) => p.creativity_rank ?? "—"} />
          <StatRow label="Selected rank" players={players} columns={columns} accessor={(p) => p.selected_rank ?? "—"} />
        </StatGroup>

        {players.some((p) => (p.europeanMatches ?? []).length > 0) && (
          <div className="compare-euro">
            <h4>European &amp; cup matches</h4>
            <div className="compare-columns" style={columns}>
              {players.map((player) => (
                <div key={player.id} className="compare-form-column">
                  <h4>{player.web_name}</h4>
                  {(player.europeanMatches ?? []).length > 0 ? (
                    player.europeanMatches!.map((match, index) => (
                      <div key={index} className="compare-euro-match">
                        <span className="aero-chip">{match.competition_short}</span>
                        <b>
                          {match.home_team} {match.home_score ?? "-"}–{match.away_score ?? "-"}{" "}
                          {match.away_team}
                        </b>
                        <small>
                          {match.minutes_played}&apos;
                          {match.goals > 0 && ` · ${match.goals}G`}
                          {match.assists > 0 && ` · ${match.assists}A`}
                          {match.rating !== null && ` · ${match.rating.toFixed(1)} rating`}
                        </small>
                      </div>
                    ))
                  ) : (
                    <p className="aero-empty">No European or cup games.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </details>
    </main>
  );
}

/** One decision metric across every player, with the best value highlighted. */
function DecisionRow({
  label,
  players,
  value,
  format,
  higherIsBetter = true,
  hint,
  columns,
}: {
  label: string;
  players: DetailedPlayer[];
  value: (player: DetailedPlayer) => number | null;
  format: (value: number | null) => string;
  higherIsBetter?: boolean;
  hint?: string;
  columns: CSSProperties;
}) {
  const winners = bestIndexes(players, value, higherIsBetter);
  return (
    <div className="compare-row" style={columns}>
      <div className="compare-row-label">
        {label}
        {hint && <small>{hint}</small>}
      </div>
      {players.map((player, index) => (
        <div key={player.id} className={`compare-cell${winners.has(index) ? " best" : ""}`}>
          <strong>{format(value(player))}</strong>
        </div>
      ))}
    </div>
  );
}

function StatGroup({
  title,
  children,
  columns,
}: {
  title: string;
  children: ReactNode;
  columns: CSSProperties;
}) {
  return (
    <div className="compare-stat-group">
      <h4>{title}</h4>
      <div className="compare-grid" style={columns}>
        {children}
      </div>
    </div>
  );
}

function StatRow({
  label,
  players,
  accessor,
  columns,
}: {
  label: string;
  players: DetailedPlayer[];
  accessor: (player: DetailedPlayer) => string | number;
  columns: CSSProperties;
}) {
  return (
    <div className="compare-row" style={columns}>
      <div className="compare-row-label">{label}</div>
      {players.map((player) => (
        <div key={player.id} className="compare-cell">
          <strong>{accessor(player)}</strong>
        </div>
      ))}
    </div>
  );
}
