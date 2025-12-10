import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for static hosting (S3 or Vercel)
  output: 'export',

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Use trailing slashes to create directory structure
  trailingSlash: true,

  // Base path: Remove '/website' for Vercel (use root), keep for S3
  // Uncomment the line below when deploying to S3
  // basePath: '/website',

  // Disable link prefetching for static hosting
  experimental: {
    // @ts-ignore - This is valid but types might not include it
    disableOptimizedLoading: true,
  },
};

export default nextConfig;
