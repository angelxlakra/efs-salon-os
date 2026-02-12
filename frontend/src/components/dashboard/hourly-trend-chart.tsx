'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
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

export function HourlyTrendChart({ data, peakHour }: HourlyTrendChartProps) {
  const formatRevenue = (value: number) => {
    return `₹${(value / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const formatHour = (hour: number) => {
    return `${hour.toString().padStart(2, '0')}:00`;
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-xs font-semibold text-gray-900 mb-1">{data.hour_label}</p>
          <div className="space-y-0.5">
            <p className="text-xs text-gray-600">
              Revenue: <span className="font-medium text-green-600">{formatRevenue(data.revenue_paise)}</span>
            </p>
            <p className="text-xs text-gray-600">
              Bills: <span className="font-medium">{data.bills_count}</span>
            </p>
            <p className="text-xs text-gray-600">
              Services: <span className="font-medium">{data.services_count}</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
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
            tickFormatter={formatHour}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            stroke="#9ca3af"
            interval={2}
          />
          <YAxis
            tickFormatter={(value) => `₹${Math.round(value / 100)}`}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            stroke="#9ca3af"
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="revenue_paise"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#colorRevenue)"
          />
        </AreaChart>
      </ResponsiveContainer>
      {peakHour !== undefined && (
        <div className="mt-2 text-center">
          <p className="text-xs text-gray-500">
            Peak hour: <span className="font-semibold text-gray-900">{formatHour(peakHour)}</span>
          </p>
        </div>
      )}
    </div>
  );
}
