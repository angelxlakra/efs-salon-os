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

  it("does not fire when metaKey is held", () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "n", metaKey: true });
    expect(handlers.onNew).not.toHaveBeenCalled();
  });

  it("does not fire view change if chord times out before second key", () => {
    vi.useFakeTimers();
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "g" });
    vi.advanceTimersByTime(801);
    fireEvent.keyDown(window, { key: "d" });
    expect(handlers.onSetView).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("does not fire any handler for an unknown chord key (g then x)", () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "x" });
    expect(handlers.onSetView).not.toHaveBeenCalled();
    expect(handlers.onNew).not.toHaveBeenCalled();
  });

  it("does not fire when a textarea is focused", () => {
    const handlers = makeHandlers();
    renderHook(() => useCalendarKeyboard(handlers));
    const textarea = document.createElement("textarea");
    document.body.appendChild(textarea);
    textarea.focus();
    fireEvent.keyDown(window, { key: "n" });
    expect(handlers.onNew).not.toHaveBeenCalled();
    document.body.removeChild(textarea);
  });
});
