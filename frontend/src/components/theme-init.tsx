'use client';

import { useEffect } from 'react';
import { initAccent } from '@/lib/theme';

export function ThemeInit() {
  useEffect(() => {
    initAccent();
  }, []);
  return null;
}
