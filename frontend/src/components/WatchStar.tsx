import { track } from "@amplitude/unified";
import { useWatchlist } from "../hooks/useWatchlist";
import "./WatchStar.css";

// A star that adds a player to (or takes him off) the watchlist, anywhere he appears.
export function WatchStar({ id, name, size = 16 }: { id: number; name?: string; size?: number }) {
  const { has, toggle } = useWatchlist();
  const on = has(id);
  return (
    <button type="button" className={`watch-star${on ? " on" : ""}`} aria-pressed={on}
      aria-label={on ? `Remove ${name ?? "player"} from your watchlist` : `Add ${name ?? "player"} to your watchlist`}
      title={on ? "On your watchlist" : "Add to your watchlist"}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (toggle(id)) track("Player Watched"); }}>
      <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
        <path d="M10 2.8l2.1 4.4 4.8.6-3.5 3.3.9 4.8L10 13.6l-4.3 2.3.9-4.8-3.5-3.3 4.8-.6z" fill={on ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
