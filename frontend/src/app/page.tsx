'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuthStore } from '@/stores/auth-store';
import { useSettingsStore } from '@/stores/settings-store';

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const { settings, fetchSettings } = useSettingsStore();

  useEffect(() => {
    if (!settings) {
      fetchSettings();
    }
  }, [settings, fetchSettings]);

  useEffect(() => {
    // Wait for hydration to complete before redirecting
    if (_hasHydrated) {
      if (isAuthenticated) {
        router.push('/dashboard');
      } else {
        router.push('/login');
      }
    }
  }, [isAuthenticated, _hasHydrated, router]);

  // Show loading while determining where to redirect
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 to-secondary/10">
      <div className="card-salon max-w-md w-full text-center space-y-6">
        <div className="flex justify-center mb-4">
          <Image
            src="/logo-black.svg"
            alt="Logo"
            width={64}
            height={64}
            className="object-contain"
          />
        </div>
        <h1 className="text-4xl font-bold text-gray-900">
          {settings?.salon_name || 'Salon Management'}
        </h1>
        <p className="text-lg text-gray-600">
          {settings?.salon_tagline || 'Professional Salon Management System'}
        </p>
        <div className="pt-4">
          <div className="animate-pulse">
            <div className="h-12 w-32 bg-gray-200 rounded-lg mx-auto"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
