import { useEffect, useMemo, useState } from "react";
import "./FixtureTickerPage.css";

interface FdrFixture {
  event: number;
  opponent: string | null;
  location: "H" | "A";
  difficulty: number | null;
}

interface TeamTickerRow {
  team_id: number;
  team_name: string;
  team_short_name: string;
  fixtures: FdrFixture[];
  avg_difficulty: number | null;
}

interface TickerResponse {
  current_gameweek: number;
  start_gameweek: number;
  end_gameweek: number;
  horizon: number;
  teams: TeamTickerRow[];
}

export function FixtureTickerPage() {
  const [horizon, setHorizon] = useState(5);
  const [data, setData] = useState<TickerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/fixtures/ticker/?horizon=${horizon}`);
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
  }, [horizon]);

  const events = useMemo(() => {
    if (!data) return [];
    return Array.from({ length: data.horizon }, (_, idx) => data.start_gameweek + idx);
  }, [data]);

  return (
    <div className="page">
      <section className="glow-card ticker-hero">
        <div className="glow-card-content">
          <div className="section-title">🗓️ Fixture Difficulty Ticker</div>
          <p className="section-subtitle">
            Scan upcoming runs across the league. Lower difficulty (1) is easier; higher (5) is tougher.
          </p>
          <div className="ticker-controls">
            <label>
              Horizon (GW)
              <input
                type="number"
                min="3"
                max="10"
                value={horizon}
                onChange={(event) => setHorizon(Number(event.target.value))}
              />
            </label>
          </div>
          {error && <div className="ticker-error">{error}</div>}
        </div>
      </section>

      <section className="glow-card ticker-board">
        <div className="glow-card-content">
          {loading && <div className="ticker-loading">Loading fixture ticker...</div>}
          {!loading && data && (
            <div className="ticker-table">
              <div className="ticker-row ticker-head">
                <div>Team</div>
                {events.map((eventId) => (
                  <div key={eventId}>GW {eventId}</div>
                ))}
                <div>Avg</div>
              </div>
              {data.teams.map((team) => (
                <div key={team.team_id} className="ticker-row">
                  <div className="ticker-team">{team.team_short_name}</div>
                  {events.map((eventId) => {
                    const fixture = team.fixtures.find((item) => item.event === eventId);
                    if (!fixture) {
                      return <div key={eventId} className="ticker-cell empty">—</div>;
                    }
                    const difficulty = fixture.difficulty ?? 0;
                    return (
                      <div
                        key={eventId}
                        className={`ticker-cell fdr-${difficulty || 0}`}
                        title={`${fixture.location}${fixture.opponent ? ` vs ${fixture.opponent}` : ""}`}
                      >
                        <span>{fixture.opponent}</span>
                        <small>{fixture.location}</small>
                      </div>
                    );
                  })}
                  <div className="ticker-cell avg">{team.avg_difficulty?.toFixed(2) || "—"}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
