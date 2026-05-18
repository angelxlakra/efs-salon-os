'use client';

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

export function HourlyTrendChart({ data, peakHour }: HourlyTrendChartProps) {
  const formatRevenue = (value: number) =>
    `₹${(value / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

  // Current local hour — trim future hours so the chart only shows up to now
  const currentHour = new Date().getHours();

  // Backend already trims to 10–23; additionally cut off future hours for today.
  // We keep past-day data fully visible. If no data past SALON_OPEN_HOUR exists
  // and it's a past date, show all returned hours.
  const hasAnyRevenue = data.some(d => d.revenue_paise > 0);
  const visibleData = data.filter(d => {
    if (d.hour < SALON_OPEN_HOUR) return false;
    // Only trim future hours if today has data or it's clearly today
    // (i.e. currentHour is within the chart range)
    if (currentHour >= SALON_OPEN_HOUR && d.hour > currentHour) return false;
    return true;
  });

  const displayData = visibleData.length > 0 ? visibleData : data;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-white p-3 rounded-lg shadow-lg border border-border-default">
        <p className="text-xs font-semibold text-text-primary mb-1">{d.hour_label}</p>
        <div className="space-y-0.5">
          <p className="text-xs text-text-secondary">
            Revenue: <span className="font-medium text-green-600">{formatRevenue(d.revenue_paise)}</span>
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
  };

  const peakHourInView = peakHour !== undefined && displayData.some(d => d.hour === peakHour);

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={displayData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="hour"
            tickFormatter={formatHour12}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            stroke="#9ca3af"
            interval={1}
          />
          <YAxis
            tickFormatter={(value) => `₹${Math.round(value / 100)}`}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            stroke="#9ca3af"
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* Peak hour reference line */}
          {peakHourInView && (
            <ReferenceLine
              x={peakHour}
              stroke="#f59e0b"
              strokeDasharray="4 2"
              label={{ value: 'Peak', position: 'top', fontSize: 10, fill: '#f59e0b' }}
            />
          )}
          <Area
            type="monotone"
            dataKey="revenue_paise"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#colorRevenue)"
          />
        </AreaChart>
      </ResponsiveContainer>
      {peakHourInView && (
        <div className="mt-2 text-center">
          <p className="text-xs text-text-muted">
            Peak hour: <span className="font-semibold text-text-primary">{formatHour12(peakHour!)}</span>
          </p>
        </div>
      )}
    </div>
  );
}
