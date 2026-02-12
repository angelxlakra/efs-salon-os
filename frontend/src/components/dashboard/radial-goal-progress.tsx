'use client';

import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';

interface RadialGoalProgressProps {
  title: string;
  current: number;
  target: number;
  formatter: (value: number) => string;
  color?: string;
}

export function RadialGoalProgress({
  title,
  current,
  target,
  formatter,
  color = '#10b981', // green-500
}: RadialGoalProgressProps) {
  const percentage = Math.min(100, Math.round((current / target) * 100));

  const data = [
    {
      name: title,
      value: percentage,
      fill: color,
    },
  ];

  return (
    <div className="flex flex-col items-center">
      <h4 className="text-sm font-medium text-gray-700 mb-2">{title}</h4>
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
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              background
              dataKey="value"
              cornerRadius={10}
              fill="url(#colorGradient)"
            />
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.8} />
                <stop offset="50%" stopColor={color} stopOpacity={0.9} />
                <stop offset="100%" stopColor={color} stopOpacity={1} />
              </linearGradient>
            </defs>
          </RadialBarChart>
        </ResponsiveContainer>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-2xl font-bold text-gray-900">{percentage}%</div>
          <div className="text-[10px] text-gray-500 mt-0.5">complete</div>
        </div>
      </div>
      <div className="mt-2 text-center">
        <div className="text-xs text-gray-600">
          <span className="font-semibold">{formatter(current)}</span>
          <span className="text-gray-400"> / </span>
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
      <RadialGoalProgress
        title="Revenue Target"
        current={currentRevenue}
        target={revenueTarget}
        formatter={formatRevenue}
        color="#10b981"
      />
      <RadialGoalProgress
        title="Services Goal"
        current={currentServices}
        target={servicesTarget}
        formatter={formatServices}
        color="#3b82f6"
      />
    </div>
  );
}
