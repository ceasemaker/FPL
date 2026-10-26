import { useState } from "react";
import { Player } from "../hooks/usePlayers";
import "./PlayersTable.css";
import { availability, SET_PIECE_LABEL, splitNews } from "./availability";
import { PriceChangeBadge } from "./priceChange/PriceChange";
import { WatchStar } from "./WatchStar";

interface PlayersTableProps {
    players: Player[];
    onPlayerClick: (player: Player) => void;
    selectedPlayers: Set<number>;
    compareMode: boolean;
    onToggleSelection: (playerId: number) => void;
    defaultSort?: SortConfig;
}

export type SortField =
    | "web_name"
    | "team"
    | "element_type"
    | "now_cost"
    | "total_points"
    | "form"
    | "avg_fdr"
    | "expected_goals"
    | "goals_scored"
    | "assists"
    | "expected_assists"
    | "clean_sheets"
    | "expected_clean_sheets"
    | "selected_by_percent"
    | "best_value";

export interface SortConfig {
    field: SortField;
    direction: "asc" | "desc";
}

function getPositionLabel(elementType: number): string {
    switch (elementType) {
        case 1: return "GKP";
        case 2: return "DEF";
        case 3: return "MID";
        case 4: return "FWD";
        default: return "-";
    }
}

function calculateBestValue(player: Player): number {
    if (player.now_cost === 0) return 0;
    // Points per 90 (last 3 GWs) / Cost
    // Cost is in 0.1m units (e.g. 100 = 10.0m)
    // We want to normalize this.
    // Let's just do (Points Last 3) / (Cost / 10)
    // But wait, user said "Points per 90 (last 3 GWs) ÷ Cost"
    // Points per 90 = (Points / Minutes) * 90

    if (player.minutes_last_3 === 0) return 0;

    const pointsPer90 = (player.points_last_3 / player.minutes_last_3) * 90;
    const costInMillions = player.now_cost / 10;

    return pointsPer90 / costInMillions;
}

