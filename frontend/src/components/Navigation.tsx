import { Link, useLocation } from "react-router-dom";

export function Navigation() {
  const location = useLocation();

  return (
    <nav className="main-nav">
      <div className="beta-badge">BETA</div>
      <nav className="nav-container">
        <div className="nav-content">
          <a href="/" className="nav-logo">
            AeroFPL
          </a>
          <div className="nav-links">
          <Link
            to="/"
            className={location.pathname === "/" ? "nav-link active" : "nav-link"}
          >
            Home
          </Link>
          <Link
            to="/players"
            className={location.pathname === "/players" ? "nav-link active" : "nav-link"}
          >
            Players
          </Link>
          <Link
            to="/dream-team"
            className={location.pathname === "/dream-team" ? "nav-link active" : "nav-link"}
          >
            Dream Team
          </Link>
          <Link
            to="/optimize"
            className={location.pathname === "/optimize" ? "nav-link active" : "nav-link"}
          >
            Optimizer
          </Link>
          <Link
            to="/transfer-planner"
            className={location.pathname === "/transfer-planner" ? "nav-link active" : "nav-link"}
          >
            Transfer Planner
          </Link>
          <Link
            to="/fixture-ticker"
            className={location.pathname === "/fixture-ticker" ? "nav-link active" : "nav-link"}
          >
            Fixture Ticker
          </Link>
          <Link
            to="/price-predictor"
            className={location.pathname === "/price-predictor" ? "nav-link active" : "nav-link"}
          >
            Price Predictor
          </Link>
          <Link
            to="/league-analytics"
            className={location.pathname === "/league-analytics" ? "nav-link active" : "nav-link"}
          >
            League Analytics
          </Link>
          <Link
            to="/analyze"
            className={location.pathname === "/analyze" ? "nav-link active" : "nav-link"}
          >
            Analyze Manager
          </Link>
          <Link
            to="/wildcard"
            className={location.pathname === "/wildcard" ? "nav-link active" : "nav-link"}
            title="Build and share your perfect wildcard team. Auto-saves every 30s. Get a shareable link to compare teams with friends!"
          >
            Wildcard Simulator ⚡
          </Link>
        </div>
      </div>
    </nav>
    </nav>
  );
}
