import { useEffect, useState } from "react";
import "./ModelLabPage.css";

interface Interval { mean: number; low: number; high: number; weeks: number }
interface Evaluation {
  createdAt: string;
  version: string;
  testSeasons: string[];
  accuracy: { player_weeks: number; model_mae: number; form_mae: number; model_corr: number; form_corr: number };
  captain: {
    weeks: number;
    points_per_week: Record<string, number>;
    versus: Record<string, Interval>;
    by_season: Record<string, Record<string, number>>;
    regret: number;
  };
  lineup: { squad_weeks: number; points_per_week: Record<string, number>; versus: Record<string, Interval> };
  accepted: { captain: boolean; lineup: boolean };
}
interface Pick { label: string; player: string; predicted: number | null; points: number | null }
interface LabPayload {
  accepted: boolean;
  season: number | null;
  nextGameweek: number | null;
  nextDeadline: string | null;
  nextPickLogged: boolean;
  model: { version: string | null; trainedAt: string | null; trainingRows: number | null; trainedThrough: { season: number; gameweek: number } | null };
  evaluation: Evaluation | null;
  record: { gameweek: number; deadline: string | null; settled: boolean; picks: Record<string, Pick> }[];
  totals: Record<string, { label: string; points: number; weeks: number }>;
}

const CAPTAIN_BASELINES: Record<string, string> = {
  elite: "Top-100 managers' captain",
  premium: "Priciest attacker who started last week",
  form: "Best form over the last six",
};
const LINEUP_BASELINES: Record<string, string> = {
  manager: "The manager's own XI and captain",
  form: "XI and captain picked by form",
};
const STRATEGY_ORDER = ["model", "ep_next", "most_captained", "premium_form"];
const SHORT_LABELS: Record<string, string> = {
  model: "AeroFPL model",
  ep_next: "FPL expected points",
  most_captained: "FPL most captained",
  premium_form: "Priciest attacker",
};

