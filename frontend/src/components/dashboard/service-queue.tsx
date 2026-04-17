'use client';

import { Clock } from 'lucide-react';

interface WalkIn {
  id: string;
  service: { id: string; name: string };
  assigned_staff: { id: string; display_name: string };
  status: string;
  checked_in_at: string | null;
}

interface CustomerSession {
  session_id: string;
  customer_name: string;
  walkins: WalkIn[];
}

interface LaneItem {
  walkinId: string;
  serviceName: string;
  customerName: string;
  checkedInAt: Date;
  status: string;
}

interface StaffLane {
  staffId: string;
  staffName: string;
  items: LaneItem[];
}

const STATUS_DOT: Record<string, string> = {
  checked_in: 'bg-blue-500',
  in_progress: 'bg-amber-400 animate-pulse',
};

function buildLanes(sessions: CustomerSession[]): StaffLane[] {
  const laneMap = new Map<string, StaffLane>();

  for (const session of sessions) {
    for (const walkin of session.walkins) {
      if (walkin.status === 'completed') continue;

      const staffId = walkin.assigned_staff.id;
      if (!laneMap.has(staffId)) {
        laneMap.set(staffId, {
          staffId,
          staffName: walkin.assigned_staff.display_name,
          items: [],
        });
      }

      laneMap.get(staffId)!.items.push({
        walkinId: walkin.id,
        serviceName: walkin.service.name,
        customerName: session.customer_name,
        checkedInAt: walkin.checked_in_at ? new Date(walkin.checked_in_at) : new Date(),
        status: walkin.status,
      });
    }
  }

  for (const lane of laneMap.values()) {
    lane.items.sort((a, b) => a.checkedInAt.getTime() - b.checkedInAt.getTime());
  }

  return Array.from(laneMap.values());
}

function elapsedMinutes(date: Date): number {
  return Math.floor((Date.now() - date.getTime()) / 60000);
}

interface ServiceQueueProps {
  sessions: CustomerSession[];
}

export function ServiceQueue({ sessions }: ServiceQueueProps) {
  const lanes = buildLanes(sessions);

  if (lanes.length === 0) {
    return (
      <div className="rounded-xl bg-surface-card border border-border-subtle p-6 text-center">
        <p className="text-sm text-text-muted">No active services</p>
      </div>
    );
  }

  const colCount = Math.min(lanes.length, 3);

  return (
    <div className="rounded-xl bg-surface-card border border-border-subtle p-4">
      <h3 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-3">
        Service Queue
      </h3>
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: `repeat(${colCount}, minmax(0, 1fr))` }}
      >
        {lanes.map((lane) => (
          <div key={lane.staffId} className="flex flex-col gap-2">
            <div className="text-xs font-semibold text-text-primary truncate pb-1 border-b border-border-subtle">
              {lane.staffName}
            </div>
            {lane.items.map((item) => (
              <div
                key={item.walkinId}
                className="flex items-start gap-2 rounded-lg bg-surface-row p-2"
              >
                <span className="mt-1 shrink-0">
                  <span
                    className={`block h-2 w-2 rounded-full ${STATUS_DOT[item.status] ?? 'bg-text-muted'}`}
                  />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-text-primary truncate">
                    {item.serviceName}
                  </p>
                  <p className="text-[10px] text-text-secondary truncate">
                    {item.customerName}
                  </p>
                </div>
                <span className="shrink-0 flex items-center gap-0.5 text-[10px] text-text-muted">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  {elapsedMinutes(item.checkedInAt)}m
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
