import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import html2canvas from "html2canvas";
import { PlayerModal } from "../components/PlayerModal";

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";
const TOTAL_BUDGET = 100.0; // £100m
// Use relative URLs for API calls (proxied by Vite in dev, absolute in production)
const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;

interface Player {
  id: number;
  first_name: string;
  second_name: string;
  web_name: string;
  team: string | null;
  team_id: number | null;
  team_code: number | null;
  element_type: number; // 1=GK, 2=DEF, 3=MID, 4=FWD
  now_cost: number;
  total_points: number;
  form: string;
  image_url: string | null;
  ep_next: number | null; // Predicted points for next GW/round
}

interface Formation {
  name: string;
  def: number;
  mid: number;
  fwd: number;
}

const FORMATIONS: Formation[] = [
  { name: "3-4-3", def: 3, mid: 4, fwd: 3 },
  { name: "3-5-2", def: 3, mid: 5, fwd: 2 },
  { name: "4-3-3", def: 4, mid: 3, fwd: 3 },
  { name: "4-4-2", def: 4, mid: 4, fwd: 2 }, // Default
  { name: "4-5-1", def: 4, mid: 5, fwd: 1 },
  { name: "5-3-2", def: 5, mid: 3, fwd: 2 },
  { name: "5-4-1", def: 5, mid: 4, fwd: 1 },
];

function getTeamBadgeUrl(teamCode: number | null): string | null {
  if (!teamCode) return null;
  return `${TEAM_BADGE_BASE}${teamCode}.svg`;
}

function getPositionName(elementType: number): string {
  switch (elementType) {
    case 1: return "GK";
    case 2: return "DEF";
    case 3: return "MID";
    case 4: return "FWD";
    default: return "UNK";
  }
}

function PlayerCard({
  player,
  isCaptain,
  isVice,
  onClick,
  onRemove,
  showRemove = true
}: {
  player: Player | null;
  isCaptain?: boolean;
  isVice?: boolean;
  onClick: () => void;
  onRemove?: () => void;
  showRemove?: boolean;
}) {
  if (!player) {
    return (
      <div className="dream-player-card empty-slot" onClick={onClick}>
        <div className="empty-slot-content">
          <span className="empty-slot-icon">+</span>
          <span className="empty-slot-text">Add Player</span>
        </div>
      </div>
    );
  }

  return (
    <div className="dream-player-card" onClick={onClick}>
      {showRemove && onRemove && (
        <button
          className="remove-player-btn"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        >
          ×
        </button>
      )}
      {isCaptain && <div className="captain-badge">C</div>}
      {isVice && <div className="vice-badge">V</div>}
      <div className="dream-player-image">
        <img
          src={player.image_url || `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`}
          alt={player.web_name}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null;
            target.src = `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`;
          }}
        />
      </div>
      <div className="dream-player-name">{player.web_name}</div>
      <div className="dream-player-stats">
        <span className="dream-stat-badge">£{(player.now_cost / 10).toFixed(1)}m</span>
        <span className="dream-stat-badge">{player.total_points} pts</span>
        {player.ep_next !== null && player.ep_next !== undefined && (
          <span className="dream-stat-badge xp-badge" title="Predicted Points Next GW">
            {player.ep_next.toFixed(1)} xP
          </span>
        )}
      </div>
      {player.team_code && (
        <img
          src={getTeamBadgeUrl(player.team_code)!}
          alt={player.team || ''}
          className="dream-player-badge"
        />
      )}
    </div>
  );
}

