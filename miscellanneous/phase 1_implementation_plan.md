# Phase 1: Engine 1 — Logging Foundation
## Comprehensive Status Report & Execution Plan

> Based on: LOCUS_SPEC_v3.md §23 Phase 1 checklist, §7 Engine 1, §13 DB Schema, §18 API Design, §21 Auth, cross-referenced against the live output pasted by the user.

---

## 1. What Has Been Confirmed WORKING (from the output)

| Item | Evidence |
|---|---|
| VM + Docker Compose running | Logs show `locus-celery-e1`, `locus-postgres` active |
| Auth: `POST /auth/login` | Successfully returned a JWT access token |
| AI Gateway: `POST /api/ai/chat` | Returned a full LLM response from `groq` (llama-3.1-8b-instant) |
| Engine 1 Celery worker active | Logs show `[Engine1] Processing event: ai_chat from ai_gateway` |
| Obsidian vault write | Logs: `Written to Obsidian: /vault/583e0bcd.../OS-managed zone/Logs/2026-03-30.md` |
| PostgreSQL write | Logs: `Written to PostgreSQL: 6c0ec58d-...` |
| Ollama fallback to Groq | Logs: `Ollama error:` then falls to Groq — cascade failover working |
| Intent extraction | Logs: `Extracted: {'intent': 'create', 'summary': '...'}` |

---

## 2. What Is BROKEN / Erroring

### Error A — `SELECT user_id FROM users` fails
```
ERROR: column "user_id" does not exist
LINE 1: SELECT user_id FROM users WHERE email='soni820034@gmail.com'
```
**Root cause:** The spec (§13.1) defines the primary key column as `id`, NOT `user_id`. The `users` table has `id UUID PRIMARY KEY`. The query used the wrong column name.  
**Impact:** Any direct psql query against users table using `user_id` will fail. The actual column is `id`. This is a query-writing error in the test/verification commands, NOT a schema error — the login JWT works fine, so the app code correctly uses `id`.

### Error B — Bearer token not passed (multi-line curl issue)
```
{"detail":"Not authenticated"}-H: command not found
```
**Root cause:** The shell commands for `GET /api/tasks` and `GET /api/goals` were multi-line with backslashes but the environment (shell state) didn't preserve `$TOKEN`. The `-H: command not found` shows the shell interpreted `-H` as a standalone command, meaning the heredoc/variable wasn't set in that shell session.  
**Impact:** `GET /api/tasks` and `GET /api/goals` were never actually tested — they may or may not work. This is a **test execution error**, not a backend error.

### Error C — `find /var/lib/docker/volumes/locus_obsidian-vault/_data` — Permission denied
```
find: '/var/lib/docker/volumes/locus_obsidian-vault/_data': Permission denied
```
**Root cause:** Docker volume data directories are owned by root. Accessing them from the ubuntu user requires `sudo`. This is expected Docker behavior.  
**Impact:** This is an **observation method error**, not a system error. The Obsidian write DID succeed (confirmed by the Celery log showing `Written to Obsidian: /vault/.../Logs/2026-03-30.md`). To inspect vault files, use `docker exec locus-syncthing cat /vault/...` instead.

---

## 3. What EXISTS in the Codebase (Local Repo)

| File | Status |
|---|---|
| `backend/app/main.py` | **STUB** — 3 lines, just a docstring, no actual code |
| `backend/requirements.txt` | **STUB** — empty (just a comment placeholder) |
| `backend/Dockerfile` | **STUB** — 1-line comment, no actual Dockerfile |
| `backend/app/api/` | **EMPTY** — only `.gitkeep` |
| `backend/app/engines/` | **EMPTY** — only `.gitkeep` |
| `backend/app/models/` | **EMPTY** — only `.gitkeep` |
| `backend/app/services/` | **EMPTY** — only `.gitkeep` |
| `infra/docker-compose.yml` | **STUB** — placeholder only |
| `infra/schema.sql` | **STUB** — placeholder only |
| `frontend/` | Not yet inspected — presumed scaffold only |

**Critical finding:** The local repo is entirely scaffold/stub placeholders. The WORKING code is on the Oracle VM at `/opt/locus/`. The local repo has never been synced back from the VM. This is the #1 structural issue.

---

## 4. What Phase 1 Requires (per LOCUS_SPEC_v3.md §23)

The spec Phase 1 checklist exactly:

```
- [ ] FastAPI skeleton with auth (JWT + register/login)
- [ ] PostgreSQL schema creation (all tables from §13)
- [ ] Basic Celery worker setup (engine1 queue)
- [ ] Task CRUD API endpoints
- [ ] Goal CRUD API endpoints
- [ ] Engine 1 normalization pipeline (§7.3)
- [ ] Obsidian vault write functions (with locking)
- [ ] Groq Whisper voice transcription
- [ ] Telegram bot (voice + text ingestion)
- [ ] Notion polling (60s Celery Beat)
- [ ] Google Calendar OAuth + event read
- [ ] AI Gateway (proxy endpoint with Ollama → Gemini → Groq fallback)
- [ ] Behavioral event logging to PostgreSQL + Qdrant
```

