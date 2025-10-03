import { useEffect, useState } from "react";

interface GameweekHistory {
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
}

interface ChipPlay {
  chip_name: string;
  event: number;
}

interface ManagerHistoryData {
  current: GameweekHistory[];
  past: any[];
  chips: ChipPlay[];
}

interface ManagerHistoryProps {
  managerId: string;
}

const ManagerHistory: React.FC<ManagerHistoryProps> = ({ managerId }) => {
  const [history, setHistory] = useState<ManagerHistoryData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!managerId) return;

    setLoading(true);
    setError(null);

    fetch(`/api/fpl/entry/${managerId}/history/`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load history (${res.status})`);
        }
        return res.json();
      })
      .then((data: ManagerHistoryData) => {
        setHistory(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [managerId]);

  if (loading) {
    return (
      <div className="manager-history-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading history...</p>
        </div>
      </div>
    );
  }

  if (error || !history) {
    return (
      <div className="manager-history-container">
        <div className="error-state">
          <div className="error-icon">⚠️</div>
          <h3>Unable to Load History</h3>
          <p>{error || "Failed to fetch manager history"}</p>
        </div>
      </div>
    );
  }

  const getChipForGameweek = (gw: number): string | null => {
    const chip = history.chips.find((c) => c.event === gw);
    return chip ? chip.chip_name : null;
  };

  const getRankChange = (index: number): number | null => {
    if (index === 0) return null;
    const current = history.current[index];
    const previous = history.current[index - 1];
    return previous.overall_rank - current.overall_rank;
  };

  const formatRankChange = (change: number | null): JSX.Element => {
    if (change === null) return <span className="rank-change">—</span>;
    if (change > 0) {
      return <span className="rank-change positive">↑ {change.toLocaleString()}</span>;
    } else if (change < 0) {
      return <span className="rank-change negative">↓ {Math.abs(change).toLocaleString()}</span>;
    }
    return <span className="rank-change neutral">—</span>;
  };

  // Calculate summary stats
  const totalPoints = history.current[history.current.length - 1]?.total_points || 0;
  const bestGameweek = history.current.reduce((max, gw) => (gw.points > max.points ? gw : max), history.current[0]);
  const worstGameweek = history.current.reduce((min, gw) => (gw.points < min.points ? gw : min), history.current[0]);
  const avgPoints = history.current.length > 0 ? (totalPoints / history.current.length).toFixed(1) : "0";
  const totalTransferCost = history.current.reduce((sum, gw) => sum + gw.event_transfers_cost, 0);

  return (
    <div className="manager-history-container">
      <div className="history-header">
        <h2 className="history-title">Season History</h2>
        <div className="history-summary-stats">
          <div className="summary-stat">
            <span className="summary-label">Avg Points/GW:</span>
            <span className="summary-value">{avgPoints}</span>
          </div>
          <div className="summary-stat">
            <span className="summary-label">Best GW:</span>
            <span className="summary-value">
              GW{bestGameweek?.event} ({bestGameweek?.points} pts)
            </span>
          </div>
          <div className="summary-stat">
            <span className="summary-label">Worst GW:</span>
            <span className="summary-value">
              GW{worstGameweek?.event} ({worstGameweek?.points} pts)
            </span>
          </div>
          <div className="summary-stat">
            <span className="summary-label">Transfer Cost:</span>
            <span className="summary-value">-{totalTransferCost} pts</span>
          </div>
        </div>
      </div>

      <div className="history-table-wrapper">
        <table className="history-table">
          <thead>
            <tr>
              <th>GW</th>
              <th>Points</th>
              <th>Total</th>
              <th>Overall Rank</th>
              <th>Rank Change</th>
              <th>Transfers</th>
              <th>Transfer Cost</th>
              <th>Bench Pts</th>
              <th>Chip</th>
            </tr>
          </thead>
          <tbody>
            {history.current.map((gw, index) => {
              const chip = getChipForGameweek(gw.event);
              const rankChange = getRankChange(index);
              return (
                <tr key={gw.event} className={chip ? "chip-used" : ""}>
                  <td className="gw-number">
                    <strong>GW{gw.event}</strong>
                  </td>
                  <td className="points-cell">
                    <strong>{gw.points}</strong>
                  </td>
                  <td>{gw.total_points.toLocaleString()}</td>
                  <td>{gw.overall_rank.toLocaleString()}</td>
                  <td>{formatRankChange(rankChange)}</td>
                  <td>{gw.event_transfers}</td>
                  <td className={gw.event_transfers_cost > 0 ? "transfer-cost" : ""}>
                    {gw.event_transfers_cost > 0 ? `-${gw.event_transfers_cost}` : "—"}
                  </td>
                  <td>{gw.points_on_bench}</td>
                  <td>
                    {chip && (
                      <span className="chip-badge">{chip}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {history.past.length > 0 && (
        <div className="past-seasons">
          <h3 className="past-seasons-title">Previous Seasons</h3>
          <table className="past-seasons-table">
            <thead>
              <tr>
                <th>Season</th>
                <th>Total Points</th>
                <th>Overall Rank</th>
              </tr>
            </thead>
            <tbody>
              {history.past.map((season) => (
                <tr key={season.season_name}>
                  <td className="season-name-cell">{season.season_name}</td>
                  <td>{season.total_points.toLocaleString()}</td>
                  <td>{season.rank.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ManagerHistory;
