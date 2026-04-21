'use client';

import { format } from 'date-fns';
import { Edit, CheckCircle, Clock, XCircle, Coffee } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface Staff {
  id: string;
  display_name: string;
  full_name: string;
  is_active: boolean;
}

interface AttendanceRecord {
  id: string;
  staff_id: string;
  date: string;
  status: 'present' | 'half_day' | 'absent' | 'leave';
  signed_in_at: string | null;
  signed_out_at: string | null;
  notes: string | null;
  staff: Staff;
}

interface AttendanceTableProps {
  records: AttendanceRecord[];
  onEdit: (staff: Staff) => void;
  canEdit: boolean;
}

const statusConfig = {
  present: {
    label: 'Present',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: CheckCircle,
  },
  half_day: {
    label: 'Half Day',
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    icon: Clock,
  },
  absent: {
    label: 'Absent',
    color: 'bg-red-100 text-red-800 border-red-200',
    icon: XCircle,
  },
  leave: {
    label: 'Leave',
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: Coffee,
  },
};

export function AttendanceTable({ records, onEdit, canEdit }: AttendanceTableProps) {
  if (records.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No attendance records for this date
      </div>
    );
  }

  return (
    <div className="rounded-md border overflow-hidden">
      {/* Mobile Card View */}
      <div className="block md:hidden divide-y">
        {records.map((record) => {
          const StatusIcon = statusConfig[record.status].icon;
          return (
            <div key={record.id} className="p-3 space-y-2">
              <div className="flex justify-between items-start">
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{record.staff.display_name}</p>
                  <p className="text-sm text-muted-foreground truncate">{record.staff.full_name}</p>
                </div>
                <div className="flex items-center gap-2 ml-2">
                  <Badge variant="outline" className={statusConfig[record.status].color}>
                    <StatusIcon className="h-3 w-3 mr-1" />
                    {statusConfig[record.status].label}
                  </Badge>
                  {canEdit && (
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => onEdit(record.staff)}>
                      <Edit className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
              <div className="flex gap-4 text-sm">
                <span className="text-muted-foreground">
                  In: <span className="text-foreground">{record.signed_in_at ? format(new Date(record.signed_in_at), 'h:mm a') : '-'}</span>
                </span>
                <span className="text-muted-foreground">
                  Out: <span className="text-foreground">{record.signed_out_at ? format(new Date(record.signed_out_at), 'h:mm a') : '-'}</span>
                </span>
              </div>
              {record.notes && (
                <p className="text-sm text-muted-foreground line-clamp-2 break-words">{record.notes}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Staff Member</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Sign In</TableHead>
              <TableHead>Sign Out</TableHead>
              <TableHead>Notes</TableHead>
              {canEdit && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((record) => {
              const StatusIcon = statusConfig[record.status].icon;
              return (
                <TableRow key={record.id}>
                  <TableCell className="font-medium">
                    <div className="min-w-0">
                      <p className="truncate">{record.staff.display_name}</p>
                      <p className="text-sm text-muted-foreground truncate">
                        {record.staff.full_name}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={statusConfig[record.status].color}
                    >
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {statusConfig[record.status].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {record.signed_in_at ? (
                      <span className="text-sm">
                        {format(new Date(record.signed_in_at), 'h:mm a')}
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {record.signed_out_at ? (
                      <span className="text-sm">
                        {format(new Date(record.signed_out_at), 'h:mm a')}
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="max-w-[250px]">
                      {record.notes ? (
                        <p className="text-sm text-muted-foreground line-clamp-2 break-words">
                          {record.notes}
                        </p>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </div>
                  </TableCell>
                  {canEdit && (
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(record.staff)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
