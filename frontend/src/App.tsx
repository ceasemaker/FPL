import { Suspense, lazy, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import anime from "animejs";
import { HomePage } from "./pages/HomePage";
import { PlayersPage } from "./pages/PlayersPage";
import { ComparePage } from "./pages/ComparePage";
import { AnalyzeManagerPage } from "./pages/AnalyzeManagerPage";

import { FixturesPage } from "./pages/FixturesPage";

const PriceMonitorPage = lazy(() => import("./pages/PriceChangePredictorPage").then((m) => ({ default: m.PriceChangePredictorPage })));
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
          <Route path="/fixtures" element={<FixturesPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/analyze" element={<AnalyzeManagerPage />} />
          <Route path="/decision-lab" element={<DecisionDashboardPage />} />
          <Route path="/price-monitor" element={<PriceMonitorPage />} />

          {/* Retired routes kept as redirects so existing links keep working. */}
          <Route path="/optimize" element={<Navigate to="/decision-lab?mode=optimizer" replace />} />
          <Route path="/price-predictor" element={<Navigate to="/price-monitor" replace />} />

        </Routes>
      </Suspense>
    </>
  );
}
