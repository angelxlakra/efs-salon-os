import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./badge";

const meta: Meta<typeof Badge> = { component: Badge, title: "UI/Badge" };
export default meta;

export const AllTones: StoryObj<typeof Badge> = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge tone="neutral">Neutral</Badge>
      <Badge tone="success">Paid</Badge>
      <Badge tone="warning">Low stock</Badge>
      <Badge tone="danger">Overdue</Badge>
      <Badge tone="info">Draft</Badge>
      <Badge tone="accent">New</Badge>
    </div>
  ),
};
