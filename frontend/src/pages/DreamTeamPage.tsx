import { useEffect, useState, useRef } from "react";
import { PlayerModal } from "../components/PlayerModal";
import html2canvas from "html2canvas";

const TEAM_BADGE_BASE = "https://resources.premierleague.com/premierleague25/badges-alt/";

interface Player {
  id: number;
  first_name: string;
  second_name: string;
  web_name: string;
  team: string | null;
  team_id: number | null;
  team_code: number | null;
  element_type: number;
  now_cost: number;
  total_points: number;
  form: number;
  avg_fdr: number;
  image_url: string | null;
  weighted_score: number;
}

interface DreamTeamData {
  starting_11: {
    goalkeeper: Player | null;
    defenders: Player[];
    midfielders: Player[];
    forwards: Player[];
  };
  bench: {
    goalkeeper: Player | null;
    defender: Player | null;
    midfielder: Player | null;
    forward: Player | null;
  };
  team_stats: {
    total_cost: number;
    total_points: number;
    avg_form: number;
    formation: string;
  };
}

function getTeamBadgeUrl(teamCode: number | null): string | null {
  if (!teamCode) return null;
  return `${TEAM_BADGE_BASE}${teamCode}.svg`;
}

function getDifficultyColor(difficulty: number | null): string {
  if (difficulty === null) return "#666";
  if (difficulty <= 1.5) return "#22c55e";
  if (difficulty <= 2.5) return "#84cc16";
  if (difficulty <= 3.5) return "#eab308";
  if (difficulty <= 4.5) return "#f97316";
  return "#ef4444";
}

function PlayerCard({ player, onClick }: { player: Player; onClick: () => void }) {
  return (
    <div className="dream-player-card" onClick={onClick}>
      <div className="dream-player-image">
        <img
          src={player.image_url || `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`}
          alt={player.web_name}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            if (target.src !== `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`) {
              target.onerror = null;
              target.src = `https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_${player.team_code}-110.webp`;
            }
          }}
        />
      </div>
      <div className="dream-player-name">{player.web_name}</div>
      <div className="dream-player-stats">
        <span className="dream-stat-badge">£{(player.now_cost / 10).toFixed(1)}m</span>
        <span className="dream-stat-badge">{player.total_points} pts</span>
        <span 
          className="dream-stat-badge fdr-badge"
          style={{ backgroundColor: getDifficultyColor(player.avg_fdr) }}
        >
          FDR {player.avg_fdr.toFixed(1)}
        </span>
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

