import { useState, useEffect } from "react";
import ManagerSummary from "../components/ManagerSummary";
import ManagerHistory from "../components/ManagerHistory";
import ManagerGameweek from "../components/ManagerGameweek";
import "./AnalyzeManagerPage.css";

export function AnalyzeManagerPage() {
  const [managerId, setManagerId] = useState<string>("");
  const [activeManagerId, setActiveManagerId] = useState<string | null>(null);
  const [view, setView] = useState<"history" | "gameweek">("gameweek");
  const [selectedGameweek, setSelectedGameweek] = useState<number | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const savedManagerId = localStorage.getItem("fpl_manager_id");
    const savedView = localStorage.getItem("fpl_manager_view");
    const savedGameweek = localStorage.getItem("fpl_selected_gameweek");

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

  // Save to localStorage whenever state changes
  useEffect(() => {
    if (activeManagerId) {
      localStorage.setItem("fpl_manager_id", activeManagerId);
    }
  }, [activeManagerId]);

  useEffect(() => {
    localStorage.setItem("fpl_manager_view", view);
  }, [view]);

  useEffect(() => {
    if (selectedGameweek !== null) {
      localStorage.setItem("fpl_selected_gameweek", String(selectedGameweek));
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
    <main className="aero-page analyze-page">
      <div className="aero-header">
        <div>
          <h1>Analyze Manager</h1>
          <p>
            Look up any FPL manager to review their season history, squad and
            gameweek performance.
          </p>
        </div>
      </div>

      <section className="aero-card analyze-lookup">
        <label className="aero-field analyze-lookup-field">
          <span>Manager ID</span>
          <input
            type="text"
            inputMode="numeric"
            className="aero-input"
            placeholder="e.g. 123456"
            value={managerId}
            onChange={(e) => setManagerId(e.target.value)}
            onKeyDown={handleKeyPress}
          />
        </label>
        <button className="aero-button primary" onClick={handleAnalyze} disabled={!managerId.trim()}>
          Analyze
        </button>
        <p className="analyze-hint">
          Your ID is the number in your FPL profile URL:
          {" "}fantasy.premierleague.com/entry/<strong>YOUR_ID</strong>/
        </p>
      </section>

      {activeManagerId && (
        <p className="aero-note analyze-data-note" role="status">
          <strong>What you are seeing:</strong> the selected manager’s official public FPL squad and scores. The gameweek selector controls the snapshot; the team panel labels whether it is current or historical and when it was loaded.
        </p>
      )}

      {activeManagerId ? (
        <>
          <div className="analyze-views" role="tablist" aria-label="Manager view">
            <button
              role="tab"
              aria-selected={view === "gameweek"}
              className={view === "gameweek" ? "active" : ""}
              onClick={() => setView("gameweek")}
            >
              Gameweek team
            </button>
            <button
              role="tab"
              aria-selected={view === "history"}
              className={view === "history" ? "active" : ""}
              onClick={() => setView("history")}
            >
              Season history
            </button>
          </div>

          <div className="analyze-content-grid">
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

            <aside className="analyze-sidebar">
              <ManagerSummary managerId={activeManagerId} />
            </aside>
          </div>
        </>
      ) : (
        <section className="aero-card analyze-empty">
          <h2>Ready when you are</h2>
          <p>Enter a manager ID above to pull their squad, chips and rank history.</p>
        </section>
      )}
    </main>
  );
}
