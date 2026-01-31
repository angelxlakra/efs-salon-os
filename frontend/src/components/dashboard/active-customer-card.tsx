'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Clock, CheckCircle, Circle, Loader } from 'lucide-react';

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

interface CustomerSession {
  session_id: string;
  customer_name: string;
  customer_phone: string;
  customer_id: string | null;
  walkins: WalkIn[];
  total_amount: number; // in paise
  time_since_checkin: number; // minutes
  all_completed: boolean;
}

interface ActiveCustomerCardProps {
  session: CustomerSession;
  onCheckout: (sessionId: string) => void;
}

export function ActiveCustomerCard({
  session,
  onCheckout,
}: ActiveCustomerCardProps) {
  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'checked_in':
        return <Circle className="h-3 w-3 text-blue-500" />;
      case 'in_progress':
        return <Loader className="h-3 w-3 text-amber-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      default:
        return <Circle className="h-3 w-3 text-gray-400" />;
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="p-4 pb-2">
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-base truncate leading-none">
                {session.customer_name}
              </h3>
              <Badge variant="secondary" className="h-5 px-1.5 text-[10px] font-normal">
                <Clock className="h-3 w-3 mr-1" />
                {session.time_since_checkin}m
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {session.customer_phone}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 py-2">
        <div className="space-y-2">
          {session.walkins.map((walkin) => (
            <div
              key={walkin.id}
              className="flex items-center justify-between text-sm"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {getStatusIcon(walkin.status)}
                <span className="truncate font-medium text-xs">
                  {walkin.service.name}
                </span>
                <span className="text-[10px] text-muted-foreground truncate">
                  • {walkin.assigned_staff.display_name}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-3 pt-2 border-t flex justify-between items-center">
          <span className="text-xs text-muted-foreground">Total Amount</span>
          <span className="font-semibold text-sm">
            {formatPrice(session.total_amount)}
          </span>
        </div>
      </CardContent>

      <CardFooter className="p-4 pt-1">
        <Button
          className="w-full h-8 text-xs"
          size="sm"
          onClick={() => onCheckout(session.session_id)}
        >
          Checkout
        </Button>
      </CardFooter>
    </Card>
  );
}
