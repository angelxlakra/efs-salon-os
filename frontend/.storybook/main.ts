import type { StorybookConfig } from "@storybook/nextjs-vite";
import path from "node:path";

const config: StorybookConfig = {
  stories: ["../src/components/ui/*.stories.tsx"],
  addons: ["@storybook/addon-docs", "@storybook/addon-themes"],
  framework: { name: "@storybook/nextjs-vite", options: {} },
  staticDirs: ["../public"],
  viteFinal: async (cfg) => {
    cfg.resolve ||= {};
    cfg.resolve.alias = {
      ...(cfg.resolve.alias ?? {}),
      "@": path.resolve(__dirname, "../src"),
    };
    return cfg;
  },
};
export default config;
