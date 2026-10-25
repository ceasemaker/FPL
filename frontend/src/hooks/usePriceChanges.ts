import { useEffect, useState } from "react";

// FPL's own price-change tracker (/api/price-changes/), loaded once per page
// and shared by every table, card and profile; refreshed every 15 minutes,
// as FPL refreshes it.

export interface PriceProjection { offset: number; percent: number | null; likelihood: number | null }
export interface PriceChange {
  id: number;
  name: string;
  team: string | null;
  position: string;
  price: number;
  ownership: number | null;
  status: string | null;
  progress: number | null;
  predicted: number | null;
  likelihood: number | null;
  label: string;
  projections: PriceProjection[];
  hourlyRate: number | null;
  trend: "up" | "down" | "flat";
  lockedUntil: string | null;
  calibrating: boolean;
}
export interface PriceChangeData {
  meta: { deadlines: string[]; lastUpdated: string | null };
  players: PriceChange[];
  byId: Map<number, PriceChange>;
}

const REFRESH_MS = 15 * 60 * 1000;
let shared: { at: number; promise: Promise<PriceChangeData | null> } | null = null;

function load(): Promise<PriceChangeData | null> {
  if (shared && Date.now() - shared.at < REFRESH_MS) return shared.promise;
  const promise = fetch("/api/price-changes/")
    .then((r) => (r.ok ? r.json() : null))
    .then((p) => (p ? { ...p, byId: new Map((p.players as PriceChange[]).map((x) => [x.id, x])) } : null))
    .catch(() => null);
  shared = { at: Date.now(), promise };
  return promise;
}

export function usePriceChanges(): PriceChangeData | null {
  const [data, setData] = useState<PriceChangeData | null>(null);
  useEffect(() => {
    let alive = true;
    const run = () => load().then((d) => { if (alive) setData(d); });
    run();
    const timer = window.setInterval(() => { shared = null; run(); }, REFRESH_MS);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);
  return data;
}

export function usePriceChange(id: number | null | undefined): PriceChange | null {
  const data = usePriceChanges();
  return id == null ? null : data?.byId.get(id) ?? null;
}

// FPL's likelihood score -5..+5: 4 or more is likely, 5 very likely.
export function direction(change: PriceChange | null): "rise" | "drop" | "hold" {
  const l = change?.likelihood ?? 0;
  return l >= 4 ? "rise" : l <= -4 ? "drop" : "hold";
}
