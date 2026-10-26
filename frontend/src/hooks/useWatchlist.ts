import { useEffect, useState } from "react";

// The watchlist: FPL player ids in the order they were added, kept in this
// browser (the same key the Stats Explorer has always used). Every star and the
// Watchlist page share it and stay in step through a window event. With a sync
// code (the transfer planner's), it also lives on the server under that code:
// each change is pushed, and the code's copy is pulled once per visit.
const KEY = "aerofpl_stats_watchlist";
const EVENT = "aerofpl:watchlist";
export const SYNC_KEY = "aerofpl_planner_sync";

export function getSyncCode(): string | null {
  try { return localStorage.getItem(SYNC_KEY); } catch { return null; }
}

export function setSyncCode(code: string | null) {
  try { if (code) localStorage.setItem(SYNC_KEY, code); else localStorage.removeItem(SYNC_KEY); } catch { /* storage blocked */ }
}

export function readWatchlist(): number[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "number") : [];
  } catch {
    return [];
  }
}

let pushTimer: number | null = null;
export function pushWatchlist(ids: number[] = readWatchlist(), code: string | null = getSyncCode()) {
  if (!code) return;
  if (pushTimer) window.clearTimeout(pushTimer);
  pushTimer = window.setTimeout(() => {
    fetch(`/api/planner/sync/${code}/`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ watchlist: ids }) }).catch(() => undefined);
  }, 600);
}

let pulled = false;
let changedHere = false;  // a star tapped before the pull answers wins over it
function write(next: number[], push = true) {
  if (push) changedHere = true;
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private window: lasts this visit */ }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: next }));
  if (push) pushWatchlist(next);
}

// Joining a code from this device: keep both lists (the code's first), then save
// the merged list back. A code that has never held a watchlist takes this one.
export function mergeRemoteWatchlist(remote: number[] | null | undefined, code: string) {
  const local = readWatchlist();
  const merged = [...(remote ?? []), ...local.filter((id) => !(remote ?? []).includes(id))];
  pulled = true;  // this is the visit's pull; a later one could beat the push below
  write(merged, false);
  if (remote == null || merged.length !== remote.length) pushWatchlist(merged, code);
}

// Once per visit, take the code's copy as the truth (it holds removals made on
// other devices too). Before any device has sent one, send ours instead.
function pullOnce() {
  const code = getSyncCode();
  if (pulled || !code) return;
  pulled = true;
  fetch(`/api/planner/sync/${code}/`)
    .then((r) => (r.ok ? r.json() : null))
    .then((d: { watchlist: number[] | null } | null) => {
      if (!d || changedHere) return;
      if (d.watchlist == null) pushWatchlist(readWatchlist(), code);
      else if (JSON.stringify(d.watchlist) !== JSON.stringify(readWatchlist())) write(d.watchlist, false);
    })
    .catch(() => { pulled = false; });
}

export function useWatchlist(): { ids: number[]; has: (id: number) => boolean; toggle: (id: number) => boolean; remove: (id: number) => void } {
  const [ids, setIds] = useState<number[]>(readWatchlist);
  useEffect(() => {
    const sync = () => setIds(readWatchlist());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);  // other tabs
    pullOnce();
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
