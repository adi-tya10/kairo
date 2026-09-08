import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      // Exclude Rust build artifacts — Windows locks .exe files during compilation
      // causing EBUSY errors when Vite tries to watch them
      ignored: ["**/src-tauri/target/**"],
    },
  },
});
