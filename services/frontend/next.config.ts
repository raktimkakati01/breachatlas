import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Every page in BreachAtlas renders live data from the read-only API
  // (fetched with cache: "no-store"), so the static Cache Components model
  // is intentionally off — the app is fully dynamic by design.
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
