import { FixturePressureResponse } from "../types";

interface FixturePressureProps {
  data: FixturePressureResponse | undefined;
  loading: boolean;
  currentGameweek: number | null;
}

export function FixturePressure({ data, loading, currentGameweek }: FixturePressureProps) {
  const easiest = data?.easiest ?? [];
  const hardest = data?.hardest ?? [];

  return (
    <section className="glow-card fixture-pressure">
      <div className="glow-card-content">
        <div className="section-title">
          Fixture pressure
          {currentGameweek ? (
            <span className="section-subtitle">Looking ahead to GW {currentGameweek + 1} - {currentGameweek + 4}</span>
          ) : null}
        </div>
        <div className="fixture-columns">
          <FixtureColumn title="Easiest runs" gradient="ease" items={loading ? skeletonItems() : easiest} />
          <FixtureColumn title="Toughest runs" gradient="tough" items={loading ? skeletonItems() : hardest} />
        </div>
      </div>
    </section>
  );
}

interface FixtureColumnProps {
  title: string;
  gradient: "ease" | "tough";
  items: Array<{ team: string; score: number }>;
}

function FixtureColumn({ title, gradient, items }: FixtureColumnProps) {
  return (
    <div className={`fixture-column ${gradient}`}>
      <header>
        <h3>{title}</h3>
        <span>Aggregate difficulty</span>
      </header>
      <ul>
        {items.map((item, index) => (
          <li key={`${item.team}-${index}`}>
            <span className="team">{item.team}</span>
            <span className="score">{item.score}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function skeletonItems(): Array<{ team: string; score: number }> {
  return new Array(5).fill(null).map((_, idx) => ({ team: `--`, score: idx }));
}
