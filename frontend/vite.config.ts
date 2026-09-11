import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  // Relative base only for the Electron build (loads dist over file://).
  // Web builds need "/" - with "./", assets 404 on nested routes like
  // /status/<token> and the SPA fallback serves HTML as JS.
  base: process.env.ELECTRON_BUILD ? "./" : "/",
  build: {
    outDir: "dist",
  },
});
