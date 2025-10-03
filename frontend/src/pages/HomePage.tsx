import { useLandingData } from "../hooks/useLandingData";
import { HeroIndex } from "../components/HeroIndex";
import { TopMoversTicker } from "../components/TopMoversTicker";
import { TransfersTicker } from "../components/TransfersTicker";
import { MomentumGrid } from "../components/MomentumGrid";
import { FixturePressure } from "../components/FixturePressure";
import { FixturesTable } from "../components/FixturesTable";
import { RawSnapshotStats } from "../components/RawSnapshotStats";
import NewsTicker from "../components/NewsTicker";

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
      <MomentumGrid movers={data?.movers.points} loading={isLoading} />
      <FixturePressure
        data={data?.fixture_pressure}
        loading={isLoading}
        currentGameweek={data?.current_gameweek ?? null}
      />
      <FixturesTable />
      <RawSnapshotStats
        pulse={data?.pulse}
        loading={isLoading}
        error={error}
      />
    </div>
  );
}
