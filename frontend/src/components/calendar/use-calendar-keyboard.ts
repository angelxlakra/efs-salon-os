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

function isEditable(el: Element | null): boolean {
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    el instanceof HTMLSelectElement ||
    (el instanceof HTMLElement && el.isContentEditable)
  );
}

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
  // Sync latest handlers each render so the stable listener always calls current callbacks.
  const handlersRef = useRef(handlers);
  useEffect(() => { handlersRef.current = handlers; });

  const pending = useRef<string | null>(null);
  const chordTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isEditable(document.activeElement)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key;
      const h = handlersRef.current;

      // Chord: g + d/w/m
      if (pending.current === "g") {
        pending.current = null;
        if (chordTimer.current) clearTimeout(chordTimer.current);
        if (key === "d") { e.preventDefault(); h.onSetView("day"); return; }
        if (key === "w") { e.preventDefault(); h.onSetView("week"); return; }
        if (key === "m") { e.preventDefault(); h.onSetView("month"); return; }
      }

      if (key === "g") {
        pending.current = "g";
        chordTimer.current = setTimeout(() => { pending.current = null; }, 800);
        return;
      }

      switch (key) {
        case "n":          e.preventDefault(); h.onNew(); break;
        case "ArrowLeft":  e.preventDefault(); h.onPrev(); break;
        case "ArrowRight": e.preventDefault(); h.onNext(); break;
        case "t":          e.preventDefault(); h.onGoToday(); break;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (chordTimer.current) clearTimeout(chordTimer.current);
    };
  }, []); // stable — registered once for the component lifetime
}
