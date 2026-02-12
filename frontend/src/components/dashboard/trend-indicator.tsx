'use client';

import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface TrendIndicatorProps {
  value: number; // Percentage change
  label?: string;
  className?: string;
}

export function TrendIndicator({ value, label, className = '' }: TrendIndicatorProps) {
  const isPositive = value > 0;
  const isNegative = value < 0;
  const isNeutral = value === 0;

  const colorClass = isPositive
    ? 'text-green-600'
    : isNegative
    ? 'text-red-600'
    : 'text-gray-500';

  const bgClass = isPositive
    ? 'bg-green-50'
    : isNegative
    ? 'bg-red-50'
    : 'bg-gray-50';

  const Icon = isPositive ? ArrowUp : isNegative ? ArrowDown : Minus;

  return (
    <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${bgClass} ${className}`}>
      <Icon className={`h-2.5 w-2.5 ${colorClass}`} />
      <span className={`text-[9px] font-medium ${colorClass}`}>
        {isNeutral ? '0%' : `${Math.abs(value).toFixed(1)}%`}
        {label && ` ${label}`}
      </span>
    </div>
  );
}
