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

// SVG ring circumference for r=35 on 84×84 viewBox: 2π×35 ≈ 219.9
const CIRCUM = 219.9;

function svgDash(pct: number) {
  const fill = Math.min(100, Math.max(0, pct)) / 100 * CIRCUM;
  return `${fill} ${CIRCUM - fill}`;
}

function getAssessment(pct: number): string {
  if (pct < 20) return 'time to push hard this afternoon.';
  if (pct < 40) return "within striking range of today's target.";
  return 'on track for a strong finish.';
}

interface RingItemProps {
  label: string;
  pct: number;
  value: string;
  color: string;
}

function RingItem({ label, pct, value, color }: RingItemProps) {
  const dash = svgDash(pct);
  // Start at 12 o'clock: dashoffset shifts arc by quarter-circumference
  const offset = CIRCUM * 0.25;
  // §08 reward moment: target met → the ring settles gold and glows.
  const met = pct >= 100;
  return (
    <div data-ring style={{ textAlign: 'center', width: 86 }}>
      <div style={{ width: 84, height: 84, position: 'relative', margin: '0 auto 8px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <svg
          style={{ position: 'absolute', top: 0, left: 0 }}
          width="84" height="84" viewBox="0 0 84 84"
          aria-label={`${label}: ${pct}% complete${met ? ' — target met' : ''}`}
          role="img"
        >
          <circle cx="42" cy="42" r="35" fill="none" stroke="var(--db-muted)" strokeWidth="6" />
          <circle
            className={met ? 'db-goal-met' : undefined}
            cx="42" cy="42" r="35" fill="none"
            stroke={met ? 'var(--db-gold)' : color} strokeWidth="6"
            strokeDasharray={dash}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <span className="db-num db-num-ring" style={met ? { color: 'var(--db-gold)' } : undefined}>{pct}</span>
      </div>
      <span className="db-label" style={{ textAlign: 'center' }}>{label}</span>
      <div className="db-ring-sub">{value}</div>
    </div>
  );
}

const HIDDEN = '₹ ••••';

interface GoalsRingsProps {
  revenueTarget: number;    // paise — accepted for future display; currently unused in rendering
  currentRevenue: number;   // paise
  servicesTarget: number;
  currentServices: number;
  customersTarget: number;
  currentCustomers: number;
  weekdayName: string;
  revenuePct: number;       // pre-computed percentage (0–100)
  revenueHidden: boolean;
}

export function GoalsRings({
  revenueTarget,
  currentRevenue,
  servicesTarget,
  currentServices,
  customersTarget,
  currentCustomers,
  weekdayName,
  revenuePct,
  revenueHidden,
}: GoalsRingsProps) {
  const svcPct = servicesTarget > 0
    ? Math.min(100, Math.round((currentServices / servicesTarget) * 100))
    : 0;
  const custPct = customersTarget > 0
    ? Math.min(100, Math.round((currentCustomers / customersTarget) * 100))
    : 0;
  const formatRupees = (p: number) => `₹${Math.round(p / 100).toLocaleString('en-IN')}`;
  const assessment = getAssessment(revenuePct);
  const revenueMet = revenuePct >= 100;

  return (
    <div className="db-goals-section">
      <div style={{ display: 'flex', gap: 16, flexShrink: 0 }}>
        <RingItem
          label="Revenue"
          pct={revenuePct}
          value={revenueHidden ? HIDDEN : formatRupees(currentRevenue)}
          color="var(--db-gold)"
        />
        <RingItem
          label="Services"
          pct={svcPct}
          value={`${currentServices} / ${servicesTarget}`}
          color="var(--db-gold)"
        />
        <RingItem
          label="Customers"
          pct={custPct}
          value={`${currentCustomers} / ${customersTarget}`}
          color="var(--db-ink-3)"
        />
      </div>
      <div className="db-goals-msg">
        <span
          className="db-editorial"
          style={{ fontSize: 20, color: revenueMet ? 'var(--db-gold)' : 'var(--db-ink)', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}
        >
          {revenueMet && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src="/aasan-mark.svg" width={20} height={20} alt="" className="db-goal-met" />
          )}
          {revenueMet
            ? "Target met — a strong day."
            : revenuePct < 40
              ? 'Three rings to close.'
              : 'Looking strong today.'}
        </span>
        <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-4)', lineHeight: 1.7 }}>
          At <strong style={{ color: 'var(--db-ink)' }}>{revenuePct}%</strong> of today&apos;s revenue target
          with <strong style={{ color: 'var(--db-ink)' }}>{currentServices} services</strong> and{' '}
          <strong style={{ color: 'var(--db-ink)' }}>{currentCustomers} customers</strong> so far
          this <strong style={{ color: 'var(--db-ink)' }}>{weekdayName}</strong> — {assessment}
        </p>
      </div>
    </div>
  );
}
