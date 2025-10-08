import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_BASE_URL ?? "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    preview: {
      port: parseInt(env.PORT || "5173"),
      host: true,
      strictPort: false, // Allow Render to use alternative port if needed
      allowedHosts: [
        'fpl-pulse-frontend.onrender.com',
        '.onrender.com',
      ],
      proxy: {
        "/api": {
          target: env.VITE_API_URL || "https://fpl-pulse-web.onrender.com",
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
