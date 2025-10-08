import { useState, useEffect, useRef } from "react";
import html2canvas from "html2canvas";

interface Player {
  id: number;
  name?: string;
  web_name?: string;
  team_name?: string;
  price?: number;
  position?: string;
}

interface WildcardTeam {
  players: Player[];
  formation: string | null;
  captain: number | null;
  viceCaptain: number | null;
}

export function WildcardSimulatorPage() {
  const [team, setTeam] = useState<WildcardTeam>({
    players: [],
    formation: null,
    captain: null,
    viceCaptain: null,
  });
  const [code, setCode] = useState<string | null>(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState<string>("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [savedData, setSavedData] = useState<any>(null);
  const teamDisplayRef = useRef<HTMLDivElement>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const storedDraft = localStorage.getItem("wildcard_draft");
    const storedCode = localStorage.getItem("wildcard_code");

    if (storedDraft) {
      try {
        const draft = JSON.parse(storedDraft);
        setTeam(draft.team || team);
      } catch (e) {
        console.error("Failed to load draft:", e);
      }
    }

    if (storedCode) {
      setCode(storedCode);
    } else {
      // Create tracking entry
      createTrackingEntry();
    }
  }, []);

  // Auto-save every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      autoSave();
    }, 30000);

    return () => clearInterval(interval);
  }, [team]);

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

  const autoSave = () => {
    const data = {
      version: 1,
      lastSaved: new Date().toISOString(),
      team,
    };
    localStorage.setItem("wildcard_draft", JSON.stringify(data));
    setAutoSaveStatus("💾 Saved");
    setTimeout(() => setAutoSaveStatus(""), 2000);
  };

  const saveToCloud = async () => {
    if (!code) {
      alert("No team code found. Please refresh the page.");
      return;
    }

    const teamName = prompt("Give your wildcard team a name (optional):");

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/wildcard/${code}/save/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          squad_data: {
            players: team.players,
            formation: team.formation,
            captain: team.captain,
            viceCaptain: team.viceCaptain,
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
    const shareUrl = `${window.location.origin}/wildcard/${code}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      alert("✅ Link copied to clipboard!");
    });
  };

  const shareAsImage = async () => {
    if (!teamDisplayRef.current) return;

    try {
      const canvas = await html2canvas(teamDisplayRef.current, {
        backgroundColor: "#37003c",
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
    const shareUrl = `${window.location.origin}/wildcard/${code}`;
    const text = "Check out my FPL Wildcard team! 🔥⚽";
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
    window.open(twitterUrl, "_blank", "width=550,height=420");
  };

  const shareOnFacebook = () => {
    if (!code) return;
    const shareUrl = `${window.location.origin}/wildcard/${code}`;
    const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
    window.open(facebookUrl, "_blank", "width=550,height=420");
  };

  const clearDraft = () => {
    if (confirm("Are you sure you want to clear your draft? This cannot be undone.")) {
      localStorage.removeItem("wildcard_draft");
      setTeam({
        players: [],
        formation: null,
        captain: null,
        viceCaptain: null,
      });
    }
  };

  return (
    <div className="page">
      <div className="wildcard-container">
        <header className="wildcard-header">
          <h1>⚽ Wildcard Simulator</h1>
          <p className="subtitle">Build and test your perfect wildcard team</p>
        </header>

        <div className="controls">
          <div className="autosave-indicator" style={{ opacity: autoSaveStatus ? 1 : 0 }}>
            {autoSaveStatus}
          </div>
          <div className="button-group">
            <button className="secondary-btn" onClick={clearDraft}>
              🗑️ Clear Draft
            </button>
            <button className="primary-btn" onClick={saveToCloud}>
              💾 Save & Share
            </button>
          </div>
        </div>

        <div className="team-display" ref={teamDisplayRef}>
          <div className="pitch">
            <div className="center-circle"></div>
            <div className="empty-team">
              <h3>🎯 Start Building Your Team</h3>
              <p>Your selections are automatically saved</p>
              <p>Click "Save & Share" when you're ready to get a shareable code</p>
              <p style={{ marginTop: "20px", fontSize: "0.9em", opacity: 0.7 }}>
                (Player selection UI coming soon - for now, this demonstrates the auto-save and sharing features)
              </p>
            </div>
          </div>
        </div>

        <div className="info-text">
          <p>💡 Your draft is saved automatically every 30 seconds</p>
          <p>Close this page and come back anytime - your team will be here!</p>
        </div>
      </div>

      {/* Success Modal */}
      {showSuccessModal && savedData && (
        <div className="modal-overlay" onClick={() => setShowSuccessModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>✅ Team Saved!</h2>
            <p>Your wildcard team has been saved and is ready to share!</p>

            <div className="code-box">
              <strong>Code:</strong> {savedData.code}
            </div>

            <div className="share-url">
              {`${import.meta.env.VITE_API_URL}/wildcard/${savedData.code}/`}
            </div>

            <div className="team-stats">
              <p>
                <strong>Total Cost:</strong> £{savedData.total_cost}m
              </p>
              <p>
                <strong>Predicted Points:</strong> {savedData.predicted_points}
              </p>
            </div>

            <h3 style={{ marginTop: "20px", marginBottom: "10px" }}>Share Your Team:</h3>

            <div className="share-buttons">
              <button className="share-btn copy" onClick={copyShareLink}>
                📋 Copy Link
              </button>
              <button className="share-btn image" onClick={shareAsImage}>
                📸 Download Image
              </button>
              <button className="share-btn twitter" onClick={shareOnTwitter}>
                🐦 Twitter
              </button>
              <button className="share-btn facebook" onClick={shareOnFacebook}>
                📘 Facebook
              </button>
            </div>

            <div className="modal-actions">
              <button onClick={() => setShowSuccessModal(false)}>Close</button>
            </div>

            <p className="note">💡 Your team is saved! Anyone with this link can view it.</p>
          </div>
        </div>
      )}

      <style>{`
        .wildcard-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .wildcard-header {
          text-align: center;
          margin-bottom: 40px;
        }

        .wildcard-header h1 {
          font-size: 2.5em;
          margin-bottom: 10px;
        }

        .wildcard-header .subtitle {
          color: var(--accent-cyan);
          font-size: 1.3em;
        }

        .controls {
          background: rgba(255, 255, 255, 0.05);
          padding: 20px;
          border-radius: 10px;
          margin-bottom: 30px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .autosave-indicator {
          color: var(--accent-cyan);
          transition: opacity 0.3s;
        }

        .button-group {
          display: flex;
          gap: 10px;
        }

        .primary-btn, .secondary-btn {
          padding: 12px 24px;
          border-radius: 8px;
          font-size: 1em;
          font-weight: bold;
          cursor: pointer;
          transition: transform 0.2s;
          border: none;
        }

        .primary-btn {
          background: var(--accent-cyan);
          color: var(--bg-primary);
        }

        .secondary-btn {
          background: rgba(255, 255, 255, 0.1);
          color: var(--text-primary);
        }

        .primary-btn:hover, .secondary-btn:hover {
          transform: scale(1.05);
        }

        .team-display {
          background: rgba(255, 255, 255, 0.05);
          padding: 30px;
          border-radius: 10px;
          min-height: 400px;
          margin-bottom: 30px;
        }

        .pitch {
          background: linear-gradient(90deg, #38003c 50%, #550044 50%);
          border-radius: 10px;
          padding: 40px;
          min-height: 500px;
          position: relative;
        }

        .center-circle {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 100px;
          height: 100px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-radius: 50%;
        }

        .empty-team {
          text-align: center;
          padding: 60px 20px;
          color: rgba(255, 255, 255, 0.8);
        }

        .empty-team h3 {
          font-size: 1.5em;
          margin-bottom: 10px;
        }

        .info-text {
          text-align: center;
          color: var(--text-muted);
        }

        .info-text p {
          margin: 10px 0;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2000;
        }

        .modal-content {
          background: var(--bg-secondary);
          color: var(--text-primary);
          padding: 40px;
          border-radius: 15px;
          max-width: 600px;
          max-height: 90vh;
          overflow-y: auto;
          text-align: center;
          border: 1px solid var(--border-glow);
        }

        .modal-content h2 {
          margin-bottom: 20px;
        }

        .code-box {
          background: rgba(0, 255, 135, 0.1);
          padding: 20px;
          margin: 20px 0;
          border-radius: 8px;
          font-size: 1.5em;
          font-weight: bold;
          color: var(--accent-cyan);
          border: 1px solid var(--accent-cyan);
        }

        .share-url {
          background: rgba(255, 255, 255, 0.05);
          padding: 15px;
          border-radius: 8px;
          word-break: break-all;
          font-family: monospace;
          font-size: 0.9em;
          margin: 15px 0;
          border: 2px solid var(--accent-cyan);
        }

        .team-stats {
          margin: 20px 0;
          padding: 20px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
        }

        .team-stats p {
          margin: 10px 0;
        }

        .share-buttons {
          display: flex;
          gap: 10px;
          justify-content: center;
          margin: 20px 0;
          flex-wrap: wrap;
        }

        .share-btn {
          padding: 10px 20px;
          border-radius: 5px;
          border: none;
          font-weight: bold;
          cursor: pointer;
          transition: transform 0.2s;
          font-size: 0.95em;
        }

        .share-btn:hover {
          transform: scale(1.05);
        }

        .share-btn.copy {
          background: var(--accent-cyan);
          color: var(--bg-primary);
        }

        .share-btn.image {
          background: var(--accent-purple);
          color: white;
        }

        .share-btn.twitter {
          background: #1da1f2;
          color: white;
        }

        .share-btn.facebook {
          background: #4267B2;
          color: white;
        }

        .modal-actions {
          margin-top: 20px;
        }

        .modal-actions button {
          background: rgba(255, 255, 255, 0.1);
          color: var(--text-primary);
          padding: 12px 30px;
          border-radius: 8px;
          border: none;
          cursor: pointer;
          font-size: 1em;
        }

        .note {
          margin-top: 20px;
          font-size: 0.9em;
          color: var(--text-muted);
        }
      `}</style>
    </div>
  );
}
