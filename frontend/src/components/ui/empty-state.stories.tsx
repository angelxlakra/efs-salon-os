import type { Meta, StoryObj } from "@storybook/react";
import { Calendar } from "lucide-react";
import { EmptyState } from "./empty-state";
import { Button } from "./button";

const meta: Meta<typeof EmptyState> = { component: EmptyState, title: "UI/EmptyState" };
export default meta;

export const Default: StoryObj<typeof EmptyState> = {
  render: () => (
    <EmptyState
      icon={<Calendar />}
      title="No bookings yet today"
      body="First appointment is at 10:00. Add a walk-in to start earlier."
      primaryAction={<Button>New walk-in</Button>}
      secondaryAction={<Button variant="ghost">View yesterday</Button>}
    />
  ),
};
