"use client";

import * as React from "react";

type PaletteValue = {
  open: () => void;
  close: () => void;
  isOpen: boolean;
};

const PaletteContext = React.createContext<PaletteValue | null>(null);

export function PaletteProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const value = React.useMemo<PaletteValue>(
    () => ({
      open: () => setIsOpen(true),
      close: () => setIsOpen(false),
      isOpen,
    }),
    [isOpen],
  );
  return <PaletteContext.Provider value={value}>{children}</PaletteContext.Provider>;
}

export function usePalette(): PaletteValue {
  const ctx = React.useContext(PaletteContext);
  if (!ctx) throw new Error("usePalette must be used inside <PaletteProvider>");
  return ctx;
}
