import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CHART_LAB_FORMULA,
  POSITION_NAMES,
  band,
  formatStat,
  isNormalised,
  minutesFor,
  ordinal,
  percentile,
  statValue,
  type ExplorerPayload,
  type ExplorerPlayer,
  type ExplorerTeam,
  type Position,
  type Stat,
  type TeamStatDef,
} from "../components/statsExplorer/explorerModel";
import {
  BookmarkIcon,
  ChartIcon,
  ChevronIcon,
  CloseIcon,
  ColumnsIcon,
  CompareIcon,
  InfoIcon,
  LinkIcon,
  SearchIcon,
  SlidersIcon,
  SortIcon,
  StarIcon,
} from "../components/statsExplorer/icons";
import { DEFAULT_STATE, useExplorerState, type ExplorerState } from "../components/statsExplorer/useExplorerState";
import "./StatsExplorerPage.css";

const SEASON = 2026;
const MAX_COMPARE = 4;
const WATCH_KEY = "aerofpl_stats_watchlist";
const VIEWS_KEY = "aerofpl_stats_views";
const CHART_LAB_KEY = "aerofpl_chart_lab_current";
const POSITIONS: (Position | "ALL")[] = ["ALL", "GKP", "DEF", "MID", "FWD"];

function readStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage blocked (private window): the feature still works for this visit.
  }
}

interface SavedView { name: string; search: string }

// ---------------------------------------------------------------- page

