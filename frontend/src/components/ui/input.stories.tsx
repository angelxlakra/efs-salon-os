import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "./input";

const meta: Meta<typeof Input> = { component: Input, title: "UI/Input" };
export default meta;

export const Default: StoryObj<typeof Input> = {
  args: { label: "Email", placeholder: "you@example.com" },
};
export const WithHint: StoryObj<typeof Input> = {
  args: { label: "Phone", hint: "We never share your number." },
};
export const WithError: StoryObj<typeof Input> = {
  args: { label: "Email", value: "bad", error: "Invalid email address" },
};
export const WithAddons: StoryObj<typeof Input> = {
  args: { label: "Price", leadingAddon: <span>₹</span>, trailingAddon: <span className="text-text-muted text-caption">.00</span> },
};