**Phase 1 is complete when:** You can add a task via Telegram, see it in PostgreSQL, see it in the Obsidian vault, and have it appear in the PWA (tasks API endpoint).

---

## 5. Status of Each Phase 1 Checklist Item

| Phase 1 Item | Status | Notes |
|---|---|---|
| FastAPI skeleton with auth (JWT + register/login) | ✅ **DONE on VM** | Login works, JWT issued correctly |
| PostgreSQL schema creation (all tables from §13) | ⚠️ **PARTIAL** | Some tables exist (users, behavioral_events confirmed). Need to verify ALL tables from §13 are present — goals, tasks, projects, habits, personality_insights, ai_conversations, content_items, recommendations, sync_events, personality_snapshots, daily_metrics |
| Basic Celery worker setup (engine1 queue) | ✅ **DONE on VM** | Engine1 worker is running, consuming events |
| Task CRUD API endpoints | ❌ **UNTESTED** | `GET /api/tasks` was called but auth broke — result unknown |
| Goal CRUD API endpoints | ❌ **UNTESTED** | `GET /api/goals` was called but auth broke — result unknown |
| Engine 1 normalization pipeline (§7.3) | ✅ **PARTIAL/DONE on VM** | Intent extraction working, Obsidian write confirmed, PostgreSQL write confirmed |
| Obsidian vault write functions (with locking) | ✅ **DONE on VM** | Vault write confirmed in logs |
| Groq Whisper voice transcription | ❌ **NOT TESTED** | No voice note was sent through Telegram in the output |
| Telegram bot (voice + text ingestion) | ❌ **NOT TESTED** | No Telegram interaction in the output |
| Notion polling (60s Celery Beat) | ❌ **NOT VERIFIED** | Celery Beat running but Notion integration not confirmed active |
| Google Calendar OAuth + event read | ❌ **NOT DONE** | No evidence of Google Calendar setup |
| AI Gateway (Ollama → Gemini → Groq fallback) | ✅ **DONE on VM** | Ollama failed → fell to Groq. Gemini fallback not tested but chain is in place |
| Behavioral event logging to PostgreSQL + Qdrant | ⚠️ **PARTIAL** | PostgreSQL write confirmed. Qdrant write NOT confirmed in logs |

---

## 6. Execution Plan — Ordered by Priority

> **Ground rule:** All fixes/builds happen AS CODE in the local repo, then pushed to GitHub, then pulled and deployed on the VM. The local repo must always reflect what's running on the VM.

---

### STEP 1 — Pull current VM code into local repo (BLOCKER)
**Why first:** Nothing can be properly tracked, debugged, or committed until the local repo reflects what's actually running on the VM.

```bash
# SSH to VM
ssh -i "infra/ssh-key-2026-03-27.key" ubuntu@140.238.245.25

# Archive current /opt/locus code
tar -czf /tmp/locus-vm-code.tar.gz /opt/locus/backend/

# On local: scp the archive back
scp -i "infra/ssh-key-2026-03-27.key" ubuntu@140.238.245.25:/tmp/locus-vm-code.tar.gz .
# Extract and replace local backend/ with VM backend/ code
```

---

### STEP 2 — Verify + complete PostgreSQL schema (§13)
**Why:** The login works but the `user_id` column error reveals schema discrepancies. We need to confirm ALL 12 tables from §13 exist correctly.

```bash
# Run on VM:
docker exec locus-postgres psql -U locus -d locus -c "\dt"
# Compare against §13 table list:
# users, goals, tasks, projects, behavioral_events, daily_metrics,
# habits, habit_completions, personality_insights, ai_conversations,
# content_items, recommendations, sync_events, personality_snapshots
```

Any missing table → apply the missing DDL from §13.1 via `docker exec locus-postgres psql`.

Also verify the `personality_snapshots` UNIQUE constraint issue (known from Phase 0 fixes — `UNIQUE(user_id, generated_at::DATE)` is not allowed in an index). The spec has this constraint but it fails — need to remove it or use a partial index.

---

### STEP 3 — Test Task CRUD and Goal CRUD endpoints properly
**Why:** These were untested due to the broken curl session. The spec requires:
- `GET /api/tasks`, `POST /api/tasks`, `GET /api/tasks/{id}`, `PATCH /api/tasks/{id}`, `POST /api/tasks/{id}/complete`, `POST /api/tasks/{id}/defer`
- `GET /api/goals`, `POST /api/goals`, `GET /api/goals/{id}`, `PATCH /api/goals/{id}`

Test with a properly structured single-line curl:
```bash
TOKEN=$(curl -s -X POST https://api.locusapp.online/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"soni820034@gmail.com","password":"Shiv@m?132003"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" https://api.locusapp.online/api/tasks
curl -s -H "Authorization: Bearer $TOKEN" https://api.locusapp.online/api/goals
```

If these return 404 → routes not yet implemented → implement them.  
If they return 200 but wrong data → debug the handlers.

---

### STEP 4 — Verify Qdrant behavioral event writes
**Why:** PostgreSQL write to `behavioral_events` is confirmed, but Qdrant embedding write is NOT confirmed. The spec requires behavioral events to be logged to BOTH (§7.3, Step 5 + §15).

