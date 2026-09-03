import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Do not drop generated AGENTS.md/CLAUDE.md into the stack; the repo root owns agent rules.
  agentRules: false,
  /* config options here */
};

export default nextConfig;
