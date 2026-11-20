import { defineConfig } from "vitest/config";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "/static/ui/",
  build: {
    outDir: resolve(here, "../static/ui"),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(here, "src/main.tsx"),
      output: {
        entryFileNames: "app.js",
        assetFileNames: "app.[ext]",
      },
    },
  },
  test: {
    environment: "jsdom",
  },
});
