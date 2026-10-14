// Stats Explorer view state lives in the URL so any view can be shared by
// link. Only non-default values are written, which keeps links short.
import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { Norm, Position, Scope } from "./explorerModel";

export type Tab = "players" | "teams";
export type ClubFilter = "all" | "only" | "exclude";
export type Window = "season" | "l6" | "l3";

export interface ExplorerState {
  tab: Tab;
  lens: string;
  scope: Scope;
  club: ClubFilter;
  window: Window;
  norm: Norm;
  minMinutes: number;
  position: Position | "ALL";
  maxPrice: number | null;
  query: string;
  extra: string[]; // columns added on top of the lens
  sort: string | null;
  dir: "asc" | "desc";
  watchOnly: boolean;
}

export const DEFAULT_STATE: ExplorerState = {
  tab: "players",
  lens: "attacking",
  scope: "pl",
  club: "all",
  window: "season",
  norm: "p90",
  minMinutes: 270,
  position: "ALL",
  maxPrice: null,
  query: "",
  extra: [],
  sort: null,
  dir: "desc",
  watchOnly: false,
};

const KEYS: Record<keyof ExplorerState, string> = {
  tab: "tab",
  lens: "lens",
  scope: "from",
  club: "ucl",
  window: "window",
  norm: "per",
  minMinutes: "min",
  position: "pos",
  maxPrice: "max",
  query: "q",
  extra: "cols",
  sort: "sort",
  dir: "dir",
  watchOnly: "watch",
};

function parse(params: URLSearchParams): ExplorerState {
  const get = (key: keyof ExplorerState) => params.get(KEYS[key]);
  const min = Number(get("minMinutes"));
  const max = Number(get("maxPrice"));
  return {
    tab: get("tab") === "teams" ? "teams" : "players",
    lens: get("lens") ?? DEFAULT_STATE.lens,
    scope: get("scope") === "all" ? "all" : "pl",
    club: (["only", "exclude"].includes(get("club") ?? "") ? get("club") : "all") as ClubFilter,
    window: (["l6", "l3"].includes(get("window") ?? "") ? get("window") : "season") as Window,
    norm: get("norm") === "total" ? "total" : "p90",
    minMinutes: Number.isFinite(min) && get("minMinutes") !== null ? Math.max(0, min) : DEFAULT_STATE.minMinutes,
    position: (["GKP", "DEF", "MID", "FWD"].includes(get("position") ?? "") ? get("position") : "ALL") as Position | "ALL",
    maxPrice: get("maxPrice") !== null && Number.isFinite(max) && max > 0 ? max : null,
    query: get("query") ?? "",
    extra: (get("extra") ?? "").split(",").filter(Boolean),
    sort: get("sort"),
    dir: get("dir") === "asc" ? "asc" : "desc",
    watchOnly: get("watchOnly") === "1",
  };
}

function serialise(state: ExplorerState): URLSearchParams {
  const params = new URLSearchParams();
  (Object.keys(KEYS) as (keyof ExplorerState)[]).forEach((key) => {
    const value = state[key];
    const fallback = DEFAULT_STATE[key];
    if (JSON.stringify(value) === JSON.stringify(fallback)) return;
    if (Array.isArray(value)) params.set(KEYS[key], value.join(","));
    else if (typeof value === "boolean") params.set(KEYS[key], value ? "1" : "0");
    else if (value !== null) params.set(KEYS[key], String(value));
  });
  return params;
}

const PLAYER_KEY = "player";

export function useExplorerState() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const pushedProfile = useRef(false);
  const state = useMemo(() => parse(params), [params]);
  const player = Number(params.get(PLAYER_KEY)) || null;
  useEffect(() => {
    // Closed by the Back gesture: nothing left to pop.
    if (!player) pushedProfile.current = false;
  }, [player]);

  const update = useCallback(
    (patch: Partial<ExplorerState>) => {
      const next = serialise({ ...parse(params), ...patch });
      const open = params.get(PLAYER_KEY);
      if (open) next.set(PLAYER_KEY, open);
      setParams(next, { replace: true });
    },
    [params, setParams],
  );
  const reset = useCallback(() => setParams(new URLSearchParams(), { replace: true }), [setParams]);

  // Opening a profile pushes a history entry, so the phone's Back closes it
  // and a copied link opens straight to that player.
  const openPlayer = useCallback(
    (id: number) => {
      const next = new URLSearchParams(params);
      next.set(PLAYER_KEY, String(id));
      pushedProfile.current = !params.get(PLAYER_KEY);
      setParams(next, { replace: Boolean(params.get(PLAYER_KEY)) });
    },
    [params, setParams],
  );
  const closePlayer = useCallback(() => {
    if (pushedProfile.current) {
      pushedProfile.current = false;
      navigate(-1);
      return;
    }
    const next = new URLSearchParams(params);
    next.delete(PLAYER_KEY);
    setParams(next, { replace: true });
  }, [params, setParams, navigate]);

  return { state, update, reset, search: serialise(state).toString(), player, openPlayer, closePlayer };
}
