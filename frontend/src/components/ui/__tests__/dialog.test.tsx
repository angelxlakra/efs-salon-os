import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Dialog, DialogContent, DialogTitle, DialogBody } from "@/components/ui/dialog";

describe("Dialog (V2)", () => {
  it("renders with size='md' max-width", () => {
    render(
      <Dialog open>
        <DialogContent size="md">
          <DialogTitle>Hi</DialogTitle>
          body
        </DialogContent>
      </Dialog>
    );
    const content = screen.getByRole("dialog");
    // Data attribute rather than inline style — easier to assert
    expect(content).toHaveAttribute("data-size", "md");
  });

  it("renders title for a11y", () => {
    render(
      <Dialog open>
        <DialogContent size="md">
          <DialogTitle>My Title</DialogTitle>
          body
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByText("My Title")).toBeInTheDocument();
  });

  it("applies destructive variant class when variant='destructive'", () => {
    render(
      <Dialog open>
        <DialogContent size="sm" variant="destructive">
          <DialogTitle>Confirm</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByRole("dialog")).toHaveAttribute("data-variant", "destructive");
  });

  it("DialogContent is a flex column so DialogBody can scroll", () => {
    render(
      <Dialog open>
        <DialogContent>
          <DialogTitle>T</DialogTitle>
          <DialogBody data-testid="body">x</DialogBody>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByRole("dialog").className).toMatch(/flex-col/);
    expect(screen.getByTestId("body").className).toMatch(/flex-1/);
  });

  it("hideClose hides the close button", () => {
    render(
      <Dialog open>
        <DialogContent hideClose>
          <DialogTitle>T</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    expect(screen.queryByRole("button", { name: /close/i })).toBeNull();
  });
});
