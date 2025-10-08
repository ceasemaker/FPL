import { Link, useLocation } from "react-router-dom";

export function Navigation() {
  const location = useLocation();

  return (
    <nav className="main-nav">
      <div className="beta-badge">BETA</div>
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          FPL Pulse
        </Link>
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
            to="/analyze"
            className={location.pathname === "/analyze" ? "nav-link active" : "nav-link"}
          >
            Analyze Manager
          </Link>
          <a
            href={`${import.meta.env.VITE_API_URL}/wildcard/`}
            className="nav-link wildcard-link"
            target="_blank"
            rel="noopener noreferrer"
            title="Build and share your perfect wildcard team. Auto-saves every 30s. Get a shareable link to compare teams with friends!"
          >
            Wildcard Simulator ⚡
          </a>
        </div>
      </div>
    </nav>
  );
}
