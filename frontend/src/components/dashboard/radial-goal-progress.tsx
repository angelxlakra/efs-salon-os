'use client';

import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';
import { useChartColors } from '@/lib/use-chart-colors';

interface RadialGoalProgressProps {
  title: string;
  current: number;
  target: number;
  formatter: (value: number) => string;
  /** Index into the data-series palette (0–5). Default 0 = data-series-1 (navy). */
  colorIndex?: number;
}

export function RadialGoalProgress({
  title,
  current,
  target,
  formatter,
  colorIndex = 0,
}: RadialGoalProgressProps) {
  const { series } = useChartColors();
  const color = series[colorIndex] ?? series[0];
  const percentage = Math.min(100, Math.round((current / target) * 100));

  const data = [{ name: title, value: percentage, fill: color }];

  return (
    <div className="flex flex-col items-center">
      <h4 className="text-sm font-medium text-text-secondary mb-2">{title}</h4>
      <div className="relative w-32 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="90%"
            barSize={12}
            data={data}
            startAngle={225}
            endAngle={-45}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background dataKey="value" cornerRadius={10} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-2xl font-bold text-text-primary">{percentage}%</div>
          <div className="text-[10px] text-text-muted mt-0.5">complete</div>
        </div>
      </div>
      <div className="mt-2 text-center">
        <div className="text-xs text-text-secondary">
          <span className="font-semibold">{formatter(current)}</span>
          <span className="text-text-disabled"> / </span>
          <span>{formatter(target)}</span>
        </div>
      </div>
    </div>
  );
}

interface DualRadialGoalsProps {
  revenueTarget: number;
  currentRevenue: number;
  servicesTarget: number;
  currentServices: number;
}

export function DualRadialGoals({
  revenueTarget,
  currentRevenue,
  servicesTarget,
  currentServices,
}: DualRadialGoalsProps) {
  const formatRevenue = (paise: number) => `₹${(paise / 100).toLocaleString('en-IN')}`;
  const formatServices = (count: number) => `${count}`;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* colorIndex 2 = data-series-3 (green #166534) for revenue */}
      <RadialGoalProgress
        title="Revenue Target"
        current={currentRevenue}
        target={revenueTarget}
        formatter={formatRevenue}
        colorIndex={2}
      />
      {/* colorIndex 1 = data-series-2 (indigo #1e40af) for services */}
      <RadialGoalProgress
        title="Services Goal"
        current={currentServices}
        target={servicesTarget}
        formatter={formatServices}
        colorIndex={1}
      />
    </div>
  );
}