function PlayerSelectionModal({
  position,
  allPlayers,
  selectedPlayers,
  onSelect,
  onClose,
}: {
  position: "GK" | "DEF" | "MID" | "FWD";
  allPlayers: Player[];
  selectedPlayers: Player[];
  onSelect: (player: Player) => void;
  onClose: () => void;
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"cost" | "points" | "form">("points");

  const elementType = { GK: 1, DEF: 2, MID: 3, FWD: 4 }[position];

  let filteredPlayers = allPlayers.filter(
    (p) => p.element_type === elementType && !selectedPlayers.find(sp => sp.id === p.id)
  );

  if (searchTerm) {
    filteredPlayers = filteredPlayers.filter((p) =>
      p.web_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.team && p.team.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  }

  filteredPlayers.sort((a, b) => {
    if (sortBy === "cost") return b.now_cost - a.now_cost;
    if (sortBy === "points") return b.total_points - a.total_points;
    if (sortBy === "form") return parseFloat(b.form) - parseFloat(a.form);
    return 0;
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="player-selection-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Select {position}</h2>
          <button className="close-modal-btn" onClick={onClose}>×</button>
        </div>

        <div className="modal-filters">
          <input
            type="text"
            placeholder="Search player or team..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="sort-select">
            <option value="points">Sort by Points</option>
            <option value="cost">Sort by Cost</option>
            <option value="form">Sort by Form</option>
          </select>
        </div>

        <div className="player-list">
          {filteredPlayers.map((player) => (
            <div
              key={player.id}
              className="player-list-item"
              onClick={() => {
                onSelect(player);
                onClose();
              }}
            >
              <img
                src={player.image_url || `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`}
                alt={player.web_name}
                className="player-list-image"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.onerror = null;
                  target.src = `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`;
                }}
              />
              <div className="player-list-info">
                <div className="player-list-name">{player.web_name}</div>
                <div className="player-list-team">{player.team}</div>
              </div>
              <div className="player-list-stats">
                <span>£{(player.now_cost / 10).toFixed(1)}m</span>
                <span>{player.total_points} pts</span>
                {/* <span>Form: {player.form}</span> */}
                {player.ep_next !== null && (
                  <span className="player-list-xp">{player.ep_next.toFixed(1)} xP</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function WildcardSimulatorPage() {
  const { code: urlCode } = useParams<{ code?: string }>();
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [formation, setFormation] = useState<Formation>(FORMATIONS[3]); // 4-4-2
  const [goalkeepers, setGoalkeepers] = useState<Player[]>([]);
  const [defenders, setDefenders] = useState<Player[]>([]);
  const [midfielders, setMidfielders] = useState<Player[]>([]);
  const [forwards, setForwards] = useState<Player[]>([]);
  const [bench, setBench] = useState<Player[]>([]);
  const [captain, setCaptain] = useState<number | null>(null);
  const [viceCaptain, setViceCaptain] = useState<number | null>(null);
  const [code, setCode] = useState<string | null>(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [savedData, setSavedData] = useState<any>(null);
  const [selectionModal, setSelectionModal] = useState<{ position: "GK" | "DEF" | "MID" | "FWD"; benchSlot?: boolean } | null>(null);
  const [detailPlayerId, setDetailPlayerId] = useState<number | null>(null);
  const teamDisplayRef = useRef<HTMLDivElement>(null);

  // Draft management
  const [currentDraftId, setCurrentDraftId] = useState<string>("draft_1");
  const [showDraftMenu, setShowDraftMenu] = useState(false);
  const [draftNames, setDraftNames] = useState<Record<string, string>>({
    draft_1: "Draft 1",
    draft_2: "Draft 2",
    draft_3: "Draft 3",
  });

  // Saved teams management
  const [savedTeams, setSavedTeams] = useState<any[]>([]);
  const [showSavedTeams, setShowSavedTeams] = useState(false);

  // Team name input modal
  const [showTeamNameModal, setShowTeamNameModal] = useState(false);
  const [teamNameInput, setTeamNameInput] = useState("");
  const [pendingSaveAction, setPendingSaveAction] = useState<'local' | 'cloud' | null>(null);

  // Viewing shared team state
  const [isViewingSharedTeam, setIsViewingSharedTeam] = useState(false);
  const [sharedTeamName, setSharedTeamName] = useState<string>("");
  const [sharedTeamCode, setSharedTeamCode] = useState<string>("");

  // Load players
  useEffect(() => {
    fetch("/api/players/?page_size=700")
      .then((res) => res.json())
      .then((data) => {
        setAllPlayers(data.players || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load players:", err);
        setLoading(false);
      });
  }, []);

  // Load from localStorage OR URL parameter
  useEffect(() => {
    // Load draft names from localStorage
    const storedNames = localStorage.getItem("wildcard_draft_names");
    if (storedNames) {
      try {
        setDraftNames(JSON.parse(storedNames));
      } catch (e) {
        console.error("Failed to load draft names:", e);
      }
    }

    // Load saved teams from localStorage
    loadSavedTeams();

    // Check if we have a code in the URL path (e.g., /wildcard/WC-ABC123)
    // or in query string (e.g., ?code=WC-ABC123)
    const queryParams = new URLSearchParams(window.location.search);
    const queryCode = queryParams.get("code");
    const codeToLoad = urlCode || queryCode;

    if (codeToLoad) {
      // Load shared wildcard from API
      loadSharedWildcard(codeToLoad);
    } else {
      // Load current draft from localStorage
      loadDraft(currentDraftId);
    }
  }, [urlCode]);

  // Auto-save every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      autoSave();
    }, 30000);
    return () => clearInterval(interval);
  }, [goalkeepers, defenders, midfielders, forwards, bench, captain, viceCaptain, formation, currentDraftId]);

  const createTrackingEntry = async (): Promise<string | null> => {
    try {
      const response = await fetch("/api/wildcard/track/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      if (data.success && data.code) {
        setCode(data.code);
        localStorage.setItem("wildcard_code", data.code);
        return data.code;
      }
      return null;
    } catch (error) {
      console.error("Failed to create tracking entry:", error);
      return null;
    }
  };

  const loadSharedWildcard = async (wildcardCode: string) => {
    try {
      const response = await fetch(`/api/wildcard/${wildcardCode}/`);
      if (!response.ok) {
        throw new Error("Failed to load wildcard team");
      }

      const data = await response.json();
      if (data.success && data.squad_data) {
        setCode(wildcardCode);

        // Load the squad data
        const squad = data.squad_data;

        // Load formation first
        let targetFormation = FORMATIONS[3]; // Default 4-4-2
        if (squad.formation) {
          const loadedFormation = FORMATIONS.find(f => f.name === squad.formation);
          if (loadedFormation) targetFormation = loadedFormation;
        }
        setFormation(targetFormation);

        if (squad.players && Array.isArray(squad.players)) {
          // Separate all players by position
          const allGKs = squad.players.filter((p: Player) => p.element_type === 1);
          const allDefs = squad.players.filter((p: Player) => p.element_type === 2);
          const allMids = squad.players.filter((p: Player) => p.element_type === 3);
          const allFwds = squad.players.filter((p: Player) => p.element_type === 4);

          // Starting XI based on formation
          // 1 GK + formation.def + formation.mid + formation.fwd = 11 players
          const startingGK = allGKs.slice(0, 1);
          const startingDefs = allDefs.slice(0, targetFormation.def);
          const startingMids = allMids.slice(0, targetFormation.mid);
          const startingFwds = allFwds.slice(0, targetFormation.fwd);

          // Bench: remaining players (should be 1 GK + 3 outfield = 4 total)
          const benchGK = allGKs.slice(1, 2); // 2nd goalkeeper
          const benchDefs = allDefs.slice(targetFormation.def); // Extra defenders
          const benchMids = allMids.slice(targetFormation.mid); // Extra midfielders
          const benchFwds = allFwds.slice(targetFormation.fwd); // Extra forwards
          const benchPlayers = [...benchGK, ...benchDefs, ...benchMids, ...benchFwds];

          // Set the state
          setGoalkeepers(startingGK); // Only starting GK - bench GK is in bench array
          setDefenders(startingDefs);
          setMidfielders(startingMids);
          setForwards(startingFwds);
          setBench(benchPlayers);
        }

        // Load captain/vice if available
        if (squad.captain) setCaptain(squad.captain);
        if (squad.viceCaptain) setViceCaptain(squad.viceCaptain);

        // Set viewing state
        setIsViewingSharedTeam(true);
        setSharedTeamName(data.team_name || "Unnamed Team");
        setSharedTeamCode(wildcardCode);
      }
    } catch (error) {
      console.error("Failed to load shared wildcard:", error);
      alert("Failed to load this wildcard team. It may not exist or the link is incorrect.");
    }
  };

  const autoSave = () => {
    const data = {
      version: 1,
      lastSaved: new Date().toISOString(),
      team: {
        goalkeepers,
        defenders,
        midfielders,
        forwards,
        bench,
        captain,
        viceCaptain,
        formation: formation.name,
      },
      code,
    };
    localStorage.setItem(`wildcard_${currentDraftId}`, JSON.stringify(data));
    setAutoSaveStatus("💾 Saved");
    setTimeout(() => setAutoSaveStatus(""), 2000);
  };

  const loadDraft = (draftId: string) => {
    const stored = localStorage.getItem(`wildcard_${draftId}`);

    if (stored) {
      try {
        const draft = JSON.parse(stored);
        if (draft.team) {
          setGoalkeepers(draft.team.goalkeepers || []);
          setDefenders(draft.team.defenders || []);
          setMidfielders(draft.team.midfielders || []);
          setForwards(draft.team.forwards || []);
          setBench(draft.team.bench || []);
          setCaptain(draft.team.captain || null);
          setViceCaptain(draft.team.viceCaptain || null);
          if (draft.team.formation) {
            const savedFormation = FORMATIONS.find(f => f.name === draft.team.formation);
            if (savedFormation) setFormation(savedFormation);
          }
        }
        if (draft.code) {
          setCode(draft.code);
        } else {
          createTrackingEntry();
        }
      } catch (e) {
        console.error("Failed to load draft:", e);
        createTrackingEntry();
      }
    } else {
      // New draft - reset everything
      setGoalkeepers([]);
      setDefenders([]);
      setMidfielders([]);
      setForwards([]);
      setBench([]);
      setCaptain(null);
      setViceCaptain(null);
      setFormation(FORMATIONS[3]); // Reset to 4-4-2
      createTrackingEntry();
    }
  };

  const switchDraft = (draftId: string) => {
    // Save current draft before switching
    autoSave();

    // Load the new draft
    setCurrentDraftId(draftId);
    loadDraft(draftId);
    setShowDraftMenu(false);
  };

  const renameDraft = (draftId: string) => {
    const newName = prompt(`Rename "${draftNames[draftId]}":`, draftNames[draftId]);
    if (newName && newName.trim()) {
      const updatedNames = { ...draftNames, [draftId]: newName.trim() };
      setDraftNames(updatedNames);
      localStorage.setItem("wildcard_draft_names", JSON.stringify(updatedNames));
    }
  };

  const deleteDraft = (draftId: string) => {
    if (draftId === currentDraftId) {
      alert("Cannot delete the currently active draft. Switch to another draft first.");
      return;
    }

    if (confirm(`Are you sure you want to delete "${draftNames[draftId]}"?`)) {
      localStorage.removeItem(`wildcard_${draftId}`);
      alert(`Deleted ${draftNames[draftId]}`);
    }
  };

  const clearCurrentDraft = () => {
    if (confirm("Are you sure you want to clear this draft? This cannot be undone.")) {
      setGoalkeepers([]);
      setDefenders([]);
      setMidfielders([]);
      setForwards([]);
      setBench([]);
      setCaptain(null);
      setViceCaptain(null);
      setFormation(FORMATIONS[3]);
      localStorage.removeItem(`wildcard_${currentDraftId}`);
      createTrackingEntry();
    }
  };

  const getAllSelectedPlayers = () => {
    return [...goalkeepers, ...defenders, ...midfielders, ...forwards, ...bench];
  };

  const getTotalCost = () => {
    return getAllSelectedPlayers().reduce((sum, p) => sum + p.now_cost, 0) / 10;
  };

  const getBudgetRemaining = () => {
    return TOTAL_BUDGET - getTotalCost();
  };

  const getTeamCounts = () => {
    const counts: Record<number, number> = {};
    getAllSelectedPlayers().forEach((p) => {
      if (p.team_id) {
        counts[p.team_id] = (counts[p.team_id] || 0) + 1;
      }
    });
    return counts;
  };

  const canAddPlayer = (player: Player) => {
    const teamCounts = getTeamCounts();
    if (player.team_id && (teamCounts[player.team_id] || 0) >= 3) {
      alert("You can't have more than 3 players from the same team!");
      return false;
    }
    if (getBudgetRemaining() < player.now_cost / 10) {
      alert("Not enough budget!");
      return false;
    }
    return true;
  };

  const handlePlayerSelect = (player: Player) => {
    if (!canAddPlayer(player)) return;

    if (selectionModal?.position === "GK") {
      if (selectionModal.benchSlot) {
        const benchGKs = bench.filter(p => p.element_type === 1);
        if (benchGKs.length < 1) {
          setBench([...bench, player]);
        }
      } else {
        if (goalkeepers.length < 1) {
          setGoalkeepers([player]);
        }
      }
    } else if (selectionModal?.position === "DEF") {
      if (selectionModal.benchSlot) {
        const benchDEFs = bench.filter(p => p.element_type === 2);
        if (benchDEFs.length < 1) {
          setBench([...bench, player]);
        }
      } else {
        if (defenders.length < formation.def) {
          setDefenders([...defenders, player]);
        }
      }
    } else if (selectionModal?.position === "MID") {
      if (selectionModal.benchSlot) {
        const benchMIDs = bench.filter(p => p.element_type === 3);
        if (benchMIDs.length < 1) {
          setBench([...bench, player]);
        }
      } else {
        if (midfielders.length < formation.mid) {
          setMidfielders([...midfielders, player]);
        }
      }
    } else if (selectionModal?.position === "FWD") {
      if (selectionModal.benchSlot) {
        const benchFWDs = bench.filter(p => p.element_type === 4);
        if (benchFWDs.length < 1) {
          setBench([...bench, player]);
        }
      } else {
        if (forwards.length < formation.fwd) {
          setForwards([...forwards, player]);
        }
      }
    }
  };

  const removePlayer = (playerId: number) => {
    setGoalkeepers(goalkeepers.filter(p => p.id !== playerId));
    setDefenders(defenders.filter(p => p.id !== playerId));
    setMidfielders(midfielders.filter(p => p.id !== playerId));
    setForwards(forwards.filter(p => p.id !== playerId));
    setBench(bench.filter(p => p.id !== playerId));
    if (captain === playerId) setCaptain(null);
    if (viceCaptain === playerId) setViceCaptain(null);
  };

  const handleFormationChange = (newFormation: Formation) => {
    // Adjust defenders
    if (newFormation.def < defenders.length) {
      const removed = defenders.slice(newFormation.def);
      setDefenders(defenders.slice(0, newFormation.def));
      setBench([...bench, ...removed]);
    }
    // Adjust midfielders
    if (newFormation.mid < midfielders.length) {
      const removed = midfielders.slice(newFormation.mid);
      setMidfielders(midfielders.slice(0, newFormation.mid));
      setBench([...bench, ...removed]);
    }
    // Adjust forwards
    if (newFormation.fwd < forwards.length) {
      const removed = forwards.slice(newFormation.fwd);
      setForwards(forwards.slice(0, newFormation.fwd));
      setBench([...bench, ...removed]);
    }
    setFormation(newFormation);
  };

  // Load saved teams from localStorage
  const loadSavedTeams = () => {
    try {
      const saved = localStorage.getItem("wildcard_saved_teams");
      if (saved) {
        setSavedTeams(JSON.parse(saved));
      }
    } catch (e) {
      console.error("Failed to load saved teams:", e);
    }
  };

  // Save team to localStorage
  const saveTeamLocally = () => {
    const allSelected = getAllSelectedPlayers();
    if (allSelected.length < 15) {
      alert("Please select all 15 players before saving!");
      return;
    }

    // Show modal to get team name
    setTeamNameInput("");
    setPendingSaveAction('local');
    setShowTeamNameModal(true);
  };

  // Actually perform the local save after getting the name
  const performLocalSave = (teamName: string) => {
    if (!teamName || !teamName.trim()) return;

    const allSelected = getAllSelectedPlayers();

    // Save only essential player data to avoid circular references and reduce size
    const simplifiedPlayers = allSelected.map(p => ({
      id: p.id,
      playerId: p.id,
      web_name: p.web_name,
      element_type: p.element_type,
      team_id: p.team_id,
      now_cost: p.now_cost,
      image_url: p.image_url
    }));

    const savedTeam = {
      id: Date.now().toString(),
      name: teamName.trim(),
      formation: formation.name,
      players: simplifiedPlayers,
      captain,
      viceCaptain,
      totalCost: getTotalCost(),
      savedAt: new Date().toISOString(),
    };

    const existingSaved = localStorage.getItem("wildcard_saved_teams");
    const savedList = existingSaved ? JSON.parse(existingSaved) : [];
    savedList.unshift(savedTeam); // Add to beginning

    // Keep only last 10 saved teams
    if (savedList.length > 10) {
      savedList.pop();
    }

    localStorage.setItem("wildcard_saved_teams", JSON.stringify(savedList));
    setSavedTeams(savedList);

    // Also update the current draft name to match the saved team name
    const updatedNames = { ...draftNames, [currentDraftId]: teamName.trim() };
    setDraftNames(updatedNames);
    localStorage.setItem("wildcard_draft_names", JSON.stringify(updatedNames));

    alert(`✅ Team "${teamName.trim()}" saved successfully!`);
  };

  // Load a saved team
  const loadSavedTeam = (team: any) => {
    if (!confirm(`Load "${team.name}"? This will replace your current team.`)) {
      return;
    }

    // Clear current team
    setGoalkeepers([]);
    setDefenders([]);
    setMidfielders([]);
    setForwards([]);
    setBench([]);
    setCaptain(team.captain);
    setViceCaptain(team.viceCaptain);

    // Set formation
    const loadedFormation = FORMATIONS.find(f => f.name === team.formation) || FORMATIONS[3];
    setFormation(loadedFormation);

    // Load players - match saved player IDs to full player objects
    const playerIds = team.players.map((p: any) => p.id || p.playerId);
    const loadedPlayers = allPlayers.filter(p => playerIds.includes(p.id));

    if (loadedPlayers.length === 0) {
      alert("Could not find players. Please ensure player data is loaded.");
      return;
    }

    // Distribute players
    const gks = loadedPlayers.filter(p => p.element_type === 1);
    const defs = loadedPlayers.filter(p => p.element_type === 2);
    const mids = loadedPlayers.filter(p => p.element_type === 3);
    const fwds = loadedPlayers.filter(p => p.element_type === 4);

    setGoalkeepers(gks.slice(0, 1));
    setDefenders(defs.slice(0, loadedFormation.def));
    setMidfielders(mids.slice(0, loadedFormation.mid));
    setForwards(fwds.slice(0, loadedFormation.fwd));

    // Remaining go to bench
    const remaining = [
      ...gks.slice(1),
      ...defs.slice(loadedFormation.def),
      ...mids.slice(loadedFormation.mid),
      ...fwds.slice(loadedFormation.fwd)
    ].slice(0, 4);
    setBench(remaining);

    setShowSavedTeams(false);
    alert(`✅ Loaded "${team.name}"`);
  };

  // Delete a saved team
  const deleteSavedTeam = (teamId: string) => {
    if (!confirm("Delete this saved team?")) return;

    const existingSaved = localStorage.getItem("wildcard_saved_teams");
    if (!existingSaved) return;

    const savedList = JSON.parse(existingSaved);
    const filtered = savedList.filter((t: any) => t.id !== teamId);

    localStorage.setItem("wildcard_saved_teams", JSON.stringify(filtered));
    setSavedTeams(filtered);
  };

  // Handle team name submission from modal
  const handleTeamNameSubmit = () => {
    if (!teamNameInput.trim()) {
      alert("Please enter a team name!");
      return;
    }

    setShowTeamNameModal(false);

    if (pendingSaveAction === 'local') {
      performLocalSave(teamNameInput);
    } else if (pendingSaveAction === 'cloud') {
      performCloudSave(teamNameInput);
    }

    setPendingSaveAction(null);
    setTeamNameInput("");
  };

  const saveToCloud = () => {
    const allSelected = getAllSelectedPlayers();
    if (allSelected.length < 15) {
      alert("Please select all 15 players before saving!");
      return;
    }

    // Show modal to get team name
    setTeamNameInput("");
    setPendingSaveAction('cloud');
    setShowTeamNameModal(true);
  };

  // Actually perform the cloud save after getting the name
  const performCloudSave = async (teamName: string) => {
    console.log('performCloudSave: Starting...');

    // Check if we have a code, if not try to load from localStorage or create a new one
    let currentCode = code;
    if (!currentCode) {
      console.log('performCloudSave: No code found, checking localStorage...');
      const storedCode = localStorage.getItem("wildcard_code");
      if (storedCode) {
        console.log('performCloudSave: Found stored code:', storedCode);
        currentCode = storedCode;
        setCode(storedCode);
      } else {
        console.log('performCloudSave: Creating new tracking entry...');
        currentCode = await createTrackingEntry();
        console.log('performCloudSave: Got code:', currentCode);
        if (!currentCode) {
          alert("Failed to generate team code. Please try again.");
          return;
        }
      }
    }

    console.log('performCloudSave: Getting selected players...');
    const allSelected = getAllSelectedPlayers();
    console.log('performCloudSave: Got players:', allSelected.length);

    console.log('performCloudSave: Simplifying player data...');
    // Simplify player data before sending to avoid circular references
    const simplifiedPlayers = allSelected.map(p => ({
      id: p.id,
      web_name: p.web_name,
      first_name: p.first_name,
      second_name: p.second_name,
      element_type: p.element_type,
      team_id: p.team_id,
      team_code: p.team_code,
      now_cost: p.now_cost,
      total_points: p.total_points,
      form: p.form,
      image_url: p.image_url,
    }));
    console.log('performCloudSave: Simplified players:', simplifiedPlayers.length);

    console.log('performCloudSave: Creating request body...');
    const requestBody = {
      squad_data: {
        players: simplifiedPlayers,
        formation: formation.name,
        captain,
        viceCaptain,
      },
      team_name: teamName || "",
    };
    console.log('performCloudSave: Request body created');

    try {
      console.log('performCloudSave: Sending PATCH request...');
      const response = await fetch(`/api/wildcard/${currentCode}/save/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      console.log('performCloudSave: Got response:', response.status);

      const data = await response.json();
      console.log('performCloudSave: Parsed response data:', data);

      if (data.success) {
        setSavedData(data);
        setShowSuccessModal(true);
      } else {
        alert(data.error || "Failed to save team");
      }
    } catch (error) {
      console.error("Failed to save to cloud:", error);
      alert("Network error. Please try again.");
    }
  };

  // Helper function to convert images to base64 to bypass CORS
  const convertImagesToBase64 = async (container: HTMLElement) => {
    const images = container.querySelectorAll('img');
    const originalSources: Map<HTMLImageElement, string> = new Map();

    // Store original sources and convert to base64
    for (const img of Array.from(images)) {
      const originalSrc = img.src;
      originalSources.set(img, originalSrc);

      try {
        const response = await fetch(`/api/image-proxy/?url=${encodeURIComponent(originalSrc)}`);
        if (!response.ok) {
          throw new Error(`Proxy failed for ${originalSrc}`);
        }
        const blob = await response.blob();
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result as string);
          reader.onerror = () => reject(new Error('FileReader failed'));
          reader.readAsDataURL(blob);
        });

        img.src = base64;
      } catch (error) {
        console.warn(`Failed to convert image: ${originalSrc}`, error);
      }
    }

    // Wait a bit for all images to update
    await new Promise(resolve => setTimeout(resolve, 200));

    return originalSources;
  };

  // Helper function to restore original image sources
  const restoreImageSources = (originalSources: Map<HTMLImageElement, string>) => {
    for (const [img, src] of originalSources.entries()) {
      img.src = src;
    }
  };

  const copyShareLink = () => {
    if (!code) return;
    const shareUrl = `${API_BASE_URL}/wildcard/${code}/`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      alert("✅ Link copied to clipboard!");
    });
  };

  const shareAsImage = async () => {
    if (!teamDisplayRef.current) return;
    try {
      console.log('Starting image generation...');

      // Convert images to base64 to bypass CORS
      const originalSources = await convertImagesToBase64(teamDisplayRef.current);

      console.log('Images converted, generating canvas...');

      const canvas = await html2canvas(teamDisplayRef.current, {
        backgroundColor: "#050714",
        scale: 2,
        logging: true, // Enable logging to see what's happening
        useCORS: true,
        allowTaint: true,
        imageTimeout: 0,
        removeContainer: true,
      });

      console.log('Canvas generated, restoring images...');

      // Restore original image sources
      restoreImageSources(originalSources);

      console.log('Creating download...');

      canvas.toBlob((blob) => {
        if (!blob) {
          console.error('Failed to create blob');
          return;
        }
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.download = `wildcard-team-${code || "draft"}.png`;
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);
        alert("✅ Image downloaded!");
      }, "image/png");
    } catch (error) {
      console.error("Failed to generate image:", error);
      alert("Failed to generate image. Please try again.");
    }
  };

  const shareOnTwitter = async () => {
    if (!code) return;

    try {
      // Fetch upcoming gameweek
      const gwResponse = await fetch('/api/fixtures/');
      const gwData = await gwResponse.json();
      const upcomingGW = gwData.current_gameweek || 8; // Fallback to 8

      // Get all selected players
      const allSelected = getAllSelectedPlayers();

      // Helper to get position name
      const getPositionName = (elementType: number) => {
        switch (elementType) {
          case 1: return 'GK';
          case 2: return 'DEF';
          case 3: return 'MID';
          case 4: return 'FWD';
          default: return 'UNK';
        }
      };

      // Group players by position
      const playersByPosition: { [key: string]: typeof allSelected } = {
        'GK': [],
        'DEF': [],
        'MID': [],
        'FWD': []
      };

      allSelected.forEach(p => {
        const pos = getPositionName(p.element_type);
        playersByPosition[pos].push(p);
      });

      // Separate starting XI and bench
      const startingXI = allSelected.filter(p => !bench.some(b => b.id === p.id));
      const benchPlayers = allSelected.filter(p => bench.some(b => b.id === p.id));

      // Group starting XI by position
      const startingByPos: { [key: string]: typeof allSelected } = {
        'GK': [],
        'DEF': [],
        'MID': [],
        'FWD': []
      };

      startingXI.forEach(p => {
        const pos = getPositionName(p.element_type);
        startingByPos[pos].push(p);
      });

      // Build condensed format
      let textLines = ['Checkout My FPL Team Draft.\n\n'];

      // Starting XI
      if (startingByPos['GK'].length > 0) {
        textLines.push(`GK->${startingByPos['GK'].map(p => p.web_name).join(', ')}\n`);
      }
      if (startingByPos['DEF'].length > 0) {
        textLines.push(`DEF->${startingByPos['DEF'].map(p => p.web_name).join(', ')}\n`);
      }
      if (startingByPos['MID'].length > 0) {
        textLines.push(`MID->${startingByPos['MID'].map(p => p.web_name).join(', ')}\n`);
      }
      if (startingByPos['FWD'].length > 0) {
        textLines.push(`FWD->${startingByPos['FWD'].map(p => p.web_name).join(', ')}\n`);
      }

      // Bench
      if (benchPlayers.length > 0) {
        textLines.push('\nBench->\n');
        benchPlayers.forEach(p => {
          textLines.push(`${p.web_name} (${getPositionName(p.element_type)})\n`);
        });
      }

      const shareUrl = `${API_BASE_URL}/wildcard/${code}/`;
      const text = `${textLines.join('')}\n#GW${upcomingGW} #FPL @aero_fpl\n\n`;

      const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
      window.open(twitterUrl, "_blank", "width=550,height=420");
    } catch (error) {
      console.error("Failed to share on Twitter:", error);
      // Fallback to simple share
      const shareUrl = `${API_BASE_URL}/wildcard/${code}/`;
      const text = "Check out my FPL Wildcard team! 🔥⚽ #FPL @aero_fpl";
      const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
      window.open(twitterUrl, "_blank", "width=550,height=420");
    }
  };

  const shareOnFacebook = async () => {
    if (!code) return;

    try {
      // Fetch upcoming gameweek
      const gwResponse = await fetch('/api/fixtures/');
      const gwData = await gwResponse.json();
      const upcomingGW = gwData.current_gameweek || 8; // Fallback to 8

      // Get all selected players
      const allSelected = getAllSelectedPlayers();

      // Helper to get position name
      const getPositionName = (elementType: number) => {
        switch (elementType) {
          case 1: return 'GK';
          case 2: return 'DEF';
          case 3: return 'MID';
          case 4: return 'FWD';
          default: return 'UNK';
        }
      };

      // Separate starting XI and bench
      const startingXI = allSelected.filter(p => !bench.some(b => b.id === p.id));
      const benchPlayers = allSelected.filter(p => bench.some(b => b.id === p.id));

      // Group starting XI by position
      const startingByPos: { [key: string]: typeof allSelected } = {
        'GK': [],
        'DEF': [],
        'MID': [],
        'FWD': []
      };

      startingXI.forEach(p => {
        const pos = getPositionName(p.element_type);
        startingByPos[pos].push(p);
      });

      // Build condensed format
      let textLines = ['Checkout My FPL Team Draft.\n'];

      // Starting XI
      if (startingByPos['GK'].length > 0) {
        textLines.push(`GK->${startingByPos['GK'].map(p => p.web_name).join(', ')}\n`);
      }
      if (startingByPos['DEF'].length > 0) {
        textLines.push(`DEF->${startingByPos['DEF'].map(p => p.web_name).join(', ')}\n`);
      }
      if (startingByPos['MID'].length > 0) {
        textLines.push(`MID->${startingByPos['MID'].map(p => p.web_name).join(', ')}\n`);
      }
      if (startingByPos['FWD'].length > 0) {
        textLines.push(`FWD->${startingByPos['FWD'].map(p => p.web_name).join(', ')}\n`);
      }

      // Bench
      if (benchPlayers.length > 0) {
        textLines.push('\nBench->\n');
        benchPlayers.forEach(p => {
          textLines.push(`${p.web_name} (${getPositionName(p.element_type)})\n`);
        });
      }

      const shareUrl = `${API_BASE_URL}/wildcard/${code}/`;
      const quote = `${textLines.join('')}\n#GW${upcomingGW} #FPL @aero_fpl`;

      // Use Facebook's sharer with quote parameter
      const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}&quote=${encodeURIComponent(quote)}`;
      window.open(facebookUrl, "_blank", "width=550,height=420");
    } catch (error) {
      console.error("Failed to share on Facebook:", error);
      const shareUrl = `${API_BASE_URL}/wildcard/${code}/`;
      const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
      window.open(facebookUrl, "_blank", "width=550,height=420");
    }
  };

  const copyToDraft = () => {
    // Save the current team to the user's draft using autoSave logic
    const data = {
      version: 1,
      lastSaved: new Date().toISOString(),
      team: {
        goalkeepers,
        defenders,
        midfielders,
        forwards,
        bench,
        captain,
        viceCaptain,
        formation: formation.name,
      },
      code: null, // Clear code so they get a new one when saving
    };
    localStorage.setItem(`wildcard_${currentDraftId}`, JSON.stringify(data));

    // Clear the viewing state
    setIsViewingSharedTeam(false);
    setSharedTeamName("");
    setSharedTeamCode("");
    setCode(null); // Clear the shared code so they get a new one when saving

    // Update the URL to remove the code parameter
    window.history.pushState({}, '', '/wildcard');

    alert(`✅ Team copied to ${draftNames[currentDraftId] || currentDraftId}!\n\nYou can now make changes and save it as your own team.`);
  };

  const startFresh = () => {
    if (confirm("Are you sure you want to start fresh? This will clear the viewed team.")) {
      // Clear all selections
      setGoalkeepers([]);
      setDefenders([]);
      setMidfielders([]);
      setForwards([]);
      setBench([]);
      setCaptain(null);
      setViceCaptain(null);
      setFormation(FORMATIONS[3]);

      // Clear viewing state
      setIsViewingSharedTeam(false);
      setSharedTeamName("");
      setSharedTeamCode("");
      setCode(null);

      // Update the URL to remove the code parameter
      window.history.pushState({}, '', '/wildcard');

      // Load the user's existing draft
      loadDraft(currentDraftId);
    }
  };

  const clearDraft = () => {
    if (confirm("Are you sure you want to clear your draft? This cannot be undone.")) {
      localStorage.removeItem("wildcard_draft");
      setGoalkeepers([]);
      setDefenders([]);
      setMidfielders([]);
      setForwards([]);
      setBench([]);
      setCaptain(null);
      setViceCaptain(null);
      setFormation(FORMATIONS[3]);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="dream-team-loading">Loading players...</div>
      </div>
    );
  }

  const allSelected = getAllSelectedPlayers();
  const totalCost = getTotalCost();
  const budgetRemaining = getBudgetRemaining();
  const isSquadComplete = allSelected.length === 15;

  return (
    <div className="page dream-team-page">
      <div className="dream-team-header">
        <h1>⚡ Wildcard Simulator</h1>
        <p className="dream-team-subtitle">
          Build your perfect wildcard team • Auto-saves every 30s
        </p>

        {/* Shared Team Viewing Banner */}
        {isViewingSharedTeam && (
          <div style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: '16px 20px',
            borderRadius: '12px',
            marginTop: '16px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
          }}>
            <div style={{ flex: '1', minWidth: '200px' }}>
              <div style={{ fontSize: '0.85em', opacity: 0.9, marginBottom: '4px' }}>
                👀 Viewing Shared Team
              </div>
              <div style={{ fontSize: '1.1em', fontWeight: 'bold' }}>
                {sharedTeamName}
              </div>
              <div style={{ fontSize: '0.8em', opacity: 0.8, marginTop: '2px' }}>
                Code: {sharedTeamCode}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                onClick={copyToDraft}
                style={{
                  background: 'rgba(255,255,255,0.95)',
                  color: '#667eea',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: 'none',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  fontSize: '0.9em',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = 'white'}
                onMouseOut={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.95)'}
              >
                📋 Copy to My Draft
              </button>
              <button
                onClick={startFresh}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  color: 'white',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.3)',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  fontSize: '0.9em',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.3)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.2)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)';
                }}
              >
                🆕 Start Fresh
              </button>
            </div>
          </div>
        )}

        {/* Draft Management Menu */}
        <div className="draft-manager">
          <button
            className="draft-selector-btn"
            onClick={() => setShowDraftMenu(!showDraftMenu)}
          >
            📁 {draftNames[currentDraftId]} <span style={{ marginLeft: '8px' }}>▼</span>
          </button>

          {showDraftMenu && (
            <div className="draft-menu">
              {Object.entries(draftNames).map(([draftId, name]) => (
                <div key={draftId} className="draft-menu-item">
                  <button
                    className={`draft-option ${draftId === currentDraftId ? 'active' : ''}`}
                    onClick={() => switchDraft(draftId)}
                  >
                    {name} {draftId === currentDraftId && '✓'}
                  </button>
                  <button
                    className="draft-action-btn"
                    onClick={() => renameDraft(draftId)}
                    title="Rename"
                  >
                    ✏️
                  </button>
                  {draftId !== currentDraftId && (
                    <button
                      className="draft-action-btn delete"
                      onClick={() => deleteDraft(draftId)}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="wildcard-controls">
          <div className="formation-selector">
            <label>Formation:</label>
            <select
              value={formation.name}
              onChange={(e) => {
                const newFormation = FORMATIONS.find(f => f.name === e.target.value);
                if (newFormation) handleFormationChange(newFormation);
              }}
              className="formation-select"
            >
              {FORMATIONS.map((f) => (
                <option key={f.name} value={f.name}>{f.name}</option>
              ))}
            </select>
          </div>

          <div className="autosave-indicator" style={{ opacity: autoSaveStatus ? 1 : 0 }}>
            {autoSaveStatus}
          </div>
        </div>

        <div className="dream-team-stats">
          <div className="dream-stat-item">
            <span className="dream-stat-label">Players</span>
            <span className="dream-stat-value">{allSelected.length}/15</span>
          </div>
          <div className="dream-stat-item">
            <span className="dream-stat-label">Budget Used</span>
            <span className="dream-stat-value">£{totalCost.toFixed(1)}m</span>
          </div>
          <div className="dream-stat-item">
            <span className="dream-stat-label">Remaining</span>
            <span className="dream-stat-value" style={{ color: budgetRemaining < 0 ? "#ef4444" : "var(--accent-cyan)" }}>
              £{budgetRemaining.toFixed(1)}m
            </span>
          </div>
        </div>

        <div className="wildcard-action-btns">
          <button
            className="secondary-btn"
            onClick={() => setShowSavedTeams(true)}
          >
            📂 My Saved Teams ({savedTeams.length})
          </button>
          <button className="secondary-btn" onClick={clearCurrentDraft}>
            🗑️ Clear Draft
          </button>
          <button
            className="primary-btn"
            onClick={saveTeamLocally}
            disabled={!isSquadComplete || budgetRemaining < 0}
          >
            💾 Save Team
          </button>
          <button
            className="share-dream-team-btn"
            onClick={saveToCloud}
            disabled={!isSquadComplete || budgetRemaining < 0}
          >
            � Share Online
          </button>
        </div>
      </div>

      <div ref={teamDisplayRef} className="dream-team-capture wildcard-compact">
        <div className="football-field">
          {/* Goalkeeper */}
          <div className="field-row goalkeeper-row">
            {goalkeepers[0] ? (
              <PlayerCard
                player={goalkeepers[0]}
                isCaptain={captain === goalkeepers[0].id}
                isVice={viceCaptain === goalkeepers[0].id}
                onClick={() => setDetailPlayerId(goalkeepers[0].id)}
                onRemove={() => removePlayer(goalkeepers[0].id)}
              />
            ) : (
              <PlayerCard
                player={null}
                onClick={() => setSelectionModal({ position: "GK" })}
                onRemove={() => { }}
                showRemove={false}
              />
            )}
          </div>

          {/* Defenders */}
          <div className="field-row defenders-row">
            {Array.from({ length: formation.def }).map((_, i) => (
              <div key={`def-${i}`}>
                {defenders[i] ? (
                  <PlayerCard
                    player={defenders[i]}
                    isCaptain={captain === defenders[i].id}
                    isVice={viceCaptain === defenders[i].id}
                    onClick={() => setDetailPlayerId(defenders[i].id)}
                    onRemove={() => removePlayer(defenders[i].id)}
                  />
                ) : (
                  <PlayerCard
                    player={null}
                    onClick={() => setSelectionModal({ position: "DEF" })}
                    onRemove={() => { }}
                    showRemove={false}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Midfielders */}
          <div className="field-row midfielders-row">
            {Array.from({ length: formation.mid }).map((_, i) => (
              <div key={`mid-${i}`}>
                {midfielders[i] ? (
                  <PlayerCard
                    player={midfielders[i]}
                    isCaptain={captain === midfielders[i].id}
                    isVice={viceCaptain === midfielders[i].id}
                    onClick={() => setDetailPlayerId(midfielders[i].id)}
                    onRemove={() => removePlayer(midfielders[i].id)}
                  />
                ) : (
                  <PlayerCard
                    player={null}
                    onClick={() => setSelectionModal({ position: "MID" })}
                    onRemove={() => { }}
                    showRemove={false}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Forwards */}
          <div className="field-row forwards-row">
            {Array.from({ length: formation.fwd }).map((_, i) => (
              <div key={`fwd-${i}`}>
                {forwards[i] ? (
                  <PlayerCard
                    player={forwards[i]}
                    isCaptain={captain === forwards[i].id}
                    isVice={viceCaptain === forwards[i].id}
                    onClick={() => setDetailPlayerId(forwards[i].id)}
                    onRemove={() => removePlayer(forwards[i].id)}
                  />
                ) : (
                  <PlayerCard
                    player={null}
                    onClick={() => setSelectionModal({ position: "FWD" })}
                    onRemove={() => { }}
                    showRemove={false}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Bench */}
        <div className="bench-section">
          <h2>Bench (4 players)</h2>
          <div className="bench-players">
            {/* GK */}
            {bench.find(p => p.element_type === 1) ? (
              <PlayerCard
                player={bench.find(p => p.element_type === 1)!}
                onClick={() => setDetailPlayerId(bench.find(p => p.element_type === 1)!.id)}
                onRemove={() => removePlayer(bench.find(p => p.element_type === 1)!.id)}
              />
            ) : (
              <PlayerCard
                player={null}
                onClick={() => setSelectionModal({ position: "GK", benchSlot: true })}
                onRemove={() => { }}
                showRemove={false}
              />
            )}

            {/* Outfield players */}
            {[2, 3, 4].map((_, idx) => {
              const benchOutfield = bench.filter(p => p.element_type !== 1);
              return benchOutfield[idx] ? (
                <PlayerCard
                  key={`bench-${idx}`}
                  player={benchOutfield[idx]}
                  onClick={() => setDetailPlayerId(benchOutfield[idx].id)}
                  onRemove={() => removePlayer(benchOutfield[idx].id)}
                />
              ) : (
                <PlayerCard
                  key={`bench-empty-${idx}`}
                  player={null}
                  onClick={() => {
                    // Allow any outfield position for bench
                    const missing = ["DEF", "MID", "FWD"].find(pos => {
                      const count = benchOutfield.filter(p => getPositionName(p.element_type) === pos).length;
                      return count < 1;
                    });
                    if (missing) {
                      setSelectionModal({ position: missing as any, benchSlot: true });
                    } else {
                      setSelectionModal({ position: "DEF", benchSlot: true });
                    }
                  }}
                  onRemove={() => { }}
                  showRemove={false}
                />
              );
            })}
          </div>
        </div>
      </div>

      {/* Player Selection Modal */}
      {selectionModal && (
        <PlayerSelectionModal
          position={selectionModal.position}
          allPlayers={allPlayers}
          selectedPlayers={getAllSelectedPlayers()}
          onSelect={handlePlayerSelect}
          onClose={() => setSelectionModal(null)}
        />
      )}

      {/* Player Detail Modal */}
      {detailPlayerId && (
        <PlayerModal
          playerId={detailPlayerId}
          onClose={() => setDetailPlayerId(null)}
        />
      )}

      {/* Success Modal */}
      {showSuccessModal && savedData && (
        <div className="modal-overlay" onClick={() => setShowSuccessModal(false)}>
          <div className="modal-content success-modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>✅ Team Saved!</h2>
            <p>Your wildcard team has been saved and is ready to share!</p>

            <div className="code-box" style={{
              background: "rgba(0, 255, 135, 0.1)",
              padding: "20px",
              margin: "20px 0",
              borderRadius: "8px",
              fontSize: "1.5em",
              fontWeight: "bold",
              color: "var(--accent-cyan)",
              border: "1px solid var(--accent-cyan)"
            }}>
              <strong>Code:</strong> {savedData.code}
            </div>

            <div className="share-url" style={{
              background: "rgba(255, 255, 255, 0.05)",
              padding: "15px",
              borderRadius: "8px",
              wordBreak: "break-all",
              fontFamily: "monospace",
              fontSize: "0.9em",
              margin: "15px 0",
              border: "2px solid var(--accent-cyan)"
            }}>
              {`${API_BASE_URL}/wildcard/${savedData.code}/`}
            </div>

            <div className="team-stats" style={{
              margin: "20px 0",
              padding: "20px",
              background: "rgba(255, 255, 255, 0.05)",
              borderRadius: "8px"
            }}>
              <p><strong>Total Cost:</strong> £{savedData.total_cost}m</p>
            </div>

            <h3 style={{ marginTop: "20px", marginBottom: "10px" }}>Share Your Team:</h3>

            <div className="share-buttons" style={{
              display: "flex",
              gap: "10px",
              justifyContent: "center",
              margin: "20px 0",
              flexWrap: "wrap"
            }}>
              <button className="share-btn-modal copy" onClick={copyShareLink} style={{
                padding: "10px 20px",
                borderRadius: "5px",
                border: "none",
                fontWeight: "bold",
                cursor: "pointer",
                fontSize: "0.95em",
                background: "var(--accent-cyan)",
                color: "var(--bg-primary)"
              }}>
                📋 Copy Link
              </button>
              <button className="share-btn-modal image" onClick={shareAsImage} style={{
                padding: "10px 20px",
                borderRadius: "5px",
                border: "none",
                fontWeight: "bold",
                cursor: "pointer",
                fontSize: "0.95em",
                background: "var(--accent-purple)",
                color: "white"
              }}>
                📸 Download Image
              </button>
              <button className="share-btn-modal twitter" onClick={shareOnTwitter} style={{
                padding: "10px 20px",
                borderRadius: "5px",
                border: "none",
                fontWeight: "bold",
                cursor: "pointer",
                fontSize: "0.95em",
                background: "#1da1f2",
                color: "white"
              }}>
                🐦 Twitter
              </button>
            </div>

            <div className="modal-actions" style={{ marginTop: "20px" }}>
              <button onClick={() => setShowSuccessModal(false)} style={{
                background: "rgba(255, 255, 255, 0.1)",
                color: "var(--text-primary)",
                padding: "12px 30px",
                borderRadius: "8px",
                border: "none",
                cursor: "pointer",
                fontSize: "1em"
              }}>Close</button>
            </div>

            <p className="note" style={{
              marginTop: "20px",
              fontSize: "0.9em",
              color: "var(--text-muted)"
            }}>💡 Your team is saved! Anyone with this link can view it.</p>
          </div>
        </div>
      )}

      {/* Team Name Input Modal */}
      {showTeamNameModal && (
        <div className="modal-overlay" onClick={() => {
          setShowTeamNameModal(false);
          setPendingSaveAction(null);
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h2>💾 {pendingSaveAction === 'local' ? 'Save Team' : 'Share Team Online'}</h2>
              <button
                className="close-modal-btn"
                onClick={() => {
                  setShowTeamNameModal(false);
                  setPendingSaveAction(null);
                }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: '20px' }}>
              <label style={{
                display: 'block',
                marginBottom: '10px',
                color: 'var(--text-primary)',
                fontWeight: '600'
              }}>
                Team Name
              </label>
              <input
                type="text"
                value={teamNameInput}
                onChange={(e) => setTeamNameInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleTeamNameSubmit();
                  }
                }}
                placeholder="e.g., My Triple Captain Team"
                autoFocus
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-glow)',
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: 'var(--text-primary)',
                  fontSize: '1rem',
                  marginBottom: '20px'
                }}
              />

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowTeamNameModal(false);
                    setPendingSaveAction(null);
                  }}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-glow)',
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '1rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleTeamNameSubmit}
                  style={{
                    padding: '10px 30px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    fontWeight: '600'
                  }}
                >
                  {pendingSaveAction === 'local' ? '💾 Save' : '🌐 Share'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Saved Teams Modal */}
      {showSavedTeams && (
        <div className="modal-overlay" onClick={() => setShowSavedTeams(false)}>
          <div className="modal-content saved-teams-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📂 My Saved Teams</h2>
              <button
                className="close-modal-btn"
                onClick={() => setShowSavedTeams(false)}
              >
                ✕
              </button>
            </div>

            <div className="saved-teams-list">
              {savedTeams.length === 0 ? (
                <div className="empty-state">
                  <p style={{ fontSize: '3em', marginBottom: '20px' }}>🏆</p>
                  <h3>No saved teams yet</h3>
                  <p style={{ color: 'var(--text-muted)', marginTop: '10px' }}>
                    Build a complete 15-player team and click "Save Team" to store it locally
                  </p>
                </div>
              ) : (
                <div className="teams-grid">
                  {savedTeams.map((team) => (
                    <div key={team.id} className="saved-team-card">
                      <div className="team-card-header">
                        <h3>{team.name}</h3>
                        <span className="team-cost">£{team.totalCost.toFixed(1)}m</span>
                      </div>

                      <div className="team-card-info">
                        <span className="team-formation">⚽ {team.formation}</span>
                        <span className="team-date">
                          📅 {new Date(team.savedAt).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </div>

                      <div className="team-card-captain">
                        <span>
                          (C) {team.players.find((p: any) => p.playerId === team.captain)?.web_name || 'None'}
                        </span>
                        {team.viceCaptain && (
                          <span style={{ marginLeft: '10px' }}>
                            (VC) {team.players.find((p: any) => p.playerId === team.viceCaptain)?.web_name || 'None'}
                          </span>
                        )}
                      </div>

                      <div className="team-card-actions">
                        <button
                          className="load-team-btn"
                          onClick={() => {
                            loadSavedTeam(team);
                            setShowSavedTeams(false);
                          }}
                        >
                          📥 Load Team
                        </button>
                        <button
                          className="delete-team-btn"
                          onClick={() => deleteSavedTeam(team.id)}
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {savedTeams.length > 0 && (
              <div className="modal-footer">
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9em' }}>
                  💾 Teams are stored locally in your browser • Max 10 teams
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
