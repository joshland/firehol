import type { Plugin } from "@opencode-ai/plugin"
const BANNED_PATTERNS = [
  ".env",
  ".pem",
  ".key",
  ".secret",
  "id_rsa",
  "id_ed25519",
  ".git/config",
  ".auth",
  ".login"
];

export const EnvProtection: Plugin = async () => {
  return {
    tool: {
      execute: {
        before: async (input, output) => {
          if (input.tool === "read") {
            const filePath = output.args.filePath;
            const lowerCasePath = filePath.toLowerCase();
            const foundBan = BANNED_PATTERNS.find(pattern => 
              lowerCasePath.includes(pattern)
            );

            if (foundBan) {
              throw new Error(`🚫 Security Alert: Reading files containing '${foundBan}' is forbidden.`)
            }
          }
        }
      }
    }
  }
}
