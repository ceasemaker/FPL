import { useState, useEffect, useRef } from "react";
import html2canvas from "html2canvas";
import { PlayerModal } from "../components/PlayerModal";

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";
const TOTAL_BUDGET = 100.0; // £100m

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
                <span>Form: {player.form}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function WildcardSimulatorPage() {
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
    // Check if we have a code in the URL (e.g., ?code=WC-ABC123)
    const urlParams = new URLSearchParams(window.location.search);
    const urlCode = urlParams.get("code");
    
    if (urlCode) {
      // Load shared wildcard from API
      loadSharedWildcard(urlCode);
    } else {
      // Load from localStorage as before
      const stored = localStorage.getItem("wildcard_draft");
      const storedCode = localStorage.getItem("wildcard_code");

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
        } catch (e) {
          console.error("Failed to load draft:", e);
        }
      }

      if (storedCode) {
        setCode(storedCode);
      } else {
        createTrackingEntry();
      }
    }
  }, []);

  // Auto-save every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      autoSave();
    }, 30000);
    return () => clearInterval(interval);
  }, [goalkeepers, defenders, midfielders, forwards, bench, captain, viceCaptain, formation]);

  const createTrackingEntry = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/wildcard/track/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      if (data.success && data.code) {
        setCode(data.code);
        localStorage.setItem("wildcard_code", data.code);
      }
    } catch (error) {
      console.error("Failed to create tracking entry:", error);
    }
  };

  const loadSharedWildcard = async (wildcardCode: string) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/wildcard/${wildcardCode}/`);
      if (!response.ok) {
        throw new Error("Failed to load wildcard team");
      }
      
      const data = await response.json();
      if (data.success && data.squad_data) {
        setCode(wildcardCode);
        
        // Load the squad data
        const squad = data.squad_data;
        if (squad.players && Array.isArray(squad.players)) {
          // Separate players by position
          const gks = squad.players.filter((p: Player) => p.element_type === 1);
          const defs = squad.players.filter((p: Player) => p.element_type === 2);
          const mids = squad.players.filter((p: Player) => p.element_type === 3);
          const fwds = squad.players.filter((p: Player) => p.element_type === 4);
          
          setGoalkeepers(gks.slice(0, 2));
          setDefenders(defs.slice(0, 5));
          setMidfielders(mids.slice(0, 5));
          setForwards(fwds.slice(0, 3));
          
          // Handle bench - any remaining players
          const starting = gks.slice(0, 2).length + defs.slice(0, 5).length + mids.slice(0, 5).length + fwds.slice(0, 3).length;
          setBench(squad.players.slice(starting));
        }
        
        // Load formation if available
        if (squad.formation) {
          const loadedFormation = FORMATIONS.find(f => f.name === squad.formation);
          if (loadedFormation) setFormation(loadedFormation);
        }
        
        // Load captain/vice if available
        if (squad.captain) setCaptain(squad.captain);
        if (squad.viceCaptain) setViceCaptain(squad.viceCaptain);
        
        // Show a message that this is a shared team
        alert(`📋 Viewing shared wildcard: ${data.team_name || wildcardCode}\nTotal Cost: £${data.total_cost}m | Views: ${data.view_count || 1}`);
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
    };
    localStorage.setItem("wildcard_draft", JSON.stringify(data));
    setAutoSaveStatus("💾 Saved");
    setTimeout(() => setAutoSaveStatus(""), 2000);
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

  const saveToCloud = async () => {
    if (!code) {
      alert("No team code found. Please refresh the page.");
      return;
    }

    const allSelected = getAllSelectedPlayers();
    if (allSelected.length < 15) {
      alert("Please select all 15 players before saving!");
      return;
    }

    const teamName = prompt("Give your wildcard team a name (optional):");

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/wildcard/${code}/save/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          squad_data: {
            players: allSelected,
            formation: formation.name,
            captain,
            viceCaptain,
          },
          team_name: teamName || "",
        }),
      });

      const data = await response.json();
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

  const copyShareLink = () => {
    if (!code) return;
    const shareUrl = `${import.meta.env.VITE_API_URL}/wildcard/${code}/`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      alert("✅ Link copied to clipboard!");
    });
  };

  const shareAsImage = async () => {
    if (!teamDisplayRef.current) return;
    try {
      const canvas = await html2canvas(teamDisplayRef.current, {
        backgroundColor: "#050714",
        scale: 2,
        logging: false,
      });
      canvas.toBlob((blob) => {
        if (!blob) return;
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

  const shareOnTwitter = () => {
    if (!code) return;
    const shareUrl = `${import.meta.env.VITE_API_URL}/wildcard/${code}/`;
    const text = "Check out my FPL Wildcard team! 🔥⚽";
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
    window.open(twitterUrl, "_blank", "width=550,height=420");
  };

  const shareOnFacebook = () => {
    if (!code) return;
    const shareUrl = `${import.meta.env.VITE_API_URL}/wildcard/${code}/`;
    const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
    window.open(facebookUrl, "_blank", "width=550,height=420");
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
          <button className="secondary-btn" onClick={clearDraft}>
            🗑️ Clear Draft
          </button>
          <button 
            className="share-dream-team-btn" 
            onClick={saveToCloud}
            disabled={!isSquadComplete || budgetRemaining < 0}
          >
            💾 Save & Share
          </button>
        </div>
      </div>

      <div ref={teamDisplayRef} className="dream-team-capture">
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
                onRemove={() => {}}
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
                    onRemove={() => {}}
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
                    onRemove={() => {}}
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
                    onRemove={() => {}}
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
                onRemove={() => {}}
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
                  onRemove={() => {}}
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
              {`${import.meta.env.VITE_API_URL}/wildcard/${savedData.code}/`}
            </div>

            <div className="team-stats" style={{
              margin: "20px 0",
              padding: "20px",
              background: "rgba(255, 255, 255, 0.05)",
              borderRadius: "8px"
            }}>
              <p><strong>Total Cost:</strong> £{savedData.total_cost}m</p>
              <p><strong>Predicted Points:</strong> {savedData.predicted_points}</p>
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
              <button className="share-btn-modal facebook" onClick={shareOnFacebook} style={{
                padding: "10px 20px",
                borderRadius: "5px",
                border: "none",
                fontWeight: "bold",
                cursor: "pointer",
                fontSize: "0.95em",
                background: "#4267B2",
                color: "white"
              }}>
                📘 Facebook
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
    </div>
  );
}