export function StatsExplorerPage() {
  const navigate = useNavigate();
  const { state, update, reset, search } = useExplorerState();
  const [data, setData] = useState<ExplorerPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [watchlist, setWatchlist] = useState<number[]>(() => readStorage(WATCH_KEY, []));
  const [views, setViews] = useState<SavedView[]>(() => readStorage(VIEWS_KEY, []));
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [menu, setMenu] = useState<"columns" | "views" | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/stats-explorer/?season=${SEASON}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<ExplorerPayload>;
      })
      .then((payload) => alive && setData(payload))
      .catch((err) => alive && setError(err instanceof Error ? err.message : String(err)));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(t);
  }, [toast]);

  const statsByKey = useMemo(() => new Map((data?.catalogue ?? []).map((s) => [s.key, s])), [data]);
  const uclTeams = useMemo(() => new Set(data?.uclTeamIds ?? []), [data]);
  const lens = data?.lenses[state.lens] ?? data?.lenses.attacking;

  const columns: Stat[] = useMemo(() => {
    if (!lens) return [];
    const keys = state.position === "GKP" && lens.keeperColumns ? lens.keeperColumns : lens.columns;
    const all = [...keys, ...state.extra.filter((k) => !keys.includes(k))];
    return all.map((k) => statsByKey.get(k)).filter((s): s is Stat => Boolean(s));
  }, [lens, state.position, state.extra, statsByKey]);

  // Percentile cohorts: same position, enough minutes in the chosen scope.
  // Club, price and search filters do not move the baseline.
  const cohorts = useMemo(() => {
    const map = new Map<string, Map<Position, number[]>>();
    if (!data) return map;
    for (const stat of data.catalogue) {
      const byPos = new Map<Position, number[]>();
      for (const player of data.players) {
        if (minutesFor(player, state.scope) < state.minMinutes) continue;
        const value = statValue(stat, player, state.scope, state.norm);
        if (value === null) continue;
        const list = byPos.get(player.position) ?? [];
        list.push(value);
        byPos.set(player.position, list);
      }
      map.set(stat.key, byPos);
    }
    return map;
  }, [data, state.scope, state.norm, state.minMinutes]);

  const pctOf = (stat: Stat, player: ExplorerPlayer, value: number | null) =>
    percentile(value, cohorts.get(stat.key)?.get(player.position) ?? [], stat.lowerIsBetter);

  const sortKey = state.sort && (statsByKey.has(state.sort) || state.sort === "name" || state.sort === "minutes")
    ? state.sort
    : columns[0]?.key ?? "name";

  const rows = useMemo(() => {
    if (!data) return [];
    const q = state.query.trim().toLowerCase();
    const filtered = data.players.filter((p) => {
      if (minutesFor(p, state.scope) < state.minMinutes) return false;
      if (state.position !== "ALL" && p.position !== state.position) return false;
      const inUcl = p.teamId !== null && uclTeams.has(p.teamId);
      if (state.club === "only" && !inUcl) return false;
      if (state.club === "exclude" && inUcl) return false;
      if (state.maxPrice !== null && (p.fpl.fpl_price ?? 0) > state.maxPrice) return false;
      if (state.watchOnly && !watchlist.includes(p.id)) return false;
      if (q && !p.name.toLowerCase().includes(q) && !(p.team ?? "").toLowerCase().includes(q)) return false;
      return true;
    });
    const stat = statsByKey.get(sortKey);
    const valueOf = (p: ExplorerPlayer): number | string | null => {
      if (sortKey === "name") return p.name;
      if (sortKey === "minutes") return minutesFor(p, state.scope);
      return stat ? statValue(stat, p, state.scope, state.norm) : null;
    };
    const dir = state.sort ? state.dir : (sortKey === "name" ? "asc" : "desc");
    return filtered.sort((a, b) => {
      const va = valueOf(a);
      const vb = valueOf(b);
      if (va === null) return 1;
      if (vb === null) return -1;
      const cmp = typeof va === "string" ? va.localeCompare(vb as string) : (va as number) - (vb as number);
      return dir === "asc" ? cmp : -cmp;
    });
  }, [data, state, uclTeams, watchlist, statsByKey, sortKey]);

  const activeFilters = [
    state.scope !== DEFAULT_STATE.scope,
    state.club !== DEFAULT_STATE.club,
    state.norm !== DEFAULT_STATE.norm,
    state.minMinutes !== DEFAULT_STATE.minMinutes,
    state.position !== DEFAULT_STATE.position,
    state.maxPrice !== null,
    state.watchOnly,
  ].filter(Boolean).length;

  const toggleWatch = (id: number) => {
    const next = watchlist.includes(id) ? watchlist.filter((w) => w !== id) : [...watchlist, id];
    setWatchlist(next);
    writeStorage(WATCH_KEY, next);
  };
  const toggleSelect = (id: number) => {
    setSelected((cur) => (cur.includes(id) ? cur.filter((s) => s !== id) : cur.length >= MAX_COMPARE ? cur : [...cur, id]));
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setToast("Link copied: anyone with it sees this exact view.");
    } catch {
      setToast("Couldn't copy automatically. Copy the address bar instead.");
    }
  };

  const saveView = (name: string) => {
    const next = [{ name, search }, ...views.filter((v) => v.name !== name)].slice(0, 12);
    setViews(next);
    writeStorage(VIEWS_KEY, next);
    setToast(`Saved "${name}" in this browser.`);
  };

  const chartable = columns.filter((c) => CHART_LAB_FORMULA[c.key]);
  const sendToChartLab = () => {
    const [x, y] = chartable;
    if (!x || !y) return;
    const norm = state.norm === "p90" ? "p90" : "total";
    writeStorage(CHART_LAB_KEY, {
      mode: "scatter",
      x: CHART_LAB_FORMULA[x.key][norm],
      y: CHART_LAB_FORMULA[y.key][norm],
      formula: CHART_LAB_FORMULA[x.key][norm],
      position: state.position,
      minMinutes: state.minMinutes,
      selected,
    });
    navigate("/chart-lab");
  };

  const drawerPlayer = data?.players.find((p) => p.id === drawerId) ?? null;
  const lensEntries = Object.entries(data?.lenses ?? {});

  return (
    <main className="aero-page sx-page">
      <header className="sx-head">
        <div className="sx-title">
          <h1>Stats Explorer</h1>
          <p>
            {data
              ? `${data.seasonLabel} season to gameweek ${data.latestGameweek} · Opta stats from the Premier League, FPL prices and ownership`
              : "Loading this season's stats…"}
          </p>
        </div>
        <div className="sx-head-actions">
          <div className="sx-tabs" role="tablist" aria-label="Explore">
            {(["players", "teams"] as const).map((tab) => (
              <button key={tab} role="tab" aria-selected={state.tab === tab}
                className={state.tab === tab ? "active" : ""}
                onClick={() => update({ tab, sort: null })}>
                {tab === "players" ? "Players" : "Teams"}
              </button>
            ))}
          </div>
          <MenuButton label="Views" icon={<BookmarkIcon />} open={menu === "views"} onToggle={() => setMenu(menu === "views" ? null : "views")}>
            <ViewsMenu views={views} onApply={(v) => { navigate(`/stats?${v.search}`); setMenu(null); }}
              onSave={saveView}
              onDelete={(name) => { const next = views.filter((v) => v.name !== name); setViews(next); writeStorage(VIEWS_KEY, next); }} />
          </MenuButton>
          <button className="sx-btn" onClick={copyLink}><LinkIcon /> <span>Copy link</span></button>
        </div>
      </header>

      <section className="sx-bar" aria-label="View controls">
        <div className="sx-bar-top">
          {state.tab === "players" && (
            <div className="sx-lenses" role="group" aria-label="Lens">
              {lensEntries.map(([key, l]) => (
                <button key={key} aria-pressed={state.lens === key} className={state.lens === key ? "active" : ""}
                  onClick={() => update({ lens: key, sort: null })}>
                  {l.label}
                </button>
              ))}
            </div>
          )}
          <div className="sx-controls-end">
            {state.tab === "players" && (
              <label className="sx-field inline sx-field-narrow">
                <span className="sx-legend">Max £</span>
                <input className="aero-input" type="number" min={4} step={0.5} inputMode="decimal" placeholder="Any"
                  value={state.maxPrice ?? ""} onChange={(e) => update({ maxPrice: e.target.value ? Number(e.target.value) : null })} />
              </label>
            )}
            {state.tab === "players" && (
              <button className={`sx-btn${state.watchOnly ? " on" : ""}`} aria-pressed={state.watchOnly}
                onClick={() => update({ watchOnly: !state.watchOnly })}>
                <StarIcon filled={state.watchOnly} /> <span>Watchlist</span>
              </button>
            )}
            <label className="sx-search">
              <SearchIcon size={16} />
              <span className="sr-only">Search players or clubs</span>
              <input value={state.query} placeholder={state.tab === "players" ? "Player or club" : "Club"}
                onChange={(e) => update({ query: e.target.value })} />
            </label>
            {state.tab === "players" && data && (
              <MenuButton label="Columns" icon={<ColumnsIcon />} open={menu === "columns"} onToggle={() => setMenu(menu === "columns" ? null : "columns")}>
                <ColumnsMenu catalogue={data.catalogue} lensKeys={columns.map((c) => c.key).filter((k) => !state.extra.includes(k))}
                  extra={state.extra} onChange={(extra) => update({ extra })} />
              </MenuButton>
            )}
          </div>
        </div>
        <div className="sx-bar-filters">
          <Controls state={state} update={update} tab={state.tab} uclRule={data?.uclClubRule} compact />
        </div>
      </section>

      {state.tab === "players" && (
        <p className="sx-key" aria-hidden="true">
          <span><i className="b4" /> Top 20%</span>
          <span><i className="b3" /> 20–40%</span>
          <span><i className="b2" /> 40–60%</span>
          <span className="sx-key-note">
            <span className="sx-wide-only">Shading is the percentile among players in the same position. Hover or focus a cell for the exact rank.</span>
            <span className="sx-phone-only">Percentile within position{state.norm === "p90" ? " · per 90" : ""}. Tap a player for details.</span>
          </span>
        </p>
      )}

      <div className="sx-phonebar">
        <button className="sx-btn" onClick={() => setSheetOpen(true)} aria-haspopup="dialog">
          <SlidersIcon /> <span>Filters{activeFilters ? ` (${activeFilters})` : ""}</span>
        </button>
        <label className="sx-search">
          <SearchIcon size={16} />
          <span className="sr-only">Search players or clubs</span>
          <input value={state.query} placeholder="Search" onChange={(e) => update({ query: e.target.value })} />
        </label>
      </div>

      {error && (
        <div className="sx-state" role="alert">
          <h2>Couldn't load the stats</h2>
          <p>The server didn't answer ({error}). Try again in a moment; your view is kept in the link.</p>
          <button className="sx-btn" onClick={() => window.location.reload()}>Try again</button>
        </div>
      )}

      {!error && !data && <SkeletonTable />}

      {data && state.tab === "players" && (
        <PlayerTable
          rows={rows}
          columns={columns}
          state={state}
          sortKey={sortKey}
          uclTeams={uclTeams}
          selected={selected}
          watchlist={watchlist}
          pctOf={pctOf}
          onSort={(key) => update({ sort: key, dir: sortKey === key && state.dir === "desc" ? "asc" : "desc" })}
          onOpen={setDrawerId}
          onSelect={toggleSelect}
          onWatch={toggleWatch}
          onReset={reset}
        />
      )}

      {data && state.tab === "teams" && (
        <TeamTable teams={data.teams} catalogue={data.teamCatalogue} state={state}
          onSort={(key) => update({ sort: key, dir: state.sort === key && state.dir === "desc" ? "asc" : "desc" })} />
      )}

      {selected.length > 0 && data && (
        <div className="sx-tray" role="region" aria-label="Selected players">
          <div className="sx-tray-chips">
            {selected.map((id) => {
              const p = data.players.find((pl) => pl.id === id);
              return (
                <span key={id} className="sx-chip">
                  {p?.name ?? id}
                  <button aria-label={`Remove ${p?.name ?? id}`} onClick={() => toggleSelect(id)}><CloseIcon size={14} /></button>
                </span>
              );
            })}
            <span className="sx-tray-count">{selected.length}/{MAX_COMPARE}</span>
          </div>
          <div className="sx-tray-actions">
            <button className="sx-btn" onClick={() => setSelected([])}>Clear</button>
            <button className="sx-btn" onClick={sendToChartLab} disabled={chartable.length < 2}
              title={chartable.length < 2 ? "Chart Lab doesn't have this lens's stats yet" : `Scatter ${chartable[0]?.label} against ${chartable[1]?.label}`}>
              <ChartIcon /> <span>Chart Lab</span>
            </button>
            <button className="aero-button primary" disabled={selected.length < 2}
              onClick={() => navigate(`/compare?ids=${selected.join(",")}`)}>
              <CompareIcon /> Compare {selected.length > 1 ? selected.length : ""}
            </button>
          </div>
        </div>
      )}

      {drawerPlayer && data && (
        <PlayerDrawer
          player={drawerPlayer}
          data={data}
          state={state}
          lensKeys={columns.map((c) => c.key)}
          pctOf={pctOf}
          inUcl={drawerPlayer.teamId !== null && uclTeams.has(drawerPlayer.teamId)}
          watched={watchlist.includes(drawerPlayer.id)}
          selected={selected.includes(drawerPlayer.id)}
          canSelect={selected.length < MAX_COMPARE}
          onWatch={() => toggleWatch(drawerPlayer.id)}
          onSelect={() => toggleSelect(drawerPlayer.id)}
          onClose={() => setDrawerId(null)}
        />
      )}

      <FilterSheet open={sheetOpen} onClose={() => setSheetOpen(false)} activeFilters={activeFilters} onReset={reset}>
        <Controls state={state} update={update} tab={state.tab} stacked uclRule={data?.uclClubRule} />
      </FilterSheet>

      {toast && <div className="sx-toast" role="status">{toast}</div>}
    </main>
  );
}

