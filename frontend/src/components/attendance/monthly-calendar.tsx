'use client';

import { CheckCircle, Clock, XCircle, Coffee, Minus } from 'lucide-react';

interface AttendanceRecord {
  id: string;
  staff_id: string;
  date: string;
  status: 'present' | 'half_day' | 'absent' | 'leave';
  signed_in_at: string | null;
  signed_out_at: string | null;
}

interface MonthlyCalendarProps {
  year: number;
  month: number;
  records: AttendanceRecord[];
}

const statusConfig = {
  present: {
    label: 'P',
    color: 'bg-green-100 text-green-800',
    icon: CheckCircle,
  },
  half_day: {
    label: 'H',
    color: 'bg-orange-100 text-orange-800',
    icon: Clock,
  },
  absent: {
    label: 'A',
    color: 'bg-red-100 text-red-800',
    icon: XCircle,
  },
  leave: {
    label: 'L',
    color: 'bg-blue-100 text-blue-800',
    icon: Coffee,
  },
};

export function MonthlyCalendar({ year, month, records }: MonthlyCalendarProps) {
  // Get number of days in month
  const daysInMonth = new Date(year, month, 0).getDate();

  // Get first day of month (0 = Sunday, 1 = Monday, etc.)
  const firstDayOfMonth = new Date(year, month - 1, 1).getDay();

  // Create a map of date -> attendance record
  const recordsByDate = new Map<string, AttendanceRecord>();
  records.forEach((record) => {
    const date = new Date(record.date);
    const day = date.getDate();
    recordsByDate.set(day.toString(), record);
  });

  // Create array of weeks
  const weeks: (number | null)[][] = [];
  let currentWeek: (number | null)[] = [];

  // Fill initial empty days
  for (let i = 0; i < firstDayOfMonth; i++) {
    currentWeek.push(null);
  }

  // Fill days
  for (let day = 1; day <= daysInMonth; day++) {
    currentWeek.push(day);

    // If Sunday (index 6) or last day, push week and start new one
    if (currentWeek.length === 7 || day === daysInMonth) {
      // Fill remaining days if last week
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      weeks.push(currentWeek);
      currentWeek = [];
    }
  }

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header with day names */}
      <div className="grid grid-cols-7 bg-muted">
        {dayNames.map((dayName) => (
          <div
            key={dayName}
            className="p-2 text-center text-sm font-medium border-r last:border-r-0"
          >
            {dayName}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div>
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="grid grid-cols-7 border-t">
            {week.map((day, dayIndex) => {
              if (day === null) {
                return (
                  <div
                    key={`empty-${dayIndex}`}
                    className="p-2 h-16 border-r last:border-r-0 bg-muted/30"
                  />
                );
              }

              const record = recordsByDate.get(day.toString());
              const dayOfWeek = new Date(year, month - 1, day).getDay();
              const isSunday = dayOfWeek === 0;

              return (
                <div
                  key={day}
                  className={`p-2 h-16 border-r last:border-r-0 ${
                    isSunday ? 'bg-muted/50' : ''
                  }`}
                >
                  <div className="flex flex-col h-full">
                    <span className="text-xs text-muted-foreground mb-1">{day}</span>
                    {record ? (
                      <div
                        className={`flex items-center justify-center rounded px-2 py-1 text-sm font-medium ${
                          statusConfig[record.status].color
                        }`}
                      >
                        {statusConfig[record.status].label}
                      </div>
                    ) : isSunday ? (
                      <div className="flex items-center justify-center rounded px-2 py-1 text-sm text-muted-foreground">
                        <Minus className="h-3 w-3" />
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="border-t p-3 bg-muted/30">
        <div className="flex items-center gap-4 flex-wrap text-sm">
          <span className="font-medium">Legend:</span>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded bg-green-100 text-green-800 flex items-center justify-center text-xs font-medium">
              P
            </div>
            <span className="text-muted-foreground">Present</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded bg-orange-100 text-orange-800 flex items-center justify-center text-xs font-medium">
              H
            </div>
            <span className="text-muted-foreground">Half Day</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded bg-red-100 text-red-800 flex items-center justify-center text-xs font-medium">
              A
            </div>
            <span className="text-muted-foreground">Absent</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded bg-blue-100 text-blue-800 flex items-center justify-center text-xs font-medium">
              L
            </div>
            <span className="text-muted-foreground">Leave</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-6 h-6 rounded bg-muted/50 flex items-center justify-center">
              <Minus className="h-3 w-3 text-muted-foreground" />
            </div>
            <span className="text-muted-foreground">Sunday</span>
          </div>
        </div>
      </div>
    </div>
  );
}
