import { useState, useEffect } from "react";
import "./FixturesPage.css";

interface FixtureOdds {
  home: number | null;
  draw: number | null;
  away: number | null;
  home_movement: string | null;
  draw_movement: string | null;
  away_movement: string | null;
  last_updated: string | null;
}

interface Fixture {
  event_id: string;
  competition: string;
  competition_name: string;
  kickoff_time: string;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  status: string;
  odds: FixtureOdds | null;
}

interface FixturesResponse {
  fixtures: Fixture[];
  total_count: number;
  days_ahead: number;
  competitions: string;
}

type CompetitionFilter = "ALL" | "PL" | "UCL" | "UEL" | "UECL" | "FAC" | "EFL";

const COMPETITION_BADGES: Record<string, { name: string; emoji: string; color: string }> = {
  PL: { name: "Premier League", emoji: "⚽", color: "#38003c" },
  UCL: { name: "Champions League", emoji: "⭐", color: "#003366" },
  UEL: { name: "Europa League", emoji: "🟠", color: "#ff6b00" },
  UECL: { name: "Conference League", emoji: "🟢", color: "#00963e" },
  FAC: { name: "FA Cup", emoji: "🏆", color: "#df0027" },
  EFL: { name: "EFL Cup", emoji: "🥇", color: "#00a9e0" },
};

export function FixturesPage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<CompetitionFilter>("ALL");
  const [days, setDays] = useState(7);

  useEffect(() => {
    fetchFixtures();
  }, [filter, days]);

  const fetchFixtures = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        days: days.toString(),
        competitions: filter,
      });

      const response = await fetch(`/api/fixtures/upcoming/?${params}`);
      
      if (!response.ok) {
        throw new Error("Failed to fetch fixtures");
      }

      const data: FixturesResponse = await response.json();
      setFixtures(data.fixtures);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load fixtures");
    } finally {
      setLoading(false);
    }
  };

  const formatKickoffTime = (kickoffTime: string): { date: string; time: string; dayOfWeek: string } => {
    const date = new Date(kickoffTime);
    const dayOfWeek = date.toLocaleDateString("en-GB", { weekday: "short" });
    const dateStr = date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    const timeStr = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    
    return { date: dateStr, time: timeStr, dayOfWeek };
  };

  const getTimeUntilKickoff = (kickoffTime: string): string => {
    const now = new Date();
    const kickoff = new Date(kickoffTime);
    const diffMs = kickoff.getTime() - now.getTime();
    
    if (diffMs < 0) return "Started";
    
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) return `In ${diffDays}d ${diffHours % 24}h`;
    if (diffHours > 0) return `In ${diffHours}h ${diffMins % 60}m`;
    return `In ${diffMins}m`;
  };

  const groupFixturesByDate = (fixtures: Fixture[]) => {
    const groups: Record<string, Fixture[]> = {};
    
    fixtures.forEach((fixture) => {
      const date = new Date(fixture.kickoff_time).toLocaleDateString("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      });
      
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(fixture);
    });
    
    return groups;
  };

  const groupedFixtures = groupFixturesByDate(fixtures);

  return (
    <div className="fixtures-page">
      <div className="fixtures-header">
        <h1>🎯 Upcoming Fixtures & Odds</h1>
        <p className="fixtures-subtitle">Live betting odds across all competitions</p>
      </div>

      {/* Filters */}
      <div className="fixtures-filters">
        <div className="competition-filters">
          <button
            className={`filter-btn ${filter === "ALL" ? "active" : ""}`}
            onClick={() => setFilter("ALL")}
          >
            All Competitions
          </button>
          <button
            className={`filter-btn ${filter === "PL" ? "active" : ""}`}
            onClick={() => setFilter("PL")}
          >
            ⚽ Premier League
          </button>
          <button
            className={`filter-btn ${filter === "UCL" ? "active" : ""}`}
            onClick={() => setFilter("UCL")}
          >
            ⭐ Champions League
          </button>
          <button
            className={`filter-btn ${filter === "UEL" ? "active" : ""}`}
            onClick={() => setFilter("UEL")}
          >
            🟠 Europa League
          </button>
          <button
            className={`filter-btn ${filter === "FAC" ? "active" : ""}`}
            onClick={() => setFilter("FAC")}
          >
            🏆 FA Cup
          </button>
        </div>

        <div className="days-filter">
          <label>Show next:</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={3}>3 days</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </div>
      </div>

      {/* Loading / Error States */}
      {loading && (
        <div className="fixtures-loading">
          <div className="spinner"></div>
          <p>Loading fixtures...</p>
        </div>
      )}

      {error && (
        <div className="fixtures-error">
          <p>❌ {error}</p>
          <button onClick={fetchFixtures}>Retry</button>
        </div>
      )}

      {/* Fixtures List */}
      {!loading && !error && fixtures.length === 0 && (
        <div className="no-fixtures">
          <p>No upcoming fixtures found for the selected criteria.</p>
        </div>
      )}

      {!loading && !error && fixtures.length > 0 && (
        <div className="fixtures-list">
          {Object.entries(groupedFixtures).map(([date, dateFixtures]) => (
            <div key={date} className="fixtures-date-group">
              <div className="date-header">
                <h2>{date}</h2>
              </div>

              {dateFixtures.map((fixture) => {
                const { time, dayOfWeek } = formatKickoffTime(fixture.kickoff_time);
                const competitionInfo = COMPETITION_BADGES[fixture.competition] || {
                  name: fixture.competition_name,
                  emoji: "⚽",
                  color: "#666",
                };
                const timeUntil = getTimeUntilKickoff(fixture.kickoff_time);

                return (
                  <div key={fixture.event_id} className="fixture-card">
                    <div className="fixture-header-info">
                      <span
                        className="competition-badge"
                        style={{ backgroundColor: competitionInfo.color }}
                      >
                        {competitionInfo.emoji} {fixture.competition}
                      </span>
                      <span className="kickoff-time">
                        {dayOfWeek} • {time}
                      </span>
                      <span className="countdown">{timeUntil}</span>
                    </div>

                    <div className="fixture-teams">
                      <div className="team-row home-team">
                        <span className="team-name">{fixture.home_team}</span>
                        {fixture.odds && fixture.odds.home && (
                          <div className="odds-display">
                            <span className="odds-value">{fixture.odds.home.toFixed(2)}</span>
                            {fixture.odds.home_movement && (
                              <span className={`odds-movement ${fixture.odds.home_movement === "↑" ? "up" : "down"}`}>
                                {fixture.odds.home_movement}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="vs-divider">
                        <span>vs</span>
                        {fixture.odds && fixture.odds.draw && (
                          <div className="draw-odds">
                            <span className="draw-label">Draw</span>
                            <span className="odds-value">{fixture.odds.draw.toFixed(2)}</span>
                            {fixture.odds.draw_movement && (
                              <span className={`odds-movement ${fixture.odds.draw_movement === "↑" ? "up" : "down"}`}>
                                {fixture.odds.draw_movement}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="team-row away-team">
                        <span className="team-name">{fixture.away_team}</span>
                        {fixture.odds && fixture.odds.away && (
                          <div className="odds-display">
                            <span className="odds-value">{fixture.odds.away.toFixed(2)}</span>
                            {fixture.odds.away_movement && (
                              <span className={`odds-movement ${fixture.odds.away_movement === "↑" ? "up" : "down"}`}>
                                {fixture.odds.away_movement}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {!fixture.odds && (
                      <div className="no-odds-message">
                        <span>Odds not available yet</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
