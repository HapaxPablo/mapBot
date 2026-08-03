import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
// vite.config.ts
export default defineConfig({
  base: "/geomap/",
  plugins: [react()],
});
