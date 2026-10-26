// Design tokens for code that draws with JavaScript (SVG attributes, canvas).
// Mirrors the CSS custom properties in design-system.css; keep the two in step.

export const colour = {
  ink: "#101011",
  surface: "#1b1b1d",
  raised: "#262628",
  text: "#f5f5f7",
  textDim: "#a1a1a6",
  textMuted: "#86868b",
  white: "#ffffff",
  lime: "#a5ff01",
  /* A dark lime for bars and lines that sit behind a lime highlight. */
  limeDeep: "#5f7a2e",
  negative: "#ff4c5e",
  /* Coral text on dark panels, and its dark track. */
  negativeSoft: "#ff7a87",
  negativeDeep: "#7a3b3b",
  warn: "#e2b75b",
  yellowCard: "#f5d64c",
  /* Neutral marks: "before" dots, unhighlighted points. */
  mark: "#6b6b6b",
} as const;

/* Categorical series, Apple's dark-mode system colours after our lime. */
export const series = [colour.lime, "#64d2ff", "#ffd60a", "#ff6482", "#bf5af2", "#ff9f0a"] as const;
