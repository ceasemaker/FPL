import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  AnalyzeManagerIcon,
  ChartLabIcon,
  DecisionLabIcon,
  FixturesIcon,
  MenuIcon,
  ModelLabIcon,
  OverviewIcon,
  PlayersIcon,
  PriceMonitorIcon,
  StatsExplorerIcon,
} from "./navIcons";

// Compare is reached from Players, and the optimiser now lives inside
// Decision Lab, so neither needs a top-level entry.
const links = [
  { to: "/", label: "Overview", icon: <OverviewIcon /> },
  { to: "/decision-lab", label: "Decision Lab", icon: <DecisionLabIcon /> },
  { to: "/players", label: "Players", icon: <PlayersIcon /> },
  { to: "/stats", label: "Stats Explorer", icon: <StatsExplorerIcon /> },
  { to: "/chart-lab", label: "Chart Lab", icon: <ChartLabIcon /> },
  { to: "/model-lab", label: "Model Lab", icon: <ModelLabIcon /> },
  { to: "/fixtures", label: "Fixtures", icon: <FixturesIcon /> },
  { to: "/price-monitor", label: "Price Monitor", icon: <PriceMonitorIcon /> },
  { to: "/analyze", label: "Analyze Manager", icon: <AnalyzeManagerIcon /> },
];

export function Navigation() {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const isActive = (to: string) =>
    to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);

  return (
    <nav className="command-nav" aria-label="Primary navigation">
      <div className="command-brand"><span>Aero</span><strong>FPL</strong></div>
      <button
        className="command-menu-button"
        onClick={() => setOpen(!open)}
        aria-label="Toggle navigation"
        aria-expanded={open}
      >
        <MenuIcon />
      </button>
      <div className={`command-nav-links ${open ? "open" : ""}`}>
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className={isActive(link.to) ? "active" : ""}
            onClick={() => setOpen(false)}
          >
            <i aria-hidden="true">{link.icon}</i>
            <span>{link.label}</span>
          </Link>
        ))}
      </div>
      <div className="command-nav-footer">
        <p><b />Better decisions<br />Higher ranks</p>
      </div>
    </nav>
  );
}
