import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { fireEvent } from "@testing-library/dom";
import { useCalendarKeyboard } from "@/components/calendar/use-calendar-keyboard";

function makeHandlers() {
  return {
    onNew: vi.fn(),
    onPrev: vi.fn(),
    onNext: vi.fn(),
    onGoToday: vi.fn(),
    onSetView: vi.fn(),
  };
}

describe("useCalendarKeyboard", () => {
  afterEach(() => {
    // restore focus to body
    (document.activeElement as HTMLElement | null)?.blur?.();
  });

  it('calls onNew when "n" is pressed', () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "n" });
    expect(handlers.onNew).toHaveBeenCalledOnce();
  });

  it("calls onPrev when ArrowLeft is pressed", () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(handlers.onPrev).toHaveBeenCalledOnce();
  });

  it("calls onNext when ArrowRight is pressed", () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(handlers.onNext).toHaveBeenCalledOnce();
  });

  it('calls onGoToday when "t" is pressed', () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "t" });
    expect(handlers.onGoToday).toHaveBeenCalledOnce();
  });

  it('calls onSetView("day") on g then d chord', () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "d" });
    expect(handlers.onSetView).toHaveBeenCalledOnce();
    expect(handlers.onSetView).toHaveBeenCalledWith("day");
  });

  it('calls onSetView("week") on g then w chord', () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "w" });
    expect(handlers.onSetView).toHaveBeenCalledOnce();
    expect(handlers.onSetView).toHaveBeenCalledWith("week");
  });

  it('calls onSetView("month") on g then m chord', () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "m" });
    expect(handlers.onSetView).toHaveBeenCalledOnce();
    expect(handlers.onSetView).toHaveBeenCalledWith("month");
  });

  it("does not fire when an input is focused", () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    fireEvent.keyDown(window, { key: "n" });
    expect(handlers.onNew).not.toHaveBeenCalled();
    document.body.removeChild(input);
  });
});
