import { useEffect, useRef } from "react";

interface Coordinate {
    x: number;
    y: number;
}

interface HeatmapProps {
    coordinates: Coordinate[];
    width?: number;
    height?: number;
    intensity?: number;
    radius?: number;
    className?: string;
}

export function Heatmap({
    coordinates,
    width = 300,
    height = 200,
    intensity = 0.6,
    radius = 20,
    className = "",
}: HeatmapProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Draw heat points
        coordinates.forEach((point) => {
            ctx.beginPath();
            // Map 0-100 coordinates to canvas dimensions
            const x = (point.x / 100) * width;
            const y = (point.y / 100) * height;

            const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);

            // Heatmap colors: transparent -> red -> yellow -> white (hot)
            gradient.addColorStop(0, `rgba(255, 0, 0, ${intensity})`);
            gradient.addColorStop(0.5, `rgba(255, 255, 0, ${intensity * 0.8})`);
            gradient.addColorStop(1, "rgba(255, 255, 255, 0)");

            ctx.fillStyle = gradient;
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
        });
    }, [coordinates, width, height, intensity, radius]);

    return (
        <div
            className={`heatmap-container ${className}`}
            style={{
                width,
                height,
                position: "relative",
                backgroundImage: "url('https://resources.premierleague.com/premierleague/photos/players/football-pitch.png')", // Fallback/Placeholder
                backgroundSize: "cover",
                backgroundColor: "#2e8b57", // Fallback green
                borderRadius: "8px",
                overflow: "hidden"
            }}
        >
            {/* Pitch markings overlay could go here if using CSS only */}
            <div className="pitch-markings" style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                border: "2px solid rgba(255,255,255,0.3)",
                pointerEvents: "none"
            }}>
                {/* Center circle */}
                <div style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    width: "20%",
                    height: "30%",
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderRadius: "50%",
                    transform: "translate(-50%, -50%)"
                }} />
                {/* Halfway line */}
                <div style={{
                    position: "absolute",
                    top: 0,
                    bottom: 0,
                    left: "50%",
                    borderLeft: "2px solid rgba(255,255,255,0.3)",
                }} />
                {/* Penalty Areas */}
                <div style={{
                    position: "absolute",
                    top: "20%",
                    bottom: "20%",
                    left: 0,
                    width: "15%",
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderLeft: "none"
                }} />
                <div style={{
                    position: "absolute",
                    top: "20%",
                    bottom: "20%",
                    right: 0,
                    width: "15%",
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderRight: "none"
                }} />
            </div>

            <canvas
                ref={canvasRef}
                width={width}
                height={height}
                style={{ position: "absolute", top: 0, left: 0 }}
            />
        </div>
    );
}
