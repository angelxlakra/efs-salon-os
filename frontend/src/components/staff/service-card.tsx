'use client';

import { useState } from 'react';
import { Play, Check, Clock, Calendar, User, FileText, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';

interface Service {
  id: string;
  name: string;
  base_price: number;
  duration_minutes: number;
}

interface Staff {
  id: string;
  display_name: string;
}

interface WalkIn {
  id: string;
  ticket_number: string;
  customer_name: string;
  customer_phone: string;
  customer_id: string | null;
  service: Service;
  assigned_staff: Staff;
  status: string;
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  service_notes: string | null;
  duration_minutes: number;
  session_id: string | null;
}

interface ServiceCardProps {
  service: WalkIn;
  onStart: (id: string) => void;
  onComplete: (id: string) => void;
  onAddNote: (id: string, note: string) => void;
  onCancel: (id: string) => void;
}

export function ServiceCard({
  service,
  onStart,
  onComplete,
  onAddNote,
  onCancel,
}: ServiceCardProps) {
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState(service.service_notes || '');
  const [isSavingNotes, setIsSavingNotes] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'checked_in':
        return 'bg-blue-50 border-blue-200';
      case 'in_progress':
        return 'bg-amber-50 border-amber-200';
      case 'completed':
        return 'bg-green-50 border-green-200';
      case 'cancelled':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'checked_in':
        return <Badge variant="secondary">Checked In</Badge>;
      case 'in_progress':
        return <Badge className="bg-amber-500">In Progress</Badge>;
      case 'completed':
        return <Badge className="bg-green-500">Completed</Badge>;
      case 'cancelled':
        return <Badge variant="destructive">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return 'Not set';
    return new Date(timestamp).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleSaveNotes = async () => {
    setIsSavingNotes(true);
    await onAddNote(service.id, notes);
    setIsSavingNotes(false);
  };

  return (
    <Card className={`${getStatusColor(service.status)} transition-all`}>
      <CardHeader className="p-3 pb-2">
        <div className="flex justify-between items-start gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base truncate">{service.service.name}</h3>
            <p className="text-xs text-muted-foreground">
              {service.ticket_number}
            </p>
          </div>
          {getStatusBadge(service.status)}
        </div>
      </CardHeader>

      <CardContent className="p-3 pt-0 space-y-2">
        {/* Customer Info - Compact */}
        <div className="bg-white/60 rounded-md p-2">
          <div className="flex items-center gap-2">
            <User className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-sm truncate">{service.customer_name}</p>
              <p className="text-xs text-muted-foreground">{service.customer_phone}</p>
            </div>
          </div>
        </div>

        {/* Service Details - Compact */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{service.duration_minutes} min</span>
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>{formatTime(service.checked_in_at)}</span>
          </div>
        </div>

        {service.started_at && (
          <div className="text-xs text-muted-foreground">
            Started: {formatTime(service.started_at)}
          </div>
        )}

        {/* Service Notes - Collapsed by default */}
        {!showNotes && service.service_notes && (
          <p className="text-xs text-muted-foreground italic truncate">
            {service.service_notes}
          </p>
        )}

        {showNotes && (
          <div className="space-y-2">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes..."
              className="min-h-[60px] text-sm"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={handleSaveNotes}
                disabled={isSavingNotes || notes === service.service_notes}
                className="flex-1 h-8 text-xs"
              >
                {isSavingNotes ? 'Saving...' : 'Save'}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowNotes(false)}
                className="h-8 text-xs"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="p-3 pt-0 flex gap-2">
        {service.status === 'checked_in' && (
          <>
            <Button onClick={() => onStart(service.id)} className="flex-1 h-9" size="sm">
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Start
            </Button>
            <Button
              onClick={() => onCancel(service.id)}
              variant="outline"
              className="h-9 px-3 text-destructive hover:bg-destructive/10"
              size="sm"
              title="Cancel service"
            >
              <XCircle className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
        {service.status === 'in_progress' && (
          <>
            <Button onClick={() => onComplete(service.id)} className="flex-1 h-9" size="sm">
              <Check className="h-3.5 w-3.5 mr-1.5" />
              Complete
            </Button>
            {!showNotes && (
              <Button
                onClick={() => setShowNotes(true)}
                variant="outline"
                className="h-9 px-3"
                size="sm"
              >
                <FileText className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button
              onClick={() => onCancel(service.id)}
              variant="outline"
              className="h-9 px-3 text-destructive hover:bg-destructive/10"
              size="sm"
              title="Cancel service"
            >
              <XCircle className="h-3.5 w-3.5" />
            </Button>
          </>
        )}
        {service.status === 'completed' && (
          <>
            <div className="flex-1 text-center text-xs text-green-600 font-medium py-2">
              ✓ Completed
            </div>
            {!showNotes && (
              <Button
                onClick={() => setShowNotes(true)}
                variant="outline"
                className="h-9 px-3"
                size="sm"
              >
                <FileText className="h-3.5 w-3.5" />
              </Button>
            )}
          </>
        )}
        {service.status === 'cancelled' && (
          <div className="flex-1 text-center text-xs text-red-600 font-medium py-2">
            ✗ Cancelled
          </div>
        )}
      </CardFooter>
    </Card>
  );
}
