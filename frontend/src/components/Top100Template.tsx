import { useTop100Template } from "../hooks/useTop100Data";
import { Top100Player, CaptainPick } from "../types";
import "./Top100Template.css";

interface Top100TemplateProps {
  gameweek?: number;
}

export function Top100Template({ gameweek }: Top100TemplateProps) {
  const { data, isLoading, error } = useTop100Template(gameweek);

  if (error) {
    return (
      <section className="glow-card top100-template">
        <div className="glow-card-content">
          <div className="section-title">Top 100 Template</div>
          <p className="error-message">Failed to load data</p>
        </div>
      </section>
    );
  }

  const starters = data?.template_squad.filter((p) => p.is_starting) ?? [];
  const bench = data?.template_squad.filter((p) => !p.is_starting).slice(0, 4) ?? [];

  // Group starters by position
  const grouped = {
    goalkeepers: starters.filter((p) => p.element_type === 1),
    defenders: starters.filter((p) => p.element_type === 2),
    midfielders: starters.filter((p) => p.element_type === 3),
    forwards: starters.filter((p) => p.element_type === 4),
  };

  return (
    <section className="glow-card top100-template">
      <div className="glow-card-content">
        <header className="template-header">
          <div className="section-title">
            🏆 Top 100 Template
            {data && <span className="gw-badge">GW{data.game_week}</span>}
          </div>
          {data && (
            <div className="template-stats">
              <span className="stat">
                <strong>{data.manager_count}</strong> managers
              </span>
              <span className="stat">
                Avg: <strong>{data.average_points.toFixed(1)}</strong> pts
              </span>
            </div>
          )}
        </header>

        {/* Pitch View */}
        <div className="pitch-container">
          <div className="pitch">
            {/* Goalkeepers */}
            <div className="position-row gk-row">
              {isLoading
                ? [1].map((i) => <SkeletonPlayer key={i} />)
                : grouped.goalkeepers.map((p) => (
                    <PlayerCard key={p.athlete_id} player={p} />
                  ))}
            </div>

            {/* Defenders */}
            <div className="position-row def-row">
              {isLoading
                ? [1, 2, 3, 4].map((i) => <SkeletonPlayer key={i} />)
                : grouped.defenders.map((p) => (
                    <PlayerCard key={p.athlete_id} player={p} />
                  ))}
            </div>

            {/* Midfielders */}
            <div className="position-row mid-row">
              {isLoading
                ? [1, 2, 3, 4].map((i) => <SkeletonPlayer key={i} />)
                : grouped.midfielders.map((p) => (
                    <PlayerCard key={p.athlete_id} player={p} />
                  ))}
            </div>

            {/* Forwards */}
            <div className="position-row fwd-row">
              {isLoading
                ? [1, 2, 3].map((i) => <SkeletonPlayer key={i} />)
                : grouped.forwards.map((p) => (
                    <PlayerCard key={p.athlete_id} player={p} />
                  ))}
            </div>
          </div>

          {/* Bench */}
          <div className="bench">
            <div className="bench-label">Bench</div>
            <div className="bench-players">
              {isLoading
                ? [1, 2, 3, 4].map((i) => <SkeletonPlayer key={i} small />)
                : bench.map((p) => (
                    <PlayerCard key={p.athlete_id} player={p} small />
                  ))}
            </div>
          </div>
        </div>

        {/* Captain & Chip Stats */}
        <div className="template-extras">
          <CaptainSection
            captains={data?.most_captained ?? []}
            loading={isLoading}
          />
          <ChipUsageSection
            chips={data?.chip_usage ?? {}}
            loading={isLoading}
          />
        </div>
      </div>
    </section>
  );
}

function PlayerCard({
  player,
  small = false,
}: {
  player: Top100Player;
  small?: boolean;
}) {
  const ownershipColor =
    player.ownership_percentage >= 80
      ? "ownership-high"
      : player.ownership_percentage >= 50
      ? "ownership-medium"
      : "ownership-low";

  return (
    <div className={`player-card ${small ? "small" : ""} ${ownershipColor}`}>
      {player.image_url && (
        <img
          src={player.image_url}
          alt={player.web_name}
          className="player-image"
          loading="lazy"
        />
      )}
      <div className="player-info">
        <span className="player-name">{player.web_name}</span>
        <span className="player-team">{player.team_short_name}</span>
        <span className="player-ownership">
          {player.ownership_percentage.toFixed(0)}%
        </span>
      </div>
      {!small && (
        <div className="player-stats">
          <span className="player-points">{player.total_points} pts</span>
          <span className="player-cost">£{(player.now_cost / 10).toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}

function SkeletonPlayer({ small = false }: { small?: boolean }) {
  return (
    <div className={`player-card skeleton ${small ? "small" : ""}`}>
      <div className="skeleton-image" />
      <div className="skeleton-text" />
    </div>
  );
}

function CaptainSection({
  captains,
  loading,
}: {
  captains: CaptainPick[];
  loading: boolean;
}) {
  return (
    <div className="captain-section">
      <h4>👑 Most Captained</h4>
      <div className="captain-list">
        {loading
          ? [1, 2, 3].map((i) => (
              <div key={i} className="captain-item skeleton">
                <div className="skeleton-circle" />
                <div className="skeleton-text" />
              </div>
            ))
          : captains.slice(0, 3).map((c, idx) => (
              <div key={c.athlete_id} className="captain-item">
                <span className="captain-rank">{idx + 1}</span>
                {c.image_url && (
                  <img
                    src={c.image_url}
                    alt={c.web_name}
                    className="captain-image"
                  />
                )}
                <div className="captain-info">
                  <span className="captain-name">{c.web_name}</span>
                  <span className="captain-percentage">
                    {c.percentage.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
      </div>
    </div>
  );
}

function ChipUsageSection({
  chips,
  loading,
}: {
  chips: Record<string, number>;
  loading: boolean;
}) {
  const chipLabels: Record<string, string> = {
    wildcard: "🃏 Wildcard",
    freehit: "🎯 Free Hit",
    bboost: "📈 Bench Boost",
    "3xc": "3️⃣ Triple Captain",
  };

  const activeChips = Object.entries(chips).filter(([_, count]) => count > 0);

  return (
    <div className="chip-section">
      <h4>🎮 Chip Usage</h4>
      <div className="chip-list">
        {loading ? (
          <div className="chip-item skeleton">
            <div className="skeleton-text" />
          </div>
        ) : activeChips.length === 0 ? (
          <span className="no-chips">No chips played</span>
        ) : (
          activeChips.map(([chip, count]) => (
            <div key={chip} className="chip-item">
              <span className="chip-name">{chipLabels[chip] ?? chip}</span>
              <span className="chip-count">{count}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
