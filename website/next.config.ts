import type { NextConfig } from "next";

// Environment-based configuration
// Vercel sets VERCEL=1 automatically, use standard Next.js build for Vercel
// Use static export for S3 deployments
const isVercel = process.env.VERCEL === '1';

const nextConfig: NextConfig = {
  // Only use static export for non-Vercel deployments (S3)
  // Vercel works best with standard Next.js builds (enables ISR, API routes, etc.)
  output: isVercel ? undefined : 'export',

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Use trailing slashes to create directory structure
  trailingSlash: true,

  // Base path: Only use '/website' for S3 deployments, not for Vercel
  basePath: isVercel ? undefined : '/website',

  // Disable link prefetching for static hosting
  experimental: {
    // @ts-ignore - This is valid but types might not include it
    disableOptimizedLoading: true,
  },
};

export default nextConfig;
