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
}

interface ScatterProps {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  highlighted: Set<number>;
  onToggle: (id: number) => void;
}

export function ScatterChart({ points, xLabel, yLabel, highlighted, onToggle }: ScatterProps) {
  if (!points.length) return <p className="aero-empty lab-chart-empty">No players match these filters.</p>;
  const w = 720, h = 420, L = 56, R = 16, T = 18, B = 46;
  const iw = w - L - R, ih = h - T - B;
  let xmin = Math.min(...points.map((p) => p.x)), xmax = Math.max(...points.map((p) => p.x));
  let ymin = Math.min(...points.map((p) => p.y)), ymax = Math.max(...points.map((p) => p.y));
  const xpad = (xmax - xmin) * 0.06 || 1, ypad = (ymax - ymin) * 0.08 || 1;
  xmin -= xpad; xmax += xpad; ymin -= ypad; ymax += ypad;
  const X = (v: number) => L + ((v - xmin) / (xmax - xmin)) * iw;
  const Y = (v: number) => T + ih - ((v - ymin) / (ymax - ymin)) * ih;
  const medX = median(points.map((p) => p.x)), medY = median(points.map((p) => p.y));

  const plain = points.filter((p) => !highlighted.has(p.id));
  const selected = points.filter((p) => highlighted.has(p.id));

  // Greedy label placement from A.R.G.U.S.: try six anchors, keep the first
  // that hits neither another highlighted dot nor an already placed label.
  const dots = selected.map((p) => ({ cx: X(p.x), cy: Y(p.y) }));
  const boxes: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const anchors: [number, number, "start" | "end" | "middle"][] = [
    [9, -6, "start"], [9, 15, "start"], [-9, -6, "end"], [-9, 15, "end"], [0, -12, "middle"], [0, 21, "middle"],
  ];
  const labels = selected.map((p, index) => {
    const cx = X(p.x), cy = Y(p.y), lw = p.name.length * 6.6 + 6, lh = 14;
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
    if (!pick) pick = { lx: cx + 9, ly: cy - 6, anchor: "start", x0: cx + 9, x1: cx + 9 + lw, y0: cy - 20, y1: cy - 4 };
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
      <line x1={X(medX)} x2={X(medX)} y1={T} y2={T + ih} stroke="#a5ff01" strokeOpacity="0.25" strokeDasharray="4 4" />
      <line x1={L} x2={w - R} y1={Y(medY)} y2={Y(medY)} stroke="#a5ff01" strokeOpacity="0.25" strokeDasharray="4 4" />
      <text x={L + iw / 2} y={h - 8} textAnchor="middle" fontSize="11" fill="#b7b7b7">{xLabel}</text>
      <text x={14} y={T + ih / 2} textAnchor="middle" fontSize="11" fill="#b7b7b7" transform={`rotate(-90 14 ${T + ih / 2})`}>{yLabel}</text>
      {plain.map((p) => (
        <circle key={p.id} className="lab-dot" cx={X(p.x)} cy={Y(p.y)} r={3.6}
          fill="rgba(255,255,255,0.28)" stroke="rgba(255,255,255,0.45)" strokeWidth={0.6}
          onClick={() => onToggle(p.id)}>
          <title>{`${p.name} (${p.detail}) · x ${formatValue(p.x)} · y ${formatValue(p.y)} — click to highlight`}</title>
        </circle>
      ))}
      {labels.map(({ p, cx, cy, pick }) => (
        <g key={p.id}>
          <circle className="lab-dot" cx={cx} cy={cy} r={5.8} fill="#a5ff01" stroke="#101011" strokeWidth={1.2}
            onClick={() => onToggle(p.id)}>
            <title>{`${p.name} (${p.detail}) · x ${formatValue(p.x)} · y ${formatValue(p.y)} — click to remove`}</title>
          </circle>
          <text x={pick.lx} y={pick.ly} textAnchor={pick.anchor} fontSize="10.5" fontWeight="700" fill="#a5ff01"
            stroke="#101011" strokeWidth={3} paintOrder="stroke" strokeLinejoin="round">{p.name}</text>
        </g>
      ))}
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

export function BarChart({ items }: { items: BarItem[] }) {
  if (!items.length) return <p className="aero-empty lab-chart-empty">No players match these filters.</p>;
  const w = 720, labelW = 190, valueW = 64, rowH = 30;
  const h = items.length * rowH + 8;
  const min = Math.min(0, ...items.map((i) => i.value));
  const max = Math.max(0, ...items.map((i) => i.value));
  const span = max - min || 1;
  const trackW = w - labelW - valueW;
  const X = (v: number) => labelW + ((v - min) / span) * trackW;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="lab-svg" role="img" aria-label="Bar chart">
      {min < 0 && <line x1={X(0)} x2={X(0)} y1={0} y2={h} stroke={GRID} />}
      {items.map((item, i) => {
        const y = i * rowH + 4;
        const x0 = Math.min(X(0), X(item.value)), bw = Math.max(2, Math.abs(X(item.value) - X(0)));
        const color = item.highlighted ? "#a5ff01" : "#5f7a2e";
        return (
          <g key={item.id}>
            <text x={0} y={y + 15} fontSize="12" fontWeight="600" fill="#ffffff">
              {item.label.length > 18 ? `${item.label.slice(0, 17)}…` : item.label}
              <tspan fill={AXIS_TEXT} fontWeight="400" fontSize="10.5">{`  ${item.detail}`}</tspan>
            </text>
            <rect x={x0} y={y + 2} width={bw} height={18} rx={4} fill={color}>
              <title>{`${item.label}: ${formatValue(item.value)}`}</title>
            </rect>
            <text x={Math.max(X(0), X(item.value)) + 6} y={y + 15} fontSize="12" fontWeight="700" fill={item.highlighted ? "#a5ff01" : "#d8d8d8"}>
              {formatValue(item.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
