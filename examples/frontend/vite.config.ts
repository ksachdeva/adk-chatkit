import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

const backendTarget = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5171,
    proxy: {
      "/support": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/facts": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/knowledge": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/widgets": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/cat": {
        target: backendTarget,
        changeOrigin: true,
      },
      "^/news/(chatkit|articles|events|health)": {
        target: backendTarget,
        changeOrigin: true,
      }
    },
    // For production deployments, you need to add your public domains to this list
    allowedHosts: [
      // You can remove these examples added just to demonstrate how to configure the allowlist
      ".ngrok.io",
      ".trycloudflare.com",
    ],
  },
});
