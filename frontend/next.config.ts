import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Self-contained server bundle, only for the Docker image (frontend/Dockerfile sets STANDALONE=1),
  // so `npm start` keeps working locally.
  output: process.env.STANDALONE === "1" ? "standalone" : undefined,
  images: {
    // Player headshots load straight from the NBA's CDN, which has them in two sizes (see the loader).
    loader: "custom",
    loaderFile: "./src/lib/image-loader.ts",
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
