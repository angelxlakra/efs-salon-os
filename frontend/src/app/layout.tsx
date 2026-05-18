import type { Metadata } from 'next';
import { Toaster } from '@/components/ui/sonner';

import './globals.css';

export const metadata: Metadata = {
  title: 'Salon Management System',
  description: 'Local-first salon POS, scheduling, inventory, and accounting system',
  icons: {
    icon: '/favicon.svg',
    apple: '/logo-navy.svg',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Restore persisted theme before first paint — must be blocking (no defer/async). */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('salon.theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);else document.documentElement.setAttribute('data-theme','light')}catch(e){document.documentElement.setAttribute('data-theme','light')}`,
          }}
        />
      </head>
      <body className="antialiased font-sans">
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
