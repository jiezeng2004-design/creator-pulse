import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, fileURLToPath(new URL(".", import.meta.url)), "");
  // Allow a different backend (e.g. a preview instance) via VITE_API_TARGET.
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8001";
  const proxy = {
    "/api": {
      target: apiTarget,
      changeOrigin: true,
    },
  };
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    build: {
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules")) {
              // Group heavy, rarely-changing libraries into their own chunks
              // so the app chunks cache separately from the framework.
              if (id.includes("lucide-react")) return "vendor-icons";
              if (id.includes("@tanstack")) return "vendor-query";
              if (id.includes("react-router")) return "vendor-router";
              if (id.includes("react-dom") || id.includes("scheduler")) return "vendor-react";
              return "vendor";
            }
            return undefined;
          },
        },
      },
    },
    server: { proxy },
    preview: { proxy },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      include: ["src/**/*.test.{ts,tsx}"],
    },
  };
});
