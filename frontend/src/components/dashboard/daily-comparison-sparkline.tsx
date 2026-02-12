'use client';

import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface TrendData {
  date: string;
  value: number;
}

interface DailyComparisonSparklineProps {
  data: TrendData[];
  color?: string;
  className?: string;
}

export function DailyComparisonSparkline({
  data,
  color = '#10b981',
  className = '',
}: DailyComparisonSparklineProps) {
  if (!data || data.length === 0) {
    return <div className={`h-12 w-24 ${className}`} />;
  }

  return (
    <div className={`h-12 w-24 ${className}`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`sparkline-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sparkline-${color})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
