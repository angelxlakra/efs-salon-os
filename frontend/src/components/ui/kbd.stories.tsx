import type { Meta, StoryObj } from "@storybook/react";
import { Kbd } from "./kbd";

const meta: Meta<typeof Kbd> = { component: Kbd, title: "UI/Kbd" };
export default meta;

export const Default: StoryObj<typeof Kbd> = { args: { keys: ["⌘", "K"] } };
export const Sequence: StoryObj<typeof Kbd> = { args: { keys: ["G", "then", "D"] } };
