import { useEffect, useRef } from "react";
import anime from "animejs";

interface HeartbeatProps {
    value: number; // 0 to 100+
    width?: number;
    height?: number;
}

export function Heartbeat({ value, width = 300, height = 100 }: HeartbeatProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<anime.AnimeInstance | null>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Set canvas resolution
        canvas.width = width * 2;
        canvas.height = height * 2;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.scale(2, 2);

        let points: { x: number; y: number }[] = [];
        const numPoints = 50;
        const step = width / numPoints;

        // Initialize points
        for (let i = 0; i <= numPoints; i++) {
            points.push({ x: i * step, y: height / 2 });
        }

        const draw = () => {
            ctx.clearRect(0, 0, width, height);

            // Draw baseline
            ctx.beginPath();
            ctx.strokeStyle = "rgba(22, 242, 255, 0.1)";
            ctx.lineWidth = 1;
            ctx.moveTo(0, height / 2);
            ctx.lineTo(width, height / 2);
            ctx.stroke();

            // Draw heartbeat
            ctx.beginPath();
            ctx.strokeStyle = "#16f2ff";
            ctx.lineWidth = 2;
            ctx.lineJoin = "round";
            ctx.shadowBlur = 10;
            ctx.shadowColor = "#16f2ff";

            // Create pulse effect based on value
            const intensity = Math.min(value / 100000, 1.5); // Normalize value
            const time = Date.now() / 200;

            ctx.moveTo(points[0].x, points[0].y);

            for (let i = 1; i < points.length; i++) {
                const point = points[i];

                // Simulate EKG wave
                let yOffset = 0;
                const x = point.x;

                // Main pulse
                const pulseX = (time * 100) % (width + 100) - 50;
                const dist = Math.abs(x - pulseX);

                if (dist < 30) {
                    // QRS complex simulation
                    if (dist < 5) yOffset = -40 * intensity;
                    else if (dist < 10) yOffset = 20 * intensity;
                    else if (dist < 20) yOffset = -10 * intensity;
                }

                // Add some noise
                yOffset += (Math.random() - 0.5) * 2;

                const targetY = (height / 2) + yOffset;

                // Smooth transition
                point.y += (targetY - point.y) * 0.3;

                ctx.lineTo(point.x, point.y);
            }

            ctx.stroke();
            requestAnimationFrame(draw);
        };

        const animId = requestAnimationFrame(draw);

        return () => {
            cancelAnimationFrame(animId);
        };
    }, [width, height, value]);

    return (
        <div className="heartbeat-container" style={{ position: "relative", width, height }}>
            <canvas ref={canvasRef} />
            <div
                className="heartbeat-value"
                style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    fontSize: "2rem",
                    fontWeight: 700,
                    color: "#fff",
                    textShadow: "0 0 20px rgba(22, 242, 255, 0.5)",
                    pointerEvents: "none"
                }}
            >
                {value.toLocaleString()}
            </div>
        </div>
    );
}
