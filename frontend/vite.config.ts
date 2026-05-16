import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Served from https://expressonly.in/school/admin/ in prod.
// Dev runs locally on http://localhost:5173 with /api proxied to FastAPI on 8000.
// (The marketing site lives at /school/ — this app is the staff portal at /school/admin/.)
export default defineConfig({
  base: "/school/admin/",
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", sourcemap: false },
});
