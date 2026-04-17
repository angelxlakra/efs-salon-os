'use client';

import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';

interface StatCardProps {
  title: string;
  value: string;
  /** Secondary line below the value (e.g. "68% of daily goal") */
  subValue?: string;
  /** If true, value is hidden by default with an eye toggle */
  sensitive?: boolean;
  /** localStorage key base (user ID is appended) for persisting visibility */
  visibilityKey?: string;
  /** Trend indicator node (e.g. <TrendIndicator /> ) */
  trend?: React.ReactNode;
  /** Icon displayed top-right alongside the eye toggle */
  icon?: React.ReactNode;
}

export function StatCard({
  title,
  value,
  subValue,
  sensitive = false,
  visibilityKey,
  trend,
  icon,
}: StatCardProps) {
  const { user } = useAuthStore();

  // Staff role never sees sensitive cards
  if (sensitive && user?.role === 'staff') return null;

  const storageKey = visibilityKey && user?.id ? `${visibilityKey}-${user.id}` : null;

  const [visible, setVisible] = useState<boolean>(() => {
    if (!sensitive) return true;
    if (typeof window === 'undefined' || !storageKey) return false;
    return localStorage.getItem(storageKey) === 'true';
  });

  const toggle = () => {
    const next = !visible;
    setVisible(next);
    if (storageKey) localStorage.setItem(storageKey, String(next));
  };

  return (
    <div className="rounded-xl bg-surface-card border border-border-subtle p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          {title}
        </span>
        <div className="flex items-center gap-2">
          {icon && <span className="text-text-muted">{icon}</span>}
          {sensitive && (
            <button
              onClick={toggle}
              className="text-text-muted hover:text-text-secondary transition-colors"
              aria-label={visible ? 'Hide value' : 'Show value'}
            >
              {visible ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-end justify-between gap-2">
        <span className="text-xl md:text-2xl font-bold text-text-primary tabular-nums">
          {sensitive && !visible ? '••••' : value}
        </span>
        {trend && <span className="shrink-0">{trend}</span>}
      </div>

      {subValue && (
        <span className="text-xs text-text-muted">
          {sensitive && !visible ? '—' : subValue}
        </span>
      )}
    </div>
  );
}
