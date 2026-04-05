/**
 * LOCUS BOOTSTRAP — Runs all Locus modifications at startup
 *
 * Import this module early in OpenClaw's initialization to activate:
 *   - MODIFICATION 1: Validate Locus skill is present
 *   - MODIFICATION 2: Validate required environment variables
 *   - MODIFICATION 3: Audit interceptor (wired via hooks.ts import)
 */

import { validateLocusSkillPresent } from "../plugins/locus-skill-validator.js";
import { validateLocusConfig } from "./locus-env-validator.js";

export function bootstrapLocus(): void {
  console.log("[LOCUS] ═══════════════════════════════════════════");
  console.log("[LOCUS] Locus Personal Cognitive Operating System");
  console.log("[LOCUS] Running startup validations...");
  console.log("[LOCUS] ═══════════════════════════════════════════");

  // MODIFICATION 2 — validate env vars first (needed by everything else)
  validateLocusConfig();

  // MODIFICATION 1 — validate Locus skill is present
  validateLocusSkillPresent();

  // MODIFICATION 3 — audit interceptor is wired via hooks.ts import
  console.log("[LOCUS] ✓ Audit interceptor active (wired in hooks.ts)");

  console.log("[LOCUS] ═══════════════════════════════════════════");
  console.log("[LOCUS] All validations passed. System ready.");
  console.log("[LOCUS] ═══════════════════════════════════════════");
}
