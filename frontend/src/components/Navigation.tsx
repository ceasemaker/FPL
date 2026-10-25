import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  AnalyzeManagerIcon,
  ChartLabIcon,
  DecisionLabIcon,
  MatchesIcon,
  MenuIcon,
  ModelLabIcon,
  OverviewIcon,
  PlayersIcon,
  PriceMonitorIcon,
  StatsExplorerIcon,
  TeamsIcon,
} from "./navIcons";

// Five sections for the game itself (Home, Matches, Teams, Players, Chart
// Lab), then the tools for your own FPL team, then the raw-data rooms.
// "match" lists other paths that belong to a section (the fixture planner
// lives under Matches; compare under Players).
const groups: { title?: string; links: { to: string; label: string; icon: JSX.Element; match?: string[] }[] }[] = [
  {
    links: [
      { to: "/", label: "Home", icon: <OverviewIcon /> },
      { to: "/matches", label: "Matches", icon: <MatchesIcon />, match: ["/fixtures"] },
      { to: "/teams", label: "Teams", icon: <TeamsIcon /> },
      { to: "/players", label: "Players", icon: <PlayersIcon />, match: ["/compare"] },
      { to: "/chart-lab", label: "Chart Lab", icon: <ChartLabIcon /> },
    ],
  },
  {
    title: "My FPL",
    links: [
      { to: "/decision-lab", label: "Decision Lab", icon: <DecisionLabIcon /> },
      { to: "/analyze", label: "Analyze Manager", icon: <AnalyzeManagerIcon /> },
      { to: "/price-monitor", label: "Price Monitor", icon: <PriceMonitorIcon /> },
    ],
  },
  {
    title: "Data rooms",
    links: [
      { to: "/stats", label: "Stats Explorer", icon: <StatsExplorerIcon /> },
      { to: "/model-lab", label: "Model Lab", icon: <ModelLabIcon /> },
    ],
  },
];

export function Navigation() {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const isActive = (to: string, match: string[] = []) =>
    to === "/" ? location.pathname === "/" : [to, ...match].some((p) => location.pathname === p || location.pathname.startsWith(`${p}/`));

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
        {groups.map((group, g) => (
          <div className={`command-nav-group${group.title ? " minor" : ""}`} key={g} role="group" aria-label={group.title ?? "Sections"}>
            {group.title && <p className="command-nav-title">{group.title}</p>}
            {group.links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={isActive(link.to, link.match) ? "active" : ""}
                aria-current={isActive(link.to, link.match) ? "page" : undefined}
                onClick={() => setOpen(false)}
              >
                <i aria-hidden="true">{link.icon}</i>
                <span>{link.label}</span>
              </Link>
            ))}
          </div>
        ))}
      </div>
      <div className="command-nav-footer">
        <p><b />Better decisions<br />Higher ranks</p>
      </div>
    </nav>
  );
}
