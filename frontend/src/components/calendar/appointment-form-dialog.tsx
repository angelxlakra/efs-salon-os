"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { format } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Combobox } from "@/components/ui/combobox";
import { toast } from "sonner";
import {
  createAppointment,
  updateAppointment,
} from "@/lib/api/appointments";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";

const schema = z.object({
  customer_name: z.string().min(2, "Name must be at least 2 characters"),
  customer_phone: z.string().min(10, "Enter a valid phone number").max(15),
  service_id: z.string().min(1, "Select a service"),
  assigned_staff_id: z.string().optional(),
  date: z.string().min(1, "Select a date"),
  time: z.string().min(1, "Select a time"),
  duration_minutes: z.coerce.number().min(15).max(480),
  booking_notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-fill date+time for "click slot to create" */
  defaultDatetime?: string;
  /** Pre-fill staff for the clicked column */
  defaultStaffId?: string;
  /** Non-null when editing an existing appointment */
  appointment?: Appointment;
  staff: StaffMember[];
  services: ServiceItem[];
  onSaved: (appt: Appointment) => void;
};

export function AppointmentFormDialog({
  open,
  onOpenChange,
  defaultDatetime,
  defaultStaffId,
  appointment,
  staff,
  services,
  onSaved,
}: Props) {
  const isEdit = !!appointment;

  const defaultDate = defaultDatetime
    ? defaultDatetime.substring(0, 10)
    : appointment
    ? appointment.scheduled_at.substring(0, 10)
    : format(new Date(), "yyyy-MM-dd");

  const defaultTime = defaultDatetime
    ? defaultDatetime.substring(11, 16)
    : appointment
    ? appointment.scheduled_at.substring(11, 16)
    : "10:00";

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      customer_name: appointment?.customer_name ?? "",
      customer_phone: appointment?.customer_phone ?? "",
      service_id: appointment?.service_id ?? "",
      assigned_staff_id: appointment?.assigned_staff_id ?? defaultStaffId ?? "",
      date: defaultDate,
      time: defaultTime,
      duration_minutes: appointment?.duration_minutes ?? 30,
      booking_notes: appointment?.booking_notes ?? "",
    },
  });

  const selectedServiceId = watch("service_id");

  // Auto-fill duration when a service is chosen
  React.useEffect(() => {
    if (!selectedServiceId) return;
    const svc = services.find((s) => s.id === selectedServiceId);
    if (svc) setValue("duration_minutes", svc.duration_minutes);
  }, [selectedServiceId, services, setValue]);

  // Reset form when dialog opens with new defaults
  React.useEffect(() => {
    if (open) reset({
      customer_name: appointment?.customer_name ?? "",
      customer_phone: appointment?.customer_phone ?? "",
      service_id: appointment?.service_id ?? "",
      assigned_staff_id: appointment?.assigned_staff_id ?? defaultStaffId ?? "",
      date: defaultDate,
      time: defaultTime,
      duration_minutes: appointment?.duration_minutes ?? 30,
      booking_notes: appointment?.booking_notes ?? "",
    });
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const onSubmit = async (values: FormValues) => {
    const scheduled_at = `${values.date}T${values.time}:00`;
    try {
      let saved: Appointment;
      if (isEdit && appointment) {
        saved = await updateAppointment(appointment.id, {
          service_id: values.service_id,
          assigned_staff_id: values.assigned_staff_id || undefined,
          scheduled_at,
          duration_minutes: values.duration_minutes,
          booking_notes: values.booking_notes || undefined,
        });
        toast.success("Appointment updated");
      } else {
        saved = await createAppointment({
          customer_name: values.customer_name,
          customer_phone: values.customer_phone,
          service_id: values.service_id,
          assigned_staff_id: values.assigned_staff_id || undefined,
          scheduled_at,
          duration_minutes: values.duration_minutes,
          booking_notes: values.booking_notes || undefined,
        });
        toast.success("Appointment booked");
      }
      onSaved(saved);
      onOpenChange(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to save";
      toast.error(msg);
    }
  };

  const serviceOptions = services.map((s) => ({
    value: s.id,
    label: `${s.name} (${s.category_name})`,
  }));

  const staffOptions = [
    { value: "", label: "— Any staff —" },
    ...staff.map((s) => ({ value: s.id, label: s.display_name })),
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit appointment" : "New appointment"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 mt-2">
          {!isEdit && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <Label htmlFor="customer_name">Customer name *</Label>
                  <Input id="customer_name" {...register("customer_name")} placeholder="Priya Sharma" />
                  {errors.customer_name && <p className="text-[11px] text-danger-fg">{errors.customer_name.message}</p>}
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="customer_phone">Phone *</Label>
                  <Input id="customer_phone" {...register("customer_phone")} placeholder="9876543210" />
                  {errors.customer_phone && <p className="text-[11px] text-danger-fg">{errors.customer_phone.message}</p>}
                </div>
              </div>
            </>
          )}

          <div className="flex flex-col gap-1">
            <Label>Service *</Label>
            <Combobox
              options={serviceOptions}
              value={watch("service_id")}
              onChange={(v) => setValue("service_id", v ?? "", { shouldValidate: true })}
              placeholder="Search services…"
            />
            {errors.service_id && <p className="text-[11px] text-danger-fg">{errors.service_id.message}</p>}
          </div>

          <div className="flex flex-col gap-1">
            <Label>Staff</Label>
            <Combobox
              options={staffOptions}
              value={watch("assigned_staff_id") ?? ""}
              onChange={(v) => setValue("assigned_staff_id", v ?? "")}
              placeholder="Any staff"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="date">Date *</Label>
              <Input id="date" type="date" {...register("date")} />
              {errors.date && <p className="text-[11px] text-danger-fg">{errors.date.message}</p>}
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="time">Time *</Label>
              <Input id="time" type="time" {...register("time")} step="900" />
              {errors.time && <p className="text-[11px] text-danger-fg">{errors.time.message}</p>}
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="duration_minutes">Duration (min)</Label>
              <Input id="duration_minutes" type="number" min={15} max={480} step={15} {...register("duration_minutes")} />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <Label htmlFor="booking_notes">Notes</Label>
            <Input id="booking_notes" {...register("booking_notes")} placeholder="Any special requests…" />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              {isEdit ? "Save changes" : "Book appointment"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
