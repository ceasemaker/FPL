import { useEffect, useState } from "react";
import { clsx } from "clsx";

interface Fixture {
  id: number;
  event: number;
  kickoff_time: string | null;
  team_h: string | null;
  team_h_short: string | null;
  team_h_id: number | null;
  team_h_code: number | null;
  team_a: string | null;
  team_a_short: string | null;
  team_a_id: number | null;
  team_a_code: number | null;
  team_h_difficulty: number | null;
  team_a_difficulty: number | null;
  team_h_score: number | null;
  team_a_score: number | null;
  finished: boolean;
  started: boolean;
}

interface FixturesResponse {
  gameweek: number;
  fixtures: Fixture[];
  available_gameweeks: number[];
}

const API_URL = import.meta.env.VITE_API_FIXTURES_URL ?? "/api/fixtures/";
const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

function getTeamBadgeUrl(teamCode: number | null): string | null {
  if (!teamCode) return null;
  return `${TEAM_BADGE_BASE}${teamCode}.svg`;
}

function getDifficultyColor(difficulty: number | null): string {
  if (difficulty === null) return "#666";
  // Green (1) → Yellow (3) → Red (5)
  if (difficulty === 1) return "#22c55e"; // green-500
  if (difficulty === 2) return "#84cc16"; // lime-500
  if (difficulty === 3) return "#eab308"; // yellow-500
  if (difficulty === 4) return "#f97316"; // orange-500
  if (difficulty === 5) return "#ef4444"; // red-500
  return "#666";
}

export function FixturesTable() {
  const [data, setData] = useState<FixturesResponse | null>(null);
  const [currentGW, setCurrentGW] = useState<number | null>(null);
  const [liveGW, setLiveGW] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFixtures = (gw?: number) => {
    setIsLoading(true);
    const url = gw ? `${API_URL}?gameweek=${gw}` : API_URL;
    
    fetch(url, {
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const payload: FixturesResponse = await response.json();
        setData(payload);
        setCurrentGW(payload.gameweek);
        if (liveGW === null) {
          setLiveGW(payload.gameweek);
        }
        setError(null);
      })
      .catch((err) => {
        console.error("Failed to load fixtures", err);
        setError(err.message ?? "Unexpected error");
        setData(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchFixtures();
  }, []);

  const handlePrev = () => {
    if (!data || !currentGW) return;
    const idx = data.available_gameweeks.indexOf(currentGW);
    if (idx > 0) {
      fetchFixtures(data.available_gameweeks[idx - 1]);
    }
  };

  const handleNext = () => {
    if (!data || !currentGW) return;
    const idx = data.available_gameweeks.indexOf(currentGW);
    if (idx >= 0 && idx < data.available_gameweeks.length - 1) {
      fetchFixtures(data.available_gameweeks[idx + 1]);
    }
  };

  const canGoPrev = data && currentGW !== null
    ? data.available_gameweeks.indexOf(currentGW) > 0
    : false;
  const canGoNext = data && currentGW !== null
    ? data.available_gameweeks.indexOf(currentGW) < data.available_gameweeks.length - 1
    : false;

  if (error) {
    return (
      <section className="fixtures-table">
        <h2>Fixtures</h2>
        <p className="error-message">Error: {error}</p>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="fixtures-table">
        <h2>Fixtures</h2>
        <p className="loading-message">Loading fixtures...</p>
      </section>
    );
  }

  if (!data || data.fixtures.length === 0) {
    return (
      <section className="fixtures-table">
        <h2>Fixtures</h2>
        <p>No fixtures available for this gameweek.</p>
      </section>
    );
  }

  return (
    <section className="fixtures-table">
      <div className="fixtures-header">
        <h2>
          Fixtures: Gameweek {currentGW}
          {liveGW !== null && currentGW === liveGW && (
            <span className="live-badge">LIVE</span>
          )}
        </h2>
        <div className="gameweek-controls">
          <button
            className="gw-btn"
            onClick={handlePrev}
            disabled={!canGoPrev}
          >
            ← Previous
          </button>
          <button
            className="gw-btn"
            onClick={handleNext}
            disabled={!canGoNext}
          >
            Next →
          </button>
        </div>
      </div>

      <div className="table-container">
        <table className="fixtures-data-table">
          <thead>
            <tr>
              <th className="kickoff-col">Kickoff</th>
              <th className="fdr-col">FDR</th>
              <th className="team-col">Home</th>
              <th className="score-col">Score</th>
              <th className="team-col">Away</th>
              <th className="fdr-col">FDR</th>
            </tr>
          </thead>
          <tbody>
            {data.fixtures.map((fixture) => {
              const kickoffDate = fixture.kickoff_time
                ? new Date(fixture.kickoff_time).toLocaleString("en-GB", {
                    weekday: "short",
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "TBD";

              return (
                <tr
                  key={fixture.id}
                  className={clsx({
                    finished: fixture.finished,
                    started: fixture.started && !fixture.finished,
                  })}
                >
                  <td className="kickoff-time">{kickoffDate}</td>
                  <td className="fdr-cell">
                    <span
                      className="difficulty-badge"
                      style={{ backgroundColor: getDifficultyColor(fixture.team_h_difficulty) }}
                    >
                      {fixture.team_h_difficulty ?? "—"}
                    </span>
                  </td>
                  <td className="team-name home-team">
                    <div className="team-cell">
                      {fixture.team_h_code && (
                        <img 
                          src={getTeamBadgeUrl(fixture.team_h_code)!} 
                          alt={fixture.team_h_short || ""} 
                          className="team-badge"
                        />
                      )}
                      <span>{fixture.team_h_short || fixture.team_h || "TBD"}</span>
                    </div>
                  </td>
                  <td className="score-cell">
                    {fixture.finished || fixture.started ? (
                      <span className="score">
                        {fixture.team_h_score ?? 0} - {fixture.team_a_score ?? 0}
                      </span>
                    ) : (
                      <span className="score-placeholder">-</span>
                    )}
                  </td>
                  <td className="team-name away-team">
                    <div className="team-cell">
                      {fixture.team_a_code && (
                        <img 
                          src={getTeamBadgeUrl(fixture.team_a_code)!} 
                          alt={fixture.team_a_short || ""} 
                          className="team-badge"
                        />
                      )}
                      <span>{fixture.team_a_short || fixture.team_a || "TBD"}</span>
                    </div>
                  </td>
                  <td className="fdr-cell">
                    <span
                      className="difficulty-badge"
                      style={{ backgroundColor: getDifficultyColor(fixture.team_a_difficulty) }}
                    >
                      {fixture.team_a_difficulty ?? "—"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
