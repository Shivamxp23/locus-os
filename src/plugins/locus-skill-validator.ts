/**
 * Ensures the repo-root Locus skill exists before the gateway starts.
 * (Separate from LOCUS MODIFICATION 1 — external ClawHub registry is disabled in skills-clawhub.ts.)
 */

import fs from "node:fs";
import path from "node:path";

const LOCUS_SKILL_DIR = path.resolve(
  process.cwd(),
  "skills/locus",
);

export function validateLocusSkillPresent(): void {
  const skillMdPath = path.join(LOCUS_SKILL_DIR, "SKILL.md");

  if (!fs.existsSync(LOCUS_SKILL_DIR)) {
    console.error(`[LOCUS] CRITICAL: Locus skill directory missing at ${LOCUS_SKILL_DIR}`);
    throw new Error(
      `Locus skill directory not found. Expected skills/locus/ at repo root (${LOCUS_SKILL_DIR}).`,
    );
  }

  if (!fs.existsSync(skillMdPath)) {
    console.error(`[LOCUS] CRITICAL: SKILL.md missing at ${skillMdPath}`);
    throw new Error(
      `SKILL.md not found in Locus skill directory. Expected skills/locus/SKILL.md.`,
    );
  }

  console.log("[LOCUS] ✓ Locus skill present at", LOCUS_SKILL_DIR);
}
