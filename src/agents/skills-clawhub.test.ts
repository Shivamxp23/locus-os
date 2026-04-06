import { describe, expect, it } from "vitest";

const LOCUS_MSG = "LOCUS MODIFICATION 1: External skill installation disabled.";

const { installSkillFromClawHub, searchSkillsFromClawHub, updateSkillsFromClawHub } =
  await import("./skills-clawhub.js");

describe("skills-clawhub (Locus MOD 1 — external registry disabled)", () => {
  it("searchSkillsFromClawHub throws", async () => {
    await expect(searchSkillsFromClawHub({ limit: 20 })).rejects.toThrow(LOCUS_MSG);
  });

  it("installSkillFromClawHub throws", async () => {
    await expect(
      installSkillFromClawHub({
        workspaceDir: "/tmp/ws",
        slug: "demo",
      }),
    ).rejects.toThrow(LOCUS_MSG);
  });

  it("updateSkillsFromClawHub throws", async () => {
    await expect(
      updateSkillsFromClawHub({
        workspaceDir: "/tmp/ws",
        slug: "demo",
      }),
    ).rejects.toThrow(LOCUS_MSG);
  });
});
