import type { Meta, StoryObj } from "@storybook/react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger } from "./dialog";
import { Button } from "./button";

const meta: Meta = { title: "UI/Dialog" };
export default meta;

export const Default: StoryObj = {
  render: () => (
    <Dialog>
      <DialogTrigger asChild><Button>Open dialog</Button></DialogTrigger>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle className="text-display-md">New bill</DialogTitle>
          <DialogDescription>Create a new bill for a walk-in customer.</DialogDescription>
        </DialogHeader>
        <div className="p-6 text-body">Form body here.</div>
        <DialogFooter>
          <Button variant="ghost">Cancel</Button>
          <Button>Create bill</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ),
};

export const Destructive: StoryObj = {
  render: () => (
    <Dialog>
      <DialogTrigger asChild><Button variant="danger">Delete customer</Button></DialogTrigger>
      <DialogContent size="sm" variant="destructive">
        <DialogHeader>
          <DialogTitle>Delete Priya Sharma?</DialogTitle>
          <DialogDescription>This cannot be undone. Type the customer name to confirm.</DialogDescription>
        </DialogHeader>
        <div className="p-6">…</div>
        <DialogFooter>
          <Button variant="ghost">Cancel</Button>
          <Button variant="danger">Delete</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ),
};
