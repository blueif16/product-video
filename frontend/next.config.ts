import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 生产环境优化
  reactStrictMode: true,

  // 允许任意超时时长（自托管环境）
  experimental: {
    serverActions: {
      bodySizeLimit: '50mb',
    },
  },

  // Turbopack 配置（Next.js 16 默认启用）
  turbopack: {},

  // Webpack 配置（兼容性回退）
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals.push({
        bufferutil: 'bufferutil',
        'utf-8-validate': 'utf-8-validate',
      });
    }
    return config;
  },
};

export default nextConfig;
