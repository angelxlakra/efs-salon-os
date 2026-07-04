import type { Metadata } from 'next';
import { Space_Grotesk } from 'next/font/google';
import { Toaster } from '@/components/ui/sonner';

import './globals.css';

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-space-grotesk',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Aasan',
  description: 'Your salon, running itself.',
  icons: {
    icon: '/favicon.svg',
    apple: '/apple-touch-icon-180.png',
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
      <body className={`${spaceGrotesk.variable} antialiased font-sans`}>
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
