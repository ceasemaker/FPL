import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PlayerGameweekModal from "./PlayerGameweekModal";

interface Player {
  element: number;
  position: number;
  multiplier: number;
  is_captain: boolean;
  is_vice_captain: boolean;
}

interface Pick {
  picks: Player[];
  active_chip: string | null;
  automatic_subs: any[];
  entry_history: {
    event: number;
    points: number;
    total_points: number;
    rank: number;
    rank_sort: number;
    overall_rank: number;
    bank: number;
    value: number;
    event_transfers: number;
    event_transfers_cost: number;
    points_on_bench: number;
  };
}

interface PlayerData {
  id: number;
  web_name: string;
  team: number;
  team_code: number;
  element_type: number;
  now_cost: number;
  photo: string;
}

interface ManagerGameweekProps {
  managerId: string;
  selectedGameweek: number | null;
  onGameweekChange: (gw: number) => void;
}

const PLAYER_IMAGE_BASE = "https://resources.premierleague.com/premierleague25/photos/players/110x140/";
const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

const ManagerGameweek: React.FC<ManagerGameweekProps> = ({
  managerId,
  selectedGameweek,
  onGameweekChange,
}) => {
  const [picks, setPicks] = useState<Pick | null>(null);
  const [allPlayers, setAllPlayers] = useState<Map<number, PlayerData>>(new Map());
  const [playerPoints, setPlayerPoints] = useState<Map<number, number>>(new Map());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentGameweek, setCurrentGameweek] = useState<number>(1);
  // FPL publishes a manager's picks only once a gameweek's deadline has passed,
  // so the selector stops at the latest started gameweek.
  const [latestStarted, setLatestStarted] = useState<number | null>(null);
  const [nextDeadline, setNextDeadline] = useState<{ id: number; time: string } | null>(null);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [finishedGameweeks, setFinishedGameweeks] = useState<Set<number>>(new Set());
  const [selectedPlayer, setSelectedPlayer] = useState<{ id: number; name: string; team: number; position: number } | null>(null);

  // Fetch bootstrap-static data for player info
  useEffect(() => {
    fetch("/api/fpl/bootstrap-static/")
      .then((res) => res.json())
      .then((data) => {
        const playerMap = new Map<number, PlayerData>();
        data.elements.forEach((player: PlayerData) => {
          playerMap.set(player.id, player);
        });
        setAllPlayers(playerMap);
        const now = Date.now();
        const started = data.events.filter((e: any) => e.deadline_time && new Date(e.deadline_time).getTime() <= now).map((e: any) => e.id as number);
        const latest = started.length ? Math.max(...started) : 1;
        const upcoming = data.events.find((e: any) => e.id === latest + 1 && new Date(e.deadline_time).getTime() > now);
        setCurrentGameweek(data.events.find((e: any) => e.is_current)?.id || latest);
        setLatestStarted(latest);
        setNextDeadline(upcoming ? { id: upcoming.id, time: upcoming.deadline_time } : null);
        setFinishedGameweeks(new Set(data.events.filter((event: any) => event.finished).map((event: any) => event.id)));
        if (!selectedGameweek || selectedGameweek > latest) {
          onGameweekChange(latest);
        }
      })
      .catch((err) => console.error("Failed to load player data:", err));
  }, []);

  // Fetch picks for selected gameweek
  useEffect(() => {
    if (!managerId || !selectedGameweek || latestStarted === null) return;
    if (selectedGameweek > latestStarted) return;  // not started: FPL has no picks yet

    setLoading(true);
    setError(null);

    fetch(`/api/fpl/entry/${managerId}/event/${selectedGameweek}/picks/`)
      .then((res) => {
        if (res.status === 404) {
          throw new Error(`This manager has no team for gameweek ${selectedGameweek}. They may have joined the game after it.`);
        }
        if (!res.ok) {
          throw new Error("FPL didn't answer just now. Try again in a minute.");
        }
        return res.json();
      })
      .then((data: Pick) => {
        setPicks(data);
        setLoadedAt(new Date());
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [managerId, selectedGameweek, latestStarted]);

  // Fetch live gameweek data for player points
  useEffect(() => {
    if (!selectedGameweek) return;

    fetch(`/api/fpl/event/${selectedGameweek}/live/`)
      .then((res) => res.json())
      .then((data) => {
        const pointsMap = new Map<number, number>();
        data.elements.forEach((element: any) => {
          pointsMap.set(element.id, element.stats.total_points);
        });
        setPlayerPoints(pointsMap);
      })
      .catch((err) => console.error("Failed to load live data:", err));
  }, [selectedGameweek]);

  const getPositionLabel = (elementType: number): string => {
    switch (elementType) {
      case 1:
        return "GKP";
      case 2:
        return "DEF";
      case 3:
        return "MID";
      case 4:
        return "FWD";
      default:
        return "—";
    }
  };

  const getPlayerImage = (photo: string | undefined): string => {
    if (!photo) return "";
    const clean = photo.split(".")[0];
    return `${PLAYER_IMAGE_BASE}${clean}.png`;
  };

  const renderPlayerCard = (pick: Player, playerData: PlayerData | undefined) => {
    if (!playerData) return null;

    const isCaptain = pick.is_captain;
    const isViceCaptain = pick.is_vice_captain;
    const multiplier = pick.multiplier;
    const basePoints = playerPoints.get(pick.element) || 0;
    const totalPoints = basePoints * multiplier;

    return (
      <div
        key={pick.element}
        className={`gameweek-player-card ${multiplier === 0 ? "benched" : ""}`}
        onClick={() => setSelectedPlayer({ 
          id: pick.element, 
          name: playerData.web_name,
          team: playerData.team_code,
          position: playerData.element_type
        })}
        style={{ cursor: 'pointer' }}
      >
        {isCaptain && <div className="captain-badge">C</div>}
        {isViceCaptain && <div className="vice-captain-badge">V</div>}
        {multiplier === 3 && <div className="triple-captain-badge">3x</div>}
        
        <div className="player-card-image">
          <img
            src={getPlayerImage(playerData.photo) || `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${playerData.team_code}-220.webp`}
            alt={playerData.web_name}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.src = `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${playerData.team_code}-220.webp`;
            }}
          />
        </div>
        
        <div className="player-card-info">
          <div className="player-card-name">{playerData.web_name}</div>
          <div className="player-card-meta">
            <span className="position-mini">{getPositionLabel(playerData.element_type)}</span>
            <img
              src={`${TEAM_BADGE_BASE}${playerData.team_code}.svg`}
              alt=""
              className="team-badge-mini"
            />
          </div>
          {basePoints > 0 && (
            <div className="player-card-points">
              {multiplier > 1 ? (
                <>
                  <span className="base-points">{basePoints}</span>
                  <span className="multiplier-text"> × {multiplier} = </span>
                  <span className="total-points">{totalPoints}</span>
                </>
              ) : (
                <span className="total-points">{totalPoints} pts</span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  const lastGw = latestStarted ?? currentGameweek;
  const selectedIsFinished = selectedGameweek !== null && finishedGameweeks.has(selectedGameweek);
  const header = (
    <>
      {/* Gameweek Selector: always shown, so a gameweek that fails never strands you */}
      <div className="gameweek-selector-header">
        <h2 className="gameweek-title">Gameweek Team</h2>
        <div className="gameweek-selector">
          <button
            className="gw-nav-button"
            aria-label="Previous gameweek"
            onClick={() => selectedGameweek && selectedGameweek > 1 && onGameweekChange(selectedGameweek - 1)}
            disabled={!selectedGameweek || selectedGameweek <= 1}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M8.5 3 4.5 7l4 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
          <select
            className="gw-select"
            aria-label="Gameweek"
            value={selectedGameweek || lastGw}
            onChange={(e) => onGameweekChange(Number(e.target.value))}
          >
            {Array.from({ length: lastGw }, (_, i) => i + 1).map((gw) => (
              <option key={gw} value={gw}>
                Gameweek {gw}
              </option>
            ))}
          </select>
          <button
            className="gw-nav-button"
            aria-label="Next gameweek"
            onClick={() => selectedGameweek && selectedGameweek < lastGw && onGameweekChange(selectedGameweek + 1)}
            disabled={!selectedGameweek || selectedGameweek >= lastGw}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M5.5 3l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </div>
      </div>
      {nextDeadline && selectedGameweek === lastGw && (
        <p className="gw-next-note">
          Gameweek {nextDeadline.id} picks appear here after its deadline,{" "}
          {new Date(nextDeadline.time).toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.{" "}
          <Link to={`/planner?manager=${managerId}`}>Plan it in the transfer planner</Link>
        </p>
      )}
    </>
  );

  if (loading) {
    return (
      <div className="manager-gameweek-container">
        {header}
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading team...</p>
        </div>
      </div>
    );
  }

  if (error || !picks) {
    return (
      <div className="manager-gameweek-container">
        {header}
        <div className="error-state">
          <div className="error-icon">⚠️</div>
          <h3>This team couldn't be loaded</h3>
          <p>{error || "Failed to fetch gameweek team"}</p>
        </div>
      </div>
    );
  }

  const starting11 = picks.picks.filter((p) => p.position <= 11);
  const bench = picks.picks.filter((p) => p.position > 11);

  // Group starting 11 by position
  const gkp = starting11.filter((p) => allPlayers.get(p.element)?.element_type === 1);
  const def = starting11.filter((p) => allPlayers.get(p.element)?.element_type === 2);
  const mid = starting11.filter((p) => allPlayers.get(p.element)?.element_type === 3);
  const fwd = starting11.filter((p) => allPlayers.get(p.element)?.element_type === 4);

  return (
    <div className="manager-gameweek-container">
      {header}

      <div className="manager-freshness" role="status">
        <strong>{selectedIsFinished ? "Completed gameweek" : "Current gameweek"}</strong>
        <span>Official FPL picks for GW{selectedGameweek}</span>
        <span>{selectedIsFinished ? "Final recorded squad and points" : "Live points may change until matches finish"}</span>
        <span>Loaded {loadedAt?.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) ?? "—"}</span>
      </div>

      {/* Gameweek Stats */}
      <div className="gameweek-stats-bar">
        <div className="gw-stat">
          <span className="gw-stat-label">Points:</span>
          <span className="gw-stat-value">{picks.entry_history.points}</span>
        </div>
        <div className="gw-stat">
          <span className="gw-stat-label">Rank:</span>
          <span className="gw-stat-value">{picks.entry_history.rank?.toLocaleString() || "—"}</span>
        </div>
        <div className="gw-stat">
          <span className="gw-stat-label">Transfers:</span>
          <span className="gw-stat-value">{picks.entry_history.event_transfers}</span>
        </div>
        <div className="gw-stat">
          <span className="gw-stat-label">Transfer Cost:</span>
          <span className="gw-stat-value">{picks.entry_history.event_transfers_cost > 0 ? `-${picks.entry_history.event_transfers_cost}` : "0"}</span>
        </div>
        <div className="gw-stat">
          <span className="gw-stat-label">Bench Points:</span>
          <span className="gw-stat-value">{picks.entry_history.points_on_bench}</span>
        </div>
        {picks.active_chip && (
          <div className="gw-stat chip">
            <span className="gw-stat-label">Chip:</span>
            <span className="gw-stat-value chip-active">{picks.active_chip}</span>
          </div>
        )}
      </div>

      {/* Formation Display */}
      <div className="formation-pitch">
        <div className="formation-row">
          {gkp.map((p) => renderPlayerCard(p, allPlayers.get(p.element)))}
        </div>
        <div className="formation-row">
          {def.map((p) => renderPlayerCard(p, allPlayers.get(p.element)))}
        </div>
        <div className="formation-row">
          {mid.map((p) => renderPlayerCard(p, allPlayers.get(p.element)))}
        </div>
        <div className="formation-row">
          {fwd.map((p) => renderPlayerCard(p, allPlayers.get(p.element)))}
        </div>
      </div>

      {/* Bench */}
      <div className="bench-section">
        <h3 className="bench-title">Bench</h3>
        <div className="bench-players">
          {bench.map((p) => renderPlayerCard(p, allPlayers.get(p.element)))}
        </div>
      </div>

      {/* Player Stats Modal */}
      {selectedPlayer && selectedGameweek && (
        <PlayerGameweekModal
          playerId={selectedPlayer.id}
          playerName={selectedPlayer.name}
          playerTeam={selectedPlayer.team}
          playerPosition={selectedPlayer.position}
          gameweek={selectedGameweek}
          onClose={() => setSelectedPlayer(null)}
        />
      )}
    </div>
  );
};

export default ManagerGameweek;
