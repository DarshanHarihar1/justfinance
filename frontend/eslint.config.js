// Minimal ESLint flat config for Phase 1. Phase 6 will expand this with
// react-hooks, react-refresh, and jsx-a11y plugins once the real UI lands.
import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";
import globals from "globals";

export default [
  { ignores: ["dist", "node_modules"] },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsparser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
      },
    },
    plugins: { "@typescript-eslint": tseslint },
    rules: {
      ...tseslint.configs.recommended.rules,
    },
  },
  {
    files: ["vite.config.ts", "postcss.config.js", "eslint.config.js"],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
];
