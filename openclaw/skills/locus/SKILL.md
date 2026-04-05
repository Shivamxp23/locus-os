---
name: locus
description: "Locus Personal Cognitive OS — morning log (DCS score + operating mode), task management (create/complete/defer), daily planning, voice notes, and vault RAG search. Use when: user sends morning metrics (log E M S ST T), manages tasks (done/defer/add), asks what to do today, sends voice notes, or searches their vault. NOT for: general chat, non-Locus operations."
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠",
        "always": true,
        "requires": { "env": ["LOCUS_API_URL"] },
      },
  }
---

# Locus Personal Cognitive OS

Locus is a Personal Cognitive Operating System that helps users manage their daily capacity, tasks, and behavioral patterns through data-driven insights.

## Core Concepts

### DCS (Daily Capacity Score)
Formula: `DCS = ((E + M + S) / 3) × (1 − ST/20)`

Where:
- **E** = Energy (1-10)
- **M** = Mood (1-10)
- **S** = Sleep quality (1-10)
- **ST** = Stress (1-10)

### Operating Modes
| Mode | DCS Range | Description |
|------|-----------|-------------|
| SURVIVAL | 0.0–2.0 | Protect non-negotiables only |
| RECOVERY | 2.1–4.0 | Gentle movement, no hard pushes |
| NORMAL | 4.1–6.0 | Standard operating, balanced day |
| DEEP_WORK | 6.1–8.0 | Sharp — schedule hardest work |
| PEAK | 8.1–10.0 | Rare — most ambitious tasks |

### Factions
Locus organizes life into 4 factions:
1. **Health** — physical/mental wellbeing
2. **Leverage** — high-impact academic/career work
3. **Craft** — skill building and creative work
4. **Expression** — social, creative, personal growth

## When to Use

✅ **USE this skill when:**

- User sends morning metrics: `log 7 6 8 3 5` (E M S ST T)
- User completes a task: `done [task name]`
- User defers a task: `defer [task name]` or `defer [task] - [reason]`
- User creates a task: `add task [name]` or `create task [name]`
- User asks for daily planning: `what should I do`, `plan my day`, `today`, `schedule`, `recommend`
- User sends a voice note or audio file
- User searches their vault/notes: `search [query]`, `find [topic]`

❌ **DON'T use this skill when:**

- General conversation unrelated to Locus operations
- Non-Locus task management (use the system's native task tools)
- General web search (use search tools)

## API Endpoints

All endpoints are called via `httpx` or `curl` against `LOCUS_API_URL`:

### Morning Log
```
POST {LOCUS_API_URL}/api/v1/log/morning
Content-Type: application/json

{
  "energy": 7,
  "mood": 6,
  "sleep": 8,
  "stress": 3,
  "time_available": 5
}
```

Response includes DCS score, operating mode, and recommended task types.

### Task Operations
```
POST {LOCUS_API_URL}/api/v1/tasks
Content-Type: application/json

{ "title": "Study for exam", "faction": "leverage", "difficulty": 7 }
```

```
POST {LOCUS_API_URL}/api/v1/tasks/{task_id}/complete
```

```
POST {LOCUS_API_URL}/api/v1/tasks/{task_id}/defer
{ "reason": "too tired today" }
```

### Daily Query
```
POST {LOCUS_API_URL}/api/v1/schedule/recommend
Content-Type: application/json

{ "user_id": "<current_user>" }
```

### Voice Note
```
POST {LOCUS_API_URL}/api/v1/log/voice
Content-Type: multipart/form-data

file: <audio file>
```

### Vault Search (RAG)
```
POST {LOCUS_API_URL}/api/v1/vault/search
Content-Type: application/json

{ "query": "study techniques", "top_k": 5 }
```

## Response Patterns

### Morning Log Response
Always respond with:
1. DCS score and operating mode (with emoji)
2. Mode description
3. Available time
4. Recommended task types for today
5. The metrics used

Example:
```
✅ DCS: 6.0 → NORMAL

Standard operating. A full, balanced day is possible.

⏱ Available time: 5.0h

Recommended for today:
• Difficulty ≤ 7 allowed
• Balance across at least 2 factions
• 3-4 tasks outside non-negotiables

_Metrics: E=7 M=6 S=8 ST=3_
```

### Task Complete Response
Acknowledge completion, prompt for quality/time tracking:
```
✅ Task completed: Study for exam

Nice work. When you have a moment, reply with:
`quality [1-10]` and `time [minutes]` so I can track your patterns.
```

### Task Defer Response
Empathetic, ask for reason if not provided:
```
➡️ Task deferred: Study for exam
Reason noted: too tired today

I'll resurface this when your DCS is better suited for it.
```

## Configuration

- `LOCUS_API_URL` — Base URL of the Locus FastAPI backend (e.g., `http://locus-api:8000`)
- `TELEGRAM_OWNER_ID` — The Telegram user ID of the Locus owner (e.g., `8089688853`)

## Notes

- Never respond with generic "Logged" — always provide contextual responses
- Morning logs are the most important input — always calculate and display DCS
- Task deferrals should be empathetic, not judgmental
- Peak mode (DCS 8.1+) is rare — acknowledge when it happens
- Survival mode (DCS 0-2) — protect the user, don't push tasks
