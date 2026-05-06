"use client";

import { useEffect, useRef } from "react";

type CalendarView = "day" | "week" | "month";

type Handlers = {
  onNew: () => void;
  onPrev: () => void;
  onNext: () => void;
  onGoToday: () => void;
  onSetView: (view: CalendarView) => void;
};

/**
 * Registers keyboard shortcuts for the appointments calendar.
 *
 * Bindings (only fires when no input/textarea/select is focused):
 *   n          → new appointment
 *   ArrowLeft  → previous day/week/month
 *   ArrowRight → next day/week/month
 *   t          → go to today
 *   g then d   → day view
 *   g then w   → week view
 *   g then m   → month view
 */
export function useCalendarKeyboard(handlers: Handlers) {
  const pending = useRef<string | null>(null); // for chord (g then d/w/m)
  const chordTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const isEditable = (el: Element | null) =>
      el instanceof HTMLInputElement ||
      el instanceof HTMLTextAreaElement ||
      el instanceof HTMLSelectElement ||
      (el instanceof HTMLElement && el.isContentEditable);

    const onKeyDown = (e: KeyboardEvent) => {
      if (isEditable(document.activeElement)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key;

      // Chord: g + d/w/m
      if (pending.current === "g") {
        pending.current = null;
        if (chordTimer.current) clearTimeout(chordTimer.current);
        if (key === "d") { e.preventDefault(); handlers.onSetView("day"); return; }
        if (key === "w") { e.preventDefault(); handlers.onSetView("week"); return; }
        if (key === "m") { e.preventDefault(); handlers.onSetView("month"); return; }
      }

      if (key === "g") {
        pending.current = "g";
        chordTimer.current = setTimeout(() => { pending.current = null; }, 800);
        return;
      }

      switch (key) {
        case "n": e.preventDefault(); handlers.onNew(); break;
        case "ArrowLeft": e.preventDefault(); handlers.onPrev(); break;
        case "ArrowRight": e.preventDefault(); handlers.onNext(); break;
        case "t": e.preventDefault(); handlers.onGoToday(); break;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (chordTimer.current) clearTimeout(chordTimer.current);
    };
  }, [handlers]);
}
