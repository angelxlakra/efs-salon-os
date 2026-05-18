'use client';

import { useCallback } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { useChartColors } from '@/lib/use-chart-colors';

interface HourlyData {
  hour: number;
  hour_label: string;
  revenue_paise: number;
  bills_count: number;
  services_count: number;
}

interface HourlyTrendChartProps {
  data: HourlyData[];
  peakHour?: number;
}

const SALON_OPEN_HOUR = 10;

function formatHour12(hour: number): string {
  const ampm = hour < 12 ? 'AM' : 'PM';
  const h = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${h}${ampm}`;
}

interface HourlyTooltipProps extends TooltipContentProps<number, string> {
  formatRevenue: (v: number) => string;
}

function HourlyTooltip({ active, payload, formatRevenue }: HourlyTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as HourlyData;
  return (
    <div className="bg-surface-card p-3 rounded-lg shadow-sm border border-border-default">
      <p className="text-xs font-semibold text-text-primary mb-1">{d.hour_label}</p>
      <div className="space-y-0.5">
        <p className="text-xs text-text-secondary">
          Revenue:{' '}
          <span className="font-medium text-success-fg">{formatRevenue(d.revenue_paise)}</span>
        </p>
        <p className="text-xs text-text-secondary">
          Bills: <span className="font-medium">{d.bills_count}</span>
        </p>
        <p className="text-xs text-text-secondary">
          Services: <span className="font-medium">{d.services_count}</span>
        </p>
      </div>
    </div>
  );
}

function formatRevenue(value: number): string {
  return `₹${(value / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export function HourlyTrendChart({ data, peakHour }: HourlyTrendChartProps) {
  const colors = useChartColors();

  const currentHour = new Date().getHours();
  const visibleData = data.filter(d => {
    if (d.hour < SALON_OPEN_HOUR) return false;
    if (currentHour >= SALON_OPEN_HOUR && d.hour > currentHour) return false;
    return true;
  });

  const displayData = visibleData.length > 0 ? visibleData : data;

  const tooltipContent = useCallback(
    (props: TooltipContentProps<number, string>) =>
      <HourlyTooltip {...props} formatRevenue={formatRevenue} />,
    []
  );

  const revenueColor = colors.series[2]; // data-series-3 (green)
  const peakColor    = colors.series[3]; // data-series-4 (amber)
  const gridColor    = colors.borderSubtle;
  const axisColor    = colors.textMuted;

  const peakHourInView =
    peakHour !== undefined && displayData.some(d => d.hour === peakHour);

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={displayData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"  stopColor={revenueColor} stopOpacity={0.3} />
              <stop offset="95%" stopColor={revenueColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="hour"
            tickFormatter={formatHour12}
            tick={{ fontSize: 11, fill: axisColor }}
            stroke={gridColor}
            interval={1}
          />
          <YAxis
            tickFormatter={(value) => `₹${Math.round(value / 100)}`}
            tick={{ fontSize: 11, fill: axisColor }}
            stroke={gridColor}
            width={50}
          />
          <Tooltip content={tooltipContent} />
          {peakHourInView && (
            <ReferenceLine
              x={peakHour}
              stroke={peakColor}
              strokeDasharray="4 2"
              label={{ value: 'Peak', position: 'top', fontSize: 10, fill: peakColor }}
            />
          )}
          <Area
            type="monotone"
            dataKey="revenue_paise"
            stroke={revenueColor}
            strokeWidth={2}
            fill="url(#colorRevenue)"
          />
        </AreaChart>
      </ResponsiveContainer>
      {peakHourInView && (
        <div className="mt-2 text-center">
          <p className="text-xs text-text-muted">
            Peak hour:{' '}
            <span className="font-semibold text-text-primary">{formatHour12(peakHour!)}</span>
          </p>
        </div>
      )}
    </div>
  );
}
