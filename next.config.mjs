/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The Python contact service runs on :8000 by default.
  env: {
    CONTACT_SVC_URL: process.env.CONTACT_SVC_URL || "http://localhost:8000",
  },
};

export default nextConfig;
