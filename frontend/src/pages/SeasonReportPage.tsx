import { track } from "@amplitude/unified";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { buildReport, rankText, type ReportRow } from "../components/seasonReport/reportModel";
import { loadExplorer } from "../components/statsExplorer/StatSheet";
import { ordinal, type ExplorerPayload } from "../components/statsExplorer/explorerModel";
import "./SeasonReportPage.css";

// Season report (/players/:id/report): one player's Premier League season on
// one page, ranked against the same position, from the Stats Explorer feed.
// This season or last; "Save as PDF" uses the browser's print dialog.

interface PageInfo {
  id: number; code: number; name: string; short: string; position: string; season: number;
  team: { name: string; short: string };
  byCompetition: { competitionId: number; competition: string; apps: number; starts: number; minutes: number; goals: number; assists: number }[];
}

const POSITION_WORD: Record<string, string> = { GKP: "goalkeeper", DEF: "defender", MID: "midfielder", FWD: "forward" };
const label = (season: number) => `${season}/${String((season + 1) % 100).padStart(2, "0")}`;

export function SeasonReportPage() {
  const { playerId } = useParams();
  const id = Number(playerId);
  const [params, setParams] = useSearchParams();
  const [info, setInfo] = useState<PageInfo | null | undefined>(undefined);
  const [payload, setPayload] = useState<ExplorerPayload | null | undefined>(undefined);
  const current = info?.season ?? null;
  const season = Number(params.get("season")) || current;

  useEffect(() => {
    let alive = true;
    fetch(`/api/players/${id}/page/`).then((r) => (r.ok ? r.json() : null)).then((d) => { if (alive) setInfo(d); }).catch(() => { if (alive) setInfo(null); });
    return () => { alive = false; };
  }, [id]);

  useEffect(() => {
    if (!season) return;
    let alive = true;
    setPayload(undefined);
    loadExplorer(season).then((d) => { if (alive) setPayload(d); });
    return () => { alive = false; };
  }, [season]);

  const report = useMemo(() => (payload ? buildReport(payload, id, { name: info?.short, finished: !!current && payload.season < current }) : null), [payload, id, info, current]);
  useEffect(() => {
    if (info) document.title = `${info.name}: season report · AeroFPL`;
    if (report) track("Season Report Viewed", { player: id, season: report.seasonLabel });
  }, [info, report, id]);

  const pick = (s: number) => { const next = new URLSearchParams(params); next.set("season", String(s)); setParams(next, { replace: true }); };

  if (info === null) {
    return <main className="aero-page sr-page"><h1>Season report</h1><p className="aero-error">We couldn't find that player.</p></main>;
  }

  return (
    <main className="aero-page sr-page">
      <nav className="sr-crumbs" aria-label="Breadcrumb">
        <Link to="/players">Players</Link><span aria-hidden="true">/</span>
        {info ? <Link to={`/players/${id}`}>{info.name}</Link> : <span>Player</span>}<span aria-hidden="true">/</span><span>Season report</span>
      </nav>

      <header className="sr-head">
        {info && <img className="sr-photo" src={`https://resources.premierleague.com/premierleague25/photos/players/110x140/${info.code}.png`} alt="" width={88} height={112} />}
        <div>
          <h1>{info?.name ?? "Season report"}</h1>
          {info && <p className="sr-sub">{info.team.name}, {POSITION_WORD[info.position] ?? "player"}. Premier League {season ? label(season) : ""}.</p>}
        </div>
        <div className="sr-tools">
          {current && (
            <div className="aero-segmented" role="group" aria-label="Season">
              {[current - 1, current].map((s) => (
                <button key={s} type="button" aria-pressed={season === s} onClick={() => pick(s)}>{label(s)}</button>
              ))}
            </div>
          )}
          <button type="button" className="aero-button" onClick={() => { track("Season Report Printed", { player: id }); window.print(); }} disabled={!report}>Save as PDF</button>
        </div>
      </header>

      {payload === undefined && <div className="mp-skeleton tall" aria-busy="true" />}
      {payload === null && <p className="aero-error">The season's stats couldn't be loaded. Try again in a minute.</p>}
      {payload && !report && <p className="aero-note">No Premier League stats for this player in {label(season!)}.</p>}

      {report && (
        <>
          <p className="sr-summary">{report.summary.join(" ")}</p>
          {report.smallSample && <p className="aero-note">Only {report.minutes.toLocaleString("en-GB")} league minutes so far, so these ranks can swing on a game or two.</p>}

          <dl className="sr-figures">
            {report.headline.map((h) => <div key={h.label}><dt>{h.label}</dt><dd>{h.value}</dd></div>)}
          </dl>

          {report.ranked && (
            <div className="sr-two">
              <ListPanel title="Strengths" rows={report.strengths} report={report} empty="Nothing at the 80th percentile or above yet." />
              <ListPanel title="Weaker areas" rows={report.weaker} report={report} empty="Nothing below the 25th percentile." />
            </div>
          )}

          {report.sections.map((s) => (
            <section key={s.title} className="sr-section" aria-labelledby={`sr-${s.title}`}>
              <h2 id={`sr-${s.title}`}>{s.title}</h2>
              <div className="sr-sheet">
                <table className="sr-table">
                  <thead>
                    <tr><th scope="col" className="text">Stat</th><th scope="col">Season</th><th scope="col">Per 90</th>{report.ranked && <><th scope="col" className="pct">Percentile among {report.positionName}</th><th scope="col">Rank</th></>}</tr>
                  </thead>
                  <tbody>
                    {s.rows.map((r) => (
                      <tr key={r.stat.key}>
                        <th scope="row" title={r.stat.help}>{r.stat.label}</th>
                        <td>{r.totalDisplay}</td>
                        <td>{r.per90 ? r.display : "–"}</td>
                        {report.ranked && (
                          <>
                            <td className="pct"><Bar pct={r.pct} /></td>
                            <td className="rank">{r.rank ? <>{ordinal(r.rank)}<span> of {report.group}</span></> : "–"}</td>
                          </>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}

          {info && season === current && info.byCompetition.length > 0 && (
            <section className="sr-section" aria-labelledby="sr-comps">
              <h2 id="sr-comps">Every competition this season</h2>
              <div className="sr-sheet">
                <table className="sr-table">
                  <thead><tr><th scope="col" className="text">Competition</th><th scope="col">Apps</th><th scope="col">Starts</th><th scope="col">Minutes</th><th scope="col">Goals</th><th scope="col">Assists</th></tr></thead>
                  <tbody>
                    {info.byCompetition.map((c) => (
                      <tr key={c.competitionId}><th scope="row">{c.competition}</th><td>{c.apps}</td><td>{c.starts}</td><td>{c.minutes.toLocaleString("en-GB")}</td><td>{c.goals}</td><td>{c.assists}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="footnote sr-note">From match records, so it can run a game ahead of the Opta season sheets above.</p>
            </section>
          )}

          <p className="sr-foot">
            {report.ranked
              ? `Compared with the ${report.group} ${report.positionName} who played at least ${report.minMinutes.toLocaleString("en-GB")} Premier League minutes in ${report.seasonLabel}. `
              : ""}
            Opta data from the Premier League's stats feeds, refreshed overnight. Per 90 where it applies. Lime marks the top 7% of the position.
          </p>
        </>
      )}
    </main>
  );
}

function Bar({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="sr-bar" aria-label="Not ranked" />;
  return (
    <span className="sr-bar" role="img" aria-label={`${Math.round(pct)}th percentile`}>
      <i className={pct >= 93 ? "top" : ""} style={{ width: `${Math.max(3, pct)}%` }} />
    </span>
  );
}

function ListPanel({ title, rows, report, empty }: { title: string; rows: ReportRow[]; report: { group: number; positionName: string }; empty: string }) {
  return (
    <section className="sr-list" aria-label={title}>
      <h2>{title}</h2>
      {rows.length === 0 ? <p className="sr-empty">{empty}</p> : (
        <ul>
          {rows.map((r) => (
            <li key={r.stat.key}>
              <span>{r.stat.label}</span>
              <b>{r.display}{r.per90 && <small> per 90</small>}</b>
              <em>{rankText(r, report)}</em>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
