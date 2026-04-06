#!/usr/bin/env node
/**
 * Creates Phase 0 directory scaffolding from LOCUS_ARCHITECTURE_v4 §25 (mkdir tree).
 * Idempotent. Does not delete existing files.
 */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

const dirs = [
  "backend/app/core",
  "backend/app/api/v1/endpoints",
  "backend/app/engines/e1",
  "backend/app/engines/e2",
  "backend/app/engines/e3",
  "backend/app/models",
  "backend/app/repositories",
  "backend/app/services/llm/prompts",
  "backend/app/services/rag",
  "backend/app/services/personality",
  "backend/app/services/cache",
  "backend/app/services/security",
  "backend/app/services/integrations",
  "backend/app/services/vault",
  "backend/fine_tuning/datasets",
  "backend/fine_tuning/models",
  "backend/fine_tuning/scripts",
  "backend/scripts",
  "backend/tests/unit",
  "backend/tests/integration",
  "backend/alembic/versions",
  "frontend/src/components/layout",
  "frontend/src/components/dashboard",
  "frontend/src/components/task",
  "frontend/src/components/ai",
  "frontend/src/components/analytics",
  "frontend/src/components/onboarding",
  "frontend/src/components/ui",
  "frontend/src/hooks",
  "frontend/src/lib",
  "frontend/src/pages",
  "frontend/src/services",
  "frontend/src/stores",
  "frontend/src/types",
  "frontend/public",
  "infra/neo4j",
  "infra/scripts",
  "skills/locus/handlers",
];

for (const d of dirs) {
  await fs.mkdir(path.join(root, d), { recursive: true });
}

console.log(`[locus] Phase 0 scaffold: ensured ${dirs.length} directories under ${root}`);
