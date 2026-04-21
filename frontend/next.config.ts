import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    remotePatterns: [],
  },
  // In Docker, Nginx intercepts /api/* before Next.js sees it.
  // In local dev (no Nginx), this proxy forwards /api/* to the backend.
  async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL ?? 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
