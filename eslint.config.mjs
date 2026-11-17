import js from "@eslint/js";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
      "**/.turbo/**",
      "**/next-env.d.ts",
      "docs/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { "simple-import-sort": simpleImportSort },
    rules: {
      // Every if/else/for/while body is a braced block.
      curly: ["error", "all"],
      // Arrow functions and function expressions only.
      "func-style": ["error", "expression"],
      // Groups: side effects, node built-ins, packages, `@/` app code, relative.
      "simple-import-sort/imports": [
        "error",
        { groups: [["^\\u0000"], ["^node:"], ["^@?\\w"], ["^@/"], ["^\\."]] },
      ],
      "simple-import-sort/exports": "error",
    },
  },
);
