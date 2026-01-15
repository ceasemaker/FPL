import { useEffect, useMemo, useState } from "react";
import "./FixturesTicker.css";

interface TickerFixture {
  event: number;
  opponent: string | null;
  location: "H" | "A";
  difficulty: number | null;
}

interface TickerTeamRow {
  team_id: number;
  team_name: string;
  team_short_name: string;
  fixtures: TickerFixture[];
  avg_difficulty: number | null;
}

interface TickerResponse {
  current_gameweek: number;
  start_gameweek: number;
  end_gameweek: number;
  horizon: number;
  teams: TickerTeamRow[];
}

export function FixturesTicker() {
  const [data, setData] = useState<TickerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"name" | "avg">("avg");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/fixtures/ticker/?horizon=5");
        if (!response.ok) throw new Error("Failed to load fixture ticker.");
        const payload = (await response.json()) as TickerResponse;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load fixture ticker.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const events = useMemo(() => {
    if (!data) return [];
    return Array.from({ length: data.horizon }, (_, idx) => data.start_gameweek + idx);
  }, [data]);

  const sortedTeams = useMemo(() => {
    if (!data) return [];
    const rows = [...data.teams];
    rows.sort((a, b) => {
      if (sortBy === "name") {
        const nameA = a.team_short_name || "";
        const nameB = b.team_short_name || "";
        return sortDir === "asc" ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
      }
      const avgA = a.avg_difficulty ?? 999;
      const avgB = b.avg_difficulty ?? 999;
      return sortDir === "asc" ? avgA - avgB : avgB - avgA;
    });
    return rows;
  }, [data, sortBy, sortDir]);

  return (
    <section className="glow-card fixtures-ticker">
      <div className="glow-card-content">
        <div className="section-title">Fixture Ticker</div>
        <p className="section-subtitle">Next 5 gameweeks per team with difficulty shading.</p>
        <div className="fixtures-ticker-controls">
          <div className="fixtures-ticker-legend">
            <span>FDR:</span>
            <span className="fdr-chip fdr-1">1</span>
            <span className="fdr-chip fdr-2">2</span>
            <span className="fdr-chip fdr-3">3</span>
            <span className="fdr-chip fdr-4">4</span>
            <span className="fdr-chip fdr-5">5</span>
          </div>
          <div className="fixtures-ticker-sort">
            <label>
              Sort
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value as "name" | "avg")}>
                <option value="avg">Avg FDR</option>
                <option value="name">Team</option>
              </select>
            </label>
            <button onClick={() => setSortDir(sortDir === "asc" ? "desc" : "asc")}>
              {sortDir === "asc" ? "↑" : "↓"}
            </button>
          </div>
        </div>
        {error && <div className="fixtures-ticker-error">{error}</div>}
        {loading && <div className="fixtures-ticker-loading">Loading ticker...</div>}
        {!loading && data && (
          <div className="fixtures-ticker-table">
            <div className="fixtures-ticker-row fixtures-ticker-head">
              <div>Team</div>
              {events.map((eventId) => (
                <div key={eventId}>GW {eventId}</div>
              ))}
              <div>Avg</div>
            </div>
            {sortedTeams.map((team) => (
              <div key={team.team_id} className="fixtures-ticker-row">
                <div className="fixtures-ticker-team">{team.team_short_name}</div>
                {events.map((eventId) => {
                  const fixture = team.fixtures.find((item) => item.event === eventId);
                  if (!fixture) {
                    return <div key={eventId} className="fixtures-ticker-cell empty">—</div>;
                  }
                  const difficulty = fixture.difficulty ?? 0;
                  return (
                    <div
                      key={eventId}
                      className={`fixtures-ticker-cell fdr-${difficulty || 0}`}
                      title={`${fixture.location}${fixture.opponent ? ` vs ${fixture.opponent}` : ""}`}
                    >
                      <span>{fixture.opponent}</span>
                      <small>{fixture.location}</small>
                    </div>
                  );
                })}
                <div className="fixtures-ticker-cell avg">{team.avg_difficulty?.toFixed(2) || "—"}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
