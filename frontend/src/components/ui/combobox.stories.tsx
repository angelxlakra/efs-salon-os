import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Combobox } from "./combobox";

const meta: Meta<typeof Combobox> = { component: Combobox, title: "UI/Combobox" };
export default meta;

const customers = [
  { value: "1", label: "Priya Sharma" },
  { value: "2", label: "Rajni Gupta" },
  { value: "3", label: "Anjali Patel" },
];

function DefaultDemo() {
  const [v, setV] = useState<string | null>(null);
  return <div className="w-[320px]"><Combobox options={customers} value={v} onChange={setV} placeholder="Pick customer" /></div>;
}

export const Default: StoryObj<typeof Combobox> = {
  render: () => <DefaultDemo />,
};
