import type { NextConfig } from "next";

const nextConfig = {
  async rewrites() {
    const shouldProxyApi =
      process.env.NODE_ENV === "development" || Boolean(process.env.BACKEND_URL);

    if (!shouldProxyApi) {
      return [];
    }

    const backendUrl = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(
      /\/$/,
      "",
    );

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
} satisfies NextConfig;

export default nextConfig;
