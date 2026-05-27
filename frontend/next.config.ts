/** @type {import('next').NextConfig} */
const nextConfig = {
  rewrites: async () => {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'development'
          ? 'http://127.0.0*' // local FastAPI proxy
          : '/api/:path*',                     // production serverless
      },
    ]
  },
}
module.exports = nextConfig
