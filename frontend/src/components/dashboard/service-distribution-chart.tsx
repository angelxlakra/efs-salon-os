'use client';

import { useState } from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { LayoutList, PieChart as PieIcon, BarChart2 } from 'lucide-react';
import { useChartColors } from '@/lib/use-chart-colors';

interface ServiceData {
  service_name: string;
  total_revenue: number;
  count: number;
}

interface ServiceDistributionChartProps {
  services: ServiceData[];
  totalServices: number;
}

type ViewMode = 'donut' | 'bar' | 'list';

export function ServiceDistributionChart({
  services,
  totalServices,
}: ServiceDistributionChartProps) {
  const [view, setView] = useState<ViewMode>('donut');
  const { series } = useChartColors();

  // Use services sum as fallback when totalServices is 0 to avoid Infinity%
  const total = totalServices > 0
    ? totalServices
    : services.reduce((sum, s) => sum + s.count, 0);

  const formatRevenue = (value: number) =>
    `₹${(value / 100).toLocaleString('en-IN')}`;

  const chartData = services.map((service, index) => ({
    name: service.service_name,
    value: service.total_revenue,
    count: service.count,
    percentage: total > 0 ? ((service.count / total) * 100).toFixed(1) : '0.0',
    fill: series[index % series.length],
  }));

  if (services.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted">
        <p className="text-sm">No service data available</p>
      </div>
    );
  }

  // ── View toggle bar ──────────────────────────────────────────────────────
  const ViewToggle = () => (
    <div className="flex gap-1 mb-3">
      {([
        { id: 'donut', icon: PieIcon, label: 'Donut' },
        { id: 'bar',   icon: BarChart2, label: 'Bar' },
        { id: 'list',  icon: LayoutList, label: 'List' },
      ] as { id: ViewMode; icon: React.ElementType; label: string }[]).map(({ id, icon: Icon, label }) => (
        <button
          key={id}
          onClick={() => setView(id)}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
            view === id
              ? 'bg-accent text-accent-fg'
              : 'bg-surface-row-hover text-text-secondary hover:bg-border-subtle'
          }`}
        >
          <Icon className="h-3 w-3" />
          {label}
        </button>
      ))}
    </div>
  );

  // ── Tooltip shared between donut & bar ───────────────────────────────────
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-surface-card p-3 rounded-lg shadow-lg border border-border-default text-xs">
        <p className="font-semibold text-text-primary mb-1">{d.name}</p>
        <p className="text-text-secondary">Revenue: <span className="font-medium">{formatRevenue(d.value)}</span></p>
        <p className="text-text-secondary">Count: <span className="font-medium">{d.count}</span></p>
        <p className="text-text-secondary">Share: <span className="font-medium">{d.percentage}%</span></p>
      </div>
    );
  };

  // ── Donut view ───────────────────────────────────────────────────────────
  if (view === 'donut') {
    return (
      <div className="w-full">
        <ViewToggle />
        {/* Relative wrapper so we can absolutely centre the label */}
        <div className="relative h-52">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={80}
                innerRadius={50}
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

          {/* Centred label — absolutely positioned over the SVG */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <div className="text-2xl font-bold text-text-primary">{total}</div>
              <div className="text-[10px] text-text-muted leading-tight">Services</div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <ul className="flex flex-col gap-1.5 mt-2">
          {chartData.map((d, i) => (
            <li key={i} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: d.fill }} />
                <span className="text-text-secondary truncate max-w-[120px]">{d.name}</span>
              </div>
              <span className="text-text-muted tabular-nums">{d.count}×</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // ── Bar view ─────────────────────────────────────────────────────────────
  if (view === 'bar') {
    return (
      <div className="w-full">
        <ViewToggle />
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 16, top: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => `₹${(v / 100).toLocaleString('en-IN', { notation: 'compact' })}`}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={80}
                tick={{ fontSize: 10 }}
                tickFormatter={(v: string) => v.length > 12 ? v.slice(0, 12) + '…' : v}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  }

  // ── List view ────────────────────────────────────────────────────────────
  return (
    <div className="w-full">
      <ViewToggle />
      <div className="space-y-2">
        {chartData.map((d, i) => (
          <div key={i} className="flex items-center gap-3">
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: d.fill }}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between text-xs mb-0.5">
                <span className="font-medium text-text-primary truncate">{d.name}</span>
                <span className="text-text-muted tabular-nums ml-2 flex-shrink-0">{d.count}× · {formatRevenue(d.value)}</span>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 w-full bg-surface-row-hover rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${d.percentage}%`, backgroundColor: d.fill }}
                />
              </div>
            </div>
            <span className="text-[10px] text-text-disabled tabular-nums w-8 text-right flex-shrink-0">
              {d.percentage}%
            </span>
          </div>
        ))}
      </div>

      {/* Footer summary */}
      <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-text-muted">
        <span>{services.length} service types</span>
        <span className="font-medium text-text-secondary">
          {formatRevenue(services.reduce((s, d) => s + d.total_revenue, 0))} total
        </span>
      </div>
    </div>
  );
}
