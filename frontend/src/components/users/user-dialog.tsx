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
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { Loader2, UserCog, UserPlus } from 'lucide-react';

const userSchema = z.object({
  full_name: z.string().min(1, 'Full name is required').max(255, 'Name too long'),
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username too long')
    .regex(/^[a-z0-9_]+$/, 'Username must be lowercase alphanumeric with underscores'),
  email: z.string().email('Invalid email address').optional().or(z.literal('')),
  phone: z.string()
    .min(10, 'Phone must be at least 10 digits')
    .max(15, 'Phone too long')
    .regex(/^\+?[0-9]+$/, 'Phone must contain only numbers and optional + prefix'),
  role_id: z.string().min(1, 'Role is required'),
  password: z.string().optional().refine(
    (val) => !val || val.length >= 8,
    { message: 'Password must be at least 8 characters' }
  ),
});

interface UserDialogProps {
  open: boolean;
  user: any | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function UserDialog({ open, user, onClose, onSuccess }: UserDialogProps) {
  const [roles, setRoles] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRolesLoading, setIsRolesLoading] = useState(false);

  const form = useForm<z.infer<typeof userSchema>>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      full_name: '',
      username: '',
      email: '',
      phone: '',
      role_id: '',
      password: '',
    },
  });

  useEffect(() => {
    if (open) {
      document.body.style.pointerEvents = 'auto'; // Fix for Radix UI issue
      fetchRoles();
      if (user) {
        form.reset({
          full_name: user.full_name,
          username: user.username,
          email: user.email || '',
          phone: user.phone,
          role_id: user.role?.id || '',
          password: '', // Password not editable here normally, but schema allows optional
        });
      } else {
        form.reset({
          full_name: '',
          username: '',
          email: '',
          phone: '',
          role_id: '',
          password: '',
        });
      }
    }
  }, [open, user, form]);

  const fetchRoles = async () => {
    try {
      setIsRolesLoading(true);
      const { data } = await apiClient.get('/roles');
      setRoles(data);
    } catch (error) {
      console.error('Failed to fetch roles', error);
      toast.error('Failed to load roles');
    } finally {
      setIsRolesLoading(false);
    }
  };

  const onSubmit = async (values: z.infer<typeof userSchema>) => {
    try {
      setIsLoading(true);

      // Filter out empty strings for optional fields
      const dataToSubmit: any = { ...values };
      if (!dataToSubmit.email) delete dataToSubmit.email;
      if (!dataToSubmit.password) delete dataToSubmit.password;

      if (user) {
        // Edit mode
        await apiClient.patch(`/users/${user.id}`, dataToSubmit);
        toast.success('User updated successfully');
      } else {
        // Create mode
        if (!values.password) {
            toast.error("Password is required for new users");
            return;
        }
        await apiClient.post('/users', dataToSubmit);
        toast.success('User created successfully');
      }
      onSuccess();
    } catch (error: any) {
      console.error('User save error:', error);

      // Handle different error response formats
      let errorMessage = 'Failed to save user';

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

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="mx-auto bg-primary/10 p-3 rounded-full w-fit mb-2">
            {user ? <UserCog className="h-6 w-6 text-primary" /> : <UserPlus className="h-6 w-6 text-primary" />}
          </div>
          <DialogTitle className="text-center text-xl">{user ? 'Edit User Profile' : 'Create New User'}</DialogTitle>
          <DialogDescription className="text-center">
            {user ? 'Update user details, roles, and contact information.' : 'Add a new system user to grant access to the dashboard.'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Full Name</FormLabel>
                  <FormControl>
                    <Input placeholder="John Doe" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
                <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                        <Input placeholder="johndoe" {...field} disabled={!!user} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
                />
                 <FormField
                control={form.control}
                name="role_id"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Role</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
                        <FormControl>
                        <SelectTrigger>
                            <SelectValue placeholder="Select role" />
                        </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                            {roles.map((role) => (
                                <SelectItem key={role.id} value={role.id}>{role.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <FormMessage />
                    </FormItem>
                )}
                />
            </div>

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input placeholder="john@example.com" type="email" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="phone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Phone</FormLabel>
                  <FormControl>
                    <Input placeholder="+91..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {!user && (
                <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                        <Input type="password" placeholder="Min 8 chars, 1 upper, 1 lower, 1 digit" {...field} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
                />
            )}

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {user ? 'Save Changes' : 'Create User'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
