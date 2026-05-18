import type { Meta, StoryObj } from "@storybook/react";
import { Home, Receipt, Users } from "lucide-react";
import { NavItem } from "./nav-item";
import { Badge } from "./badge";

const meta: Meta<typeof NavItem> = { component: NavItem, title: "UI/NavItem" };
export default meta;

export const Sidebar: StoryObj<typeof NavItem> = {
  render: () => (
    <div className="w-48 flex flex-col gap-1 bg-surface-sidebar p-2 rounded-lg">
      <NavItem label="Today" href="#" icon={<Home />} active />
      <NavItem label="POS" href="#" icon={<Receipt />} />
      <NavItem label="Customers" href="#" icon={<Users />} badge={<Badge tone="accent" size="sm">3</Badge>} />
    </div>
  ),
};

export const Rail: StoryObj<typeof NavItem> = {
  render: () => (
    <div className="w-14 flex flex-col gap-1 bg-surface-sidebar p-1 rounded-lg items-center">
      <NavItem variant="rail" label="Today" href="#" icon={<Home />} active />
      <NavItem variant="rail" label="POS" href="#" icon={<Receipt />} />
      <NavItem variant="rail" label="Cust." href="#" icon={<Users />} />
    </div>
  ),
};
