/**
 * LOCUS MODIFICATION 2 — config locked to environment
 *
 * Validates that all required Locus environment variables are present.
 * Called at OpenClaw startup before any other initialization.
 *
 * Required env vars:
 *   TELEGRAM_TOKEN       — Telegram bot token (mapped from TELEGRAM_BOT_TOKEN)
 *   TELEGRAM_OWNER_ID    — Telegram user ID for the bot owner
 *   LOCUS_API_URL        — FastAPI base URL for all skill handler calls
 *
 * Also sets up aliases so OpenClaw's internal code (which expects
 * TELEGRAM_BOT_TOKEN) continues to work with our renamed env vars.
 */

// LOCUS MODIFICATION 2 — config locked to environment
const REQUIRED_ENV_VARS = [
  "TELEGRAM_TOKEN",
  "LOCUS_API_URL",
  "TELEGRAM_OWNER_ID",
] as const;

// LOCUS MODIFICATION 2 — config locked to environment
export function validateLocusConfig(): void {
  const missing: string[] = [];

  for (const key of REQUIRED_ENV_VARS) {
    const value = process.env[key];
    if (!value || value.trim() === "") {
      missing.push(key);
    }
  }

  if (missing.length > 0) {
    const message =
      `LOCUS MODIFICATION 2: Required environment variables missing: ${missing.join(", ")}. ` +
      `All sensitive configuration must be provided via environment variables, not config files.`;
    console.error(`[LOCUS] CRITICAL: ${message}`);
    throw new Error(message);
  }

  // LOCUS MODIFICATION 2 — config locked to environment
  // Alias TELEGRAM_TOKEN → TELEGRAM_BOT_TOKEN for OpenClaw internal compatibility
  if (process.env.TELEGRAM_TOKEN && !process.env.TELEGRAM_BOT_TOKEN) {
    process.env.TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_TOKEN;
  }

  console.log("[LOCUS] ✓ Environment config validated:");
  console.log(`[LOCUS]   TELEGRAM_TOKEN=***${process.env.TELEGRAM_TOKEN!.slice(-6)}`);
  console.log(`[LOCUS]   TELEGRAM_OWNER_ID=${process.env.TELEGRAM_OWNER_ID}`);
  console.log(`[LOCUS]   LOCUS_API_URL=${process.env.LOCUS_API_URL}`);
}
