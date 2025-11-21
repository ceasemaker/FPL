import { ReactNode } from "react";

interface BentoGridProps {
    children: ReactNode;
    className?: string;
}

interface BentoItemProps {
    children: ReactNode;
    className?: string;
    colSpan?: 1 | 2 | 3 | 4;
    rowSpan?: 1 | 2;
}

export function BentoGrid({ children, className = "" }: BentoGridProps) {
    return (
        <div
            className={`grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 auto-rows-[minmax(180px,auto)] ${className}`}
            style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: "1.5rem",
            }}
        >
            {children}
        </div>
    );
}

export function BentoItem({
    children,
    className = "",
    colSpan = 1,
    rowSpan = 1,
}: BentoItemProps) {
    return (
        <div
            className={`bento-card glow-card ${className}`}
            style={{
                gridColumn: `span ${colSpan}`,
                gridRow: `span ${rowSpan}`,
                display: "flex",
                flexDirection: "column",
                height: "100%",
                minHeight: "200px",
            }}
        >
            <div className="glow-card-content h-full flex flex-col">
                {children}
            </div>
        </div>
    );
}
