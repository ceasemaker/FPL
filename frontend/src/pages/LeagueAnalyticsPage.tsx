import { useEffect, useMemo, useState } from "react";
import "./LeagueAnalyticsPage.css";

interface ClassicLeague {
  id: number;
  name: string;
  entry_rank: number | null;
}

interface ManagerSummaryResponse {
  leagues: {
    classic: ClassicLeague[];
  };
}

interface LeagueEntry {
  entry: number;
  entry_name: string;
  player_name: string;
  rank: number;
  total_points: number;
  live_points: number;
  live_rank: number;
}

interface LeagueLiveResponse {
  league_id: number;
  league_name: string;
  current_gameweek: number;
  entries: LeagueEntry[];
}

const MANAGER_ID_KEY = "league_manager_id";
const LEAGUE_ID_KEY = "league_selected_id";

export function LeagueAnalyticsPage() {
  const [managerId, setManagerId] = useState("");
  const [activeManagerId, setActiveManagerId] = useState<string | null>(null);
  const [leagues, setLeagues] = useState<ClassicLeague[]>([]);
  const [selectedLeagueId, setSelectedLeagueId] = useState<number | null>(null);
  const [liveData, setLiveData] = useState<LeagueLiveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedManager = localStorage.getItem(MANAGER_ID_KEY);
    const storedLeague = localStorage.getItem(LEAGUE_ID_KEY);
    if (storedManager) {
      setManagerId(storedManager);
      setActiveManagerId(storedManager);
    }
    if (storedLeague) {
      const parsed = Number(storedLeague);
      if (!Number.isNaN(parsed)) setSelectedLeagueId(parsed);
    }
  }, []);

  useEffect(() => {
    if (activeManagerId) {
      localStorage.setItem(MANAGER_ID_KEY, activeManagerId);
    }
  }, [activeManagerId]);

  useEffect(() => {
    if (selectedLeagueId) {
      localStorage.setItem(LEAGUE_ID_KEY, String(selectedLeagueId));
    }
  }, [selectedLeagueId]);

  const loadLeagues = async () => {
    if (!managerId.trim()) {
      setError("Enter a manager ID first.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/fpl/entry/${managerId.trim()}/`);
      if (!response.ok) throw new Error("Failed to load manager data.");
      const payload = (await response.json()) as ManagerSummaryResponse;
      const classic = payload.leagues?.classic || [];
      setLeagues(classic);
      setActiveManagerId(managerId.trim());
      if (!selectedLeagueId && classic.length) {
        setSelectedLeagueId(classic[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load manager data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadLive = async () => {
      if (!selectedLeagueId) return;
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/fpl/league/${selectedLeagueId}/live/?limit=30`);
        if (!response.ok) throw new Error("Failed to load league live data.");
        const payload = (await response.json()) as LeagueLiveResponse;
        setLiveData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load league live data.");
      } finally {
        setLoading(false);
      }
    };

    loadLive();
  }, [selectedLeagueId]);

  const leagueOptions = useMemo(() => {
    return [...leagues].sort((a, b) => a.name.localeCompare(b.name));
  }, [leagues]);

  return (
    <div className="page">
      <section className="glow-card league-hero">
        <div className="glow-card-content">
          <div className="section-title">🏟️ Mini-League Analytics</div>
          <p className="section-subtitle">
            Track league standings with live gameweek points. Your manager ID is saved locally so you do not need to
            re-enter it.
          </p>

          <div className="league-controls">
            <label>
              Manager ID
              <input
                value={managerId}
                onChange={(event) => setManagerId(event.target.value)}
                placeholder="e.g. 123456"
              />
            </label>
            <button onClick={loadLeagues} disabled={loading}>
              {loading ? "Loading..." : "Load Leagues"}
            </button>
          </div>

          {leagueOptions.length > 0 && (
            <div className="league-select">
              <label>
                League
                <select
                  value={selectedLeagueId || undefined}
                  onChange={(event) => setSelectedLeagueId(Number(event.target.value))}
                >
                  {leagueOptions.map((league) => (
                    <option key={league.id} value={league.id}>
                      {league.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {error && <div className="league-error">{error}</div>}
        </div>
      </section>

      {liveData && (
        <section className="glow-card league-board">
          <div className="glow-card-content">
            <div className="league-header">
              <div>
                <div className="section-title">{liveData.league_name}</div>
                <p className="section-subtitle">Live GW {liveData.current_gameweek} snapshot (top 30).</p>
              </div>
            </div>

            <div className="league-table">
              <div className="league-row league-head">
                <div>Rank</div>
                <div>Live</div>
                <div>Team</div>
                <div>Manager</div>
                <div>Total</div>
                <div>Live Pts</div>
              </div>
              {liveData.entries.map((entry) => (
                <div key={entry.entry} className="league-row">
                  <div>{entry.rank}</div>
                  <div>{entry.live_rank}</div>
                  <div>{entry.entry_name}</div>
                  <div>{entry.player_name}</div>
                  <div>{entry.total_points}</div>
                  <div className="live-points">{entry.live_points}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
