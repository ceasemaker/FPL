import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

// Compare is reached from Players, and the optimiser now lives inside
// Decision Lab, so neither needs a top-level entry.
const links = [
  { to: "/", label: "Overview", icon: "⌂" },
  { to: "/decision-lab", label: "Decision Lab", icon: "▣" },
  { to: "/players", label: "Players", icon: "♙" },
  { to: "/fixtures", label: "Fixtures", icon: "▦" },
  { to: "/price-monitor", label: "Price Monitor", icon: "↗" },
  { to: "/analyze", label: "Analyze Manager", icon: "◇" },
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
        ☰
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
