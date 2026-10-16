import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart,
  LineChart,
  ScatterChart,
  SERIES_COLORS,
  type BarItem,
  type LineSeries,
  type ScatterPoint,
} from "../components/chartLab/LabCharts";
import { DEFAULT_USAGE, useUsageView, type UsageConfig } from "../components/chartLab/UsageView";
import { DEFAULT_CHANGES, useChangesView, type ChangesConfig } from "../components/chartLab/ChangesView";
import { DEFAULT_HOLDUP, useHoldupView, type HoldupConfig } from "../components/chartLab/HoldupView";
import { DEFAULT_CLUTCH, useClutchView, type ClutchConfig } from "../components/chartLab/ClutchView";
import { compileFormula, FORMULA_FUNCTIONS, type StatValues } from "../utils/formula";
import "./ChartLabPage.css";

// Chart Lab, adapted from the A.R.G.U.S. Chart Lab in the power_rankings
// repo: trend / scatter / bar charts, saved charts and PNG export. The FPL
// version replaces the fixed metric list with free-form formulas over the
// season's base stats.

type Mode = "scatter" | "bars" | "trend" | "usage" | "changes" | "holdup" | "clutch";
type Position = "ALL" | "GKP" | "DEF" | "MID" | "FWD";

interface Metric { key: string; label: string }
interface LabPlayer { id: number; name: string; full_name: string; team: string | null; position: string; values: StatValues }
interface PlayersPayload { latest_gameweek: number; metrics: Metric[]; players: LabPlayer[] }
interface SeriesPayload { series: { id: number; name: string; team: string | null; points: { gameweek: number; values: StatValues }[] }[] }

interface LabConfig {
  mode: Mode;
  x: string;
  y: string;
  formula: string;
  position: Position;
  minMinutes: number;
  selected: number[];
  barCount: number;
  barSource: "top" | "selected";
  cumulative: boolean;
  usage: UsageConfig;
  changes: ChangesConfig;
  holdup: HoldupConfig;
  clutch: ClutchConfig;
}

interface SavedChart { name: string; config: LabConfig }

const MODE_LABELS: Record<Mode, string> = {
  scatter: "Scatter", bars: "Ranking", trend: "Trend", usage: "Usage", changes: "Changes", holdup: "Hold-up", clutch: "Clutch",
};

const MAX_SELECTED = 6;
const SAVED_KEY = "aerofpl_chart_lab_saved";
const CURRENT_KEY = "aerofpl_chart_lab_current";

const DEFAULT_CONFIG: LabConfig = {
  mode: "scatter",
  x: "per90(xg)",
  y: "per90(xa)",
  formula: "xg * xa",
  position: "ALL",
  minMinutes: 270,
  selected: [],
  barCount: 15,
  barSource: "top",
  cumulative: true,
  usage: DEFAULT_USAGE,
  changes: DEFAULT_CHANGES,
  holdup: DEFAULT_HOLDUP,
  clutch: DEFAULT_CLUTCH,
};

const PRESETS: { label: string; formula: string }[] = [
  { label: "xG × xA", formula: "xg * xa" },
  { label: "xG/90 ÷ xA", formula: "per90(xg) / xa" },
  { label: "xGI per 90", formula: "per90(xg + xa)" },
  { label: "Points per £m", formula: "pts / price" },
  { label: "Finishing (G − xG)", formula: "g - xg" },
  { label: "CS luck (CS − xCS)", formula: "cs - xcs" },
  { label: "Bonus per 90", formula: "per90(bonus)" },
  { label: "Points per 90", formula: "per90(pts)" },
];

// Stats that add up across gameweeks; price and ownership do not.
const NON_SUMMABLE = new Set(["price", "own"]);

// Fill in defaults for any view a stored or saved chart predates.
function withDefaults(stored: Partial<LabConfig>): LabConfig {
  return {
    ...DEFAULT_CONFIG,
    ...stored,
    usage: { ...DEFAULT_USAGE, ...(stored.usage ?? {}) },
    changes: { ...DEFAULT_CHANGES, ...(stored.changes ?? {}) },
    holdup: { ...DEFAULT_HOLDUP, ...(stored.holdup ?? {}) },
    clutch: { ...DEFAULT_CLUTCH, ...(stored.clutch ?? {}) },
  };
}

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
    // Private windows and blocked storage: the lab still works, it just forgets.
  }
}

