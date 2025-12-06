import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for S3 deployment
  output: 'export',

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Trailing slashes for clean URLs on S3
  trailingSlash: true,

  // Base path if deployed to subdirectory (empty for root)
  basePath: '/website',
};

export default nextConfig;
