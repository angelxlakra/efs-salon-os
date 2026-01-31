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
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen w-full flex font-sans bg-white">
      {/* Left Column - Branding (Visual) - 50% width */}
      <div className="hidden lg:flex w-1/2 bg-black relative flex-col justify-between p-16 text-white">
        {/* Background Pattern */}
        <div 
          className="absolute inset-0 z-0 opacity-40"
          style={{ 
            backgroundImage: 'url("https://images.unsplash.com/photo-1633681926022-84c23e8cb2d6?q=80&w=2574&auto=format&fit=crop")',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            filter: 'grayscale(100%) contrast(120%)'
          }}
        />
        <div className="absolute inset-0 z-0 bg-gradient-to-br from-black/90 via-black/50 to-transparent" />

        {/* Content */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className="h-10 w-10 bg-white rounded-lg flex items-center justify-center overflow-hidden">
              <Image
                src="/logo-black.svg"
                alt="Logo"
                width={40}
                height={40}
                className="object-contain"
              />
            </div>
            <span className="text-2xl font-bold tracking-tight">
              {settings?.salon_name || 'Salon'}
            </span>
          </div>

          <h1 className="text-6xl font-extrabold tracking-tight leading-tight max-w-3xl mb-8" style={{ fontFamily: 'var(--font-heading)' }}>
            {settings?.salon_tagline || 'The Operating System for Modern Salons.'}
          </h1>
          <p className="text-2xl text-gray-300 font-light leading-relaxed">
            Manage appointments, inventory, and point-of-sale in one unified, beautiful interface. Designed for speed and elegance.
          </p>
        </div>

        <div className="relative z-10">
           <div className="flex gap-8 text-sm font-medium text-gray-400 uppercase tracking-widest">
             <span>Speed</span>
             <span>Security</span>
             <span>Simplicity</span>
           </div>
        </div>
      </div>

      {/* Right Column - Login Form - 50% width */}
      <div className="flex-1 flex flex-col justify-center px-12 lg:px-24 xl:px-32 bg-white text-gray-900">
        <div className="w-full">
           <div className="mb-10">
             <h2 className="text-4xl font-bold tracking-tight text-gray-900 mb-3" style={{ fontFamily: 'var(--font-heading)' }}>Welcome back</h2>
             <p className="text-xl text-gray-500">Please enter your details to sign in.</p>
           </div>

           <form onSubmit={handleSubmit} className="space-y-8">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-base font-semibold text-gray-900">Email or Username</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                  className="h-14 px-4 text-lg bg-gray-50 border-gray-200 focus:border-black focus:ring-black rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-base font-semibold text-gray-900">Password</Label>
                  <a href="#" className="text-sm font-medium text-gray-600 hover:text-black">Forgot password?</a>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-14 px-4 text-lg bg-gray-50 border-gray-200 focus:border-black focus:ring-black rounded-xl"
                />
              </div>
            </div>

            <Button 
              type="submit" 
              className="w-full h-14 text-lg font-bold bg-black text-white hover:bg-gray-800 rounded-xl transition-all shadow-xl hover:shadow-2xl hover:-translate-y-1" 
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Signing in...</span>
                </div>
              ) : 'Sign in to Account'}
            </Button>
          </form>

          <p className="mt-10 text-center text-gray-500">
            Don't have an account? <a href="#" className="font-semibold text-black hover:underline">Contact Owner</a>
          </p>
        </div>
      </div>
    </div>
  );
}
