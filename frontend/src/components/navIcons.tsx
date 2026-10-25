// Primary navigation icons: 20px grid, 1.5px round strokes, currentColor.
// Same drawing rules as components/statsExplorer/icons.tsx.

function Svg({ children }: { children: React.ReactNode }) {
  return (
    <svg
      width={20}
      height={20}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={{ display: "block", margin: "0 auto" }}
    >
      {children}
    </svg>
  );
}

export const OverviewIcon = () => (
  <Svg>
    <path d="M3.5 9.2L10 3.5l6.5 5.7" />
    <path d="M5 8v8.5h3.5v-4.5h3v4.5H15V8" />
  </Svg>
);

export const DecisionLabIcon = () => (
  <Svg>
    <path d="M7.5 3.5h5M8.5 3.5v4.2l-4.3 7.2a1.1 1.1 0 001 1.6h9.6a1.1 1.1 0 001-1.6l-4.3-7.2V3.5" />
    <path d="M6.2 12h7.6" />
  </Svg>
);

export const PlayersIcon = () => (
  <Svg>
    <circle cx="10" cy="6.5" r="3" />
    <path d="M4.5 16.5c.6-3 2.9-4.8 5.5-4.8s4.9 1.8 5.5 4.8" />
  </Svg>
);

export const StatsExplorerIcon = () => (
  <Svg>
    <rect x="3" y="3.5" width="14" height="13" rx="2" />
    <path d="M3 7.5h14M7.5 7.5v9M3 12h14" />
  </Svg>
);

export const ChartLabIcon = () => (
  <Svg>
    <path d="M3.5 16.5h13M3.5 16.5V3.5" />
    <circle cx="7.5" cy="12" r="1.2" />
    <circle cx="11" cy="8" r="1.2" />
    <circle cx="14.5" cy="10.5" r="1.2" />
  </Svg>
);

export const ModelLabIcon = () => (
  <Svg>
    <path d="M3.5 14.5a6.5 6.5 0 0113 0" />
    <path d="M10 14.5l3-4.5" />
    <path d="M3.5 17h13" />
  </Svg>
);

export const FixturesIcon = () => (
  <Svg>
    <rect x="3" y="4.5" width="14" height="12" rx="2" />
    <path d="M3 8.5h14M7 3v3M13 3v3" />
  </Svg>
);

export const PriceMonitorIcon = () => (
  <Svg>
    <path d="M3.5 14l4-4.5 3 2.5 5.5-6" />
    <path d="M12.5 6h3.5v3.5" />
  </Svg>
);

export const AnalyzeManagerIcon = () => (
  <Svg>
    <circle cx="8.5" cy="8.5" r="4.5" />
    <path d="M12 12l4.5 4.5" />
    <path d="M6.8 9.8c.4-.9 1-1.3 1.7-1.3s1.3.4 1.7 1.3" />
    <circle cx="8.5" cy="6.7" r=".9" />
  </Svg>
);

export const MatchesIcon = () => (
  <Svg>
    <circle cx="10" cy="10" r="6.5" />
    <path d="M10 6.2l2.6 1.9-1 3.1H8.4l-1-3.1z" />
    <path d="M10 3.5v2.7M16.2 8.1l-3.6 0M14 15.2l-2.4-4M6 15.2l2.4-4M3.8 8.1l3.6 0" />
  </Svg>
);

export const TeamsIcon = () => (
  <Svg>
    <path d="M10 3l5.5 2v4.6c0 3.4-2.3 5.9-5.5 7.4-3.2-1.5-5.5-4-5.5-7.4V5z" />
    <path d="M10 6.5v7" />
  </Svg>
);

export const PlannerIcon = () => (
  <Svg>
    <rect x="3.5" y="4.5" width="13" height="12" rx="2" />
    <path d="M3.5 8.5h13M7 3v3M13 3v3" />
    <path d="M7 12.2h3.5m0 0-1.6-1.5m1.6 1.5-1.6 1.5" />
  </Svg>
);

export const TeamNewsIcon = () => (
  <Svg>
    <rect x="3.5" y="4" width="13" height="12.5" rx="2" />
    <path d="M6.5 7.5h7M6.5 10.5h7M6.5 13.5h4" />
  </Svg>
);

export const DefconIcon = () => (
  <Svg>
    <path d="M10 3l6 2.2v4.3c0 3.6-2.4 6.2-6 7.5-3.6-1.3-6-3.9-6-7.5V5.2z" />
    <path d="M7.2 10.2l2 2 3.8-4" />
  </Svg>
);

export const RateIcon = () => (
  <Svg>
    <path d="M10 3.2l2 4.1 4.5.6-3.3 3.1.8 4.5-4-2.2-4 2.2.8-4.5L3.5 7.9 8 7.3z" />
  </Svg>
);

export const MenuIcon = () => (
  <Svg>
    <path d="M3.5 6h13M3.5 10h13M3.5 14h13" />
  </Svg>
);
