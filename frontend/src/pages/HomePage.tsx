import { useLandingData } from "../hooks/useLandingData";
import { HeroIndex } from "../components/HeroIndex";
import { TopMoversTicker } from "../components/TopMoversTicker";
import { TransfersTicker } from "../components/TransfersTicker";
import { MomentumGrid } from "../components/MomentumGrid";
import { FixturePressure } from "../components/FixturePressure";
import { FixturesTable } from "../components/FixturesTable";
import NewsTicker from "../components/NewsTicker";
import { BentoGrid, BentoItem } from "../components/BentoGrid";

export function HomePage() {
  const { data, isLoading, error } = useLandingData();

  return (
    <div className="page">
      <NewsTicker news={data?.news || []} />

      <BentoGrid>
        {/* Hero Section - Spans 2 cols, 2 rows */}
        <BentoItem colSpan={2} rowSpan={2} className="p-0 overflow-hidden">
          <HeroIndex data={data?.pulse} loading={isLoading} error={error} />
        </BentoItem>

        {/* Top Movers */}
        <BentoItem colSpan={1} rowSpan={1}>
          <h3 className="section-title text-lg mb-4">Top Movers</h3>
          <TopMoversTicker
            priceMovers={data?.movers.price}
            pointsMovers={data?.movers.points}
            loading={isLoading}
          />
        </BentoItem>

        {/* Transfers */}
        <BentoItem colSpan={1} rowSpan={1}>
          <h3 className="section-title text-lg mb-4">Transfers</h3>
          <TransfersTicker
            transfersIn={data?.transfers.in}
            transfersOut={data?.transfers.out}
            loading={isLoading}
          />
        </BentoItem>

        {/* Momentum */}
        <BentoItem colSpan={2} rowSpan={1}>
          <h3 className="section-title text-lg mb-4">Momentum</h3>
          <MomentumGrid movers={data?.movers.points} loading={isLoading} />
        </BentoItem>

        {/* Fixture Pressure */}
        <BentoItem colSpan={2} rowSpan={1}>
          <h3 className="section-title text-lg mb-4">Fixture Pressure</h3>
          <FixturePressure
            data={data?.fixture_pressure}
            loading={isLoading}
            currentGameweek={data?.current_gameweek ?? null}
          />
        </BentoItem>

        {/* Fixtures Table - Full Width */}
        <BentoItem colSpan={4} className="overflow-x-auto">
          <FixturesTable />
        </BentoItem>
      </BentoGrid>
    </div>
  );
}
