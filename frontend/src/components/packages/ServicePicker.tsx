// frontend/src/components/packages/ServicePicker.tsx
// Combobox wrapper for picking a service from the catalog.
// Used in package builder line items and redemption flows.

import { useMemo } from "react";
import { Combobox } from "@/components/ui/combobox";
import { useServicesList } from "@/hooks/useServicesList";

interface ServicePickerProps {
  value: string | null;
  onChange: (selection: { service_id: string; service_name: string } | null) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ServicePicker({
  value,
  onChange,
  disabled,
  placeholder = "Select service…",
}: ServicePickerProps) {
  const { services, loading, error } = useServicesList();

  const options = useMemo(
    () =>
      services.map((s) => ({
        value: s.id,
        label: s.name,
        keywords: [s.category_name],
      })),
    [services],
  );

  // Resolve display states
  const isDisabled = disabled || loading || !!error;
  const resolvedPlaceholder = error
    ? "Failed to load services"
    : loading
      ? "Loading…"
      : placeholder;

  function handleChange(selectedValue: string | null) {
    if (selectedValue === null) {
      onChange(null);
      return;
    }
    const service = services.find((s) => s.id === selectedValue);
    if (service) {
      onChange({ service_id: service.id, service_name: service.name });
    }
  }

  return (
    <Combobox
      options={options}
      value={value}
      onChange={handleChange}
      placeholder={resolvedPlaceholder}
      searchPlaceholder="Search services…"
      emptyMessage="No services found."
      disabled={isDisabled}
    />
  );
}
