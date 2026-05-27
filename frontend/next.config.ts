/** @type {import('next').NextConfig} */
const nextConfig = {
  rewrites: async () => {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'development'
          ? 'http://127.0.0*' // Local FastAPI
          : '/api/:path*',                     // Production Vercel Functions
      },
    ]
  },
}

module.exports = nextConfig
