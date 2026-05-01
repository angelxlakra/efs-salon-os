import type { Meta, StoryObj } from "@storybook/react";
import { Trash2, Plus } from "lucide-react";
import { Button } from "./button";

const meta: Meta<typeof Button> = { component: Button, title: "UI/Button" };
export default meta;

export const Variants: StoryObj<typeof Button> = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Button>Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="danger">Delete</Button>
      <Button variant="icon" aria-label="Add"><Plus /></Button>
    </div>
  ),
};

export const Sizes: StoryObj<typeof Button> = {
  render: () => (
    <div className="flex items-center gap-3">
      <Button size="sm">Small</Button>
      <Button size="md">Medium</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
};

export const Loading: StoryObj<typeof Button> = {
  args: { loading: true, children: "Saving…" },
};

export const WithIcons: StoryObj<typeof Button> = {
  args: { leadingIcon: <Plus />, children: "New bill" },
};

export const Danger: StoryObj<typeof Button> = {
  args: { variant: "danger", leadingIcon: <Trash2 />, children: "Delete customer" },
};
