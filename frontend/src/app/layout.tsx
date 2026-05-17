import type { Metadata } from 'next';
import { Toaster } from '@/components/ui/sonner';

import './globals.css';

export const metadata: Metadata = {
  title: 'Salon Management System',
  description: 'Local-first salon POS, scheduling, inventory, and accounting system',
  icons: {
    icon: '/favicon.svg',
    apple: '/logo-black.svg',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <body className="antialiased font-sans">
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
