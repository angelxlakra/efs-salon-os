import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Output standalone for Docker deployment
  output: 'standalone',

  // Configure image domains if needed
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
