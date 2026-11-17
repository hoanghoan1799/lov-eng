import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  target: "node20",
  clean: true,
  // Workspace packages ship TypeScript source, so they are bundled; real dependencies stay external.
  noExternal: [/^@park\//],
});