export function DreamTeamPage() {
  const [dreamTeam, setDreamTeam] = useState<DreamTeamData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalPlayerId, setModalPlayerId] = useState<number | null>(null);
  const [isSharing, setIsSharing] = useState(false);
  const dreamTeamRef = useRef<HTMLDivElement>(null);

  // Helper function to convert images to base64 to bypass CORS
  const convertImagesToBase64 = async (container: HTMLElement) => {
    const images = container.querySelectorAll('img');
    const originalSources: Map<HTMLImageElement, string> = new Map();
    
    // Store original sources and convert to base64
    for (const img of Array.from(images)) {
      const originalSrc = img.src;
      originalSources.set(img, originalSrc);
      
      try {
        // Fetch the image and convert to base64
        const response = await fetch(originalSrc);
        const blob = await response.blob();
        const base64 = await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result as string);
          reader.readAsDataURL(blob);
        });
        
        // Replace with base64
        img.src = base64;
      } catch (error) {
        console.warn(`Failed to convert image: ${originalSrc}`, error);
        // Keep original if conversion fails
      }
    }
    
    return originalSources;
  };

  // Helper function to restore original image sources
  const restoreImageSources = (originalSources: Map<HTMLImageElement, string>) => {
    for (const [img, src] of originalSources.entries()) {
      img.src = src;
    }
  };

  const handleShare = async () => {
    if (!dreamTeamRef.current) return;
    
    setIsSharing(true);
    
    try {
      // Convert images to base64 to bypass CORS
      const originalSources = await convertImagesToBase64(dreamTeamRef.current);
      
      // Small delay to ensure images are loaded
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const canvas = await html2canvas(dreamTeamRef.current, {
        backgroundColor: "#050714",
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: true,
        foreignObjectRendering: false,
        imageTimeout: 15000,
      });
      
      // Restore original image sources
      restoreImageSources(originalSources);
      
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.download = `fpl-dream-team-${new Date().toISOString().split('T')[0]}.png`;
          link.href = url;
          link.click();
          URL.revokeObjectURL(url);
        }
        setIsSharing(false);
      });
    } catch (err) {
      console.error("Failed to generate image", err);
      alert("Failed to generate image. Please try again.");
      setIsSharing(false);
    }
  };

  useEffect(() => {
    fetch("/api/dream-team/", {
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const data: DreamTeamData = await response.json();
        setDreamTeam(data);
        setError(null);
      })
      .catch((err) => {
        console.error("Failed to load dream team", err);
        setError(err.message ?? "Unexpected error");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  if (error) {
    return (
      <div className="page">
        <div className="dream-team-error">
          <h2>Error loading dream team</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (isLoading || !dreamTeam) {
    return (
      <div className="page">
        <div className="dream-team-loading">Loading dream team...</div>
      </div>
    );
  }

  const { starting_11, bench, team_stats } = dreamTeam;

  return (
    <div className="page dream-team-page">
      <div className="dream-team-header">
        <h1>🏆 Dream Team</h1>
        <p className="dream-team-subtitle">
          Auto-selected based on proprietary analysis
        </p>
        <button 
          className="share-dream-team-btn"
          onClick={handleShare}
          disabled={isSharing}
        >
          {isSharing ? "Generating..." : "📸 Share Dream Team"}
        </button>
        <div className="dream-team-stats">
          <div className="dream-stat-item">
            <span className="dream-stat-label">Formation</span>
            <span className="dream-stat-value">{team_stats.formation}</span>
          </div>
          <div className="dream-stat-item">
            <span className="dream-stat-label">Total Cost</span>
            <span className="dream-stat-value">£{team_stats.total_cost.toFixed(1)}m</span>
          </div>
          <div className="dream-stat-item">
            <span className="dream-stat-label">Total Points</span>
            <span className="dream-stat-value">{team_stats.total_points}</span>
          </div>
          <div className="dream-stat-item">
            <span className="dream-stat-label">Avg Form</span>
            <span className="dream-stat-value">{team_stats.avg_form}</span>
          </div>
        </div>
      </div>

      <div ref={dreamTeamRef} className="dream-team-capture">
        <div className="football-field">
        {/* Goalkeeper */}
        <div className="field-row goalkeeper-row">
          {starting_11.goalkeeper && (
            <PlayerCard 
              player={starting_11.goalkeeper} 
              onClick={() => setModalPlayerId(starting_11.goalkeeper!.id)}
            />
          )}
        </div>

        {/* Defenders */}
        <div className="field-row defenders-row">
          {starting_11.defenders.map((player) => (
            <PlayerCard 
              key={player.id} 
              player={player}
              onClick={() => setModalPlayerId(player.id)}
            />
          ))}
        </div>

        {/* Midfielders */}
        <div className="field-row midfielders-row">
          {starting_11.midfielders.map((player) => (
            <PlayerCard 
              key={player.id} 
              player={player}
              onClick={() => setModalPlayerId(player.id)}
            />
          ))}
        </div>

        {/* Forwards */}
        <div className="field-row forwards-row">
          {starting_11.forwards.map((player) => (
            <PlayerCard 
              key={player.id} 
              player={player}
              onClick={() => setModalPlayerId(player.id)}
            />
          ))}
        </div>
      </div>

      {/* Bench */}
      <div className="bench-section">
        <h2>Bench</h2>
        <div className="bench-players">
          {bench.goalkeeper && (
            <PlayerCard 
              player={bench.goalkeeper}
              onClick={() => setModalPlayerId(bench.goalkeeper!.id)}
            />
          )}
          {bench.defender && (
            <PlayerCard 
              player={bench.defender}
              onClick={() => setModalPlayerId(bench.defender!.id)}
            />
          )}
          {bench.midfielder && (
            <PlayerCard 
              player={bench.midfielder}
              onClick={() => setModalPlayerId(bench.midfielder!.id)}
            />
          )}
          {bench.forward && (
            <PlayerCard 
              player={bench.forward}
              onClick={() => setModalPlayerId(bench.forward!.id)}
            />
          )}
        </div>
      </div>
      </div>

      {/* Player Detail Modal */}
      {modalPlayerId !== null && (
        <PlayerModal
          playerId={modalPlayerId}
          onClose={() => setModalPlayerId(null)}
        />
      )}
    </div>
  );
}
