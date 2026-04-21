'use client';

import { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/stores/auth-store';

interface StatCardProps {
  title: string;
  value: string;
  subValue?: string;
  sensitive?: boolean;
  visibilityKey?: string;
  trend?: ReactNode;
  icon?: ReactNode;
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

  const storageKey = visibilityKey && user?.id ? `${visibilityKey}-${user.id}` : null;

  // All hooks BEFORE any early return
  const [visible, setVisible] = useState<boolean>(false);

  useEffect(() => {
    if (!sensitive || !storageKey) return;
    const stored = localStorage.getItem(storageKey);
    if (stored === 'true') setVisible(true);
  }, [sensitive, storageKey]);

  // Early return AFTER all hooks
  if (sensitive && user?.role === 'staff') return null;

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
              type="button"
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
