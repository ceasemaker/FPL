import React from "react";
import { initAll } from "@amplitude/unified";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/design-system.css";

// Crawlers that run JavaScript (AhrefsBot, Googlebot, headless browsers) would
// otherwise show up in Amplitude as hundreds of one-page "users".
const BOT_UA = /bot|crawl|spider|slurp|headless|lighthouse|pagespeed|prerender|scanner|python|curl|wget/i;
const isBot = typeof navigator !== "undefined" && (navigator.webdriver || BOT_UA.test(navigator.userAgent));

// Amplitude: page views, sessions and clicks (autocapture) plus a few named
// events. Session Replay is off: we want counts, not recordings.
const amplitudeKey = import.meta.env.VITE_AMPLITUDE_API_KEY;
if (isBot) {
  // No analytics for crawlers.
} else if (!amplitudeKey) {
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
