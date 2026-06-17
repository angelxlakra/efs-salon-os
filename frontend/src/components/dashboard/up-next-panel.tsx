'use client';

import { useState, useEffect, useCallback } from 'react';
import { format, parseISO, differenceInMinutes } from 'date-fns';
import {
  listAppointments,
  listActiveStaff,
  listServices,
  type Appointment,
  type StaffMember,
  type ServiceItem,
} from '@/lib/api/appointments';
import { CheckInDialog } from './checkin-dialog';

const MAX_VISIBLE = 5;
const POLL_INTERVAL_MS = 2 * 60 * 1000;

interface EnrichedAppointment {
  appt: Appointment;
  staffName: string;
  serviceName: string;
  minsUntil: number;
}

function enrich(
  appointments: Appointment[],
  staffMap: Map<string, string>,
  serviceMap: Map<string, string>,
  now: Date
): EnrichedAppointment[] {
  return appointments
    .filter(a => a.status === 'scheduled' && differenceInMinutes(parseISO(a.scheduled_at), now) > -1)
    .sort((a, b) => parseISO(a.scheduled_at).getTime() - parseISO(b.scheduled_at).getTime())
    .slice(0, MAX_VISIBLE)
    .map(appt => ({
      appt,
      staffName: staffMap.get(appt.assigned_staff_id ?? '') ?? 'Unassigned',
      serviceName: serviceMap.get(appt.service_id ?? '') ?? 'Service',
      minsUntil: Math.max(0, differenceInMinutes(parseISO(appt.scheduled_at), now)),
    }));
}

export function UpNextPanel() {
  const [items, setItems] = useState<EnrichedAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [staffMap, setStaffMap] = useState<Map<string, string>>(new Map());
  const [serviceMap, setServiceMap] = useState<Map<string, string>>(new Map());
  const [selectedAppt, setSelectedAppt] = useState<EnrichedAppointment | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const today = format(new Date(), 'yyyy-MM-dd');
      const [appts, staff, services] = await Promise.all([
        listAppointments(today, 'scheduled'),
        listActiveStaff(),
        listServices(),
      ]);
      const sMap = new Map<string, string>(staff.map((s: StaffMember) => [s.id, s.display_name]));
      const svMap = new Map<string, string>(services.map((s: ServiceItem) => [s.id, s.name]));
      setStaffMap(sMap);
      setServiceMap(svMap);
      setItems(enrich(appts, sMap, svMap, new Date()));
      setError(null);
    } catch {
      setError('Could not load upcoming appointments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const poll = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(poll);
  }, [fetchData]);

  // Refresh countdowns every minute from local state — no extra API call needed
  useEffect(() => {
    const tick = setInterval(() => {
      setItems(prev => prev.map(i => ({
        ...i,
        minsUntil: Math.max(0, differenceInMinutes(parseISO(i.appt.scheduled_at), new Date())),
      })));
    }, 60_000);
    return () => clearInterval(tick);
  }, []);

  const handleCheckedIn = (id: string) => {
    setItems(prev => prev.filter(i => i.appt.id !== id));
  };

  const handleRowClick = (item: EnrichedAppointment) => {
    setSelectedAppt(item);
    setDialogOpen(true);
  };

  return (
    <>
      <div className="db-sidebar-section">
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 2 }}>
          <span className="db-upnext-title">Up next</span>
          <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-5)' }}>
            {loading ? '' : `${items.length} today`}
          </span>
        </div>
        <span
          className="db-editorial"
          style={{ fontSize: 14, color: 'var(--db-ink-4)', display: 'block', marginBottom: 12 }}
        >
          The next guests through the door.
        </span>

        {loading && (
          <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-5)' }}>
            Loading…
          </p>
        )}

        {!loading && error && (
          <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-red)' }}>
            {error}
          </p>
        )}

        {!loading && !error && items.length === 0 && (
          <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-5)', fontStyle: 'italic' }}>
            No appointments scheduled for the rest of today.
          </p>
        )}

        {!loading && items.map((item) => (
          <div
            key={item.appt.id}
            className="db-appt-row"
            style={{ cursor: 'pointer' }}
            onClick={() => handleRowClick(item)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && handleRowClick(item)}
          >
            {/* Time column */}
            <div style={{ textAlign: 'center', minWidth: 40, flexShrink: 0 }}>
              <div
                className="db-num"
                style={{ fontSize: 17, fontWeight: 300, letterSpacing: '-0.5px', fontVariantNumeric: 'tabular-nums', color: 'var(--db-ink)', lineHeight: 1 }}
              >
                {format(parseISO(item.appt.scheduled_at), 'HH:mm')}
              </div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, color: 'var(--db-ink-5)', marginTop: 1 }}>
                in {item.minsUntil}m
              </div>
            </div>

            {/* Status dot */}
            <div className="db-appt-dot" />

            {/* Customer / service / staff info */}
            <div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, fontWeight: 700, color: 'var(--db-ink)' }}>
                {item.appt.customer_name}
              </div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-3)', marginTop: 1 }}>
                {item.serviceName}
              </div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, color: 'var(--db-ink-5)', marginTop: 1 }}>
                with {item.staffName}
              </div>
            </div>
          </div>
        ))}

        {!loading && items.length === MAX_VISIBLE && (
          <p className="db-editorial" style={{ fontSize: 12, color: 'var(--db-ink-5)', textAlign: 'center', paddingTop: 8 }}>
            Tap a row to check in →
          </p>
        )}
      </div>

      <CheckInDialog
        open={dialogOpen}
        appointment={selectedAppt?.appt ?? null}
        staffName={selectedAppt?.staffName ?? ''}
        serviceName={selectedAppt?.serviceName ?? ''}
        onCheckedIn={handleCheckedIn}
        onOpenChange={setDialogOpen}
      />
    </>
  );
}
