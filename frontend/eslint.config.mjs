import js from "@eslint/js";
import ts from "typescript-eslint";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

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
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "prefer-const": "warn",
    },
  },
];
