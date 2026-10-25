import type { SyntheticEvent } from "react";
import type { Kind } from "./matchModel";

// Match event icons on the 20px grid: drawn, not glyphs. Card colours are the
// real-world card colours; substitution arrows lime (on) and coral (off).

export function EventIcon({ kind, size = 16 }: { kind: Kind | "play" | "pause"; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 20 20", "aria-hidden": true as const, focusable: false as const };
  switch (kind) {
    case "goal":
      return (
        <svg {...common}>
          <circle cx="10" cy="10" r="8.25" fill="#fff" stroke="#101011" strokeWidth="1.5" />
          <path d="M10 6.2l3.1 2.3-1.2 3.6H8.1L6.9 8.5z" fill="#101011" />
          <path d="M10 6.2V2.4M13.1 8.5l3.6-1.2M11.9 12.1l2.2 3.1M8.1 12.1l-2.2 3.1M6.9 8.5L3.3 7.3" stroke="#101011" strokeWidth="1.2" fill="none" />
        </svg>
      );
    case "yellow":
      return <svg {...common}><rect x="5" y="2.5" width="10" height="15" rx="1.5" fill="#f5d64c" /></svg>;
    case "red":
      return <svg {...common}><rect x="5" y="2.5" width="10" height="15" rx="1.5" fill="#ff4c5e" /></svg>;
    case "second_yellow":
      return (
        <svg {...common}>
          <rect x="3" y="2.5" width="9" height="13.5" rx="1.5" fill="#f5d64c" />
          <rect x="8" y="4.5" width="9" height="13.5" rx="1.5" fill="#ff4c5e" stroke="#101011" strokeWidth="1" />
        </svg>
      );
    case "sub":
      return (
        <svg {...common} fill="none" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 15V5m0 0L3 8m3-3l3 3" stroke="#a5ff01" />
          <path d="M14 5v10m0 0l-3-3m3 3l3-3" stroke="#ff4c5e" />
        </svg>
      );
    case "var":
      return (
        <svg {...common} fill="none" stroke="#e2b75b" strokeWidth="1.4">
          <rect x="2.5" y="4.5" width="15" height="11" rx="2" />
          <path d="M6.5 8l1.8 4 1.8-4M11.7 12l1.3-4 1.3 4" />
        </svg>
      );
    case "play":
      return <svg {...common}><path d="M6 4l10 6-10 6z" fill="currentColor" /></svg>;
    case "pause":
      return <svg {...common}><path d="M5.5 4h3v12h-3zM11.5 4h3v12h-3z" fill="currentColor" /></svg>;
  }
}

export const crestUrl = (teamId: string) => `https://resources.premierleague.com/premierleague25/badges/${teamId}.svg`;

// The SVG set covers Premier League clubs only; cup and European opponents
// fall back to the older PNG set, and the image hides if that has none either.
export function Crest({ team, className, alt = "" }: { team: string; className?: string; alt?: string }) {
  const onError = (e: SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    if (!img.dataset.fallback) { img.dataset.fallback = "1"; img.src = `https://resources.premierleague.com/premierleague/badges/100/t${team}.png`; }
    else img.style.visibility = "hidden";
  };
  return <img className={className} src={crestUrl(team)} alt={alt} onError={onError} />;
}
