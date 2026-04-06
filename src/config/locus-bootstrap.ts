/**
 * LOCUS bootstrap — runs before the rest of the gateway starts.
 *
 * - MODIFICATION 1 (external skills): enforced in src/agents/skills-clawhub.ts
 * - MODIFICATION 2: validate required env (src/config/locus-env-validator.ts)
 * - MODIFICATION 3: audit hooks wired in src/plugins/hooks.ts
 */

import { validateLocusSkillPresent } from "../plugins/locus-skill-validator.js";
import { validateLocusConfig } from "./locus-env-validator.js";

export function bootstrapLocus(): void {
  console.log("[LOCUS] ═══════════════════════════════════════════");
  console.log("[LOCUS] Locus Personal Cognitive Operating System");
  console.log("[LOCUS] Running startup validations...");
  console.log("[LOCUS] ═══════════════════════════════════════════");

  // LOCUS MODIFICATION 2 — config locked to environment
  validateLocusConfig();

  validateLocusSkillPresent();

  console.log("[LOCUS] ✓ ClawHub skill install disabled (MODIFICATION 1)");
  // LOCUS MODIFICATION 3 — audit interceptor (wired in hooks.ts)
  console.log("[LOCUS] ✓ Audit interceptor active (wired in hooks.ts)");

  console.log("[LOCUS] ═══════════════════════════════════════════");
  console.log("[LOCUS] All validations passed. System ready.");
  console.log("[LOCUS] ═══════════════════════════════════════════");
}
