// Stats Explorer icon set: 20px grid, 1.5px round strokes, currentColor.

type IconProps = { size?: number; className?: string };

function Svg({ size = 18, className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const StarIcon = ({ filled, ...p }: IconProps & { filled?: boolean }) => (
  <Svg {...p}>
    <path
      d="M10 2.8l2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L2.8 8.1l5-.7z"
      fill={filled ? "currentColor" : "none"}
    />
  </Svg>
);

export const SlidersIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3.5 6h8M15 6h1.5M3.5 14h2M9 14h7.5" />
    <circle cx="13" cy="6" r="1.8" />
    <circle cx="7" cy="14" r="1.8" />
  </Svg>
);

export const ColumnsIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="3.5" width="14" height="13" rx="2" />
    <path d="M7.7 3.5v13M12.3 3.5v13" />
  </Svg>
);

export const LinkIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M8.3 11.7a3 3 0 004.2 0l2.6-2.6a3 3 0 00-4.2-4.2l-.9.9" />
    <path d="M11.7 8.3a3 3 0 00-4.2 0l-2.6 2.6a3 3 0 004.2 4.2l.9-.9" />
  </Svg>
);

export const BookmarkIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5.5 3.5h9v13l-4.5-3-4.5 3z" />
  </Svg>
);

export const ChartIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3.5 16.5h13" />
    <circle cx="7" cy="11.5" r="1.3" />
    <circle cx="10.5" cy="7.5" r="1.3" />
    <circle cx="14" cy="9.5" r="1.3" />
    <circle cx="6" cy="6" r="1.3" />
  </Svg>
);

export const CompareIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="4" width="5.5" height="12" rx="1.5" />
    <rect x="11.5" y="4" width="5.5" height="12" rx="1.5" />
  </Svg>
);

export const CloseIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5 5l10 10M15 5L5 15" />
  </Svg>
);

export const SearchIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="9" cy="9" r="5" />
    <path d="M13 13l3.5 3.5" />
  </Svg>
);

export const SortIcon = ({ dir, ...p }: IconProps & { dir: "asc" | "desc" | null }) => (
  <Svg {...p}>
    <path d="M7 8l3-3 3 3" opacity={dir === "desc" ? 0.3 : 1} />
    <path d="M7 12l3 3 3-3" opacity={dir === "asc" ? 0.3 : 1} />
  </Svg>
);

export const InfoIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="10" cy="10" r="7" />
    <path d="M10 9v4.5M10 6.6v.1" />
  </Svg>
);

export const ChevronIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7.5 5l5 5-5 5" />
  </Svg>
);
