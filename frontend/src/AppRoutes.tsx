import { Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { PlayersPage } from "./pages/PlayersPage";
import { AnalyzeManagerPage } from "./pages/AnalyzeManagerPage";
import { Navigation } from "./components/Navigation";

export default function App() {
  return (
    <>
      <Navigation />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/players" element={<PlayersPage />} />
        <Route path="/analyze" element={<AnalyzeManagerPage />} />
      </Routes>
    </>
  );
}
