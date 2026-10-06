import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail clearly if the port is taken, rather than moving to another
    // Anything starting with /api is forwarded to the Python backend.
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
