import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { CurrencyInput } from "./currency-input";

const meta: Meta<typeof CurrencyInput> = { component: CurrencyInput, title: "UI/CurrencyInput" };
export default meta;

function DefaultDemo() {
  const [paise, setPaise] = useState(24800);
  return <CurrencyInput label="Amount" value={paise} onChange={setPaise} />;
}

export const Default: StoryObj<typeof CurrencyInput> = {
  render: () => <DefaultDemo />,
};
