import { useEffect, useRef, useState } from "react";
import "./PlayerHeatmap.css";

interface HeatmapPoint {
    x: number;
    y: number;
}

interface HeatmapData {
    player_id: number;
    player_name: string;
    gameweek: number;
    coordinates: HeatmapPoint[];
    point_count: number;
}

interface PlayerHeatmapProps {
    playerId: number;
    gameweek: number;
    className?: string;
}

export function PlayerHeatmap({ playerId, gameweek, className = "" }: PlayerHeatmapProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [data, setData] = useState<HeatmapData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;
        setIsLoading(true);
        setError(null);

        fetch(`/api/sofasport/player/${playerId}/heatmap/${gameweek}/`)
            .then(async (res) => {
                if (!res.ok) {
                    if (res.status === 404) return null; // No data is fine
                    throw new Error(`Failed to load heatmap (Status: ${res.status})`);
                }
                return res.json();
            })
            .then((data) => {
                if (isMounted) {
                    setData(data);
                }
            })
            .catch((err) => {
                if (isMounted) {
                    console.error("Heatmap fetch error:", err);
                    setError(err.message);
                }
            })
            .finally(() => {
                if (isMounted) setIsLoading(false);
            });

        return () => {
            isMounted = false;
        };
    }, [playerId, gameweek]);

    useEffect(() => {
        if (!canvasRef.current || !data || !data.coordinates.length) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw heatmap
        // Coordinates are typically 0-100. We scale to canvas size.
        // Note: SofaScore coordinates might need rotation or flipping depending on data source.
        // Usually x is length (0-100) and y is width (0-100).
        // Let's assume standard horizontal pitch for now.

        // Simple heat visualization: draw radial gradients for each point
        data.coordinates.forEach(point => {
            // Flip Y if needed (sometimes 0 is top, sometimes bottom). 
            // Assuming 0,0 is top-left.
            const x = (point.x / 100) * canvas.width;
            const y = (point.y / 100) * canvas.height;

            const radius = 15; // Adjust based on canvas size
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);

            // Heat color: Red/Orange/Yellow with transparency
            gradient.addColorStop(0, "rgba(255, 0, 0, 0.3)");
            gradient.addColorStop(0.5, "rgba(255, 165, 0, 0.15)");
            gradient.addColorStop(1, "rgba(255, 255, 0, 0)");

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
        });

    }, [data]);

    if (isLoading) return <div className="heatmap-loading">Loading heatmap...</div>;
    if (error) return <div className="heatmap-error">Error: {error}</div>;
    if (!data || !data.coordinates.length) return <div className="heatmap-empty">No heatmap data for GW{gameweek}</div>;

    return (
        <div className={`player-heatmap-container ${className}`}>
            <div className="pitch-background">
                {/* Simple CSS pitch lines */}
                <div className="pitch-line center-line"></div>
                <div className="pitch-circle center-circle"></div>
                <div className="pitch-box penalty-box-left"></div>
                <div className="pitch-box penalty-box-right"></div>
                <div className="pitch-box goal-box-left"></div>
                <div className="pitch-box goal-box-right"></div>

                <canvas
                    ref={canvasRef}
                    width={300}
                    height={200}
                    className="heatmap-canvas"
                />
            </div>
            <div className="heatmap-caption">
                Heatmap GW{gameweek} • {data.point_count} touches
            </div>
        </div>
    );
}
