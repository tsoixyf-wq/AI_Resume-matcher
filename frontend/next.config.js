/** @type {import('next').NextConfig} */

// Vercel uses its own optimized build pipeline — standalone mode is only for Docker self-hosting.
const isDocker = process.env.DOCKER_BUILD === '1';

const nextConfig = {
  // Docker: standalone output for node server.js
  // Vercel: default output (Vercel handles the build pipeline natively)
  ...(isDocker ? { output: 'standalone' } : {}),
  transpilePackages: ['echarts', 'echarts-for-react', '@ant-design/charts', 'zrender'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `http://${process.env.NEXT_PUBLIC_API_HOST || 'localhost'}:8000/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
