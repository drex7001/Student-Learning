import type { NextConfig } from "next";

// The API is reached same-origin through a rewrite rather than a public base URL.
// Two reasons: the session cookie stays first-party (no CORS, no third-party cookie
// rules), and the target is read at request time instead of being inlined into the
// bundle at build time, so one image works in every environment.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` },
      { source: "/internal/:path*", destination: `${API_ORIGIN}/internal/:path*` },
    ];
  },
};

export default nextConfig;
