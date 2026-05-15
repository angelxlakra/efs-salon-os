'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuthStore } from '@/stores/auth-store';
import { useSettingsStore } from '@/stores/settings-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const { settings, fetchSettings } = useSettingsStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!settings) {
      fetchSettings();
    }
  }, [settings, fetchSettings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      await login({ username, password });

      const currentUser = useAuthStore.getState().user;
      if (currentUser?.role === 'staff') {
        router.push('/dashboard/staff');
      } else {
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen w-full flex font-sans">
      {/* Left Column — Brand panel */}
      <div
        className="hidden lg:flex w-1/2 relative flex-col justify-between p-16 text-white overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #1c104c 0%, #0e0828 100%)' }}
      >
        {/* Subtle dot-grid texture */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />
        {/* Gold accent rule at top edge */}
        <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: 'var(--gold-default)' }} />

        {/* Logo + salon name */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="h-9 w-9 bg-white rounded-md flex items-center justify-center overflow-hidden flex-shrink-0">
              <Image
                src="/logo-black.svg"
                alt="Logo"
                width={36}
                height={36}
                className="object-contain"
              />
            </div>
            <span className="text-base font-semibold tracking-wide opacity-90">
              {settings?.salon_name || 'Elegance'}
            </span>
          </div>

          <h1
            className="text-5xl font-light leading-snug tracking-tight mb-5"
            style={{ color: 'var(--accent-fg)', fontFamily: 'var(--font-display)' }}
          >
            The quiet system<br />behind elegant service.
          </h1>
          <p className="text-sm font-light leading-relaxed" style={{ color: 'rgba(245, 240, 232, 0.55)' }}>
            Everything your salon needs. Nothing it doesn&apos;t.
          </p>
        </div>

        {/* Footer — brand values */}
        <div className="relative z-10 flex items-center gap-3 text-xs font-medium uppercase tracking-widest" style={{ color: 'var(--gold-default)' }}>
          <span>Speed</span>
          <span className="opacity-40">·</span>
          <span>Care</span>
          <span className="opacity-40">·</span>
          <span>Family</span>
        </div>
      </div>

      {/* Right Column — Login form */}
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-20 xl:px-28 bg-white text-text-primary">
        <div className="w-full max-w-sm mx-auto">
          {/* Mobile-only logo */}
          <div className="lg:hidden mb-10 flex items-center gap-2">
            <div className="h-8 w-8 rounded-md flex items-center justify-center overflow-hidden flex-shrink-0" style={{ background: 'var(--accent-default)' }}>
              <Image src="/logo-black.svg" alt="Logo" width={32} height={32} className="object-contain invert" />
            </div>
            <span className="text-base font-semibold">{settings?.salon_name || 'Elegance'}</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-semibold tracking-tight text-text-primary mb-1">Welcome back</h2>
            <p className="text-sm text-text-muted">Sign in to continue to your dashboard.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-sm font-medium">Username</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                  className="h-11 px-4"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-sm font-medium">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-11 px-4"
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-11 font-semibold"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Signing in…</span>
                </div>
              ) : 'Sign in'}
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-text-muted">
            Need access?{' '}
            <a href="#" className="font-semibold text-accent hover:underline">
              Contact your owner
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
