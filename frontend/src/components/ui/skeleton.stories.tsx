import type { Meta, StoryObj } from "@storybook/react";
import { Skeleton } from "./skeleton";

const meta: Meta<typeof Skeleton> = { component: Skeleton, title: "UI/Skeleton" };
export default meta;

export const Shapes: StoryObj<typeof Skeleton> = {
  render: () => (
    <div className="flex flex-col gap-3 w-[320px]">
      <Skeleton shape="text" width="70%" />
      <Skeleton shape="text" width="40%" />
      <Skeleton shape="row" />
      <Skeleton shape="kpi" />
      <Skeleton shape="card" />
    </div>
  ),
};
