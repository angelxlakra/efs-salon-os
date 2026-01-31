'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import {
  Dialog,
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
import { Switch } from '@/components/ui/switch';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface ServiceCategory {
  id: string;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
}

interface Service {
  id: string;
  category_id: string;
  name: string;
  description: string;
  base_price: number; // in paise
  duration_minutes: number;
  is_active: boolean;
  display_order: number;
}

interface ServiceDialogProps {
  open: boolean;
  service: Service | null;
  categories: ServiceCategory[];
  onClose: () => void;
  onSuccess: () => void;
}

const serviceSchema = z.object({
  name: z.string().min(1, 'Service name is required').max(100, 'Name too long'),
  description: z.string().max(500, 'Description too long').optional(),
  category_id: z.string().min(1, 'Category is required'),
  base_price: z.string().min(1, 'Price is required'),
  duration_minutes: z.string().min(1, 'Duration is required'),
  is_active: z.boolean(),
});

type ServiceFormData = z.infer<typeof serviceSchema>;

export function ServiceDialog({ open, service, categories, onClose, onSuccess }: ServiceDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEdit = !!service;

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<ServiceFormData>({
    resolver: zodResolver(serviceSchema),
    defaultValues: {
      name: '',
      description: '',
      category_id: '',
      base_price: '',
      duration_minutes: '',
      is_active: true,
    },
  });

  const isActive = watch('is_active');

  useEffect(() => {
    if (open && service) {
      // Populate form with existing service data
      reset({
        name: service.name,
        description: service.description || '',
        category_id: service.category_id,
        base_price: (service.base_price / 100).toFixed(2), // Convert paise to rupees
        duration_minutes: service.duration_minutes.toString(),
        is_active: service.is_active,
      });
    } else if (open && !service) {
      // Reset form for new service
      reset({
        name: '',
        description: '',
        category_id: '',
        base_price: '',
        duration_minutes: '',
        is_active: true,
      });
    }
  }, [open, service, reset]);

  const onSubmit = async (data: ServiceFormData) => {
    try {
      setIsSubmitting(true);

      // Convert price from rupees to paise
      const priceInPaise = Math.round(parseFloat(data.base_price) * 100);
      const durationMinutes = parseInt(data.duration_minutes);

      const payload = {
        name: data.name,
        description: data.description || '',
        category_id: data.category_id,
        base_price: priceInPaise,
        duration_minutes: durationMinutes,
        is_active: data.is_active,
      };

      if (isEdit) {
        await apiClient.put(`/catalog/services/${service.id}`, payload);
        toast.success('Service updated successfully');
      } else {
        await apiClient.post('/catalog/services', payload);
        toast.success('Service created successfully');
      }

      onSuccess();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Failed to ${isEdit ? 'update' : 'create'} service`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Service' : 'Create New Service'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Update service details below.' : 'Add a new service to your catalog.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Service Name *</Label>
            <Input
              id="name"
              placeholder="e.g., Men's Haircut"
              {...register('name')}
              disabled={isSubmitting}
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Brief description of the service"
              rows={3}
              {...register('description')}
              disabled={isSubmitting}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description.message}</p>
            )}
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label htmlFor="category_id">Category *</Label>
            <Select
              value={watch('category_id')}
              onValueChange={(value) => setValue('category_id', value)}
              disabled={isSubmitting}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.category_id && (
              <p className="text-sm text-red-600">{errors.category_id.message}</p>
            )}
          </div>

          {/* Price and Duration */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="base_price">Price (₹) *</Label>
              <Input
                id="base_price"
                type="number"
                step="0.01"
                min="0"
                placeholder="500.00"
                {...register('base_price')}
                disabled={isSubmitting}
              />
              {errors.base_price && (
                <p className="text-sm text-red-600">{errors.base_price.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="duration_minutes">Duration (min) *</Label>
              <Input
                id="duration_minutes"
                type="number"
                min="1"
                placeholder="30"
                {...register('duration_minutes')}
                disabled={isSubmitting}
              />
              {errors.duration_minutes && (
                <p className="text-sm text-red-600">{errors.duration_minutes.message}</p>
              )}
            </div>
          </div>

          {/* Active Status */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="is_active">Active</Label>
              <p className="text-sm text-gray-500">
                Inactive services won't appear in POS
              </p>
            </div>
            <Switch
              id="is_active"
              checked={isActive}
              onCheckedChange={(checked) => setValue('is_active', checked)}
              disabled={isSubmitting}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEdit ? 'Update' : 'Create'} Service
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
