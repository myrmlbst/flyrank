import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to this directory -- otherwise Turbopack walks up
  // looking for a lockfile and can pick up an unrelated one in $HOME.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
