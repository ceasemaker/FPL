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
        </div>
      </div>
    </nav>
  );
}
