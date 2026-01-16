import { useState } from "react";
import { useLandingData } from "../hooks/useLandingData";
import { TopMoversTicker } from "../components/TopMoversTicker";
import { TransfersTicker } from "../components/TransfersTicker";
import { MomentumGrid } from "../components/MomentumGrid";
import { FixturesTicker } from "../components/FixturesTicker";
import { FixturesTable } from "../components/FixturesTable";
import NewsTicker from "../components/NewsTicker";
import { Top100Overview } from "../components/Top100Overview";
import { BestValuePlayers } from "../components/BestValuePlayers";
import { Top100PointsChart } from "../components/Top100PointsChart";
import { PlayerModal } from "../components/PlayerModal";

export function HomePage() {
  const { data, isLoading, error } = useLandingData();
  const [modalPlayerId, setModalPlayerId] = useState<number | null>(null);

  const handlePlayerClick = (playerId: number) => {
    setModalPlayerId(playerId);
  };

  return (
    <div className="page">
      <NewsTicker news={data?.news || []} />
      <TopMoversTicker
        priceMovers={data?.movers.price}
        pointsMovers={data?.movers.points}
        loading={isLoading}
        onPlayerClick={handlePlayerClick}
      />
      <TransfersTicker
        transfersIn={data?.transfers.in}
        transfersOut={data?.transfers.out}
        loading={isLoading}
        onPlayerClick={handlePlayerClick}
      />
      
      {/* Top 100 Section */}
      <section className="top100-section">
        <div className="section-divider">
          <span>Elite Manager Insights</span>
        </div>
        <Top100Overview onPlayerClick={handlePlayerClick} />
        <BestValuePlayers onPlayerClick={handlePlayerClick} />
        <Top100PointsChart />
      </section>
      
      <MomentumGrid movers={data?.movers.points} loading={isLoading} onPlayerClick={handlePlayerClick} />
      <FixturesTicker />
      <FixturesTable />

      {/* Player Detail Modal */}
      {modalPlayerId !== null && (
        <PlayerModal
          playerId={modalPlayerId}
          onClose={() => setModalPlayerId(null)}
        />
      )}
    </div>
  );
}
