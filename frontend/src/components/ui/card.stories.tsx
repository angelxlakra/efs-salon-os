import type { Meta, StoryObj } from "@storybook/react";
import { Card } from "./card";
import { Badge } from "./badge";

const meta: Meta<typeof Card> = { component: Card, title: "UI/Card" };
export default meta;

export const KPI: StoryObj<typeof Card> = {
  render: () => (
    <Card density="lg" className="w-[280px]">
      <Card.Header title="Revenue" description="Today" />
      <Card.Body>
        <div className="text-money-lg text-text-primary">₹24,800</div>
        <div className="text-caption text-text-muted mt-1">+12% vs 7-day avg</div>
      </Card.Body>
    </Card>
  ),
};

export const WithAction: StoryObj<typeof Card> = {
  render: () => (
    <Card density="md" className="w-[400px]">
      <Card.Header title="Service queue" description="4 waiting" action={<Badge tone="accent">4</Badge>} />
      <Card.Body>List goes here.</Card.Body>
    </Card>
  ),
};
