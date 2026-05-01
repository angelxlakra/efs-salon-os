import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { FilterBar } from "./filter-bar";
import { Button } from "./button";

const meta: Meta = { title: "UI/FilterBar" };
export default meta;

function DefaultDemo() {
  const [q, setQ] = useState("");
  const [tab, setTab] = useState("all");
  return (
    <div className="w-[720px]">
      <FilterBar>
        <FilterBar.Search value={q} onChange={setQ} placeholder="Search bills…" />
        <FilterBar.Pills
          value={tab}
          onChange={setTab}
          options={[
            { value: "all",     label: "All",     count: 171 },
            { value: "paid",    label: "Paid",    count: 142 },
            { value: "pending", label: "Pending", count: 29 },
          ]}
        />
        <FilterBar.Actions>
          <Button variant="secondary">Export</Button>
        </FilterBar.Actions>
      </FilterBar>
    </div>
  );
}

export const Default: StoryObj = {
  render: () => <DefaultDemo />,
};
