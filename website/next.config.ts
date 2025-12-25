import type { NextConfig } from "next";

// Environment-based configuration
// Vercel sets VERCEL=1 automatically, use standard Next.js build for Vercel
// Use static export for S3 deployments
const isVercel = process.env.VERCEL === '1';

const nextConfig: NextConfig = {
  // TODO Phase 8: Re-enable static export after adding generateStaticParams to all dynamic routes
  // Currently disabled to allow dynamic routes: /bills/[congress]/[type]/[number], /committees/[chamber]/[code], /politician/[id]
  // output: isVercel ? undefined : 'export',

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Use trailing slashes to create directory structure
  trailingSlash: true,

  // Base path: Only use '/website' for S3 deployments, not for Vercel
  // basePath: isVercel ? undefined : '/website',
};

export default nextConfig;
