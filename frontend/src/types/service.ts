// frontend/src/types/service.ts

export interface ServiceCategory {
  id: string;
  name: string;
}

export interface Service {
  id: string;
  name: string;
  base_price: number; // paise
  duration_minutes?: number;
  tax_rate?: number;
  is_active?: boolean;
  category?: ServiceCategory;
}
