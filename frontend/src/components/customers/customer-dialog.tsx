'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  date_of_birth: string | null;
  gender: string | null;
  notes: string | null;
  total_visits: number;
  total_spent: number;
  last_visit_at: string | null;
  created_at: string;
}

interface CustomerDialogProps {
  open: boolean;
  customer: Customer | null;
  initialPhone?: string;
  onClose: () => void;
  onSuccess: (customer?: { id: string; first_name: string; last_name: string; phone: string }) => void;
}

const customerSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(50, 'Name too long'),
  last_name: z.string().min(1, 'Last name is required').max(50, 'Name too long'),
  phone: z
    .string()
    .min(10, 'Phone must be 10 digits')
    .max(10, 'Phone must be 10 digits')
    .regex(/^\d+$/, 'Phone must contain only numbers'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  date_of_birth: z.string().optional(),
  gender: z.string().optional(),
  notes: z.string().max(1000, 'Notes too long').optional(),
});

type CustomerFormData = z.infer<typeof customerSchema>;

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function CustomerDialog({ open, customer, initialPhone, onClose, onSuccess }: CustomerDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [birthMonth, setBirthMonth] = useState('');
  const [birthDay, setBirthDay] = useState('');
  const isEdit = !!customer;

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      date_of_birth: '',
      gender: '',
      notes: '',
    },
  });

  const gender = watch('gender');

  useEffect(() => {
    if (open && customer) {
      // Populate form with existing customer data
      reset({
        first_name: customer.first_name,
        last_name: customer.last_name,
        phone: customer.phone || '',
        email: customer.email || '',
        date_of_birth: customer.date_of_birth || '',
        gender: customer.gender || '',
        notes: customer.notes || '',
      });
      // Parse stored date into month + day (ignore year)
      if (customer.date_of_birth) {
        const parts = customer.date_of_birth.split('-');
        setBirthMonth(parts[1] ? String(parseInt(parts[1], 10)) : '');
        setBirthDay(parts[2] ? String(parseInt(parts[2], 10)) : '');
      } else {
        setBirthMonth('');
        setBirthDay('');
      }
    } else if (open && !customer) {
      // Reset form for new customer, pre-fill phone if provided
      const phoneValue = initialPhone?.replace(/\D/g, '').slice(-10) || '';
      reset({
        first_name: '',
        last_name: '',
        phone: phoneValue,
        email: '',
        date_of_birth: '',
        gender: '',
        notes: '',
      });
      setBirthMonth('');
      setBirthDay('');
    }
  }, [open, customer, initialPhone, reset]);

  const onSubmit = async (data: CustomerFormData) => {
    try {
      setIsSubmitting(true);

      // Construct date_of_birth from month+day selects; use 1900 as placeholder year
      const date_of_birth =
        birthMonth && birthDay
          ? `1900-${String(birthMonth).padStart(2, '0')}-${String(birthDay).padStart(2, '0')}`
          : null;

      const payload = {
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone,
        email: data.email || null,
        date_of_birth,
        gender: data.gender || null,
        notes: data.notes || '',
      };

      if (isEdit) {
        await apiClient.patch(`/customers/${customer.id}`, payload);
        toast.success('Customer updated successfully');
        onSuccess();
      } else {
        const { data: created } = await apiClient.post('/customers', payload);
        toast.success('Customer created successfully');
        onSuccess({
          id: created.id,
          first_name: created.first_name,
          last_name: created.last_name,
          phone: created.phone,
        });
      }
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || `Failed to ${isEdit ? 'update' : 'create'} customer`
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent size="md">
        <form onSubmit={handleSubmit(onSubmit)} className="contents">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Customer' : 'Add New Customer'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Update customer details below.' : 'Add a new customer to your database.'}
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="space-y-4">
          {/* Name */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First Name *</Label>
              <Input
                id="first_name"
                placeholder="John"
                {...register('first_name')}
                disabled={isSubmitting}
              />
              {errors.first_name && (
                <p className="text-sm text-red-600">{errors.first_name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="last_name">Last Name *</Label>
              <Input
                id="last_name"
                placeholder="Doe"
                {...register('last_name')}
                disabled={isSubmitting}
              />
              {errors.last_name && (
                <p className="text-sm text-red-600">{errors.last_name.message}</p>
              )}
            </div>
          </div>

          {/* Phone */}
          <div className="space-y-2">
            <Label htmlFor="phone">Phone Number *</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="9876543210"
              maxLength={10}
              {...register('phone')}
              disabled={isSubmitting}
            />
            {errors.phone && <p className="text-sm text-red-600">{errors.phone.message}</p>}
            <p className="text-xs text-gray-500">10-digit mobile number without +91</p>
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="john.doe@example.com"
              {...register('email')}
              disabled={isSubmitting}
            />
            {errors.email && <p className="text-sm text-red-600">{errors.email.message}</p>}
          </div>

          {/* Gender and DOB */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="gender">Gender</Label>
              <Select
                value={gender}
                onValueChange={(value) => setValue('gender', value)}
                disabled={isSubmitting}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select gender" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="male">Male</SelectItem>
                  <SelectItem value="female">Female</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Birthday</Label>
              <div className="flex gap-2">
                <Select
                  value={birthMonth}
                  onValueChange={setBirthMonth}
                  disabled={isSubmitting}
                >
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="Month" />
                  </SelectTrigger>
                  <SelectContent>
                    {MONTHS.map((name, i) => (
                      <SelectItem key={i + 1} value={String(i + 1)}>
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={birthDay}
                  onValueChange={setBirthDay}
                  disabled={isSubmitting}
                >
                  <SelectTrigger className="w-20">
                    <SelectValue placeholder="Day" />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
                      <SelectItem key={d} value={String(d)}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes / Preferences</Label>
            <Textarea
              id="notes"
              placeholder="Allergies, preferences, special instructions..."
              rows={3}
              {...register('notes')}
              disabled={isSubmitting}
            />
            {errors.notes && <p className="text-sm text-red-600">{errors.notes.message}</p>}
          </div>
        </DialogBody>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEdit ? 'Update' : 'Create'} Customer
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
