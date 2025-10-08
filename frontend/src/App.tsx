import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import anime from "animejs";
import { HomePage } from "./pages/HomePage";
import { PlayersPage } from "./pages/PlayersPage";
import { ComparePage } from "./pages/ComparePage";
import { AnalyzeManagerPage } from "./pages/AnalyzeManagerPage";
import { DreamTeamPage } from "./pages/DreamTeamPage";
import { WildcardSimulatorPage } from "./pages/WildcardSimulatorPage";
import { Navigation } from "./components/Navigation";
import { MobileBlocker } from "./components/MobileBlocker";

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
    <MobileBlocker>
      <Navigation />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/players" element={<PlayersPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/analyze" element={<AnalyzeManagerPage />} />
        <Route path="/dream-team" element={<DreamTeamPage />} />
        <Route path="/wildcard" element={<WildcardSimulatorPage />} />
      </Routes>
    </MobileBlocker>
  );
}
