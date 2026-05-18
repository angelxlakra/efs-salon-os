import type { Preview } from "@storybook/react";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import "../src/app/globals.css";
import React from "react";

const preview: Preview = {
  parameters: {
    backgrounds: { disable: true },
    controls: { expanded: true },
    layout: "centered",
  },
  decorators: [
    withThemeByDataAttribute({
      themes: { light: "light", dark: "dark" },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
    (Story) => (
      <div style={{ padding: 24, minWidth: 320, background: "var(--surface-page)" }}>
        <Story />
      </div>
    ),
  ],
};
export default preview;
