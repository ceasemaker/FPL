import { useEffect, useState } from "react";

// Shared by the ready-made Chart Lab views (Changes, Hold-up, Clutch).

// Phone widths get the compact charts (larger text, no detail labels).
export function useNarrow(query = "(max-width: 600px)") {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const onChange = () => setNarrow(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  return narrow;
}

// GET a JSON payload; pass null to skip (e.g. while the view is hidden).
export function useFetch<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!url) return;
    let alive = true;
    setData(null);
    fetch(url)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<T>; })
      .then((p) => { if (alive) { setData(p); setError(null); } })
      .catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [url]);
  return { data, error };
}

export const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;

// How strongly two things move together, in words, for the takeaway lines.
export function strength(r: number): "barely" | "somewhat" | "clearly" {
  const size = Math.abs(r);
  return size < 0.2 ? "barely" : size < 0.4 ? "somewhat" : "clearly";
}
