'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { Loader2, User, UserPlus } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';

const staffSchema = z.object({
  user_id: z.string().min(1, 'User is required'),
  display_name: z.string().min(1, 'Display name is required'),
  specialization: z.string().optional(), // Comma separated string for input
  is_active: z.boolean(),
  is_service_provider: z.boolean(),
});

interface StaffDialogProps {
  open: boolean;
  staff: any | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function StaffDialog({ open, staff, onClose, onSuccess }: StaffDialogProps) {
  const [users, setUsers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUsersLoading, setIsUsersLoading] = useState(false);

  const form = useForm<z.infer<typeof staffSchema>>({
    resolver: zodResolver(staffSchema),
    defaultValues: {
      user_id: '',
      display_name: '',
      specialization: '',
      is_active: true,
      is_service_provider: true,
    },
  });

  useEffect(() => {
    if (open) {
        document.body.style.pointerEvents = 'auto';
      if (staff) {
        // Edit mode
        form.reset({
          user_id: staff.user_id,
          display_name: staff.display_name,
          specialization: staff.specialization?.join(', ') || '',
          is_active: staff.is_active,
          is_service_provider: staff.is_service_provider ?? true,
        });
      } else {
        // Create mode - fetch eligible users
        form.reset({
          user_id: '',
          display_name: '',
          specialization: '',
          is_active: true,
          is_service_provider: true,
        });
        fetchEligibleUsers();
      }
    }
  }, [open, staff, form]);

  const fetchEligibleUsers = async () => {
    try {
      setIsUsersLoading(true);
      // Fetch users and staff profiles, then cross-reference to find users without staff profiles
      const [usersRes, staffRes] = await Promise.all([
        apiClient.get('/users?size=100'),
        apiClient.get('/staff?size=100'),
      ]);

      const usersWithStaff = new Set(
        (staffRes.data.items || []).map((s: any) => s.user_id)
      );
      const eligibleUsers = (usersRes.data.items || []).filter(
        (u: any) => u.is_active && !usersWithStaff.has(u.id)
      );
      setUsers(eligibleUsers);

    } catch (error) {
      console.error('Failed to fetch users', error);
      toast.error('Failed to load eligible users');
    } finally {
      setIsUsersLoading(false);
    }
  };

  const onSubmit = async (values: z.infer<typeof staffSchema>) => {
    try {
      setIsLoading(true);

      const payload: any = {
        ...values,
        specialization: values.specialization
          ? values.specialization.split(',').map(s => s.trim()).filter(Boolean)
          : [],
      };

      if (staff) {
        // Edit
        await apiClient.patch(`/staff/${staff.id}`, {
            display_name: payload.display_name,
            specialization: payload.specialization,
            is_active: payload.is_active,
            is_service_provider: payload.is_service_provider,
        });
        toast.success('Staff profile updated');
      } else {
        // Create
        await apiClient.post('/staff', payload);
        toast.success('Staff profile created');
      }
      onSuccess();
    } catch (error: any) {
      console.error('Staff save error:', error);

      // Handle different error response formats
      let errorMessage = 'Failed to save staff profile';

      if (error.response?.data) {
        const detail = error.response.data.detail;

        // Handle validation errors object with errors array
        if (detail?.message && detail?.errors) {
          errorMessage = detail.message;
          if (Array.isArray(detail.errors) && detail.errors.length > 0) {
            errorMessage += ': ' + detail.errors.join(', ');
          }
        }
        // Handle simple string detail
        else if (typeof detail === 'string') {
          errorMessage = detail;
        }
        // Handle detail object with message
        else if (detail?.message) {
          errorMessage = detail.message;
        }
      }
      // Handle network errors
      else if (error.request) {
        errorMessage = 'Network error. Please check your connection.';
      }
      // Handle other errors
      else if (error.message) {
        errorMessage = error.message;
      }

      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // When a user is selected, auto-fill display name if empty
  const handleUserSelect = (userId: string) => {
    form.setValue('user_id', userId);
    const selectedUser = users.find(u => u.id === userId);
    if (selectedUser && !form.getValues('display_name')) {
        form.setValue('display_name', selectedUser.full_name);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="mx-auto bg-purple-100 p-3 rounded-full w-fit mb-2">
            {staff ? <User className="h-6 w-6 text-purple-600" /> : <UserPlus className="h-6 w-6 text-purple-600" />}
          </div>
          <DialogTitle className="text-center text-xl">{staff ? 'Edit Staff Profile' : 'Add Staff Member'}</DialogTitle>
          <DialogDescription className="text-center">
            {staff ? 'Update staff details.' : 'Create a staff profile for an existing system user.'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            
            {!staff && (
                 <FormField
                 control={form.control}
                 name="user_id"
                 render={({ field }) => (
                     <FormItem>
                     <FormLabel>Select User</FormLabel>
                     <Select onValueChange={handleUserSelect} defaultValue={field.value}>
                         <FormControl>
                         <SelectTrigger>
                             <SelectValue placeholder={isUsersLoading ? "Loading..." : "Select a user"} />
                         </SelectTrigger>
                         </FormControl>
                         <SelectContent>
                             {users.map((u) => (
                                 <SelectItem key={u.id} value={u.id}>
                                     {u.full_name} (@{u.username})
                                 </SelectItem>
                             ))}
                         </SelectContent>
                     </Select>
                     <FormDescription>
                        Users without a staff profile are shown.
                     </FormDescription>
                     <FormMessage />
                     </FormItem>
                 )}
                 />
            )}

            <FormField
              control={form.control}
              name="display_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display Name</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Sarah J." {...field} />
                  </FormControl>
                  <FormDescription>Name shown on appointments and receipts.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="specialization"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Specializations</FormLabel>
                  <FormControl>
                    <Input placeholder="Hair Cutting, Coloring, Styling" {...field} />
                  </FormControl>
                  <FormDescription>Comma separated list of skills.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>
                      Active Status
                    </FormLabel>
                    <FormDescription>
                      Inactive staff cannot be assigned new appointments.
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_service_provider"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>
                      Service Provider
                    </FormLabel>
                    <FormDescription>
                      When enabled, this staff member appears in the service assignment dropdown in POS.
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {staff ? 'Save Changes' : 'Create Profile'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
