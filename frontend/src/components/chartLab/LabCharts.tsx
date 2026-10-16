// SVG charts for Chart Lab, ported from the A.R.G.U.S. Chart Lab
// (power_rankings analytics.html: svgScatter / svgLineChart / svgBars).
// Plain SVG keeps them dependency-free and lets the PNG export serialise
// exactly what is on screen.

export const SERIES_COLORS = ["#a5ff01", "#2bb1ff", "#ffc603", "#f472b6", "#a78bfa", "#ff7a45"];

const AXIS_TEXT = "#8f8f8f";
const GRID = "rgba(255,255,255,0.07)";

export function formatValue(value: number): string {
  const magnitude = Math.abs(value);
  if (magnitude >= 100) return value.toFixed(0);
  if (magnitude >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function niceTicks(min: number, max: number, count = 4): number[] {
  if (min === max) { min -= 1; max += 1; }
  const span = max - min;
  const step = Math.pow(10, Math.floor(Math.log10(span / count)));
  const error = span / count / step;
  const size = (error >= 7.5 ? 10 : error >= 3.5 ? 5 : error >= 1.5 ? 2 : 1) * step;
  const ticks: number[] = [];
  for (let v = Math.floor(min / size) * size; v <= max + size * 0.5; v += size) ticks.push(+v.toFixed(6));
  return ticks.filter((t) => t >= min && t <= max);
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// ------------------------------------------------------------------ scatter

export interface ScatterPoint {
  id: number;
  name: string;
  detail: string;
  x: number;
  y: number;
  /** Optional third variable shown as dot area (e.g. goals + assists). */
  size?: number;
}

interface ScatterProps {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  highlighted: Set<number>;
  onToggle: (id: number) => void;
  /** A line through the origin, y = slope × x (e.g. the group's average return per action). */
  originLine?: { slope: number; label: string };
  /** Players labelled without being highlighted (e.g. the outliers). */
  labelled?: Set<number>;
  /** Start both axes at zero so a line through the origin reads correctly. */
  fromZero?: boolean;
  sizeLabel?: string;
}

export function ScatterChart({ points, xLabel, yLabel, highlighted, onToggle, originLine, labelled, fromZero, sizeLabel }: ScatterProps) {
  if (!points.length) return <p className="aero-empty lab-chart-empty">No players match these filters.</p>;
  const w = 720, h = 420, L = 56, R = 16, T = 18, B = 46;
  const iw = w - L - R, ih = h - T - B;
  let xmin = Math.min(...points.map((p) => p.x)), xmax = Math.max(...points.map((p) => p.x));
  let ymin = Math.min(...points.map((p) => p.y)), ymax = Math.max(...points.map((p) => p.y));
  const xpad = (xmax - xmin) * 0.06 || 1, ypad = (ymax - ymin) * 0.08 || 1;
  xmin -= xpad; xmax += xpad; ymin -= ypad; ymax += ypad;
  if (fromZero) { xmin = Math.min(0, xmin + xpad); ymin = Math.min(0, ymin + ypad); }
  const sizes = points.map((p) => p.size ?? 0);
  const maxSize = Math.max(1, ...sizes);
  // Area, not radius, carries the value, so a player with twice the output reads as twice the ink.
  const radius = (p: ScatterPoint, base: number) => (p.size === undefined ? base : 2.5 + 9 * Math.sqrt(Math.max(0, p.size) / maxSize));
  const X = (v: number) => L + ((v - xmin) / (xmax - xmin)) * iw;
  const Y = (v: number) => T + ih - ((v - ymin) / (ymax - ymin)) * ih;
  const medX = median(points.map((p) => p.x)), medY = median(points.map((p) => p.y));

  const plain = points.filter((p) => !highlighted.has(p.id));
  const selected = points.filter((p) => highlighted.has(p.id) || labelled?.has(p.id));

  // Greedy label placement from A.R.G.U.S.: try six anchors, keep the first
  // that hits neither another highlighted dot nor an already placed label.
  const dots = selected.map((p) => ({ cx: X(p.x), cy: Y(p.y) }));
  const boxes: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const anchors: [number, number, "start" | "end" | "middle"][] = [
    [9, -6, "start"], [9, 15, "start"], [-9, -6, "end"], [-9, 15, "end"], [0, -12, "middle"], [0, 21, "middle"],
  ];
  const labels = selected.map((p, index) => {
    const cx = X(p.x), cy = Y(p.y), lw = p.name.length * 7.2 + 8, lh = 14;
    let pick: { lx: number; ly: number; anchor: "start" | "end" | "middle"; x0: number; x1: number; y0: number; y1: number } | null = null;
    for (const [dx, dy, anchor] of anchors) {
      const lx = cx + dx, ly = cy + dy;
      const x0 = anchor === "start" ? lx : anchor === "end" ? lx - lw : lx - lw / 2;
      const box = { x0, x1: x0 + lw, y0: ly - lh, y1: ly + 2 };
      if (box.x0 < 2 || box.x1 > w - 2 || box.y0 < 2 || box.y1 > h - B + 10) continue;
      const hitsDot = dots.some((d, j) => j !== index && box.x1 > d.cx - 9 && box.x0 < d.cx + 9 && box.y1 > d.cy - 9 && box.y0 < d.cy + 9);
      const hitsBox = boxes.some((b) => box.x1 > b.x0 && box.x0 < b.x1 && box.y1 > b.y0 && box.y0 < b.y1);
      if (!hitsDot && !hitsBox) { pick = { lx, ly, anchor, ...box }; break; }
    }
    // Nothing fits cleanly: at least keep the label inside the chart.
    if (!pick) pick = cx > w / 2
      ? { lx: cx - 9, ly: cy - 6, anchor: "end", x0: cx - 9 - lw, x1: cx - 9, y0: cy - 20, y1: cy - 4 }
      : { lx: cx + 9, ly: cy - 6, anchor: "start", x0: cx + 9, x1: cx + 9 + lw, y0: cy - 20, y1: cy - 4 };
    boxes.push(pick);
    return { p, cx, cy, pick };
  });

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="lab-svg" role="img" aria-label={`${yLabel} against ${xLabel}`}>
      {niceTicks(ymin, ymax).map((t) => (
        <g key={`y${t}`}>
          <line x1={L} x2={w - R} y1={Y(t)} y2={Y(t)} stroke={GRID} />
          <text x={L - 8} y={Y(t) + 3.5} textAnchor="end" fontSize="10" fill={AXIS_TEXT}>{formatValue(t)}</text>
        </g>
      ))}
      {niceTicks(xmin, xmax).map((t) => (
        <g key={`x${t}`}>
          <line x1={X(t)} x2={X(t)} y1={T} y2={T + ih} stroke={GRID} strokeOpacity="0.6" />
          <text x={X(t)} y={h - 28} textAnchor="middle" fontSize="10" fill={AXIS_TEXT}>{formatValue(t)}</text>
        </g>
      ))}
      {originLine ? (() => {
        // Clip y = slope·x to the plot box.
        const xEnd = Math.min(xmax, originLine.slope > 0 ? ymax / originLine.slope : xmax);
        const x0 = Math.max(xmin, 0);
        return (
          <g>
            <line x1={X(x0)} y1={Y(originLine.slope * x0)} x2={X(xEnd)} y2={Y(originLine.slope * xEnd)}
              stroke="#a5ff01" strokeOpacity="0.55" strokeDasharray="6 5" strokeWidth={1.4} />
            <text x={X(xEnd) - 4} y={Y(originLine.slope * xEnd) - 6} textAnchor="end" fontSize="10" fill="#a5ff01" fillOpacity="0.8">
              {originLine.label}
            </text>
          </g>
        );
      })() : (
        <>
          <line x1={X(medX)} x2={X(medX)} y1={T} y2={T + ih} stroke="#a5ff01" strokeOpacity="0.25" strokeDasharray="4 4" />
          <line x1={L} x2={w - R} y1={Y(medY)} y2={Y(medY)} stroke="#a5ff01" strokeOpacity="0.25" strokeDasharray="4 4" />
        </>
      )}
      <text x={L + iw / 2} y={h - 8} textAnchor="middle" fontSize="11" fill="#b7b7b7">{xLabel}</text>
      <text x={14} y={T + ih / 2} textAnchor="middle" fontSize="11" fill="#b7b7b7" transform={`rotate(-90 14 ${T + ih / 2})`}>{yLabel}</text>
      {plain.filter((p) => !labelled?.has(p.id)).map((p) => (
        <circle key={p.id} className="lab-dot" cx={X(p.x)} cy={Y(p.y)} r={radius(p, 3.6)}
          fill="rgba(255,255,255,0.22)" stroke="rgba(255,255,255,0.5)" strokeWidth={0.6}
          onClick={() => onToggle(p.id)}>
          <title>{`${p.name} (${p.detail}) · x ${formatValue(p.x)} · y ${formatValue(p.y)}${p.size !== undefined ? ` · ${sizeLabel ?? "size"} ${formatValue(p.size)}` : ""} — click to highlight`}</title>
        </circle>
      ))}
      {labels.map(({ p, cx, cy, pick }) => {
        const strong = highlighted.has(p.id);
        return (
          <g key={p.id}>
            <circle className="lab-dot" cx={cx} cy={cy} r={radius(p, 5.8)}
              fill={strong ? "#a5ff01" : "rgba(255,255,255,0.55)"} stroke="#101011" strokeWidth={1.2}
              onClick={() => onToggle(p.id)}>
              <title>{`${p.name} (${p.detail}) · x ${formatValue(p.x)} · y ${formatValue(p.y)}${p.size !== undefined ? ` · ${sizeLabel ?? "size"} ${formatValue(p.size)}` : ""} — click to ${strong ? "remove" : "highlight"}`}</title>
            </circle>
            <text x={pick.lx} y={pick.ly} textAnchor={pick.anchor} fontSize="10.5" fontWeight="700" fill={strong ? "#a5ff01" : "#e6e6e6"}
              stroke="#101011" strokeWidth={3} paintOrder="stroke" strokeLinejoin="round">{p.name}</text>
          </g>
        );
      })}
    </svg>
  );
}

// --------------------------------------------------------------------- line

export interface LineSeries {
  name: string;
  color: string;
  values: { label: string; value: number | null }[];
}

export function LineChart({ series, yLabel }: { series: LineSeries[]; yLabel: string }) {
  const all = series.flatMap((s) => s.values.map((v) => v.value)).filter((v): v is number => v !== null);
  if (!all.length) return <p className="aero-empty lab-chart-empty">No values to plot for this formula.</p>;
  const w = 720, h = 320, L = 52, R = 14, T = 16, B = 34;
  const iw = w - L - R, ih = h - T - B;
  const labels = series.reduce<string[]>((longest, s) => (s.values.length > longest.length ? s.values.map((v) => v.label) : longest), []);
  const count = labels.length;
  let min = Math.min(...all), max = Math.max(...all);
  const pad = (max - min) * 0.12 || 1;
  min -= pad; max += pad;
  const X = (i: number) => L + (count < 2 ? iw / 2 : (i / (count - 1)) * iw);
  const Y = (v: number) => T + ih - ((v - min) / (max - min)) * ih;
  const labelEvery = Math.max(1, Math.ceil(count / 12));

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="lab-svg" role="img" aria-label={yLabel}>
      {niceTicks(min, max).map((t) => (
        <g key={t}>
          <line x1={L} x2={w - R} y1={Y(t)} y2={Y(t)} stroke={GRID} />
          <text x={L - 8} y={Y(t) + 3.5} textAnchor="end" fontSize="10" fill={AXIS_TEXT}>{formatValue(t)}</text>
        </g>
      ))}
      {labels.map((label, i) => (i % labelEvery === 0 || i === count - 1) && (
        <text key={label} x={X(i)} y={h - 12} textAnchor="middle" fontSize="10" fill={AXIS_TEXT}>{label}</text>
      ))}
      {series.map((s) => {
        const index = new Map(labels.map((label, i) => [label, i]));
        const pts = s.values
          .filter((v) => v.value !== null)
          .map((v) => ({ ...v, i: index.get(v.label) ?? 0 }));
        return (
          <g key={s.name}>
            {pts.length > 1 && (
              <polyline fill="none" stroke={s.color} strokeWidth={2.2} strokeLinejoin="round"
                points={pts.map((p) => `${X(p.i).toFixed(1)},${Y(p.value as number).toFixed(1)}`).join(" ")} />
            )}
            {pts.map((p) => (
              <circle key={p.label} cx={X(p.i)} cy={Y(p.value as number)} r={3.2} fill={s.color}>
                <title>{`${s.name} · ${p.label}: ${formatValue(p.value as number)}`}</title>
              </circle>
            ))}
          </g>
        );
      })}
    </svg>
  );
}

// --------------------------------------------------------------------- bars

export interface BarItem {
  id: number;
  label: string;
  detail: string;
  value: number;
  highlighted: boolean;
}

// `compact` is for phone widths: a narrower canvas so text renders larger,
// and labels without the detail line. `stacked` puts the detail on its own
// line under the name, for details too long to share a line (club names).
export function BarChart({ items, format = formatValue, compact = false, stacked = false }: { items: BarItem[]; format?: (value: number) => string; compact?: boolean; stacked?: boolean }) {
  if (!items.length) return <p className="aero-empty lab-chart-empty">No players match these filters.</p>;
  const twoLines = stacked && !compact;
  const w = compact ? 400 : 720, labelW = compact ? 118 : 190, valueW = compact ? 48 : 64, rowH = twoLines ? 40 : 30;
  const maxLabel = compact ? 15 : twoLines ? 26 : 18;
  const maxDetail = 34;
  const h = items.length * rowH + 8;
  const min = Math.min(0, ...items.map((i) => i.value));
  const max = Math.max(0, ...items.map((i) => i.value));
  const span = max - min || 1;
  const trackW = w - labelW - valueW;
  const X = (v: number) => labelW + ((v - min) / span) * trackW;
  const clip = (text: string, n: number) => (text.length > n ? `${text.slice(0, n - 1)}…` : text);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="lab-svg" role="img" aria-label="Bar chart">
      {min < 0 && <line x1={X(0)} x2={X(0)} y1={0} y2={h} stroke={GRID} />}
      {items.map((item, i) => {
        const y = i * rowH + 4;
        const barY = twoLines ? y + 7 : y + 2;
        const x0 = Math.min(X(0), X(item.value)), bw = Math.max(2, Math.abs(X(item.value) - X(0)));
        const color = item.highlighted ? "#a5ff01" : "#5f7a2e";
        return (
          <g key={item.id}>
            {twoLines ? (
              <>
                <text x={0} y={y + 13} fontSize="12" fontWeight="600" fill="#ffffff">{clip(item.label, maxLabel)}</text>
                <text x={0} y={y + 28} fontSize="10.5" fill={AXIS_TEXT}>{clip(item.detail, maxDetail)}</text>
              </>
            ) : (
              <text x={0} y={y + 15} fontSize="12" fontWeight="600" fill="#ffffff">
                {clip(item.label, maxLabel)}
                {!compact && <tspan fill={AXIS_TEXT} fontWeight="400" fontSize="10.5">{`  ${item.detail}`}</tspan>}
              </text>
            )}
            <rect x={x0} y={barY} width={bw} height={18} rx={4} fill={color}>
              <title>{`${item.label} (${item.detail}): ${format(item.value)}`}</title>
            </rect>
            <text x={Math.max(X(0), X(item.value)) + 6} y={barY + 13} fontSize="12" fontWeight="700" fill={item.highlighted ? "#a5ff01" : "#d8d8d8"}>
              {format(item.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export interface ChangeItem {
  id: string;
  label: string;
  detail: string;
  before: number;
  after: number;
}

// Before → after per row: a grey dot for the earlier value, a lime dot for the
// later one, joined by a line. Reads like a ranking with the old value kept in view.
export function ChangeChart({ items, beforeLabel, afterLabel, digits = 2, compact = false }: { items: ChangeItem[]; beforeLabel: string; afterLabel: string; digits?: number; compact?: boolean }) {
  if (!items.length) return <p className="aero-empty lab-chart-empty">No players match these filters.</p>;
  const w = compact ? 400 : 720, labelW = compact ? 118 : 200, valueW = compact ? 46 : 70, rowH = 30, top = 26;
  const maxLabel = compact ? 15 : 18;
  const legendX = compact ? 0 : labelW;
  const h = top + items.length * rowH + 6;
  const max = Math.max(...items.flatMap((i) => [i.before, i.after]));
  const min = Math.min(0, ...items.flatMap((i) => [i.before, i.after]));
  const span = max - min || 1;
  const trackW = w - labelW - valueW - 12;
  const X = (v: number) => labelW + ((v - min) / span) * trackW;
  const fmt = (v: number) => v.toFixed(digits);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="lab-svg" role="img" aria-label={`Change from ${beforeLabel} to ${afterLabel}`}>
      <g fontSize="11" fill={AXIS_TEXT}>
        <circle cx={legendX + 6} cy={10} r={5} fill="#6b6b6b" />
        <text x={legendX + 16} y={14}>{beforeLabel}</text>
        <circle cx={legendX + 116} cy={10} r={5} fill="#a5ff01" />
        <text x={legendX + 126} y={14}>{afterLabel}</text>
      </g>
      {items.map((item, i) => {
        const y = top + i * rowH + 12;
        const rise = item.after >= item.before;
        const delta = item.after - item.before;
        return (
          <g key={item.id}>
            <text x={0} y={y + 4} fontSize="12" fontWeight="600" fill="#ffffff">
              {item.label.length > maxLabel ? `${item.label.slice(0, maxLabel - 1)}…` : item.label}
              {!compact && <tspan fill={AXIS_TEXT} fontWeight="400" fontSize="10.5">{`  ${item.detail}`}</tspan>}
            </text>
            <line x1={labelW} x2={labelW + trackW} y1={y} y2={y} stroke={GRID} />
            <line x1={X(item.before)} x2={X(item.after)} y1={y} y2={y} stroke={rise ? "#5f7a2e" : "#7a3b3b"} strokeWidth={4} strokeLinecap="round" />
            <circle cx={X(item.before)} cy={y} r={5.5} fill="#6b6b6b" stroke="#101011" strokeWidth={2}>
              <title>{`${item.label}, ${beforeLabel}: ${fmt(item.before)}`}</title>
            </circle>
            <circle cx={X(item.after)} cy={y} r={6} fill="#a5ff01" stroke="#101011" strokeWidth={2}>
              <title>{`${item.label}, ${afterLabel}: ${fmt(item.after)}`}</title>
            </circle>
            <text x={w - valueW + 8} y={y + 4} fontSize="12" fontWeight="700" fill={rise ? "#a5ff01" : "#ff8a8a"}>
              {`${delta >= 0 ? "+" : "−"}${fmt(Math.abs(delta))}`}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
