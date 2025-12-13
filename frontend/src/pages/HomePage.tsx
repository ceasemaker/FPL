import { useLandingData } from "../hooks/useLandingData";
import { HeroIndex } from "../components/HeroIndex";
import { TopMoversTicker } from "../components/TopMoversTicker";
import { TransfersTicker } from "../components/TransfersTicker";
import { MomentumGrid } from "../components/MomentumGrid";
import { FixturePressure } from "../components/FixturePressure";
import { FixturesTable } from "../components/FixturesTable";
import NewsTicker from "../components/NewsTicker";
import { Top100Overview } from "../components/Top100Overview";
import { BestValuePlayers } from "../components/BestValuePlayers";
import { Top100PointsChart } from "../components/Top100PointsChart";
import { Top100Extras } from "../components/Top100Extras";

export function HomePage() {
  const { data, isLoading, error } = useLandingData();

  return (
    <div className="page">
      <NewsTicker news={data?.news || []} />
      <HeroIndex data={data?.pulse} loading={isLoading} error={error} />
      <TopMoversTicker
        priceMovers={data?.movers.price}
        pointsMovers={data?.movers.points}
        loading={isLoading}
      />
      <TransfersTicker
        transfersIn={data?.transfers.in}
        transfersOut={data?.transfers.out}
        loading={isLoading}
      />
      
      {/* Top 100 Section */}
      <section className="top100-section">
        <div className="section-divider">
          <span>Elite Manager Insights</span>
        </div>
        <Top100Overview />
        <BestValuePlayers />
        <Top100PointsChart />
      </section>
      
      <MomentumGrid movers={data?.movers.points} loading={isLoading} />
      <FixturePressure
        data={data?.fixture_pressure}
        loading={isLoading}
        currentGameweek={data?.current_gameweek ?? null}
      />
      <FixturesTable />
    </div>
  );
}
