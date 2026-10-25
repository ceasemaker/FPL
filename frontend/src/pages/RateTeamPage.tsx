import { type FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { track } from "@amplitude/unified";
import "./MatchPage.css";
import "./TeamPage.css";
import "./PlannerPage.css";
import "./PlayerPage.css";
import "./RateTeamPage.css";

// Rate My Team (/rate-my-team): your squad's projected points over the next
// gameweeks, ranked against the top 100 managers' squads, with strengths and
// weaknesses by position and the weakest starters to look at replacing.

interface P { id: number; name: string; team: string; position: string; price: number | null; projected: number; status: string }
interface Rating {
  available: boolean; reason?: string;
  manager: { id: number; name: string; teamName: string };
  weeks: number[]; projected: number;
  top100: { count: number; gameweek: number | null; median: number | null; best: number | null; beaten: number; percentile: number | null };
  positions: { position: string; you: number; top100: number | null }[];
  weakest: P[]; bench: P[]; flagged: P[];
  record: { playerWeeks: number; modelError: number; formError: number; seasons: string[] } | null;
}
const POS_WORD: Record<string, string> = { GKP: "Goalkeeper", DEF: "Defence", MID: "Midfield", FWD: "Attack" };
const safeGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };

export function RateTeamPage() {
  const [params, setParams] = useSearchParams();
  const initial = params.get("manager") ?? safeGet("fpl_manager_id") ?? "";
  const [draft, setDraft] = useState(initial);
  const [id, setId] = useState<number | null>(/^\d+$/.test(initial) ? Number(initial) : null);
  const [data, setData] = useState<Rating | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { document.title = "Rate my team · AeroFPL"; }, []);
  useEffect(() => {
    if (!id) return;
    let alive = true;
    setLoading(true); setError(null); setData(null);
    fetch(`/api/rate-my-team/${id}/`)
      .then(async (r) => { if (!r.ok) throw new Error(r.status === 404 ? "We couldn't find that FPL manager ID." : "Something went wrong rating your team. Try again in a minute."); return r.json(); })
      .then((d) => { if (alive) { setData(d); track("Team Rated"); try { localStorage.setItem("fpl_manager_id", String(id)); } catch { /* ignore */ } } })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [id]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!/^\d+$/.test(draft.trim())) { setError("Enter the number in your FPL team's address, e.g. 576154."); return; }
    setId(Number(draft.trim()));
    const next = new URLSearchParams(params); next.set("manager", draft.trim()); setParams(next, { replace: true });
  };

  const t = data?.top100;
  const span = data?.weeks.length ? (data.weeks.length > 1 ? `GW${data.weeks[0]}–${data.weeks[data.weeks.length - 1]}` : `GW${data.weeks[0]}`) : "";
  return (
    <main className="aero-page mp-page tp-page pl-page rt-page">
      <header className="tp-index-head">
        <h1>Rate my team</h1>
        <p>Your squad's projected points over the next gameweeks, ranked against the top 100 managers' squads.</p>
      </header>
      <form className="pl-import" onSubmit={submit}>
        <label htmlFor="rt-id">FPL manager ID</label>
        <input id="rt-id" className="aero-input" inputMode="numeric" placeholder="e.g. 576154" value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button type="submit" className="aero-button primary" disabled={loading}>{loading ? "Rating…" : "Rate my team"}</button>
      </form>
      {error && <p className="mp-error" role="alert">{error}</p>}
      {loading && <div className="mp-skeleton tall" aria-busy="true" />}
      {data && !data.available && <p className="mp-note">{data.reason}</p>}
      {data && data.available && (
        <>
          <section className="mp-sheet rt-hero">
            <div className="rt-score">
              <b>{t?.percentile != null ? `${t.percentile}%` : "–"}</b>
              <span>{t?.count ? `better than ${t.beaten} of the top ${t.count} squads` : "Top-100 comparison not loaded yet"}</span>
              {t?.percentile != null && <span className="rt-meter" aria-hidden="true"><i style={{ width: `${Math.max(2, t.percentile)}%` }} /></span>}
            </div>
            <p>
              <b>{data.manager.teamName}</b> projects <b>{data.projected.toFixed(1)}</b> points over {span} (best XI, captain doubled).
              {t?.median != null && <> The top-100 squads' middle is {t.median.toFixed(1)} and their best {t.best?.toFixed(1)}.</>}
            </p>
          </section>

          <div className="pp-grid">
            <section>
              <div className="mp-sec-title"><div><h2>By position</h2><p>Projected points from your best XI, against the top 100's average.</p></div></div>
              <div className="mp-sheet mp-compare">
                <div className="mp-compare-head"><span>You</span><span>Top 100</span></div>
                {data.positions.map((p) => {
                  const total = (p.you + (p.top100 ?? 0)) || 1;
                  return (
                    <div className="mp-crow" key={p.position}>
                      <span className={`v${p.top100 != null && p.you < p.top100 ? " lo" : ""}`}>{p.you.toFixed(1)}</span>
                      <span className="l">{POS_WORD[p.position]}{p.top100 != null && <span className="mp-split" aria-hidden="true"><i style={{ width: `${(p.you / total) * 100}%` }} /><i style={{ width: `${((p.top100 ?? 0) / total) * 100}%` }} /></span>}
                        {p.top100 != null && <small className="tp-avg">{p.you >= p.top100 ? `${(p.you - p.top100).toFixed(1)} ahead` : `${(p.top100 - p.you).toFixed(1)} behind`}</small>}</span>
                      <span className="v r">{p.top100 != null ? p.top100.toFixed(1) : "–"}</span>
                    </div>
                  );
                })}
              </div>
            </section>
            <section>
              <div className="mp-sec-title"><div><h2>Weakest links</h2><p>The starters projected lowest over {span}: the first places to look for an upgrade.</p></div></div>
              <ul className="mp-sheet pp-next">
                {data.weakest.map((p) => (
                  <li key={p.id}><Link to={`/players/${p.id}`}><span className="d">{p.position}</span><span className="o">{p.name}</span><span className="d">{p.team}</span><b>{p.projected.toFixed(1)} pts</b></Link></li>
                ))}
              </ul>
              {data.flagged.length > 0 && <p className="mp-note">Flagged by FPL: {data.flagged.map((p) => p.name).join(", ")}.</p>}
              <Link className="aero-button primary rt-plan" to={`/planner?manager=${data.manager.id}`}>Plan transfers for these</Link>
            </section>
          </div>
          {data.record && <p className="mp-foot">Projections from the AeroFPL points forecast: tested on {data.record.playerWeeks.toLocaleString()} player-weeks ({data.record.seasons.join(", ")}), off by {data.record.modelError.toFixed(2)} points a week on average against {data.record.formError.toFixed(2)} for form alone. The top-100 squads are from gameweek {t?.gameweek ?? "–"}; each squad is scored the same way (best legal XI each week, captain doubled, no transfers).</p>}
        </>
      )}
    </main>
  );
}
