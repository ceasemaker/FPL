import { useEffect, useState } from "react";

// The watchlist: FPL player ids in the order they were added, kept in this
// browser (the same key the Stats Explorer has always used). Every star and the
// Watchlist page share it and stay in step through a window event.
const KEY = "aerofpl_stats_watchlist";
const EVENT = "aerofpl:watchlist";

export function readWatchlist(): number[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "number") : [];
  } catch {
    return [];
  }
}

function write(next: number[]) {
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private window: lasts this visit */ }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: next }));
}

export function useWatchlist(): { ids: number[]; has: (id: number) => boolean; toggle: (id: number) => boolean; remove: (id: number) => void } {
  const [ids, setIds] = useState<number[]>(readWatchlist);
  useEffect(() => {
    const sync = () => setIds(readWatchlist());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);  // other tabs
    return () => { window.removeEventListener(EVENT, sync); window.removeEventListener("storage", sync); };
  }, []);
  const toggle = (id: number) => {
    const cur = readWatchlist();
    const on = !cur.includes(id);
    write(on ? [...cur, id] : cur.filter((x) => x !== id));
    return on;
  };
  return { ids, has: (id) => ids.includes(id), toggle, remove: (id) => write(readWatchlist().filter((x) => x !== id)) };
}
