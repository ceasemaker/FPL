import React from "react";
import { initAll } from "@amplitude/unified";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/design-system.css";

// Amplitude: page views, sessions and clicks (autocapture) plus a few named
// events. Session Replay is off: we want counts, not recordings.
const amplitudeKey = import.meta.env.VITE_AMPLITUDE_API_KEY;
if (!amplitudeKey) {
  console.error("[amplitude] VITE_AMPLITUDE_API_KEY is not set — no events will be sent");
} else {
  initAll(amplitudeKey, {
    serverZone: "US",
    analytics: { autocapture: true },
    sessionReplay: { sampleRate: 0 },
  });
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