export function PlayersTable({
    players,
    onPlayerClick,
    selectedPlayers,
    compareMode,
    onToggleSelection,
    defaultSort = { field: "total_points", direction: "desc" }
}: PlayersTableProps) {
    const [sortConfig, setSortConfig] = useState<SortConfig>(defaultSort);

    const handleSort = (field: SortField) => {
        setSortConfig((prev) => ({
            field,
            direction: prev.field === field && prev.direction === "desc" ? "asc" : "desc",
        }));
    };

    const sortedPlayers = [...players].sort((a, b) => {
        const { field, direction } = sortConfig;
        let valA: number | string = 0;
        let valB: number | string = 0;

        switch (field) {
            case "web_name":
                valA = a.web_name;
                valB = b.web_name;
                break;
            case "team":
                valA = a.team || "";
                valB = b.team || "";
                break;
            case "element_type":
                valA = a.element_type;
                valB = b.element_type;
                break;
            case "now_cost":
                valA = a.now_cost;
                valB = b.now_cost;
                break;
            case "total_points":
                valA = a.total_points;
                valB = b.total_points;
                break;
            case "form":
                valA = a.form || 0;
                valB = b.form || 0;
                break;
            case "avg_fdr":
                valA = a.avg_fdr || 0;
                valB = b.avg_fdr || 0;
                break;
            case "expected_goals":
                valA = a.expected_goals || 0;
                valB = b.expected_goals || 0;
                break;
            case "goals_scored":
                valA = a.goals_scored;
                valB = b.goals_scored;
                break;
            case "assists":
                valA = a.assists;
                valB = b.assists;
                break;
            case "expected_assists":
                valA = a.expected_assists || 0;
                valB = b.expected_assists || 0;
                break;
            case "clean_sheets":
                valA = a.clean_sheets;
                valB = b.clean_sheets;
                break;
            case "expected_clean_sheets":
                valA = a.expected_clean_sheets;
                valB = b.expected_clean_sheets;
                break;
            case "selected_by_percent":
                valA = a.selected_by_percent || 0;
                valB = b.selected_by_percent || 0;
                break;
            case "best_value":
                valA = calculateBestValue(a);
                valB = calculateBestValue(b);
                break;
        }

        if (valA < valB) return direction === "asc" ? -1 : 1;
        if (valA > valB) return direction === "asc" ? 1 : -1;
        return 0;
    });

    const SortIcon = ({ field }: { field: SortField }) => {
        if (sortConfig.field !== field) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon">{sortConfig.direction === "asc" ? "↑" : "↓"}</span>;
    };

    return (
        <div className="players-table-container">
            <table className="players-table">
                <thead>
                    <tr>
                        {compareMode && <th className="th-checkbox"></th>}
                        <th className="text" onClick={() => handleSort("web_name")}>Name <SortIcon field="web_name" /></th>
                        <th className="text" onClick={() => handleSort("team")}>Team <SortIcon field="team" /></th>
                        <th className="text" onClick={() => handleSort("element_type")}>Pos <SortIcon field="element_type" /></th>
                        <th onClick={() => handleSort("now_cost")}>Cost <SortIcon field="now_cost" /></th>
                        <th onClick={() => handleSort("selected_by_percent")}>Owned <SortIcon field="selected_by_percent" /></th>
                        <th onClick={() => handleSort("total_points")}>Pts <SortIcon field="total_points" /></th>
                        <th onClick={() => handleSort("form")}>Form <SortIcon field="form" /></th>
                        <th onClick={() => handleSort("avg_fdr")}>FDR <SortIcon field="avg_fdr" /></th>
                        <th onClick={() => handleSort("goals_scored")}>G <SortIcon field="goals_scored" /></th>
                        <th onClick={() => handleSort("assists")}>A <SortIcon field="assists" /></th>
                        <th onClick={() => handleSort("expected_goals")}>xG <SortIcon field="expected_goals" /></th>
                        <th onClick={() => handleSort("expected_assists")}>xA <SortIcon field="expected_assists" /></th>
                        <th onClick={() => handleSort("clean_sheets")}>CS <SortIcon field="clean_sheets" /></th>
                        <th
                            onClick={() => handleSort("expected_clean_sheets")}
                            title="Estimated expected clean sheets: chance of keeping a clean sheet in each 60+ minute appearance, from expected goals conceded. FPL does not publish this."
                        >
                            xCS <SortIcon field="expected_clean_sheets" />
                        </th>
                        <th onClick={() => handleSort("best_value")}>Value <SortIcon field="best_value" /></th>
                    </tr>
                </thead>
                <tbody>
                    {sortedPlayers.map((player) => {
                        const isSelected = selectedPlayers.has(player.id);
                        const bestValue = calculateBestValue(player);

                        return (
                            <tr
                                key={player.id}
                                onClick={() => onPlayerClick(player)}
                                className={isSelected ? "selected" : ""}
                            >
                                {compareMode && (
                                    <td className="td-checkbox" onClick={(e) => e.stopPropagation()}>
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => onToggleSelection(player.id)}
                                        />
                                    </td>
                                )}
                                <td className="td-name">
                                    <div className="player-cell">
                                        {player.image_url && <img src={player.image_url} alt="" className="player-thumb" />}
                                        <div className="pc-text">
                                            <span className="pc-name">{player.web_name}<PriceChangeBadge athleteId={player.id} /></span>
                                            <PlayerNotes player={player} />
                                        </div>
                                        <WatchStar id={player.id} name={player.web_name} size={14} />
                                    </div>
                                </td>
                                <td className="text">{player.team}</td>
                                <td className="text">{getPositionLabel(player.element_type)}</td>
                                <td>£{(player.now_cost / 10).toFixed(1)}m</td>
                                <td>{player.selected_by_percent != null ? `${player.selected_by_percent.toFixed(1)}%` : "-"}</td>
                                <td className="fw-bold">{player.total_points}</td>
                                <td>{player.form?.toFixed(1)}</td>
                                <td>
                                    {player.avg_fdr !== null && (
                                        <span
                                            className="aero-fdr"
                                            data-fdr={player.avg_fdr <= 2.5 ? 2 : player.avg_fdr <= 3.5 ? 3 : player.avg_fdr <= 4.2 ? 4 : 5}
                                        >
                                            {player.avg_fdr.toFixed(1)}
                                        </span>
                                    )}
                                </td>
                                <td>{player.goals_scored}</td>
                                <td>{player.assists}</td>
                                <td>{player.expected_goals?.toFixed(2) ?? "-"}</td>
                                <td>{player.expected_assists?.toFixed(2) ?? "-"}</td>
                                <td>{player.clean_sheets}</td>
                                <td>{player.expected_clean_sheets.toFixed(1)}</td>
                                <td className="td-value">
                                    {bestValue > 0 ? bestValue.toFixed(2) : "-"}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

// Under the name: FPL's flag and news, then the set pieces he takes.
export function PlayerNotes({ player }: { player: Player }) {
    const flag = availability(player.status, player.chance);
    const { injury, detail } = splitNews(player.news);
    if (!flag && !player.set_pieces?.length) return null;
    const news = flag ? [injury, detail].filter(Boolean).join(" · ") : "";
    return (
        <small className="pc-sub" title={player.news || undefined}>
            {flag && <span className={`av-chip ${flag.tone}`}>{flag.text}</span>}
            {news && <span className="pc-news">{news}</span>}
            {player.set_pieces?.map((k) => <span key={k} className="sp-tag" title={`Takes most of ${player.team ?? "his club"}'s ${SET_PIECE_LABEL[k].toLowerCase()} this season`}>{SET_PIECE_LABEL[k]}</span>)}
        </small>
    );
}
