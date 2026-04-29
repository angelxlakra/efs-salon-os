import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FilterBar } from "@/components/ui/filter-bar";

describe("FilterBar", () => {
  it("renders search input", () => {
    render(
      <FilterBar>
        <FilterBar.Search placeholder="Search bills…" value="" onChange={() => {}} />
      </FilterBar>
    );
    expect(screen.getByPlaceholderText("Search bills…")).toBeInTheDocument();
  });

  it("renders pills with counts and fires onChange", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FilterBar>
        <FilterBar.Pills
          value="all"
          onChange={onChange}
          options={[
            { value: "all",  label: "All",  count: 171 },
            { value: "paid", label: "Paid", count: 142 },
          ]}
        />
      </FilterBar>
    );
    await user.click(screen.getByRole("button", { name: /Paid/ }));
    expect(onChange).toHaveBeenCalledWith("paid");
  });

  it("marks active pill", () => {
    render(
      <FilterBar>
        <FilterBar.Pills
          value="paid"
          onChange={() => {}}
          options={[{ value: "paid", label: "Paid", count: 142 }]}
        />
      </FilterBar>
    );
    expect(screen.getByRole("button", { name: /Paid/ })).toHaveAttribute("data-active", "true");
  });

  it("uses aria-pressed (toggle-button semantics, not aria-selected)", () => {
    render(
      <FilterBar>
        <FilterBar.Pills
          value="paid"
          onChange={() => {}}
          options={[
            { value: "all",  label: "All" },
            { value: "paid", label: "Paid" },
          ]}
        />
      </FilterBar>
    );
    expect(screen.getByRole("button", { name: /Paid/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /All/ })).toHaveAttribute("aria-pressed", "false");
    // aria-selected would be invalid ARIA on a button — must NOT be set
    expect(screen.getByRole("button", { name: /Paid/ })).not.toHaveAttribute("aria-selected");
  });
});