export function ChartLabPage() {
  const [data, setData] = useState<PlayersPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<LabConfig>(() => {
    return withDefaults(readStorage<Partial<LabConfig>>(CURRENT_KEY, {}));
  });
  const [usageHighlight, setUsageHighlight] = useState<Set<number>>(new Set());
  const [saved, setSaved] = useState<SavedChart[]>(() => readStorage<SavedChart[]>(SAVED_KEY, []));
  const [series, setSeries] = useState<SeriesPayload | null>(null);
  const [search, setSearch] = useState("");
  const [activeField, setActiveField] = useState<"x" | "y" | "formula">("formula");
  const chartRef = useRef<HTMLDivElement>(null);
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const update = (patch: Partial<LabConfig>) => setConfig((current) => ({ ...current, ...patch }));
  const updateUsage = (patch: Partial<UsageConfig>) => setConfig((current) => ({ ...current, usage: { ...current.usage, ...patch } }));
  const updateChanges = (patch: Partial<ChangesConfig>) => setConfig((current) => ({ ...current, changes: { ...current.changes, ...patch } }));
  const updateHoldup = (patch: Partial<HoldupConfig>) => setConfig((current) => ({ ...current, holdup: { ...current.holdup, ...patch } }));
  const updateClutch = (patch: Partial<ClutchConfig>) => setConfig((current) => ({ ...current, clutch: { ...current.clutch, ...patch } }));
  const toggleUsage = (id: number) => setUsageHighlight((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const isUsage = config.mode === "usage";
  const usageView = useUsageView(isUsage, config.usage, updateUsage, usageHighlight, toggleUsage);
  const isChanges = config.mode === "changes";
  const changesView = useChangesView(isChanges, config.changes, updateChanges);
  const holdupView = useHoldupView(config.mode === "holdup", config.holdup, updateHoldup);
  const clutchView = useClutchView(config.mode === "clutch", config.clutch, updateClutch);
  // Modes with their own data and controls instead of the formula builder.
  const custom = isUsage ? usageView : isChanges ? changesView : config.mode === "holdup" ? holdupView
    : config.mode === "clutch" ? clutchView : null;
  // The ready-made views lead with a one-paragraph answer built from the data.
  const takeaway = custom && "takeaway" in custom ? custom.takeaway : null;

  useEffect(() => { writeStorage(CURRENT_KEY, config); }, [config]);

  useEffect(() => {
    let alive = true;
    fetch("/api/chart-lab/players/")
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<PlayersPayload>;
      })
      .then((payload) => { if (alive) setData(payload); })
      .catch((err) => { if (alive) setError(err instanceof Error ? err.message : String(err)); });
    return () => { alive = false; };
  }, []);

  const selectedKey = config.selected.join(",");
  useEffect(() => {
    if (config.mode !== "trend" || !config.selected.length) { setSeries(null); return; }
    let alive = true;
    fetch(`/api/chart-lab/series/?ids=${selectedKey}`)
      .then((response) => (response.ok ? (response.json() as Promise<SeriesPayload>) : null))
      .then((payload) => { if (alive) setSeries(payload); })
      .catch(() => { if (alive) setSeries(null); });
    return () => { alive = false; };
  }, [config.mode, selectedKey]);

  const variables = useMemo(() => data?.metrics.map((m) => m.key) ?? [], [data]);
  const playersById = useMemo(() => new Map((data?.players ?? []).map((p) => [p.id, p])), [data]);

  const compiledX = useMemo(() => compileFormula(config.x, variables), [config.x, variables]);
  const compiledY = useMemo(() => compileFormula(config.y, variables), [config.y, variables]);
  const compiledFormula = useMemo(() => compileFormula(config.formula, variables), [config.formula, variables]);

  const pool = useMemo(() => (data?.players ?? []).filter((p) =>
    (config.position === "ALL" || p.position === config.position) && (p.values.mins ?? 0) >= config.minMinutes,
  ), [data, config.position, config.minMinutes]);

  const highlighted = useMemo(() => new Set(config.selected), [config.selected]);

  const toggleSelected = (id: number) => {
    if (highlighted.has(id)) update({ selected: config.selected.filter((s) => s !== id) });
    else if (config.selected.length < MAX_SELECTED) update({ selected: [...config.selected, id] });
  };

  const scatterPoints = useMemo<ScatterPoint[]>(() => {
    if (!compiledX.ok || !compiledY.ok) return [];
    return pool.flatMap((p) => {
      const x = compiledX.evaluate(p.values), y = compiledY.evaluate(p.values);
      return x === null || y === null ? [] : [{ id: p.id, name: p.name, detail: `${p.team ?? "—"} ${p.position}`, x, y }];
    });
  }, [pool, compiledX, compiledY]);

  // Players whose formula is undefined (e.g. dividing by a zero stat) are
  // dropped from the chart; say how many so the gap is never silent.
  const barUndefinedCount = useMemo(() => {
    if (!compiledFormula.ok || config.barSource === "selected") return 0;
    return pool.filter((p) => compiledFormula.evaluate(p.values) === null).length;
  }, [compiledFormula, config.barSource, pool]);

  const barItems = useMemo<BarItem[]>(() => {
    if (!compiledFormula.ok) return [];
    const source = config.barSource === "selected"
      ? config.selected.map((id) => playersById.get(id)).filter((p): p is LabPlayer => Boolean(p))
      : pool;
    const scored = source.flatMap((p) => {
      const value = compiledFormula.evaluate(p.values);
      return value === null ? [] : [{ id: p.id, label: p.name, detail: `${p.team ?? "—"} ${p.position}`, value, highlighted: highlighted.has(p.id) }];
    });
    scored.sort((a, b) => b.value - a.value);
    return config.barSource === "selected" ? scored : scored.slice(0, config.barCount);
  }, [compiledFormula, config.barSource, config.selected, config.barCount, pool, playersById, highlighted]);

  const lineSeries = useMemo<LineSeries[]>(() => {
    if (!compiledFormula.ok || !series) return [];
    return series.series.map((s, index) => {
      const running: Record<string, number> = {};
      const values = s.points.map((point) => {
        let row: StatValues = point.values;
        if (config.cumulative) {
          for (const [key, value] of Object.entries(point.values)) {
            if (NON_SUMMABLE.has(key) || value === null || value === undefined) continue;
            running[key] = (running[key] ?? 0) + value;
          }
          row = { ...point.values, ...running };
        }
        return { label: `GW${point.gameweek}`, value: compiledFormula.evaluate(row) };
      });
      return { name: s.name, color: SERIES_COLORS[index % SERIES_COLORS.length], values };
    });
  }, [compiledFormula, series, config.cumulative]);

  const searchResults = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (q.length < 2 || !data) return [];
    return data.players
      .filter((p) => p.name.toLowerCase().includes(q) || p.full_name.toLowerCase().includes(q))
      .slice(0, 8);
  }, [search, data]);

  const insertVariable = (key: string) => {
    const field = config.mode === "scatter" ? (activeField === "formula" ? "y" : activeField) : "formula";
    const input = inputRefs.current[field];
    const current = config[field];
    const start = input?.selectionStart ?? current.length;
    const end = input?.selectionEnd ?? current.length;
    const next = `${current.slice(0, start)}${key}${current.slice(end)}`;
    update({ [field]: next } as Partial<LabConfig>);
    requestAnimationFrame(() => {
      input?.focus();
      input?.setSelectionRange(start + key.length, start + key.length);
    });
  };

  const applyPreset = (formula: string) => {
    if (config.mode === "scatter") update({ [activeField === "formula" ? "y" : activeField]: formula } as Partial<LabConfig>);
    else update({ formula });
  };

  const chartTitle = custom ? custom.title : config.mode === "scatter" ? `${config.y}  vs  ${config.x}` : config.formula;
  const chartSubtitle = custom ? custom.subtitle : config.mode === "trend"
    ? `${config.cumulative ? "Season to date" : "Each gameweek"} · ${config.selected.length} player${config.selected.length === 1 ? "" : "s"}`
    : [
        config.mode === "scatter" ? `${scatterPoints.length} of ${pool.length} players` : `${pool.length} players`,
        config.position === "ALL" ? "all positions" : config.position,
        `${config.minMinutes}+ minutes`,
        `through GW${data?.latest_gameweek ?? "—"}`,
        ...(() => {
          const skipped = config.mode === "scatter" ? pool.length - scatterPoints.length : barUndefinedCount;
          return skipped > 0 ? [`${skipped} skipped (formula undefined, e.g. ÷ 0)`] : [];
        })(),
      ].join(" · ");

  const saveChart = () => {
    const name = `${chartTitle} (${config.mode})`;
    const next = [{ name, config }, ...saved.filter((s) => s.name !== name)].slice(0, 12);
    setSaved(next);
    writeStorage(SAVED_KEY, next);
  };

  const deleteSaved = (index: number) => {
    const next = saved.filter((_, i) => i !== index);
    setSaved(next);
    writeStorage(SAVED_KEY, next);
  };

  const exportPng = () => {
    const svg = chartRef.current?.querySelector("svg");
    if (!svg) return;
    const [, , sw, sh] = (svg.getAttribute("viewBox") ?? "0 0 720 420").split(" ").map(Number);
    const scale = 2, pad = 28, headH = 64, footH = 36;
    const canvas = document.createElement("canvas");
    canvas.width = (sw + pad * 2) * scale;
    canvas.height = (sh + headH + footH + pad) * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(scale, scale);
    ctx.fillStyle = "#101011";
    ctx.fillRect(0, 0, sw + pad * 2, sh + headH + footH + pad);
    ctx.fillStyle = "#ffffff";
    ctx.font = "700 19px Inter, sans-serif";
    ctx.fillText(chartTitle, pad, 34);
    ctx.fillStyle = "#8f8f8f";
    ctx.font = "12px Inter, sans-serif";
    ctx.fillText(chartSubtitle, pad, 54);
    const image = new Image();
    image.onload = () => {
      ctx.drawImage(image, pad, headH, sw, sh);
      ctx.fillStyle = "#a5ff01";
      ctx.font = "800 13px Inter, sans-serif";
      ctx.fillText("AEROFPL CHART LAB", pad, headH + sh + 24);
      const date = new Date().toISOString().slice(0, 10);
      ctx.fillStyle = "#8f8f8f";
      ctx.font = "11px Inter, sans-serif";
      ctx.fillText(date, pad + 160, headH + sh + 24);
      canvas.toBlob((blob) => {
        if (!blob) return;
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `aerofpl_chart_${date}.png`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 5000);
      });
    };
    image.src = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(new XMLSerializer().serializeToString(svg))))}`;
  };

  const formulaField = (field: "x" | "y" | "formula", label: string) => {
    const compiled = field === "x" ? compiledX : field === "y" ? compiledY : compiledFormula;
    return (
      <label className="aero-field lab-formula-field">
        {label}
        <input
          ref={(el) => { inputRefs.current[field] = el; }}
          className={`aero-input lab-formula-input ${compiled.ok ? "" : "invalid"}`}
          value={config[field]}
          spellCheck={false}
          onFocus={() => setActiveField(field)}
          onChange={(event) => update({ [field]: event.target.value } as Partial<LabConfig>)}
          aria-invalid={!compiled.ok}
        />
        {!compiled.ok && data && <span className="lab-formula-error" role="alert">{compiled.error}</span>}
      </label>
    );
  };

  if (error) {
    return (
      <main className="aero-page chart-lab-page">
        <div className="aero-header"><div><h1>Chart Lab</h1></div></div>
        <p className="aero-note">Could not load Chart Lab data ({error}).</p>
      </main>
    );
  }

  return (
    <main className="aero-page chart-lab-page">
      <div className="aero-header">
        <div>
          <span className="aero-eyebrow">Build your own</span>
          <h1>Chart Lab</h1>
          <p>Write any formula over this season's stats, like <code>xg * xa</code> or <code>per90(xg) / xa</code>, then plot it as a scatter, a ranking or a gameweek trend. Usage plots how much of the ball a player uses against what he makes of it; Changes shows which clubs lost their defenders and which players made the leap; Hold-up and Clutch rank lay-offs and how many points each player's goals were worth.</p>
        </div>
      </div>

      <div className="lab-layout">
        <aside className="aero-card lab-controls">
          <div className="lab-mode" role="tablist" aria-label="Chart type">
            {(["scatter", "bars", "trend", "usage", "changes", "holdup", "clutch"] as Mode[]).map((mode) => (
              <button key={mode} role="tab" aria-selected={config.mode === mode}
                className={`lab-pill ${config.mode === mode ? "active" : ""}`}
                onClick={() => update({ mode })}>
                {MODE_LABELS[mode]}
              </button>
            ))}
          </div>

          {custom ? custom.controls : (<>
          {config.mode === "scatter" ? (
            <>
              {formulaField("x", "X axis formula")}
              {formulaField("y", "Y axis formula")}
            </>
          ) : formulaField("formula", "Formula")}

          <div className="lab-presets">
            {PRESETS.map((preset) => (
              <button key={preset.label} className="lab-chip" onClick={() => applyPreset(preset.formula)} title={preset.formula}>
                {preset.label}
              </button>
            ))}
          </div>

          {config.mode !== "trend" && (
            <div className="lab-filter-row">
              <label className="aero-field">
                Position
                <select className="aero-select" value={config.position}
                  onChange={(event) => update({ position: event.target.value as Position })}>
                  {["ALL", "GKP", "DEF", "MID", "FWD"].map((p) => <option key={p} value={p}>{p === "ALL" ? "All" : p}</option>)}
                </select>
              </label>
              <label className="aero-field">
                Min minutes
                <input className="aero-input" type="number" min={0} step={90} value={config.minMinutes}
                  onChange={(event) => update({ minMinutes: Math.max(0, Number(event.target.value) || 0) })} />
              </label>
            </div>
          )}

          {config.mode === "bars" && (
            <div className="lab-filter-row">
              <label className="aero-field">
                Show
                <select className="aero-select" value={config.barSource}
                  onChange={(event) => update({ barSource: event.target.value as "top" | "selected" })}>
                  <option value="top">Top players</option>
                  <option value="selected">My selection</option>
                </select>
              </label>
              {config.barSource === "top" && (
                <label className="aero-field">
                  How many
                  <select className="aero-select" value={config.barCount}
                    onChange={(event) => update({ barCount: Number(event.target.value) })}>
                    {[10, 15, 20, 30].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
              )}
            </div>
          )}

          {config.mode === "trend" && (
            <label className="lab-check">
              <input type="checkbox" checked={config.cumulative} onChange={(event) => update({ cumulative: event.target.checked })} />
              Season to date (otherwise each gameweek on its own)
            </label>
          )}

          <div className="lab-selection">
            <div className="aero-field">
              {config.mode === "scatter" ? "Highlight players" : config.mode === "trend" ? "Players to plot" : "Selection"} ({config.selected.length}/{MAX_SELECTED})
            </div>
            {config.selected.map((id, index) => {
              const player = playersById.get(id);
              return (
                <div key={id} className="lab-selected">
                  <i style={{ background: SERIES_COLORS[index % SERIES_COLORS.length] }} />
                  <span>{player?.name ?? `#${id}`}</span>
                  <small>{player ? `${player.team ?? "—"} ${player.position}` : ""}</small>
                  <button aria-label={`Remove ${player?.name ?? id}`} onClick={() => toggleSelected(id)}>✕</button>
                </div>
              );
            })}
            {config.selected.length < MAX_SELECTED && (
              <div className="lab-search">
                <input className="aero-input" placeholder="Add a player…" value={search}
                  onChange={(event) => setSearch(event.target.value)} />
                {searchResults.length > 0 && (
                  <div className="lab-search-results">
                    {searchResults.map((p) => (
                      <button key={p.id} onClick={() => { toggleSelected(p.id); setSearch(""); }} disabled={highlighted.has(p.id)}>
                        <span>{p.name}</span><small>{p.team ?? "—"} {p.position}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          </>)}

          <div className="lab-actions">
            <button className="aero-button" onClick={saveChart}>★ Save chart</button>
            <button className="aero-button" onClick={exportPng}>⤓ Export PNG</button>
          </div>

          {saved.length > 0 && (
            <div className="lab-saved">
              <div className="aero-field">Saved charts</div>
              {saved.map((chart, index) => (
                <div key={chart.name} className="lab-saved-row">
                  <button onClick={() => setConfig(withDefaults(chart.config))} title={chart.name}>{chart.name}</button>
                  <button aria-label={`Delete ${chart.name}`} onClick={() => deleteSaved(index)}>✕</button>
                </div>
              ))}
            </div>
          )}
        </aside>

        <section className="lab-main">
          <article className="aero-card lab-chart-card">
            <div className="aero-card-title">
              <div>
                <h2 className="lab-chart-title">{chartTitle}</h2>
                <p>{chartSubtitle}</p>
              </div>
            </div>
            {takeaway && <p className="lab-takeaway">{takeaway}</p>}
            <div ref={chartRef} className="lab-chart">
              {custom ? custom.chart : !data ? <div className="lab-skeleton" /> :
                config.mode === "scatter" ? (
                  compiledX.ok && compiledY.ok
                    ? <ScatterChart points={scatterPoints} xLabel={config.x} yLabel={config.y} highlighted={highlighted} onToggle={toggleSelected} />
                    : <p className="aero-empty lab-chart-empty">Fix the formula on the left to draw the chart.</p>
                ) : config.mode === "bars" ? (
                  compiledFormula.ok
                    ? <BarChart items={barItems} />
                    : <p className="aero-empty lab-chart-empty">Fix the formula on the left to draw the chart.</p>
                ) : !config.selected.length ? (
                  <p className="aero-empty lab-chart-empty">Add up to six players on the left to plot them gameweek by gameweek.</p>
                ) : compiledFormula.ok ? (
                  <>
                    <LineChart series={lineSeries} yLabel={config.formula} />
                    <div className="lab-legend">
                      {lineSeries.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}
                    </div>
                  </>
                ) : <p className="aero-empty lab-chart-empty">Fix the formula on the left to draw the chart.</p>}
            </div>
            {config.mode === "scatter" && <p className="aero-empty lab-hint">Dashed lines are the medians. Click any dot to highlight that player.</p>}
            {isUsage && <p className="aero-empty lab-hint">{usageView.hint} Click any dot to highlight that player.</p>}
            {isChanges && changesView.details}
            {custom && !isUsage && <p className="aero-empty lab-hint">{custom.hint}</p>}
          </article>

          {!custom && <article className="aero-card lab-reference">
            <div className="aero-card-title">
              <div>
                <h3>Stats you can use</h3>
                <p>Click one to insert it. Combine with + − × ÷ ^ and brackets. Functions: {FORMULA_FUNCTIONS.map((f) => `${f}()`).join(", ")}. per90(x) divides by minutes × 90.</p>
              </div>
            </div>
            <div className="lab-stat-grid">
              {data?.metrics.map((metric) => (
                <button key={metric.key} className="lab-stat" onClick={() => insertVariable(metric.key)}>
                  <code>{metric.key}</code><span>{metric.label}</span>
                </button>
              ))}
            </div>
            <p className="aero-empty lab-hint">xCS is an estimate (FPL does not publish it): the clean-sheet chance in each 60+ minute appearance, from expected goals conceded. Ownership is season-level only, so it is blank in trends.</p>
          </article>}
        </section>
      </div>
    </main>
  );
}