// ------------------------------------------------------------ controls

function Segmented<T extends string>({ label, value, options, onChange, disabled, compact, hideLabel }: {
  label: string;
  value: T;
  options: { value: T; label: string; disabled?: string; title?: string }[];
  onChange: (v: T) => void;
  disabled?: string;
  compact?: boolean;
  hideLabel?: boolean;
}) {
  return (
    <fieldset className={`sx-field${compact ? " inline" : ""}`} disabled={Boolean(disabled)} title={disabled}>
      <legend className={compact ? "sr-only" : undefined}>{label}</legend>
      {compact && !hideLabel && <span className="sx-legend" aria-hidden="true">{label}</span>}
      <div className="sx-seg">
        {options.map((o) => (
          <button key={o.value} type="button" aria-pressed={value === o.value}
            className={value === o.value ? "active" : ""}
            disabled={Boolean(o.disabled)} title={o.disabled ?? o.title}
            onClick={() => onChange(o.value)}>
            {o.label}
            {o.disabled && <span className="sx-soon">soon</span>}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function Controls({ state, update, tab, stacked, compact, uclRule }: {
  state: ExplorerState;
  update: (patch: Partial<ExplorerState>) => void;
  tab: ExplorerState["tab"];
  stacked?: boolean;
  compact?: boolean;
  uclRule?: string;
}) {
  const perLabel = tab === "teams" ? "Per match" : "Per 90";
  const field = `sx-field${compact ? " inline" : ""}`;
  return (
    <div className={`sx-control-row${stacked ? " stacked" : ""}`}>
      <Segmented label="Stats from" value={state.scope} compact={compact}
        options={compact
          ? [{ value: "pl", label: "PL", title: "Premier League only" }, { value: "all", label: "PL + UCL", title: "Premier League plus Champions League" }]
          : [{ value: "pl", label: "Premier League" }, { value: "all", label: "PL + Champions League" }]}
        onChange={(scope) => update({ scope })}
        disabled={tab === "teams" ? "Champions League club stats aren't loaded yet; Teams shows the Premier League only." : undefined} />
      <label className={field} title={uclRule ? `Counts as a Champions League club: ${uclRule}` : undefined}>
        <span className="sx-legend">{compact ? "UCL clubs" : "Champions League clubs"}</span>
        <select className="aero-select" value={state.club} onChange={(e) => update({ club: e.target.value as ExplorerState["club"] })}>
          <option value="all">Include</option>
          <option value="only">Only these</option>
          <option value="exclude">Exclude</option>
        </select>
      </label>
      <Segmented label="Window" value={state.window} compact={compact} hideLabel
        options={[
          { value: "season", label: "Season" },
          { value: "l6", label: "Last 6", disabled: "Needs per-match stats, coming next" },
          { value: "l3", label: "Last 3", disabled: "Needs per-match stats, coming next" },
        ]}
        onChange={(window) => update({ window })} />
      <Segmented label="Show" value={state.norm} compact={compact} hideLabel
        options={[{ value: "p90", label: perLabel }, { value: "total", label: "Totals" }]}
        onChange={(norm) => update({ norm })} />
      {tab === "players" && (
        <>
          <label className={field}>
            <span className="sx-legend">Position</span>
            <select className="aero-select" value={state.position} onChange={(e) => update({ position: e.target.value as ExplorerState["position"], sort: null })}>
              {POSITIONS.map((p) => <option key={p} value={p}>{p === "ALL" ? "All" : p}</option>)}
            </select>
          </label>
          <label className={`${field} sx-field-narrow`}>
            <span className="sx-legend">Min minutes</span>
            <input className="aero-input" type="number" min={0} step={90} inputMode="numeric" value={state.minMinutes}
              onChange={(e) => update({ minMinutes: Math.max(0, Number(e.target.value) || 0) })} />
          </label>
          {!compact && <label className={`${field} sx-field-narrow`}>
            <span className="sx-legend">Max £</span>
            <input className="aero-input" type="number" min={4} step={0.5} inputMode="decimal" placeholder="Any"
              value={state.maxPrice ?? ""} onChange={(e) => update({ maxPrice: e.target.value ? Number(e.target.value) : null })} />
          </label>}
          {!compact && (
            <label className="sx-check">
              <input type="checkbox" checked={state.watchOnly} onChange={(e) => update({ watchOnly: e.target.checked })} />
              Watchlist only
            </label>
          )}
        </>
      )}
    </div>
  );
}

function MenuButton({ label, icon, open, onToggle, children }: {
  label: string; icon: React.ReactNode; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onToggle(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onToggle(); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open, onToggle]);
  return (
    <div className="sx-menu" ref={ref}>
      <button className="sx-btn" aria-expanded={open} aria-haspopup="true" onClick={onToggle}>{icon} <span>{label}</span></button>
      {open && <div className="sx-menu-panel">{children}</div>}
    </div>
  );
}

function ViewsMenu({ views, onApply, onSave, onDelete }: {
  views: SavedView[]; onApply: (v: SavedView) => void; onSave: (name: string) => void; onDelete: (name: string) => void;
}) {
  const [name, setName] = useState("");
  return (
    <div className="sx-views">
      <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) { onSave(name.trim()); setName(""); } }}>
        <label className="sx-legend" htmlFor="sx-view-name">Save this view</label>
        <div className="sx-inline">
          <input id="sx-view-name" className="aero-input" value={name} placeholder="e.g. Cheap mids, no UCL" onChange={(e) => setName(e.target.value)} />
          <button className="aero-button primary" type="submit" disabled={!name.trim()}>Save</button>
        </div>
      </form>
      {views.length ? (
        <ul>
          {views.map((v) => (
            <li key={v.name}>
              <button className="sx-view" onClick={() => onApply(v)}>{v.name} <ChevronIcon size={14} /></button>
              <button className="sx-icon-btn" aria-label={`Delete view ${v.name}`} onClick={() => onDelete(v.name)}><CloseIcon size={14} /></button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="sx-muted">Saved views live in this browser. Use Copy link to share one.</p>
      )}
    </div>
  );
}

function ColumnsMenu({ catalogue, lensKeys, extra, onChange }: {
  catalogue: Stat[]; lensKeys: string[]; extra: string[]; onChange: (extra: string[]) => void;
}) {
  const [q, setQ] = useState("");
  const groups = useMemo(() => {
    const out = new Map<string, Stat[]>();
    for (const s of catalogue) {
      if (q && !`${s.label} ${s.help}`.toLowerCase().includes(q.toLowerCase())) continue;
      out.set(s.group, [...(out.get(s.group) ?? []), s]);
    }
    return out;
  }, [catalogue, q]);
  return (
    <div className="sx-columns">
      <label className="sx-search sx-search-wide">
        <SearchIcon size={16} />
        <span className="sr-only">Find a stat</span>
        <input autoFocus value={q} placeholder="Find a stat" onChange={(e) => setQ(e.target.value)} />
      </label>
      <div className="sx-columns-list">
        {[...groups.entries()].map(([group, stats]) => (
          <fieldset key={group}>
            <legend>{group}</legend>
            {stats.map((s) => {
              const inLens = lensKeys.includes(s.key);
              return (
                <label key={s.key} className="sx-check" title={inLens ? "Part of this lens" : s.help}>
                  <input type="checkbox" checked={inLens || extra.includes(s.key)} disabled={inLens}
                    onChange={(e) => onChange(e.target.checked ? [...extra, s.key] : extra.filter((k) => k !== s.key))} />
                  {s.label}
                  {s.plOnly && s.source === "Opta" && <span className="sx-badge">PL only</span>}
                  {s.source === "Estimate" && <span className="sx-badge">Estimate</span>}
                </label>
              );
            })}
          </fieldset>
        ))}
        {!groups.size && <p className="sx-muted">No curated stat matches “{q}”.</p>}
      </div>
      <p className="sx-muted sx-columns-foot">Coming next: search all 290+ raw Opta stats, not just this curated set.</p>
    </div>
  );
}

// --------------------------------------------------------------- tables

function PlayerTable({ rows, columns, state, sortKey, uclTeams, selected, watchlist, pctOf, onSort, onOpen, onSelect, onWatch, onReset }: {
  rows: ExplorerPlayer[];
  columns: Stat[];
  state: ExplorerState;
  sortKey: string;
  uclTeams: Set<number>;
  selected: number[];
  watchlist: number[];
  pctOf: (stat: Stat, player: ExplorerPlayer, value: number | null) => number | null;
  onSort: (key: string) => void;
  onOpen: (id: number) => void;
  onSelect: (id: number) => void;
  onWatch: (id: number) => void;
  onReset: () => void;
}) {
  const groups: { group: string; span: number }[] = [];
  for (const c of columns) {
    const last = groups[groups.length - 1];
    if (last && last.group === c.group) last.span += 1;
    else groups.push({ group: c.group, span: 1 });
  }
  const [active, setActive] = useState({ r: 0, c: 0 });
  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  const focusCell = (r: number, c: number) => {
    const rr = Math.max(0, Math.min(rows.length - 1, r));
    const cc = Math.max(0, Math.min(columns.length - 1, c));
    setActive({ r: rr, c: cc });
    tbodyRef.current?.querySelector<HTMLElement>(`td[data-r="${rr}"][data-c="${cc}"]`)?.focus();
  };
  const onCellKey = (e: React.KeyboardEvent<HTMLTableSectionElement>) => {
    const cell = (e.target as HTMLElement).closest<HTMLElement>("td[data-r]");
    if (!cell) return;
    const r = Number(cell.dataset.r);
    const c = Number(cell.dataset.c);
    const moves: Record<string, [number, number]> = { ArrowRight: [0, 1], ArrowLeft: [0, -1], ArrowDown: [1, 0], ArrowUp: [-1, 0] };
    if (moves[e.key]) {
      e.preventDefault();
      focusCell(r + moves[e.key][0], c + moves[e.key][1]);
    } else if (e.key === "Enter") {
      onOpen(rows[r].id);
    }
  };
  const dirFor = (key: string): "asc" | "desc" | null => (sortKey === key ? (state.sort ? state.dir : key === "name" ? "asc" : "desc") : null);
  const ariaSort = (key: string) => {
    const d = dirFor(key);
    return d === "asc" ? "ascending" : d === "desc" ? "descending" : "none";
  };

  if (!rows.length) {
    return (
      <div className="sx-state">
        <h2>No players match this view</h2>
        <p>
          {state.watchOnly
            ? "Your watchlist has no one who fits these filters. Star players from the table or their profile to add them."
            : `Nobody with ${state.minMinutes}+ minutes fits these filters. Lower the minimum minutes, raise the max price or include Champions League clubs.`}
        </p>
        <button className="sx-btn" onClick={onReset}>Reset all filters</button>
      </div>
    );
  }

  return (
    <div className="sx-table-wrap" tabIndex={0} aria-label="Player stats table, scrolls sideways">
      <table className="sx-table">
        <caption className="sr-only">
          {rows.length} players. Cells are shaded by percentile within each player's position; the percentile is included in each cell's label. Use the arrow keys to move between cells and Enter to open a player's profile.
        </caption>
        <thead>
          <tr className="sx-group-row">
            <th className="sx-frozen" scope="col" aria-hidden="true" />
            <th scope="colgroup" colSpan={2} className="sx-group sx-wide-only">FPL</th>
            {groups.map((g, i) => <th key={`${g.group}-${i}`} scope="colgroup" colSpan={g.span} className="sx-group">{g.group}</th>)}
          </tr>
          <tr>
            <th className="sx-frozen" scope="col" aria-sort={ariaSort("name")}>
              <button className="sx-sort" onClick={() => onSort("name")}>Player <SortIcon size={14} dir={dirFor("name")} /></button>
            </th>
            <th scope="col" className="sx-num sx-wide-only">£</th>
            <th scope="col" className="sx-num sx-wide-only" aria-sort={ariaSort("minutes")}>
              <button className="sx-sort" onClick={() => onSort("minutes")}>Mins <SortIcon size={14} dir={dirFor("minutes")} /></button>
            </th>
            {columns.map((c) => (
              <th key={c.key} scope="col" className="sx-num" aria-sort={ariaSort(c.key)}>
                <button className="sx-sort" onClick={() => onSort(c.key)} title={c.help}>
                  <span className="sx-col-label">
                    {c.label}
                    {state.norm === "p90" && isNormalised(c) && <small>/90</small>}
                  </span>
                  <SortIcon size={14} dir={dirFor(c.key)} />
                </button>
                {state.scope === "all" && c.plOnly && c.source === "Opta" && (
                  <span className="sx-badge" title="The Champions League feed has no xG data, so this column counts Premier League matches only.">PL only</span>
                )}
                {c.source === "Estimate" && <span className="sx-badge" title={c.help}>Estimate</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody ref={tbodyRef} onKeyDown={onCellKey}>
          {rows.map((p, rowIndex) => {
            const inUcl = p.teamId !== null && uclTeams.has(p.teamId);
            const isSel = selected.includes(p.id);
            const watched = watchlist.includes(p.id);
            return (
              <tr key={p.id} className={isSel ? "selected" : ""}>
                <th scope="row" className="sx-frozen">
                  <div className="sx-player">
                    <input type="checkbox" checked={isSel} onChange={() => onSelect(p.id)}
                      disabled={!isSel && selected.length >= MAX_COMPARE}
                      aria-label={`Select ${p.name} to compare`} />
                    <button className={`sx-star${watched ? " on" : ""}`} onClick={() => onWatch(p.id)}
                      aria-pressed={watched} aria-label={watched ? `Remove ${p.name} from watchlist` : `Add ${p.name} to watchlist`}>
                      <StarIcon size={16} filled={watched} />
                    </button>
                    <button className="sx-name" onClick={() => onOpen(p.id)}>
                      <span className="sx-name-line">
                        <strong>{p.name}</strong>
                        {inUcl && <span className="sx-ucl" title="Club plays in the Champions League">UCL</span>}
                        {p.status && p.status !== "a" && (
                          <span className={`sx-status s-${p.status}`} title={p.news || "Availability flag"}>
                            <span className="sx-wide-only">{p.status === "d" ? "Doubt" : "Out"}</span>
                            <span className="sx-phone-only">
                              <span aria-hidden="true">{p.status === "d" ? "D" : "O"}</span>
                              <span className="sr-only">{p.status === "d" ? "Doubtful" : "Unavailable"}</span>
                            </span>
                          </span>
                        )}
                      </span>
                      <span className="sx-sub">
                        <span className="sx-wide-only">{p.team} · {p.position}</span>
                        <span className="sx-phone-only">{p.team}{state.position === "ALL" ? ` ${p.position}` : ""} £{(p.fpl.fpl_price ?? 0).toFixed(1)}</span>
                      </span>
                    </button>
                  </div>
                </th>
                <td className="sx-num sx-wide-only">{(p.fpl.fpl_price ?? 0).toFixed(1)}</td>
                <td className="sx-num sx-dim sx-wide-only">{Math.round(minutesFor(p, state.scope))}</td>
                {columns.map((c, colIndex) => {
                  const value = statValue(c, p, state.scope, state.norm);
                  const pct = pctOf(c, p, value);
                  const b = band(pct);
                  const text = formatStat(c, value, state.norm);
                  const label = pct === null
                    ? `${c.label} ${text}`
                    : `${c.label} ${text}, ${ordinal(pct)} percentile among ${POSITION_NAMES[p.position]}`;
                  return (
                    <td key={c.key} className={`sx-num sx-cell${b !== null ? ` b${b}` : ""}`} aria-label={label}
                      data-r={rowIndex} data-c={colIndex}
                      tabIndex={active.r === rowIndex && active.c === colIndex ? 0 : -1}
                      onFocus={() => setActive({ r: rowIndex, c: colIndex })}
                      data-tip={pct === null ? undefined : `${ordinal(pct)} percentile among ${POSITION_NAMES[p.position]}`}>
                      {text}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      <TableTooltip />
    </div>
  );
}

function TeamTable({ teams, catalogue, state, onSort }: {
  teams: ExplorerTeam[]; catalogue: TeamStatDef[]; state: ExplorerState; onSort: (key: string) => void;
}) {
  if (!teams.length) {
    return (
      <div className="sx-state">
        <h2>Club stats aren't loaded yet</h2>
        <p>Run <code>sync_team_season_stats --season 2026</code> to load the Premier League's club sheets.</p>
      </div>
    );
  }
  const q = state.query.trim().toLowerCase();
  const perMatch = state.norm === "p90";
  const valueOf = (t: ExplorerTeam, d: TeamStatDef): number | null => {
    const v = t.stats[d.key];
    if (v === null || v === undefined) return null;
    const played = t.stats.gamesPlayed ?? 0;
    return perMatch && d.perMatch ? (played ? v / played : null) : v;
  };
  const sortKey = state.sort && catalogue.some((d) => d.key === state.sort) ? state.sort : "expectedGoals";
  const sortDef = catalogue.find((d) => d.key === sortKey)!;
  const visible = teams
    .filter((t) => (state.club === "only" ? t.inUcl : state.club === "exclude" ? !t.inUcl : true))
    .filter((t) => !q || t.name.toLowerCase().includes(q) || t.short.toLowerCase().includes(q))
    .sort((a, b) => {
      const cmp = (valueOf(a, sortDef) ?? -Infinity) - (valueOf(b, sortDef) ?? -Infinity);
      return (state.sort ? state.dir : "desc") === "asc" ? cmp : -cmp;
    });
  const groups: { group: string; span: number }[] = [];
  for (const d of catalogue) {
    const last = groups[groups.length - 1];
    if (last && last.group === d.group) last.span += 1;
    else groups.push({ group: d.group, span: 1 });
  }
  const fmt = (d: TeamStatDef, v: number | null) => {
    if (v === null) return "–";
    if (d.format === "percent") return `${v.toFixed(1)}%`;
    return perMatch && d.perMatch ? v.toFixed(2) : String(Math.round(v * 100) / 100);
  };
  return (
    <div className="sx-table-wrap" tabIndex={0} aria-label="Club stats table, scrolls sideways">
      <table className="sx-table">
        <caption className="sr-only">Premier League clubs. Cells are shaded by percentile among all 20 clubs.</caption>
        <thead>
          <tr className="sx-group-row">
            <th className="sx-frozen" scope="col" aria-hidden="true" />
            {groups.map((g, i) => <th key={`${g.group}-${i}`} scope="colgroup" colSpan={g.span} className="sx-group">{g.group}</th>)}
          </tr>
          <tr>
            <th className="sx-frozen" scope="col">Club</th>
            {catalogue.map((d) => (
              <th key={d.key} scope="col" className="sx-num" aria-sort={sortKey === d.key ? ((state.sort ? state.dir : "desc") === "asc" ? "ascending" : "descending") : "none"}>
                <button className="sx-sort" onClick={() => onSort(d.key)} title={d.help}>
                  <span className="sx-col-label">{d.label}{perMatch && d.perMatch && <small>/match</small>}</span>
                  <SortIcon size={14} dir={sortKey === d.key ? (state.sort ? state.dir : "desc") : null} />
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((t) => (
            <tr key={t.id}>
              <th scope="row" className="sx-frozen">
                <div className="sx-team-name"><strong>{t.name}</strong>{t.inUcl && <span className="sx-ucl">UCL</span>}</div>
              </th>
              {catalogue.map((d) => {
                const v = valueOf(t, d);
                const pct = percentile(v, teams.map((x) => valueOf(x, d)).filter((x): x is number => x !== null), Boolean(d.lowerIsBetter));
                const b = d.key === "gamesPlayed" ? null : band(pct);
                return (
                  <td key={d.key} className={`sx-num sx-cell${b !== null ? ` b${b}` : ""}`}
                    aria-label={pct === null || b === null ? `${d.label} ${fmt(d, v)}` : `${d.label} ${fmt(d, v)}, ${ordinal(pct)} percentile among clubs`}
                    data-tip={pct === null || b === null ? undefined : `${ordinal(pct)} percentile among clubs`}>
                    {fmt(d, v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <TableTooltip />
    </div>
  );
}

// Floating explanation for shaded cells (mouse); screen readers get the same
// text from each cell's aria-label.
function TableTooltip() {
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const wrap = ref.current?.parentElement;
    if (!wrap) return;
    const over = (e: MouseEvent) => {
      const cell = (e.target as HTMLElement).closest<HTMLElement>("td[data-tip]");
      if (!cell) { setTip(null); return; }
      const r = cell.getBoundingClientRect();
      setTip({ text: cell.dataset.tip ?? "", x: r.left + r.width / 2, y: r.top });
    };
    const leave = () => setTip(null);
    const focus = (e: FocusEvent) => over(e as unknown as MouseEvent);
    wrap.addEventListener("mouseover", over);
    wrap.addEventListener("mouseleave", leave);
    wrap.addEventListener("focusin", focus);
    wrap.addEventListener("focusout", leave);
    wrap.addEventListener("scroll", leave);
    return () => {
      wrap.removeEventListener("mouseover", over);
      wrap.removeEventListener("mouseleave", leave);
      wrap.removeEventListener("focusin", focus);
      wrap.removeEventListener("focusout", leave);
      wrap.removeEventListener("scroll", leave);
    };
  }, []);
  return (
    <div ref={ref} aria-hidden="true">
      {tip && <div className="sx-tip" style={{ left: tip.x, top: tip.y }}>{tip.text}</div>}
    </div>
  );
}

function SkeletonTable() {
  return (
    <div className="sx-table-wrap sx-skeleton" aria-busy="true" aria-label="Loading stats">
      {Array.from({ length: 12 }).map((_, i) => <div key={i} className="sx-skel-row" />)}
    </div>
  );
}

// ----------------------------------------------------------- drawer, sheet

function PlayerDrawer({ player, data, state, lensKeys, pctOf, inUcl, watched, selected, canSelect, onWatch, onSelect, onClose }: {
  player: ExplorerPlayer;
  data: ExplorerPayload;
  state: ExplorerState;
  lensKeys: string[];
  pctOf: (stat: Stat, player: ExplorerPlayer, value: number | null) => number | null;
  inUcl: boolean;
  watched: boolean;
  selected: boolean;
  canSelect: boolean;
  onWatch: () => void;
  onSelect: () => void;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCloseRef.current(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      opener?.focus?.(); // return focus to the row that opened the profile
    };
  }, [player.id]);

  const plMins = player.pl.mins_played ?? 0;
  const uclMins = player.ucl?.mins_played ?? 0;
  const lensStats = lensKeys.map((k) => data.catalogue.find((s) => s.key === k)).filter((s): s is Stat => Boolean(s));
  const otherGroups = new Map<string, Stat[]>();
  for (const s of data.catalogue) {
    if (lensKeys.includes(s.key) || s.kind === "fpl") continue;
    otherGroups.set(s.group, [...(otherGroups.get(s.group) ?? []), s]);
  }

  const uclOnly = (stat: Stat): number | null => {
    if (!player.ucl || stat.plOnly || stat.kind === "fpl") return null;
    const shadow: ExplorerPlayer = { ...player, pl: player.ucl, ucl: null };
    return statValue(stat, shadow, "pl", state.norm);
  };

  const StatRows = ({ stats }: { stats: Stat[] }) => (
    <>
      {stats.map((s) => {
        const pl = statValue(s, player, "pl", state.norm);
        const ucl = uclOnly(s);
        const combined = statValue(s, player, "all", state.norm);
        const pct = pctOf(s, player, statValue(s, player, state.scope, state.norm));
        return (
          <tr key={s.key}>
            <th scope="row" title={s.help}>
              {s.label}
              {s.plOnly && s.source === "Opta" && <span className="sx-badge">PL only</span>}
              {s.source === "Estimate" && <span className="sx-badge">Estimate</span>}
            </th>
            <td className="sx-num">{formatStat(s, pl, state.norm)}</td>
            <td className="sx-num sx-dim">{player.ucl ? formatStat(s, ucl, state.norm) : "–"}</td>
            <td className="sx-num">{player.ucl && !s.plOnly ? formatStat(s, combined, state.norm) : "–"}</td>
            <td className="sx-pct">
              {pct !== null && (
                <span className="sx-pctbar" role="img" aria-label={`${ordinal(pct)} percentile among ${POSITION_NAMES[player.position]}`}>
                  <i style={{ width: `${Math.max(3, pct)}%` }} className={`b${band(pct)}`} />
                </span>
              )}
            </td>
          </tr>
        );
      })}
    </>
  );

  return (
    <div className="sx-drawer-layer">
      <button className="sx-drawer-scrim" aria-label="Close player profile" onClick={onClose} tabIndex={-1} />
      <aside className="sx-drawer" role="dialog" aria-modal="true" aria-labelledby="sx-drawer-title">
        <header className="sx-drawer-head">
          <div>
            <h2 id="sx-drawer-title">{player.name}</h2>
            <p>
              {player.team} · {POSITION_NAMES[player.position].replace(/s$/, "")} · £{(player.fpl.fpl_price ?? 0).toFixed(1)}m · owned by {(player.fpl.fpl_ownership ?? 0).toFixed(1)}%
            </p>
            {player.status && player.status !== "a" && player.news && <p className="sx-news">{player.news}</p>}
          </div>
          <button ref={closeRef} className="sx-icon-btn" onClick={onClose} aria-label="Close player profile"><CloseIcon /></button>
        </header>
        <div className="sx-drawer-actions">
          <button className={`sx-btn${watched ? " on" : ""}`} aria-pressed={watched} onClick={onWatch}>
            <StarIcon filled={watched} /> {watched ? "Watching" : "Watch"}
          </button>
          <button className={`sx-btn${selected ? " on" : ""}`} aria-pressed={selected} onClick={onSelect} disabled={!selected && !canSelect}>
            <CompareIcon /> {selected ? "Selected to compare" : "Select to compare"}
          </button>
        </div>
        <dl className="sx-minutes">
          <div><dt>Premier League</dt><dd>{Math.round(plMins)} min</dd></div>
          <div><dt>Champions League</dt><dd>{player.ucl ? `${Math.round(uclMins)} min` : inUcl ? "No minutes yet" : "Club not in it"}</dd></div>
        </dl>
        <div className="sx-drawer-body">
          <table className="sx-split">
            <caption>
              {data.lenses[state.lens]?.label ?? "Lens"} · {state.norm === "p90" ? "per 90" : "totals"} · bar = percentile among {POSITION_NAMES[player.position]}
            </caption>
            <thead>
              <tr><th scope="col">Stat</th><th scope="col" className="sx-num">PL</th><th scope="col" className="sx-num">UCL</th><th scope="col" className="sx-num">Both</th><th scope="col"><span className="sr-only">Percentile</span></th></tr>
            </thead>
            <tbody><StatRows stats={lensStats.filter((s) => s.kind !== "fpl")} /></tbody>
          </table>
          {[...otherGroups.entries()].map(([group, stats]) => (
            <details key={group} className="sx-more">
              <summary>
                <span>{group} <span className="sx-dim">· {stats.length} more</span></span>
                <ChevronIcon size={14} />
              </summary>
              <table className="sx-split">
                <thead className="sr-only"><tr><th>Stat</th><th>PL</th><th>UCL</th><th>Both</th><th>Percentile</th></tr></thead>
                <tbody><StatRows stats={stats} /></tbody>
              </table>
            </details>
          ))}
          <p className="sx-muted sx-foot"><InfoIcon size={14} /> UCL has no xG feed, so xG-family stats are Premier League only.</p>
        </div>
      </aside>
    </div>
  );
}

function FilterSheet({ open, onClose, activeFilters, onReset, children }: {
  open: boolean; onClose: () => void; activeFilters: number; onReset: () => void; children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog ref={ref} className="sx-sheet" onClose={onClose} aria-labelledby="sx-sheet-title">
      <header>
        <h2 id="sx-sheet-title">Filters</h2>
        <button className="sx-icon-btn" onClick={onClose} aria-label="Close filters"><CloseIcon /></button>
      </header>
      <div className="sx-sheet-body">{children}</div>
      <footer>
        <button className="sx-btn" onClick={onReset} disabled={!activeFilters}>Reset</button>
        <button className="aero-button primary" onClick={onClose}>Show results</button>
      </footer>
    </dialog>
  );
}

export default StatsExplorerPage;
