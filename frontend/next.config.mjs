/** @type {import('next').NextConfig} */
const nextConfig = {
  // Deployed as a static export served by the FastAPI backend (single Cloud
  // Run service) — everything in this app is already client-side fetches to
  // NEXT_PUBLIC_API_URL, no server components or API routes, so nothing here
  // needs a Node server. Local dev still uses `next dev` as normal.
  output: "export",
};

export default nextConfig;
