import * as React from "react";

export default function ShellLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  // T2-T6 will replace this skeleton with sidebar + topbar + content grid.
  // For now we just verify the route group compiles and the @modal slot is wired.
  return (
    <div className="min-h-dvh bg-surface-page text-text-primary">
      <main>{children}</main>
      {modal}
    </div>
  );
}
