'use client';

import { Eye, EyeOff } from 'lucide-react';

const HIDDEN = '₹ ••••';

interface StatsBarProps {
  revenueToday: number;       // paise
  revenueTarget: number;      // paise
  revenueDeltaPaise: number;  // positive = ahead vs yesterday, negative = behind
  activeServices: number;
  checkedInWaiting: number;
  pendingBills: number;
  avgBillTodayPaise: number;  // paise; 0 if no bills yet
  revenueHidden: boolean;
  onToggleRevenue: () => void;
}

function formatRupees(paise: number): string {
  return `₹${Math.round(paise / 100).toLocaleString('en-IN')}`;
}

function mask(value: string, hidden: boolean): string {
  return hidden ? HIDDEN : value;
}

interface GlanceRowProps { label: string; value: string | number }
function GlanceRow({ label, value }: GlanceRowProps) {
  return (
    <div className="db-glance-row">
      <span className="db-glance-key">{label}</span>
      <span className="db-num db-num-mini">{value}</span>
    </div>
  );
}

export function StatsBar({
  revenueToday,
  revenueTarget,
  revenueDeltaPaise,
  activeServices,
  checkedInWaiting,
  pendingBills,
  avgBillTodayPaise,
  revenueHidden,
  onToggleRevenue,
}: StatsBarProps) {
  const pct = revenueTarget > 0
    ? Math.min(100, Math.round((revenueToday / revenueTarget) * 100))
    : 0;
  const toGo = Math.max(0, revenueTarget - revenueToday);
  const isAhead = revenueDeltaPaise >= 0;
  const deltaAbs = Math.abs(revenueDeltaPaise);

  return (
    <div className="db-stats-bar">
      {/* Panel 1: Revenue */}
      <div className="db-stats-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="db-label">Today&apos;s Revenue</span>
          <button
            onClick={onToggleRevenue}
            aria-label={revenueHidden ? 'Show revenue' : 'Hide revenue'}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px 4px', color: 'var(--db-ink-4)', display: 'flex', alignItems: 'center' }}
          >
            {revenueHidden ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <span className="db-num db-num-hero">{mask(formatRupees(revenueToday), revenueHidden)}</span>
        <p className="db-stats-sub">
          <span className={isAhead ? 'db-text-ahead' : 'db-text-behind'} style={{ fontWeight: 600 }}>
            {isAhead ? '↑' : '↓'} {mask(formatRupees(deltaAbs), revenueHidden)}
          </span>
          {' '}vs same time yesterday
        </p>
        <div
          className="db-progress-track"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Revenue target progress: ${pct}%`}
        >
          <div className="db-progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="db-stats-sub" style={{ marginTop: 4 }}>
          {pct}% of {formatRupees(revenueTarget)} target · {mask(formatRupees(toGo), revenueHidden)} to go
        </p>
      </div>

      {/* Panel 2: Pace */}
      <div className="db-stats-panel">
        <span className="db-label">Pace</span>
        <span className="db-editorial" style={{ fontSize: 15, color: 'var(--db-ink-4)', display: 'block', marginBottom: 2 }}>
          {isAhead ? 'Ahead by' : 'Behind by'}
        </span>
        <span className={`db-num db-num-warn ${isAhead ? 'db-text-ahead' : 'db-text-behind'}`}>
          ~{mask(formatRupees(deltaAbs), revenueHidden)}
        </span>
        <p className="db-stats-sub" style={{ marginTop: 8 }}>
          {isAhead
            ? "You're tracking ahead of yesterday — keep the momentum."
            : 'Afternoon walk-ins typically close the gap on busy days.'}
        </p>
      </div>

      {/* Panel 3: Right Now (operational, no goal duplication) */}
      <div className="db-stats-panel">
        <span className="db-label">Right Now</span>
        <GlanceRow label="Active services" value={activeServices} />
        <GlanceRow label="Checked in, waiting" value={checkedInWaiting} />
        <GlanceRow label="Pending bills" value={pendingBills} />
        <GlanceRow
          label="Avg. bill today"
          value={avgBillTodayPaise > 0 ? formatRupees(avgBillTodayPaise) : '—'}
        />
      </div>
    </div>
  );
}
