'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface ServiceData {
  service_name: string;
  total_revenue: number;
  count: number;
}

interface ServiceDistributionChartProps {
  services: ServiceData[];
  totalServices: number;
}

const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'];

export function ServiceDistributionChart({
  services,
  totalServices,
}: ServiceDistributionChartProps) {
  const formatRevenue = (value: number) => {
    return `₹${(value / 100).toLocaleString('en-IN')}`;
  };

  const chartData = services.map((service, index) => ({
    name: service.service_name,
    value: service.total_revenue,
    count: service.count,
    percentage: ((service.count / totalServices) * 100).toFixed(1),
    fill: COLORS[index % COLORS.length],
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-xs font-semibold text-gray-900 mb-1">{data.name}</p>
          <div className="space-y-0.5">
            <p className="text-xs text-gray-600">
              Revenue: <span className="font-medium">{formatRevenue(data.value)}</span>
            </p>
            <p className="text-xs text-gray-600">
              Count: <span className="font-medium">{data.count}</span>
            </p>
            <p className="text-xs text-gray-600">
              Share: <span className="font-medium">{data.percentage}%</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percentage }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    // Only show label if percentage is >= 10% to avoid overlap
    if (parseFloat(percentage) < 10) return null;

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        className="text-xs font-semibold"
      >
        {`${percentage}%`}
      </text>
    );
  };

  const renderLegend = (props: any) => {
    const { payload } = props;
    return (
      <ul className="flex flex-col gap-1.5 mt-3">
        {payload.map((entry: any, index: number) => (
          <li key={`legend-${index}`} className="flex items-center gap-2 text-xs">
            <span
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-700 leading-tight">{entry.value}</span>
          </li>
        ))}
      </ul>
    );
  };

  if (services.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <p className="text-sm">No service data available</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={80}
              innerRadius={50}
              fill="#8884d8"
              dataKey="value"
              animationBegin={0}
              animationDuration={800}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {/* Center text */}
      <div className="flex justify-center -mt-32 pointer-events-none">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{totalServices}</div>
          <div className="text-[10px] text-gray-500">Services</div>
        </div>
      </div>
      {/* Legend below chart */}
      <div className="mt-4">
        {renderLegend({ payload: chartData.map(d => ({ value: d.name, color: d.fill })) })}
      </div>
    </div>
  );
}