const seasonLabel = (s: number | string) => `${s}/${String((Number(s) + 1) % 100).padStart(2, "0")}`;
const signed = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(2)}`;
const deadlineText = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function verdictOf(i: Interval): { word: string; tone: "better" | "worse" | "unclear" } {
  if (i.low > 0) return { word: "Better", tone: "better" };
  if (i.high < 0) return { word: "Worse", tone: "worse" };
  return { word: "No clear difference", tone: "unclear" };
}

/** Difference vs each baseline with its 95% interval, on one shared scale around zero. */
function IntervalChart({ rows, unit }: { rows: { key: string; label: string; interval: Interval }[]; unit: string }) {
  const extent = Math.max(1, ...rows.flatMap((r) => [Math.abs(r.interval.low), Math.abs(r.interval.high)]));
  const span = Math.ceil(extent);
  const W = 360;
  const x = (v: number) => ((v + span) / (2 * span)) * W;
  const ticks = [-span, 0, span];
  return (
    <div className="ml-intervals" role="table" aria-label={`Model minus baseline, ${unit} per week, with 95% intervals`}>
      <div className="ml-int-head" role="row">
        <span role="columnheader">Compared with</span>
        <span role="columnheader" className="ml-int-axis" aria-hidden="true">
          <svg viewBox={`0 0 ${W} 16`} preserveAspectRatio="none">
            {ticks.map((t) => (
              <text key={t} x={x(t)} y={12} textAnchor={t === -span ? "start" : t === span ? "end" : "middle"}>{t === 0 ? "0" : signed(t).replace(".00", "")}</text>
            ))}
          </svg>
        </span>
        <span role="columnheader" className="ml-num">Difference</span>
      </div>
      {rows.map(({ key, label, interval }) => {
        const v = verdictOf(interval);
        return (
          <div key={key} className={`ml-int-row ${v.tone}`} role="row"
            title={`${label}: ${signed(interval.mean)} ${unit} a week (95% interval ${signed(interval.low)} to ${signed(interval.high)}) over ${interval.weeks} gameweeks`}>
            <span role="cell" className="ml-int-label">{label}</span>
            <span role="cell" className="ml-int-plot" aria-hidden="true">
              <svg viewBox={`0 0 ${W} 28`} preserveAspectRatio="none">
                <line className="ml-zero" x1={x(0)} x2={x(0)} y1={0} y2={28} />
                <line className="ml-ci" x1={x(interval.low)} x2={x(interval.high)} y1={14} y2={14} />
                <line className="ml-cap" x1={x(interval.low)} x2={x(interval.low)} y1={9} y2={19} />
                <line className="ml-cap" x1={x(interval.high)} x2={x(interval.high)} y1={9} y2={19} />
              </svg>
              <i className="ml-dot" style={{ left: `${(x(interval.mean) / W) * 100}%` }} />
            </span>
            <span role="cell" className="ml-num">
              <strong>{signed(interval.mean)}</strong>
              <small>{signed(interval.low)} to {signed(interval.high)}</small>
              <em>{v.word}</em>
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function ModelLabPage() {
  const [data, setData] = useState<LabPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/forecast-lab/")
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<LabPayload>; })
      .then((p) => alive && setData(p))
      .catch((e: Error) => alive && setError(e.message));
    return () => { alive = false; };
  }, []);

  const ev = data?.evaluation ?? null;
  const losses = ev ? Object.entries(ev.captain.versus).filter(([, i]) => i.low <= 0).map(([k]) => CAPTAIN_BASELINES[k]?.toLowerCase()) : [];

  return (
    <main className="aero-page ml-page">
      <header className="ml-head">
        <h1>Model Lab</h1>
        <p>How the AeroFPL points forecast is tested before its picks are shown, and how those picks do each week.</p>
      </header>

      {error && (
        <section className="ml-panel ml-state" role="alert">
          <h2>Couldn't load the model's record</h2>
          <p>The server didn't answer ({error}). Try again in a moment.</p>
          <button className="aero-button" onClick={() => window.location.reload()}>Try again</button>
        </section>
      )}
      {!error && !data && <section className="ml-panel ml-skeleton" aria-busy="true" aria-label="Loading" />}

      {data && (
        <section className={`ml-verdict ${data.accepted ? "pass" : "hold"}`} aria-labelledby="ml-verdict-title">
          <h2 id="ml-verdict-title">
            {!ev ? "Not tested yet" : data.accepted ? "Captain picks passed their test" : "Captain picks are on hold"}
          </h2>
          <p>
            {!ev
              ? "The backtest hasn't run on this server yet, so no picks are shown."
              : data.accepted
                ? `Across ${ev.captain.weeks} past gameweeks the model's captain beat every baseline, so the homepage shows its pick.`
                : `The model beats simple rules but not ${losses.join(" or ")}, so the homepage shows no captain. Its picks are still logged before each deadline and scored below.`}
          </p>
          {ev && (
            <p className="ml-meta">
              Tested week by week on {ev.testSeasons.join(", ")}, each week using only the weeks before it
              {data.model.trainedThrough && <> · Live model {data.model.version}, trained through {seasonLabel(data.model.trainedThrough.season)} gameweek {data.model.trainedThrough.gameweek} on {data.model.trainingRows?.toLocaleString("en-GB")} player-weeks</>}
            </p>
          )}
        </section>
      )}

      {data && (
        <section className="ml-panel" aria-labelledby="ml-live-title">
          <div className="ml-section-head">
            <h2 id="ml-live-title">This season, live</h2>
            <p>Each strategy's captain, logged before the deadline and frozen once it passes. Points are single, not doubled.</p>
          </div>
          {data.record.length === 0 ? (
            <div className="ml-empty">
              <p>
                {data.nextGameweek && data.nextDeadline
                  ? `${data.nextPickLogged ? "Picks for" : "The first picks are logged before"} gameweek ${data.nextGameweek} (deadline ${deadlineText(data.nextDeadline)})${data.nextPickLogged ? " are logged" : ""}. They appear here when the deadline passes and are scored when the gameweek finishes.`
                  : "No picks logged yet."}
              </p>
            </div>
          ) : (
            <div className="ml-table-wrap">
              <table className="ml-table">
                <thead>
                  <tr>
                    <th scope="col">GW</th>
                    {STRATEGY_ORDER.map((s) => <th key={s} scope="col">{SHORT_LABELS[s]}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {data.record.map((week) => {
                    const best = Math.max(...Object.values(week.picks).map((p) => p.points ?? -99));
                    return (
                      <tr key={week.gameweek}>
                        <th scope="row">{week.gameweek}</th>
                        {STRATEGY_ORDER.map((s) => {
                          const pick = week.picks[s];
                          if (!pick) return <td key={s} className="ml-na">–</td>;
                          return (
                            <td key={s} className={week.settled && pick.points === best ? "ml-top" : ""}>
                              <span>{pick.player}</span>
                              <b>{pick.points ?? (week.settled ? 0 : "…")}</b>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
                {Object.keys(data.totals).length > 0 && (
                  <tfoot>
                    <tr>
                      <th scope="row">Total</th>
                      {STRATEGY_ORDER.map((s) => (
                        <td key={s}>{data.totals[s] ? <b>{data.totals[s].points}</b> : "–"}</td>
                      ))}
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}
          {data.record.length > 0 && data.nextPickLogged && data.nextGameweek && data.nextDeadline && (
            <p className="ml-note">
              Picks for gameweek {data.nextGameweek} are logged and appear when its deadline passes ({deadlineText(data.nextDeadline)}).
            </p>
          )}
        </section>
      )}

      {ev && (
        <section className="ml-panel" aria-labelledby="ml-captain-title">
          <div className="ml-section-head">
            <h2 id="ml-captain-title">Captain test</h2>
            <p>Points a week the model's captain scored minus each baseline's, over {ev.captain.weeks} gameweeks, with the 95% range a re-sample of those weeks gives. To pass, every range must sit above zero.</p>
          </div>
          <IntervalChart unit="points" rows={Object.entries(CAPTAIN_BASELINES).filter(([k]) => ev.captain.versus[k]).map(([k, label]) => ({ key: k, label, interval: ev.captain.versus[k] }))} />
          <div className="ml-table-wrap">
            <table className="ml-table ml-compact">
              <caption>Captain points per gameweek (single)</caption>
              <thead>
                <tr>
                  <th scope="col">Season</th>
                  <th scope="col">Model</th>
                  {Object.entries(CAPTAIN_BASELINES).map(([k, l]) => <th key={k} scope="col">{l}</th>)}
                </tr>
              </thead>
              <tbody>
                {Object.entries(ev.captain.by_season).map(([season, row]) => (
                  <tr key={season}>
                    <th scope="row">{seasonLabel(season)}</th>
                    <td>{row.model.toFixed(2)}</td>
                    {Object.keys(CAPTAIN_BASELINES).map((k) => <td key={k}>{row[k]?.toFixed(2) ?? "–"}</td>)}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">All</th>
                  <td>{ev.captain.points_per_week.model.toFixed(2)}</td>
                  {Object.keys(CAPTAIN_BASELINES).map((k) => <td key={k}>{ev.captain.points_per_week[k]?.toFixed(2) ?? "–"}</td>)}
                </tr>
              </tfoot>
            </table>
          </div>
          <p className="ml-note">
            The best possible captain scored {ev.captain.points_per_week.best.toFixed(2)} a week, so the model left {ev.captain.regret.toFixed(2)} on the table on average.
            The top-100 baseline is the hardest and is flattered: those managers are in the sample because their choices worked out.
          </p>
        </section>
      )}

      {ev && (
        <section className="ml-panel" aria-labelledby="ml-lineup-title">
          <div className="ml-section-head">
            <h2 id="ml-lineup-title">Lineup test</h2>
            <p>On the real 15-man squads of the top-100 managers ({ev.lineup.squad_weeks.toLocaleString("en-GB")} squad-weeks), the model picks the XI and captain. Everyone is scored with ordinary autosubs and no chips.</p>
          </div>
          <IntervalChart unit="points" rows={Object.entries(LINEUP_BASELINES).filter(([k]) => ev.lineup.versus[k]).map(([k, label]) => ({ key: k, label, interval: ev.lineup.versus[k] }))} />
          <p className="ml-note">
            Points a week: model {ev.lineup.points_per_week.model.toFixed(1)}, managers {ev.lineup.points_per_week.manager.toFixed(1)}, form {ev.lineup.points_per_week.form.toFixed(1)}.
            The managers knew things the model doesn't yet: team news, injuries on the day, penalty duty.
          </p>
        </section>
      )}

      {ev && (
        <section className="ml-panel ml-split" aria-labelledby="ml-acc-title">
          <div className="ml-section-head">
            <h2 id="ml-acc-title">Forecast accuracy</h2>
            <p>Every player-week with a fixture in the test seasons ({ev.accuracy.player_weeks.toLocaleString("en-GB")}).</p>
          </div>
          <table className="ml-table ml-compact">
            <thead>
              <tr><th scope="col" /><th scope="col">Average miss (points)</th><th scope="col">Correlation</th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Model</th><td>{ev.accuracy.model_mae.toFixed(2)}</td><td>{ev.accuracy.model_corr.toFixed(2)}</td></tr>
              <tr><th scope="row">Last-six form</th><td>{ev.accuracy.form_mae.toFixed(2)}</td><td>{ev.accuracy.form_corr.toFixed(2)}</td></tr>
            </tbody>
          </table>
        </section>
      )}

      {data && (
        <section className="ml-panel ml-method" aria-labelledby="ml-method-title">
          <h2 id="ml-method-title">What the model uses, and what it doesn't</h2>
          <ul>
            <li>Four seasons of FPL gameweek data: minutes, starts, xG, xA, bonus and points, with last season's rates as the starting point for this one.</li>
            <li>Each club's recent xG for and against, and the same for its opponents; home or away; double and blank gameweeks.</li>
            <li>Not yet: team news history, bookmaker odds, or penalty duty. Live picks skip players FPL flags as injured or below a 75% chance of playing.</li>
            <li>Players with no FPL history (new signings, promoted squads) get no forecast rather than a guess.</li>
          </ul>
        </section>
      )}
    </main>
  );
}
