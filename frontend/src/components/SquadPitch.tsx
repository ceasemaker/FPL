import { Link } from "react-router-dom";
import "./planner/PlannerPitch.css";

// A read-only FPL squad on the pitch: the XI in formation rows, the bench
// underneath in substitution order. Same look as the planner's pitch.

const SHIRT = "https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_";
const ROWS = ["GKP", "DEF", "MID", "FWD"] as const;

export interface SquadPlayer { id: number; name: string; team: string; teamShort: string; position: (typeof ROWS)[number]; points: number }
export interface Squad<P extends SquadPlayer = SquadPlayer> { players: P[]; xi: number[]; bench: number[]; captain: number; vice: number }

interface Props<P extends SquadPlayer> {
  squad: Squad<P>;
  stat: (p: P) => string;         // the figure under each name, e.g. "98%" or "68 pts"
  describe: (p: P) => string;     // the same, spelt out for screen readers
}

export function SquadPitch<P extends SquadPlayer>({ squad, stat, describe }: Props<P>) {
  const byId = new Map(squad.players.map((p) => [p.id, p]));
  const card = (id: number, benchSlot?: string) => {
    const p = byId.get(id);
    if (!p) return null;
    const arm = squad.captain === id ? "captain" : squad.vice === id ? "vice-captain" : "";
    return (
      <div className="pp-slot" key={id}>
        {benchSlot && <span className="pp-bench-label">{benchSlot}</span>}
        <Link to={`/players/${id}`} className="pp-card" aria-label={`${p.name}, ${p.teamShort}, ${describe(p)}${arm ? `, ${arm}` : ""}`}>
          {arm === "captain" && <span className="pp-arm c" title="Captain">C</span>}
          {arm === "vice-captain" && <span className="pp-arm v" title="Vice-captain">V</span>}
          <img className="pp-shirt" src={`${SHIRT}${p.team}${p.position === "GKP" ? "_1" : ""}-110.webp`} alt="" width={56} height={56} loading="lazy" />
          <span className="pp-name">{p.name}</span>
          <span className="pp-info"><span className="pp-opp">{p.teamShort}</span><b>{stat(p)}</b></span>
        </Link>
      </div>
    );
  };

  return (
    <div className="pp">
      <div className="pp-pitch">
        <svg className="pp-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <rect x="1" y="1" width="98" height="98" />
          <rect x="22" y="1" width="56" height="17" />
          <rect x="37" y="1" width="26" height="6" />
          <path d="M40 18a10 6 0 0 0 20 0" />
          <path d="M1 99h98" />
          <path d="M38 99a12 9 0 0 1 24 0" />
        </svg>
        {ROWS.map((pos) => (
          <div className="pp-row" key={pos}>{squad.xi.filter((id) => byId.get(id)?.position === pos).map((id) => card(id))}</div>
        ))}
      </div>
      <div className="pp-bench" aria-label="Bench">
        <span className="pp-bench-title">Bench</span>
        <div className="pp-row">{squad.bench.map((id, i) => card(id, i === 0 ? "GK" : String(i)))}</div>
      </div>
    </div>
  );
}
