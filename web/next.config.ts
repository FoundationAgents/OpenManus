/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/openmanus/:path*',
        destination: 'http://localhost:5172/:path*',
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/api/openmanus/tasks/:task_id/events',
        headers: [
          { key: 'Connection', value: 'keep-alive' },
          { key: 'Cache-Control', value: 'no-cache' },
          { key: 'Content-Type', value: 'text/event-stream' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
