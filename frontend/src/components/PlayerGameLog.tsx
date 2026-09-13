import { useEffect, useState } from "react";
import "./PlayerGameLog.css";

interface FixtureLabel {
  opponent: string;
  was_home: boolean;
  team_h_score: number | null;
  team_a_score: number | null;
}

interface GameweekRow {
  game_week: number;
  fixtures: FixtureLabel[];
  minutes: number;
  total_points: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  goals_conceded: number;
  saves: number;
  bonus: number;
  bps: number;
  expected_goals: number;
  expected_assists: number;
  expected_goal_involvements: number;
  expected_goals_conceded: number;
  ict_index: number;
  yellow_cards: number;
  red_cards: number;
  value: number | null;
  selected: number | null;
  transfers_in: number | null;
  transfers_out: number | null;
}

interface PercentileStat {
  key: string;
  label: string;
  value: number;
  percentile: number;
  higher_is_better: boolean;
}

interface GameweeksPayload {
  data_through_gameweek: number;
  source: string;
  gameweeks: GameweekRow[];
  percentiles: {
    position: string;
    cohort_size: number;
    cohort_min_minutes: number;
    player_in_cohort: boolean;
    stats: PercentileStat[];
  };
}

const COLUMNS: { key: keyof GameweekRow; label: string; fmt?: (v: number) => string }[] = [
  { key: "minutes", label: "Min" },
  { key: "total_points", label: "Pts" },
  { key: "goals_scored", label: "G" },
  { key: "assists", label: "A" },
  { key: "expected_goals", label: "xG", fmt: (v) => v.toFixed(2) },
  { key: "expected_assists", label: "xA", fmt: (v) => v.toFixed(2) },
  { key: "expected_goal_involvements", label: "xGI", fmt: (v) => v.toFixed(2) },
  { key: "expected_goals_conceded", label: "xGC", fmt: (v) => v.toFixed(2) },
  { key: "clean_sheets", label: "CS" },
  { key: "goals_conceded", label: "GC" },
  { key: "saves", label: "Sv" },
  { key: "bonus", label: "Bon" },
  { key: "bps", label: "BPS" },
  { key: "ict_index", label: "ICT", fmt: (v) => v.toFixed(1) },
  { key: "yellow_cards", label: "YC" },
  { key: "red_cards", label: "RC" },
];

function fixtureText(fixtures: FixtureLabel[]): string {
  if (!fixtures.length) return "—";
  return fixtures
    .map((f) => {
      const venue = f.was_home ? "vs" : "@";
      const score =
        f.team_h_score !== null && f.team_a_score !== null ? ` ${f.team_h_score}-${f.team_a_score}` : "";
      return `${venue} ${f.opponent}${score}`;
    })
    .join(" · ");
}

function tone(percentile: number): string {
  if (percentile >= 80) return "high";
  if (percentile >= 50) return "mid";
  return "low";
}

export function PlayerGameLog({ playerId }: { playerId: number }) {
  const [data, setData] = useState<GameweeksPayload | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(false);
    fetch(`/api/players/${playerId}/gameweeks/`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((json: GameweeksPayload) => {
        if (!cancelled) setData(json);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [playerId]);

  if (error) {
    return <div className="gamelog-empty">Gameweek log unavailable.</div>;
  }
  if (!data) {
    return <div className="gamelog-empty">Loading gameweek log…</div>;
  }

  const { percentiles, gameweeks } = data;
  const provenance = `Official FPL stats · through GW${data.data_through_gameweek}`;

  return (
    <>
      <section className="modal-fixtures-section gamelog-section">
        <div className="gamelog-heading">
          <h3>Percentile vs {percentiles.position}s</h3>
          <span className="gamelog-provenance">
            {provenance} · cohort {percentiles.cohort_size} {percentiles.position}s with {percentiles.cohort_min_minutes}+ min
          </span>
        </div>
        {!percentiles.player_in_cohort && (
          <p className="gamelog-note">
            Under {percentiles.cohort_min_minutes} minutes this season — ranked against the cohort but not part of it.
          </p>
        )}
        {percentiles.stats.length === 0 ? (
          <div className="gamelog-empty">No season totals yet.</div>
        ) : (
          <ul className="percentile-list">
            {percentiles.stats.map((s) => (
              <li key={s.key} className="percentile-row">
                <span className="percentile-label">{s.label}</span>
                <span className="percentile-track" aria-hidden="true">
                  <span className={`percentile-fill ${tone(s.percentile)}`} style={{ width: `${s.percentile}%` }} />
                </span>
                <span className="percentile-value">{Number.isInteger(s.value) ? s.value : s.value.toFixed(2)}</span>
                <span className={`percentile-pct ${tone(s.percentile)}`}>
                  {s.percentile}
                  <small>th</small>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="modal-fixtures-section gamelog-section">
        <div className="gamelog-heading">
          <h3>Gameweek log</h3>
          <span className="gamelog-provenance">{provenance}</span>
        </div>
        {gameweeks.length === 0 ? (
          <div className="gamelog-empty">No gameweeks recorded this season.</div>
        ) : (
          <div className="gamelog-scroll">
            <table className="gamelog-table">
              <thead>
                <tr>
                  <th className="sticky">GW</th>
                  <th className="sticky-2">Fixture</th>
                  {COLUMNS.map((c) => (
                    <th key={c.key}>{c.label}</th>
                  ))}
                  <th>£</th>
                  <th>Own</th>
                  <th>Net tr.</th>
                </tr>
              </thead>
              <tbody>
                {gameweeks.map((g) => {
                  const net =
                    g.transfers_in !== null && g.transfers_out !== null ? g.transfers_in - g.transfers_out : null;
                  return (
                    <tr key={g.game_week}>
                      <td className="sticky">{g.game_week}</td>
                      <td className="sticky-2 fixture-cell">{fixtureText(g.fixtures)}</td>
                      {COLUMNS.map((c) => {
                        const v = g[c.key] as number;
                        return (
                          <td key={c.key} className={c.key === "total_points" ? "pts-cell" : undefined}>
                            {c.fmt ? c.fmt(v) : v}
                          </td>
                        );
                      })}
                      <td>{g.value !== null ? (g.value / 10).toFixed(1) : "—"}</td>
                      <td>{g.selected !== null ? `${(g.selected / 1000).toFixed(0)}k` : "—"}</td>
                      <td className={net === null ? undefined : net >= 0 ? "net-pos" : "net-neg"}>
                        {net === null ? "—" : `${net >= 0 ? "+" : ""}${(net / 1000).toFixed(0)}k`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
