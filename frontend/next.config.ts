import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Self-contained server bundle, only for the Docker image (frontend/Dockerfile sets STANDALONE=1),
  // so `npm start` keeps working locally.
  output: process.env.STANDALONE === "1" ? "standalone" : undefined,
  images: {
    // Player headshots come from the NBA's public CDN, resized by the Next.js image optimizer.
    remotePatterns: [new URL("https://cdn.nba.com/headshots/**")],
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
