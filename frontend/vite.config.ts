import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "build",
    rollupOptions: {
      output: {
        // Split the heaviest stable libraries into their own long-cached
        // chunks so app-code updates don't re-download ~1MB every release.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
          vendor: ["axios", "@tanstack/react-query", "lucide-react", "html-to-image"],
        },
      },
    },
  },
  server: {
    port: 3000,
  },
});
