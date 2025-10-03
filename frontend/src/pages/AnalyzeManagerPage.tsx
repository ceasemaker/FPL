import { useState, useEffect } from "react";
import ManagerSummary from "../components/ManagerSummary";
import ManagerHistory from "../components/ManagerHistory";
import ManagerGameweek from "../components/ManagerGameweek";

export function AnalyzeManagerPage() {
  const [managerId, setManagerId] = useState<string>("");
  const [activeManagerId, setActiveManagerId] = useState<string | null>(null);
  const [view, setView] = useState<"history" | "gameweek">("gameweek");
  const [selectedGameweek, setSelectedGameweek] = useState<number | null>(null);

  // Load from sessionStorage on mount
  useEffect(() => {
    const savedManagerId = sessionStorage.getItem("fpl_manager_id");
    const savedView = sessionStorage.getItem("fpl_manager_view");
    const savedGameweek = sessionStorage.getItem("fpl_selected_gameweek");

    if (savedManagerId) {
      setManagerId(savedManagerId);
      setActiveManagerId(savedManagerId);
    }
    if (savedView === "history" || savedView === "gameweek") {
      setView(savedView);
    }
    if (savedGameweek) {
      setSelectedGameweek(Number(savedGameweek));
    }
  }, []);

  // Save to sessionStorage whenever state changes
  useEffect(() => {
    if (activeManagerId) {
      sessionStorage.setItem("fpl_manager_id", activeManagerId);
    }
  }, [activeManagerId]);

  useEffect(() => {
    sessionStorage.setItem("fpl_manager_view", view);
  }, [view]);

  useEffect(() => {
    if (selectedGameweek !== null) {
      sessionStorage.setItem("fpl_selected_gameweek", String(selectedGameweek));
    }
  }, [selectedGameweek]);

  const handleAnalyze = () => {
    if (managerId.trim()) {
      setActiveManagerId(managerId.trim());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleAnalyze();
    }
  };

  return (
    <div className="page">
      <div className="analyze-manager-container">
        {/* Header Section */}
        <div className="analyze-header">
          <h1 className="analyze-title">Analyze Manager</h1>
          <p className="analyze-subtitle">
            Enter a manager ID to view detailed team analysis, history, and performance
          </p>
        </div>

        {/* Input Section */}
        <div className="analyze-input-section">
          <div className="manager-id-input-wrapper">
            <input
              type="text"
              className="manager-id-input"
              placeholder="Enter Manager ID (e.g., 123456)"
              value={managerId}
              onChange={(e) => setManagerId(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            <button className="analyze-button" onClick={handleAnalyze}>
              Analyze
            </button>
          </div>
          <p className="input-hint">
            💡 Find your manager ID in your FPL profile URL: fantasy.premierleague.com/entry/<strong>YOUR_ID</strong>/
          </p>
        </div>

        {/* Content Section */}
        {activeManagerId && (
          <>
            {/* View Toggle */}
            <div className="view-toggle">
              <button
                className={`toggle-button ${view === "history" ? "active" : ""}`}
                onClick={() => setView("history")}
              >
                📊 Season History
              </button>
              <button
                className={`toggle-button ${view === "gameweek" ? "active" : ""}`}
                onClick={() => setView("gameweek")}
              >
                ⚽ Gameweek Team
              </button>
            </div>

            {/* Main Content Grid */}
            <div className="analyze-content-grid">
              {/* Left: Main Content */}
              <div className="analyze-main-content">
                {view === "history" ? (
                  <ManagerHistory managerId={activeManagerId} />
                ) : (
                  <ManagerGameweek
                    managerId={activeManagerId}
                    selectedGameweek={selectedGameweek}
                    onGameweekChange={setSelectedGameweek}
                  />
                )}
              </div>

              {/* Right: Manager Summary Sidebar */}
              <div className="analyze-sidebar">
                <ManagerSummary managerId={activeManagerId} />
              </div>
            </div>
          </>
        )}

        {/* Empty State */}
        {!activeManagerId && (
          <div className="analyze-empty-state">
            <div className="empty-state-icon">🔍</div>
            <h3>Ready to Analyze</h3>
            <p>Enter a manager ID above to get started with detailed team analysis</p>
          </div>
        )}
      </div>
    </div>
  );
}
