"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  service_id: z.string().optional(),
  assigned_staff_id: z.string().optional(),
  date: z.string().min(1, "Select a date"),
  time: z.string().min(1, "Select a time"),
  duration_minutes: z.number().min(15).max(480),
  booking_notes: z.string().optional(),
});

/** Pre-built list of HH:MM strings at 15-minute intervals (07:00 – 22:00). */
const TIME_SLOTS = (() => {
  const slots: string[] = [];
  for (let h = 7; h <= 22; h++) {
    for (const m of [0, 15, 30, 45]) {
      if (h === 22 && m > 0) break;
      slots.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
    }
  }
  return slots;
})();

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
      date: defaultDatetime
        ? defaultDatetime.substring(0, 10)
        : appointment
        ? appointment.scheduled_at.substring(0, 10)
        : "",
      time: defaultDatetime
        ? defaultDatetime.substring(11, 16)
        : appointment
        ? appointment.scheduled_at.substring(11, 16)
        : "10:00",
      duration_minutes: appointment?.duration_minutes ?? 30,
      booking_notes: appointment?.booking_notes ?? "",
    },
  });

  const selectedServiceId = watch("service_id");
  const selectedStaffId = watch("assigned_staff_id");

  // Auto-fill duration when a service is chosen
  React.useEffect(() => {
    if (!selectedServiceId || isEdit) return;
    const svc = services.find((s) => s.id === selectedServiceId);
    if (svc) setValue("duration_minutes", svc.duration_minutes);
  }, [selectedServiceId, services, setValue, isEdit]);

  // Reset form when dialog opens with new defaults
  React.useEffect(() => {
    if (!open) return;
    const d = defaultDatetime
      ? defaultDatetime.substring(0, 10)
      : appointment
      ? appointment.scheduled_at.substring(0, 10)
      : "";
    const t = defaultDatetime
      ? defaultDatetime.substring(11, 16)
      : appointment
      ? appointment.scheduled_at.substring(11, 16)
      : "10:00";
    reset({
      customer_name: appointment?.customer_name ?? "",
      customer_phone: appointment?.customer_phone ?? "",
      service_id: appointment?.service_id ?? "",
      assigned_staff_id: appointment?.assigned_staff_id ?? defaultStaffId ?? "",
      date: d,
      time: t,
      duration_minutes: appointment?.duration_minutes ?? 30,
      booking_notes: appointment?.booking_notes ?? "",
    });
  }, [open, defaultDatetime, defaultStaffId, appointment, reset]);

  const onSubmit = async (values: FormValues) => {
    const scheduled_at = `${values.date}T${values.time}:00+05:30`;
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
          service_id: values.service_id || undefined,
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

        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogBody className="flex flex-col gap-4">
            {!isEdit && (
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Customer name *"
                  placeholder="Priya Sharma"
                  error={errors.customer_name?.message}
                  {...register("customer_name")}
                />
                <Input
                  label="Phone *"
                  type="tel"
                  placeholder="9876543210"
                  error={errors.customer_phone?.message}
                  {...register("customer_phone")}
                />
              </div>
            )}

            {/* Service — optional */}
            <div className="flex flex-col gap-1">
              <span className="text-heading-sm text-text-secondary">Service</span>
              <Combobox
                options={[{ value: "", label: "— No service yet —" }, ...serviceOptions]}
                value={selectedServiceId ?? ""}
                onChange={(v) => setValue("service_id", v ?? "", { shouldValidate: true })}
                placeholder="Search services…"
              />
            </div>

            {/* Staff — same pattern */}
            <div className="flex flex-col gap-1">
              <span className="text-heading-sm text-text-secondary">Staff</span>
              <Combobox
                options={staffOptions}
                value={selectedStaffId ?? ""}
                onChange={(v) => setValue("assigned_staff_id", v ?? "")}
                placeholder="Any staff"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <Input
                label="Date *"
                type="date"
                error={errors.date?.message}
                {...register("date")}
              />
              <div className="flex flex-col gap-1">
                <span className="text-heading-sm text-text-secondary">Time *</span>
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  {...register("time")}
                >
                  {TIME_SLOTS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                {errors.time && (
                  <p className="text-body-sm text-danger-fg">{errors.time.message}</p>
                )}
              </div>
              <Input
                label="Duration (min)"
                type="number"
                min={15}
                max={480}
                step={15}
                error={errors.duration_minutes?.message}
                {...register("duration_minutes", { valueAsNumber: true })}
              />
            </div>

            <Input
              label="Notes"
              placeholder="Any special requests…"
              {...register("booking_notes")}
            />
          </DialogBody>

          <DialogFooter>
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              {isEdit ? "Save changes" : "Book appointment"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
