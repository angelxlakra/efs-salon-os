"use client";

export function Breadcrumb({ className }: { className?: string }) {
  return (
    <div className={className}>
      <span>Today</span>
      <span aria-hidden="true"> / </span>
      <span>Bills</span>
    </div>
  );
}
