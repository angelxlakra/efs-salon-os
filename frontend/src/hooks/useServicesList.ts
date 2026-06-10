// frontend/src/hooks/useServicesList.ts
import { useState, useEffect } from "react";
import type { Service } from "@/types/service";
import { fetchServicesList } from "@/lib/api/services";

let cachedServices: Service[] | null = null;

export function useServicesList() {
  const [services, setServices] = useState<Service[]>(cachedServices ?? []);
  const [loading, setLoading] = useState(cachedServices === null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cachedServices !== null) return; // cache hit
    fetchServicesList()
      .then((data) => {
        cachedServices = data;
        setServices(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : "Failed to load services";
        setError(message);
        setLoading(false);
      });
  }, []);

  return { services, loading, error };
}
