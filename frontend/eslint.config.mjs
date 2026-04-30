import js from "@eslint/js";
import ts from "typescript-eslint";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import salon from "./eslint-plugin-salon/index.js";

export default [
  js.configs.recommended,
  ...ts.configs.recommended,
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "eslint-plugin-salon/**",
      "scripts/**",
    ],
  },
  {
    files: ["src/{app,components}/**/*.{ts,tsx}"],
    ignores: ["src/styles/**", "src/components/ui/**/*.stories.tsx"],
    plugins: { salon },
    rules: {
      "salon/no-raw-grays": "warn",
      "salon/no-hex-literals-in-classname": "warn",
      "salon/no-h-screen": "warn",
    },
  },
  {
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "prefer-const": "warn",
    },
  },
];
