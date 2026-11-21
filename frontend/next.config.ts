import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // The dev server otherwise prints every server action with its arguments, including passwords.
  logging: { serverFunctions: false },
  experimental: {
    // Panel photos (up to 8 MB) travel base64-encoded to a server action, which adds about a third.
    serverActions: { bodySizeLimit: '12mb' },
  },
};

export default nextConfig;
