import { defineConfig } from "vite";
import path from "path";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ command }) => {
  return {
    plugins: [tailwindcss()],
    base: "/static/",
    server: {
      origin: "http://localhost:5173",
      // Allow Django dev server (8000) to load module scripts from Vite.
      cors: {
        origin: ["http://localhost:8000", "http://127.0.0.1:8000"],
      },
    },
    clearScreen: false,
    build: {
      // Where Vite will save its output files.
      // This should be something in your settings.STATICFILES_DIRS
      outDir: path.resolve(__dirname, "./static"),
      emptyOutDir: false, // Preserve the outDir to not clobber Django's other files.
      manifest: "manifest.json",
      rollupOptions: {
        input: {
          shifter: path.resolve(__dirname, "./assets/js/shifter.js"),
          filepond: path.resolve(__dirname, "./assets/js/filepond.js"),
          sitesettings: path.resolve(__dirname, "./assets/js/site-settings.js"),
        },
        output: {
          // Output JS bundles to js/ directory with -bundle suffix
          entryFileNames: `js/[name]-bundle.js`,
          assetFileNames: `css/[name].css`,
        },
      },
    },
  };
});
