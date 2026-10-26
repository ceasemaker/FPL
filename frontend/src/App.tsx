import { Suspense, lazy, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import anime from "animejs";
import { HomePage } from "./pages/HomePage";
import { PlayersPage } from "./pages/PlayersPage";
import { ComparePage } from "./pages/ComparePage";
import { AnalyzeManagerPage } from "./pages/AnalyzeManagerPage";

import { FixturesPage } from "./pages/FixturesPage";

const PriceMonitorPage = lazy(() => import("./pages/PriceChangePredictorPage").then((m) => ({ default: m.PriceChangePredictorPage })));
const StatsExplorerPage = lazy(() => import("./pages/StatsExplorerPage").then((m) => ({ default: m.StatsExplorerPage })));
const ChartLabPage = lazy(() => import("./pages/ChartLabPage").then((m) => ({ default: m.ChartLabPage })));
const MatchesPage = lazy(() => import("./pages/MatchesPage").then((m) => ({ default: m.MatchesPage })));
const TeamPage = lazy(() => import("./pages/TeamPage").then((m) => ({ default: m.TeamPage })));
const TeamsPage = lazy(() => import("./pages/TeamPage").then((m) => ({ default: m.TeamsPage })));
const PlayerPage = lazy(() => import("./pages/PlayerPage").then((m) => ({ default: m.PlayerPage })));
const PlannerPage = lazy(() => import("./pages/PlannerPage").then((m) => ({ default: m.PlannerPage })));
const DefconPage = lazy(() => import("./pages/DefconPage").then((m) => ({ default: m.DefconPage })));
const RateTeamPage = lazy(() => import("./pages/RateTeamPage").then((m) => ({ default: m.RateTeamPage })));
const WatchlistPage = lazy(() => import("./pages/WatchlistPage").then((m) => ({ default: m.WatchlistPage })));
const MatchPage = lazy(() => import("./pages/MatchPage").then((m) => ({ default: m.MatchPage })));
const MatchFromFixture = lazy(() => import("./pages/MatchPage").then((m) => ({ default: m.MatchFromFixture })));
const ModelLabPage = lazy(() => import("./pages/ModelLabPage").then((m) => ({ default: m.ModelLabPage })));
const DecisionDashboardPage = lazy(() => import("./pages/DecisionDashboardPage").then((m) => ({ default: m.DecisionDashboardPage })));

import { Navigation } from "./components/Navigation";


const bgAnimation = () => {
  anime({
    targets: "body",
    backgroundPosition: ["0% 50%", "100% 50%"],
    duration: 16000,
    easing: "linear",
    loop: true,
    direction: "alternate",
  });
};

export default function App() {
  useEffect(() => {
    bgAnimation();
  }, []);

  return (
    <>
      <Navigation />
      <Suspense fallback={<div className="page">Loading...</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/players" element={<PlayersPage />} />
          <Route path="/players/:playerId" element={<PlayerPage />} />
          <Route path="/fixtures" element={<FixturesPage />} />
          <Route path="/matches" element={<MatchesPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/teams/:teamId" element={<TeamPage />} />
          <Route path="/matches/fixture/:fixtureId" element={<MatchFromFixture />} />
          <Route path="/matches/:matchId" element={<MatchPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/analyse" element={<AnalyzeManagerPage />} />
          <Route path="/analyze" element={<Navigate to="/analyse" replace />} />
          <Route path="/planner" element={<PlannerPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/team-news" element={<Navigate to="/players?status=flagged" replace />} />
          <Route path="/rate-my-team" element={<RateTeamPage />} />
          <Route path="/defcon" element={<DefconPage />} />
          <Route path="/decision-lab" element={<DecisionDashboardPage />} />
          <Route path="/price-monitor" element={<PriceMonitorPage />} />
          <Route path="/stats" element={<StatsExplorerPage />} />
          <Route path="/chart-lab" element={<ChartLabPage />} />
          <Route path="/model-lab" element={<ModelLabPage />} />

          {/* Retired routes kept as redirects so existing links keep working. */}
          <Route path="/optimize" element={<Navigate to="/decision-lab?mode=optimizer" replace />} />
          <Route path="/price-predictor" element={<Navigate to="/price-monitor" replace />} />

        </Routes>
      </Suspense>
    </>
  );
}