```bash
# Query Qdrant directly:
curl http://localhost:6333/collections/behavioral_logs/points/scroll \
  -X POST -H "Content-Type: application/json" \
  -d '{"limit": 5, "with_payload": true}'
# (must run from inside VM or port 6333 tunneled)
```

If empty → Engine 1 is not writing to Qdrant → add the embedding + Qdrant write step.

---

### STEP 5 — Test & fix Telegram bot (voice + text ingestion)
**Why:** A core Phase 1 deliverable. The completion criterion is "add a task via Telegram, see it in PostgreSQL, see it in the Obsidian vault."

Test sequence:
1. Send a text message to the Locus Telegram bot → verify it appears in `behavioral_events` and in the Obsidian `/vault/{user_id}/OS-managed zone/Logs/` file
2. Send a voice note → verify Groq Whisper transcription → verify logged in both places
3. Check the deferral and task-creation flows work via Telegram commands

---

### STEP 6 — Verify Groq Whisper voice transcription
**Why:** Spec requirement. API endpoint `POST /api/ai/voice` must exist. Telegram voice handler must call Groq Whisper.

```bash
# Test voice endpoint directly:
curl -X POST https://api.locusapp.online/api/ai/voice \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_voice.ogg"
```

---

### STEP 7 — Verify Notion polling is active
**Why:** Celery Beat must be polling Notion every 60s. Confirm beat schedule includes this task.

```bash
docker exec locus-beat celery -A app.celery inspect scheduled
# Should show notion_poll task registered
```

If not configured → add the Celery Beat task per the Notion integration spec (§20.2).

---

### STEP 8 — Google Calendar OAuth + event read
**Why:** This is the only Phase 1 item with zero evidence of existence. Spec requires OAuth 2.0 setup with Google Cloud Console, redirect URI at `https://api.locusapp.online/auth/google/callback`, and a Celery Beat task polling events every 15 min.

This requires:
1. Google Cloud Console project created, OAuth credentials generated
2. `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` added to `.env` on VM
3. `GET /auth/google` and `POST /auth/google` callback endpoints implemented
4. Google Calendar read task added to Celery Beat

---

### STEP 9 — Sync local repo with VM code, commit everything
**Why:** The local repo must be the source of truth per the project's own architecture. Every piece of working code must be in git.

```bash
# After pulling VM code locally:
git add -A
git commit -m "feat: Phase 1 — Engine 1 implementation (synced from VM)"
git push origin main

# On VM:
cd /opt/locus
git pull origin main
docker compose up -d --build
```

---

### STEP 10 — End-to-end Phase 1 completion test
**Why:** The spec defines a specific completion criterion that must be met before calling Phase 1 done.

**Test:** 
1. Send a Telegram message: "Add task: Review portfolio video"
2. Verify in PostgreSQL: `SELECT * FROM tasks WHERE user_id='583e0bcd-...' ORDER BY created_at DESC LIMIT 1;`
3. Verify in Obsidian vault: `docker exec locus-syncthing cat "/vault/583e0bcd-.../OS-managed zone/Logs/$(date +%Y-%m-%d).md"`
4. Verify via API: `GET /api/tasks` returns the task
5. Verify PWA (Phase 2 prerequisite) will be able to display it via the tasks endpoint

---

## 7. Priority Order Summary

| Order | Step | Blocking? | Spec Section |
|---|---|---|---|
| 1 | Pull VM code into local repo | YES — all else is blind without this | Appendix A |
| 2 | Verify all 12 PostgreSQL tables exist | YES — Tasks/Goals APIs depend on this | §13.1 |
| 3 | Test Task CRUD + Goal CRUD endpoints | YES — core API surface | §18.2, §18.3 |
| 4 | Verify Qdrant behavioral event writes | YES — required dual-write | §7.3, §15 |
| 5 | Test Telegram bot (text + voice) | YES — Phase 1 completion criterion | §20.3, §23 |
| 6 | Verify Groq Whisper voice endpoint | YES — Phase 1 checklist | §7.2, §11.1 |
| 7 | Verify Notion polling is scheduled | Partial — Notion not connected yet | §20.2 |
| 8 | Google Calendar OAuth setup | YES — Phase 1 checklist item | §20.1 |
| 9 | Sync code to local repo + git commit | YES — project integrity | §6.2 |
| 10 | Full end-to-end completion test | YES — Phase 1 gate criterion | §23 |

---

## 8. First Action to Execute

**STEP 1: SSH into the VM and SCP the actual running backend code back to the local repo.**

This is the foundational blocker. Every other step requires knowing what's actually deployed. The local `backend/` directory has only stubs. Without the real code, we cannot debug, fix, or extend anything correctly.

Command to run:
```powershell
# From local machine (Windows PowerShell):
scp -i "c:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\infra\ssh-key-2026-03-27.key" -r ubuntu@140.238.245.25:/opt/locus/backend "c:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\"
```

Then examine the pulled code, identify all gaps vs the spec, and proceed step by step.
