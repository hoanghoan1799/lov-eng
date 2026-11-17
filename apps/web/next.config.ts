import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@park/shared", "@park/content"],
  reactStrictMode: false,
};

export default nextConfig;
