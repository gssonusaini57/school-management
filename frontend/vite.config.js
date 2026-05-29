var _a, _b;
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { writeFileSync } from "node:fs";
// Build id used by the runtime cache-bust check. Each build gets a fresh id;
// it's both injected into the bundle as `__BUILD_ID__` (via `define`) and
// written to `dist/version.json` after build. At runtime the SPA polls
// `version.json` and reloads with a cache-bust query when the values diverge,
// so users never have to hard-refresh after a deploy.
var BUILD_ID = (_a = process.env.VITE_BUILD_ID) !== null && _a !== void 0 ? _a : new Date().toISOString().replace(/[:.]/g, "-");
function emitVersionJson() {
    return {
        name: "kis-version-json",
        apply: "build",
        closeBundle: function () {
            var outDir = path.resolve(__dirname, "dist");
            writeFileSync(path.join(outDir, "version.json"), JSON.stringify({ build_id: BUILD_ID, built_at: new Date().toISOString() }, null, 2));
        },
    };
}
// Served under a per-environment base path. TEST mounts the staff portal at
// /school/admin/ (shared expressonly.in box); PROD mounts it at the domain root
// /admin/ (dedicated kisschool.in). The base is build-time configurable via the
// VITE_BASE env var (set by scripts/deploy/<env>/env.sh); the default keeps TEST
// behaviour byte-identical. Everything downstream (router basename, version.json
// poll, login redirect, APK url) derives from import.meta.env.BASE_URL, so this
// single knob flips the whole SPA.
// Dev runs locally on http://localhost:5173 with /api proxied to FastAPI on 8000.
var BASE = (_b = process.env.VITE_BASE) !== null && _b !== void 0 ? _b : "/school/admin/";
// Substitute %BASE_URL% in index.html with the resolved base at build time. Used
// for the favicon, which must be an ABSOLUTE base-relative path (a plain relative
// path would resolve against the current SPA route on deep links and 404).
function htmlBaseUrl() {
    return {
        name: "kis-html-base-url",
        transformIndexHtml: function (html) {
            return html.replace(/%BASE_URL%/g, BASE);
        },
    };
}
export default defineConfig({
    base: BASE,
    plugins: [react(), emitVersionJson(), htmlBaseUrl()],
    define: {
        __BUILD_ID__: JSON.stringify(BUILD_ID),
    },
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
