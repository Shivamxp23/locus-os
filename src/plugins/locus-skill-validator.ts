/**
 * LOCUS MODIFICATION 1 — ensure locus skill always loaded
 *
 * This module validates that the Locus skill directory exists and contains
 * a valid SKILL.md at startup. It logs confirmation for observability.
 * All external skill downloads, marketplace access, and community skill
 * installations remain fully functional — nothing is restricted.
 */

import fs from "node:fs";
import path from "node:path";

// LOCUS MODIFICATION 1 — ensure locus skill always loaded
const LOCUS_SKILL_DIR = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  "../../../skills/locus"
);

// LOCUS MODIFICATION 1 — ensure locus skill always loaded
export function validateLocusSkillPresent(): void {
  const skillMdPath = path.join(LOCUS_SKILL_DIR, "SKILL.md");

  if (!fs.existsSync(LOCUS_SKILL_DIR)) {
    console.error(
      `[LOCUS] CRITICAL: Locus skill directory missing at ${LOCUS_SKILL_DIR}`
    );
    throw new Error(
      "LOCUS MODIFICATION 1: Locus skill directory not found. " +
        "The Locus skill must be present at openclaw/skills/locus/"
    );
  }

  if (!fs.existsSync(skillMdPath)) {
    console.error(
      `[LOCUS] CRITICAL: SKILL.md missing at ${skillMdPath}`
    );
    throw new Error(
      "LOCUS MODIFICATION 1: SKILL.md not found in Locus skill directory. " +
        "Ensure openclaw/skills/locus/SKILL.md exists."
    );
  }

  // LOCUS MODIFICATION 1 — ensure locus skill always loaded
  console.log("[LOCUS] ✓ Locus skill loaded from", LOCUS_SKILL_DIR);
}
