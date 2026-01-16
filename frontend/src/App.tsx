import { Suspense, lazy, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import anime from "animejs";
import { HomePage } from "./pages/HomePage";
import { PlayersPage } from "./pages/PlayersPage";
import { ComparePage } from "./pages/ComparePage";
import { AnalyzeManagerPage } from "./pages/AnalyzeManagerPage";
import { DreamTeamPage } from "./pages/DreamTeamPage";
import { WildcardSimulatorPage } from "./pages/WildcardSimulatorPage";
import { FixturesPage } from "./pages/FixturesPage";
const OptimizeTeamPage = lazy(() => import("./pages/OptimizeTeamPage").then((m) => ({ default: m.OptimizeTeamPage })));
const TransferPlannerPage = lazy(() => import("./pages/TransferPlannerPage").then((m) => ({ default: m.TransferPlannerPage })));
const PriceChangePredictorPage = lazy(() => import("./pages/PriceChangePredictorPage").then((m) => ({ default: m.PriceChangePredictorPage })));
const LeagueAnalyticsPage = lazy(() => import("./pages/LeagueAnalyticsPage").then((m) => ({ default: m.LeagueAnalyticsPage })));
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
          <Route path="/fixtures" element={<FixturesPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/analyze" element={<AnalyzeManagerPage />} />
          <Route path="/dream-team" element={<DreamTeamPage />} />
          <Route path="/optimize" element={<OptimizeTeamPage />} />
          <Route path="/transfer-planner" element={<TransferPlannerPage />} />
          <Route path="/price-predictor" element={<PriceChangePredictorPage />} />
          <Route path="/league-analytics" element={<LeagueAnalyticsPage />} />
          <Route path="/wildcard" element={<WildcardSimulatorPage />} />
          <Route path="/wildcard/:code" element={<WildcardSimulatorPage />} />
        </Routes>
      </Suspense>
    </>
  );
}
