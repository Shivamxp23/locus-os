# LOCUS — Personal Cognitive Operating System
## Master Technical Specification · Version 3.0 · Definitive & Frozen

> **Document Status:** FINAL. This is the single source of truth for Locus. All architectural, technical, and design decisions made herein are binding. No decisions in this document may be changed without a full version increment and executive sign-off. This document is handed to engineers, designers, and executives simultaneously.

---

## Table of Contents

1. [Vision & Philosophy](#1-vision--philosophy)
2. [What Locus Is — And Is Not](#2-what-locus-is--and-is-not)
3. [System Design Principles](#3-system-design-principles)
4. [Complete Tech Stack with Rationale](#4-complete-tech-stack-with-rationale)
5. [System Architecture Overview](#5-system-architecture-overview)
6. [Oracle VM Infrastructure](#6-oracle-vm-infrastructure)
   - 6.1 [Provisioning Steps](#61-provisioning-steps-do-this-once-never-again)
   - 6.2 [Confirmed VM Details & Phase 0 Status](#62-confirmed-vm-details--phase-0-status)
7. [Engine 1 — The Logging Engine](#7-engine-1--the-logging-engine)
8. [Engine 2 — The GraphRAG & Personality Engine](#8-engine-2--the-graphrag--personality-engine)
9. [Engine 3 — The Scheduling & Recommendation Engine](#9-engine-3--the-scheduling--recommendation-engine)
10. [The Master System — Task Intelligence](#10-the-master-system--task-intelligence)
11. [LLM Architecture & Hierarchy](#11-llm-architecture--hierarchy)
12. [Offline-First Architecture](#12-offline-first-architecture)
13. [Database Schemas — Complete DDL](#13-database-schemas--complete-ddl)
14. [Neo4j Graph Schema](#14-neo4j-graph-schema)
15. [Qdrant Vector Collections](#15-qdrant-vector-collections)
16. [Redis Key Patterns & Queue Design](#16-redis-key-patterns--queue-design)
17. [IndexedDB Schema (Offline Layer)](#17-indexeddb-schema-offline-layer)
18. [API Design — Complete Endpoint Reference](#18-api-design--complete-endpoint-reference)
19. [Frontend Architecture — PWA](#19-frontend-architecture--pwa)
20. [All External Integrations](#20-all-external-integrations)
21. [Security & Multi-User Architecture](#21-security--multi-user-architecture)
22. [Monitoring & Reliability](#22-monitoring--reliability)
23. [Build Order & Phased Roadmap](#23-build-order--phased-roadmap)
24. [Design System — For Designers](#24-design-system--for-designers)
25. [Agentic Capabilities — The OS Builds Its Own Tools](#25-agentic-capabilities--the-os-builds-its-own-tools)

**Appendices**
- [Appendix A: Local Project Directory Structure](#appendix-a-local-project-directory-structure)
- [Appendix B: Environment Variables](#appendix-b-environment-variables)
- [Appendix C: File Naming & Versioning Conventions](#appendix-c-file-naming--versioning-conventions)
- [Appendix D: Glossary](#appendix-d-glossary)

---

# 1. Vision & Philosophy

## 1.1 The Problem Locus Solves

Every productivity system ever built fails at the same thing: it treats you like a static, rational agent who consistently acts on declared intentions. You tell it your goals. It makes a schedule. You ignore the schedule. The system doesn't learn. You blame yourself.

The reality is that human behavior is dynamic, contextual, cyclical, and often contradictory. Your energy varies by hour, day, and season. Your interests evolve. Your avoidance patterns repeat. Your creativity spikes in bursts that your calendar never captures. No app built on Notion databases, task managers, or habit trackers has ever understood this — because they are tools, not systems.

**Locus is not a tool. Locus is a system that understands you.**

## 1.2 The PCOS Concept — Personal Cognitive Operating System

A PCOS does three things that no productivity tool has ever done together:

1. **It observes.** Every task you complete, defer, or abandon. Every note you write. Every conversation you have with an AI. Every article you save. Every goal you set and forget. All of it is behavioral data about who you actually are, not who you think you are.

2. **It understands.** It builds a living, multi-dimensional model of your personality, energy patterns, interest clusters, avoidance behaviors, creative cycles, and growth trajectory. Not from a questionnaire you filled out once — from continuous inference on real data.

3. **It acts.** Based on what it understands about you, it proactively routes your attention. It schedules the right work at the right time. It tells you what to read today. It drafts content from your own ideas. It alerts you to patterns you haven't noticed. It pushes you toward growth you've declared you want but haven't acted on.

This is the Personal Cognitive Operating System. Not a second brain. Not a productivity app. An operating system for a human life.

## 1.3 The Name: Locus

*Locus* — Latin for "place." In psychology, *locus of control* is the degree to which you believe you control outcomes in your life. An internal locus of control is one of the strongest predictors of success, resilience, and wellbeing in the research literature.

Locus returns locus of control to the user. It takes the chaos of a complex human life — ambitions, tasks, habits, ideas, consumption, creation — and creates structure, direction, and momentum. Not by constraining you, but by understanding you.

## 1.4 The Founding Constraints

These constraints are non-negotiable and drive every decision in this document:

| Constraint | What it means in practice |
|---|---|
| **Free** | Zero cost. Every service used must have a genuinely free tier or be self-hosted. No credit card surprises. |
| **Hassle-free** | Minimal maintenance. Once set up, it runs. No babysitting infrastructure. |
| **Reliable** | If it breaks, it breaks gracefully. No single point of failure that takes down the whole system. |
| **Offline-capable** | The system works on a plane. You can log, schedule, query, and infer without internet. |
| **Maximum control** | Full ownership of code, data, models, and infrastructure. No vendor lock-in. |
| **Scalable** | Built for one user now. Architected for N users from day one. |
| **Agentic** | If you ask it to do something, it finds a way. It can build tools, write scripts, and execute tasks autonomously. |

---

# 2. What Locus Is — And Is Not

## 2.1 What Locus Is

- A **Personal Cognitive Operating System** that learns who you are from your behavior
- A **three-engine intelligence pipeline**: Logging → GraphRAG/Personality → Scheduling/Recommendation
- A **PWA** (Progressive Web App) that works fully offline on iOS and Android
- A **self-hosted system** running on Oracle Cloud Free Tier with zero ongoing cost
- An **agentic system** that can autonomously complete complex tasks using built-in LLMs
- A **GraphRAG** that crawls your behavioral data to build a living personality model
- A **proactive coach** that pushes recommendations, insights, and reflections to you daily
- A **content engine** that drafts LinkedIn posts, reading lists, and reflections from your own data

## 2.2 What Locus Is Not

- It is not a task manager (though it manages tasks)
- It is not a habit tracker (though it tracks habits)
- It is not a note-taking app (though it ingests notes)
- It is not a calendar app (though it controls calendars)
- It is not a chatbot (though it has conversational AI)
- It is not a journal (though it creates one)
- It is not any one of these things — it is the system that connects all of them

## 2.3 Who Locus Is For (Now and Eventually)

**Phase 1 (now):** Single user. The founder. The system is built around one person's life and tuned to their specific goals, patterns, and personality. This phase is about building and proving the core intelligence.

**Phase 2 (eventually):** Multi-user. Other people onboard with their own completely isolated experience. The personality graph, data, AI outputs, and schedules are entirely separate per user. User isolation is not an afterthought — it is designed into every table, every API endpoint, and every query from day one via `user_id` fields.

---

# 3. System Design Principles

These principles govern every engineering and design decision. When in doubt, return to these.

## 3.1 Offline-First, Sync-Second

The system must be fully functional without internet. Not "degraded mode." Fully functional. You can log, schedule, infer, and query on a 10-hour flight with airplane mode on. Data queues locally and syncs when connectivity returns. The cloud makes you faster; it does not make you functional.

## 3.2 Engines Are Decoupled, Data Is Shared

The three engines (Logging, Personality, Scheduling) communicate through a message queue (Redis), not direct function calls. If Engine 2 goes down, Engine 1 keeps logging and Engine 3 keeps scheduling from the last known personality state. No cascade failures. Each engine degrades independently.

## 3.3 One Write Lock Per Data Source

Only one thing writes to any given data store at a time. The Logging Engine owns writes to PostgreSQL behavioral tables and Obsidian vault files. Engine 2 owns writes to Neo4j and Qdrant. Engine 3 owns writes to the calendar and Notion task properties. Nothing writes to a store it doesn't own.

## 3.4 Declared Data Is a Seed, Inferred Data Is the Truth

What you tell the system about yourself (goals, personality type, preferences) is a starting point. What the system infers from your actual behavior is treated as more reliable over time. A goal you declared three months ago but have produced zero output toward is a dead node — the system flags this rather than pretending the goal is still active.

## 3.5 The Signal Filter Principle

Not all data is equally valuable. A single deferral of a task tells you very little. Deferring the same task eleven times tells you everything. The system applies signal filtering — repeated patterns, emotional spikes, and long-term trends are high-signal. One-off events are low-signal unless they cluster. High-signal data influences the personality graph. Low-signal data is stored but weighted near zero.

## 3.6 Never Ask What You Can Infer

If the system can determine something from behavioral data, it does not ask the user. You should never be prompted "are you an introvert?" — the system reads your task completion patterns, response latencies, and communication frequency to infer social energy levels. Questions are for bootstrapping only.

## 3.7 Graceful Degradation at Every Level

| If this fails | The system does this |
|---|---|
| Oracle VM unreachable | PWA serves from cache, queues all inputs, uses WebLLM |
| Neo4j graph unavailable | Scheduling uses PostgreSQL behavioral tables as fallback |
| Qdrant unavailable | Embeddings use Transformers.js locally |
| Gemini API rate-limited | Falls back to Groq, then to Ollama on Oracle VM |
| All LLM APIs down | Falls back to Ollama on Oracle VM |
| Oracle Ollama unavailable | Falls back to WebLLM in browser |
| Internet gone entirely | Full offline mode: IndexedDB + WebLLM + JS formulas |

---

# 4. Complete Tech Stack with Rationale

Every choice below is final. The rationale is provided so engineers understand why and do not substitute without understanding the tradeoff.

## 4.1 Infrastructure

### Oracle Cloud Free Tier — ARM A1 Compute Instance
- **Spec:** 4 OCPU (ARM Ampere A1), 24 GB RAM, 200 GB block storage
- **Cost:** $0 forever (Always Free tier)
- **Why:** The most powerful free compute available anywhere. 24 GB RAM is enough to run Neo4j, Qdrant, Redis, PostgreSQL, Ollama with Llama 3.1 8B, and the application stack simultaneously. No other free tier comes close. The ARM architecture is modern, efficient, and Dockerized services run on it without modification.
- **Why not a paid VPS:** The founding constraint is free. Oracle gives us datacenter-grade hardware for nothing.
- **Supplementary:** 2× AMD micro instances (1 GB RAM each), also Always Free. Used for Caddy reverse proxy and Uptime Kuma monitoring.

### Cloudflare Tunnel
- **Cost:** $0 (Cloudflare Tunnel is permanently free, no credit card required)
- **Domain:** `locusapp.online` — registered on [Hostinger.in](https://hostinger.in), paid in INR via Indian debit card. Annual renewal is minimal (₹69–99/year for `.online`). This was chosen because Indian debit cards are not accepted on most Western registrars, and free domain options (`.us.kg`, `trycloudflare.com` quick tunnels) either require KYC verification or change URL on every restart — both unsuitable for production.
- **Live API URL:** `https://api.locusapp.online` — this is the permanent, production URL for all API calls from the PWA and Telegram bot.
- **Cloudflare nameservers:** `carter.ns.cloudflare.com` and `lorna.ns.cloudflare.com`
- **Cloudflare domain status:** Active ✅
- **Why:** Permanent, stable HTTPS URL for the Oracle VM without opening firewall ports, without a static IP concern, without ngrok's session timeouts or paid tier requirements. Cloudflare Tunnel creates an outbound-only encrypted connection from the VM to Cloudflare's edge. The URL never changes. It never drops.
- **Why not ngrok:** ngrok free tier sessions expire, URLs change, and reliability is unsuitable for production.
- **Why not Caddy alone:** Caddy on the VM handles internal routing. Cloudflare Tunnel handles the external exposure. Both are used; they do different jobs.
- **Important for new setup:** You must add your domain to Cloudflare (free account at dash.cloudflare.com) and wait for it to show as Active *before* running `cloudflared tunnel login`. The login page shows a domain picker — if no domain is added, the list is empty and login cannot proceed.

### Cloudflare Pages
- **Cost:** $0 (unlimited builds, unlimited bandwidth on free tier)
- **Frontend URL:** `https://locusapp.online` (root domain, served from Cloudflare Pages)
- **Why:** Hosts the PWA frontend. Globally distributed CDN, instant cache invalidation on deploy, built-in HTTPS, zero configuration. The PWA's static assets live here and are served with zero latency from Cloudflare's edge nodes.
- **Migration note:** The project was previously linked to Vercel at `locusproject.vercel.app`. This must be migrated to Cloudflare Pages. Vercel subdomains cannot be pointed to Cloudflare nameservers and therefore cannot be used with a custom domain.

### Syncthing (on Oracle VM)
- **Cost:** $0 (open source, self-hosted)
- **Why:** Syncs the Obsidian vault between Oracle VM and all devices. No cloud intermediary. No subscription. Encrypts in transit. Works on local network and over internet. Syncs are near-instant on the same network. The Oracle VM vault is canonical; devices are synchronized replicas.
- **Why not Obsidian Sync:** $8/month subscription. Unnecessary cost when Syncthing exists.

## 4.2 Databases

### PostgreSQL 15 + pgvector (self-hosted on Oracle VM)
- **Cost:** $0 (open source)
- **Why PostgreSQL:** The gold standard relational database. Battle-tested, ACID-compliant, excellent JSON support, excellent full-text search, and with pgvector, it can serve as a vector database for smaller embedding workloads. Self-hosting on the Oracle VM's 200 GB disk means we will never hit a storage limit.
- **Why not Neon:** Neon's free tier gives 0.5 GB storage. A personal life OS will exceed this in weeks with behavioral logging. Migrating from Neon to a self-hosted instance mid-project would require schema changes, data export, reimport, and code changes to connection strings. This violates the zero-migration constraint.
- **Why not SQLite:** SQLite has no built-in network access (requires workarounds for multi-process), no pgvector support, and is not designed for concurrent writes from multiple engine workers.
- **pgvector extension:** Enables vector similarity search directly in PostgreSQL. Used for embedding storage and semantic search on smaller collections (< 100K vectors) where Qdrant's overhead is unnecessary.
- **Storage estimate:** 200 GB supports approximately 10 years of aggressive behavioral logging for a single user, or ~50 users at moderate usage.

### Qdrant (self-hosted on Oracle VM)
- **Cost:** $0 (open source)
- **Why:** Purpose-built vector database. Faster and more memory-efficient than pgvector at scale (> 100K vectors). Supports payload filtering, sparse vectors, and named vectors. Used for semantic search over behavioral logs, Obsidian notes, and chat exports. The personality engine queries Qdrant to find semantically similar past behaviors when building insights.
- **RAM allocation:** ~2 GB for the vector index. With 24 GB available on the ARM instance, this is trivial.
- **Why not Pinecone/Weaviate:** Both require cloud hosting (paid at scale) or complex self-hosting. Qdrant is the easiest to self-host with the best performance per GB.

### Neo4j Community Edition (self-hosted on Oracle VM)
- **Cost:** $0 (Community Edition is open source and fully featured for single-instance use)
- **Why:** The personality graph requires a native graph database. Neo4j's Cypher query language is expressive for pattern detection ("find all nodes connected to Filmmaking where intensity > 7 and last_active > 30 days ago"). PostgreSQL can store graph-like data with recursive CTEs, but querying it is verbose, slow, and error-prone compared to native graph traversal.
- **The personality graph lives here:** Every interest node, behavioral pattern, goal relationship, and personality dimension is stored as nodes and relationships in Neo4j.
- **RAM allocation:** ~3 GB. Neo4j Community is single-instance (no clustering), which is fine — this is a personal OS.

### Redis (self-hosted on Oracle VM)
- **Cost:** $0 (open source)
- **Why:** Two roles. First, the **message queue** that decouples the three engines — Engine 1 publishes events to Redis queues, Engines 2 and 3 consume them. This is the circuit breaker that prevents cascade failures. Second, **ephemeral state storage** — API rate limit counters, sync locks, session tokens, Notion polling state (last seen `last_edited_time`), and task decomposition in-flight state.
- **Persistence:** Redis is configured with AOF (Append Only File) persistence so the queue survives a VM restart.
- **RAM allocation:** ~1 GB.

## 4.3 LLM Stack

### Ollama (self-hosted on Oracle VM)
- **Cost:** $0 (open source)
- **Models:**
  - `llama3.1:8b` — Primary reasoning model. Used for task decomposition, insight generation, LinkedIn draft creation, long-form reflection. At 4-bit quantization, uses ~6 GB RAM.
  - `phi3.5` — Fast lightweight model. Used for quick tasks: normalization, entity extraction, frontmatter tagging, mood inference. ~3 GB RAM.
  - `nomic-embed-text` — Embedding model. Generates 768-dimensional embeddings for all behavioral logs, notes, and chat exports. ~500 MB RAM.
- **Why Ollama:** Single command to install and run any GGUF model. Automatic hardware detection (uses ARM NEON instructions on the Oracle A1 core). REST API compatible with the OpenAI SDK — drop-in replacement with zero code change for most operations.
- **RAM budget for Ollama:** 9.5 GB total (one model loaded at a time, model swapping is automatic).

### Gemini 2.0 Flash (primary external LLM API)
- **Cost:** $0 on free tier (1M tokens/minute, 15 requests/minute — generous for a personal OS)
- **Why:** Google's Gemini 2.0 Flash has the largest free context window available (1M tokens), excellent instruction following, and is fast. Used when the task exceeds Ollama's quality threshold — complex multi-step reasoning, very long context (reading entire Obsidian vault sections), or when Ollama is under load.
- **Why primary over Claude/GPT-4o:** Both have significantly lower free tier limits. Gemini 2.0 Flash is the best free LLM API available as of this document's writing.

### Groq (fallback external LLM API + voice transcription)
- **Cost:** $0 on free tier (rate limits are generous for personal use)
- **Why:** Groq's hardware (LPU) makes inference extremely fast — often 10× faster than Gemini for the same model. Used as the fallback when Gemini is rate-limited. Also the primary API for **Groq Whisper** — voice note transcription from Telegram voice messages and in-app recordings.
- **Models on Groq:** `llama-3.1-8b-instant` for text, `whisper-large-v3` for voice.

### WebLLM (in-browser, offline)
- **Model:** `Phi-3.5-mini-instruct` (~2.7 GB download, cached in browser storage permanently)
- **Why WebLLM:** The only technology that runs a real LLM entirely in the browser using WebGPU. No server. No API call. Downloaded once, runs forever offline. On iPhone 16 Pro Max (A18 Pro chip, Neural Engine, iOS 18 with full WebGPU support in Safari), this runs at approximately 15–25 tokens/second — genuinely usable.
- **On Samsung A32:** Chrome on Android has full WebGPU support. Phi-3.5-mini at 2.7 GB fits in 6 GB RAM with headroom.
- **Why Phi-3.5-mini specifically:** Best reasoning quality per GB of any model that fits on a mobile device. Microsoft's Phi series is specifically optimized for structured tasks — exactly what the offline use case requires (task decomposition, goal breakdown, data querying).
- **Download UX:** A prominent "Download for offline AI" button in Settings, with a progress bar. The download is intentional — the user triggers it on Wi-Fi. It is never triggered automatically.

### Transformers.js (in-browser embedding generation, offline)
- **Model:** `all-MiniLM-L6-v2` (~25 MB model weights, ~50 MB total with tokenizer assets) for embeddings
- **Why:** When offline, the app still needs to perform semantic search over the locally cached personality snapshot and behavioral data. Transformers.js runs ONNX models in the browser. `all-MiniLM-L6-v2` generates 384-dimensional embeddings that are semantically compatible (with normalization) with `nomic-embed-text` outputs, enabling cross-mode search.

### Confirmed Device Capabilities

| Device | Chip | RAM | WebGPU | WebLLM Status |
|---|---|---|---|---|
| iPhone 16 Pro Max | A18 Pro (Neural Engine) | 8 GB | ✅ Safari iOS 18 | ✅ Confirmed capable, ~15–25 tok/s |
| Samsung Galaxy A32 | Mediatek Helio G80 | 6 GB | ✅ Android Chrome | ✅ Confirmed capable |

Both devices have the PWA installed to their home screen. No App Store required. Behaves as a native app — full screen, no browser chrome, push notifications enabled.

## 4.4 Frontend

### Vite + React (PWA)
- **Why Vite:** Fastest build tool available. HMR (Hot Module Replacement) in < 100ms. Production builds are extremely lean. Native ES module support means zero-config tree shaking.
- **Why React:** Largest ecosystem, best WebLLM integration examples, team familiarity, and component reuse across PWA and any future native shells.
- **Why PWA, not Expo React Native:**
  - Expo Go has been causing consistent issues (the direct reason for this decision)
  - A PWA runs in Safari (iOS) and Chrome (Android) — no app store, no review, no update delays
  - WebLLM requires browser APIs (WebGPU, OPFS) that are not available in Expo's JavaScript runtime
  - Cloudflare Pages deployment is instant (git push = live in 30 seconds)
  - A single codebase serves web, iOS, and Android
  - The iPhone 16 Pro Max and Samsung A32 both have modern browsers that support every PWA feature needed
- **PWA features enabled:** Service Worker (offline caching), Web App Manifest (installable to home screen), Background Sync, Push Notifications, IndexedDB, OPFS (Origin Private File System for WebLLM model storage)
- **State management:** Zustand (lightweight, no boilerplate, works seamlessly with React Query)
- **Data fetching:** TanStack Query (React Query) — handles caching, background refresh, and optimistic updates for the online/offline boundary

### IndexedDB (offline storage layer)
- **Library:** Dexie.js — the best TypeScript-first IndexedDB wrapper. Provides reactive queries, migrations, and a clean API.
- **Why IndexedDB over localStorage:** localStorage is synchronous, limited to ~5 MB, and stores only strings. IndexedDB is asynchronous, limited only by device storage (tens of GB), and stores structured objects including Blobs.
- **Contents:** Full task/goal/project cache, 30 days of behavioral metrics, last personality snapshot, sync queue for all offline writes, cached schedule (7 days), cached recommendations.

## 4.5 Backend

### FastAPI (Python)
- **Why FastAPI:** Async-native (built on Starlette + uvicorn), automatic OpenAPI documentation, type validation via Pydantic, native async PostgreSQL support via asyncpg. Python is the right language for this project because the entire ML/AI ecosystem (LangChain, Mem0, LlamaIndex utilities, pgvector client, Neo4j driver) is Python-first.
- **Why not Node.js/Express:** The document from the earlier conversation suggested Node.js. FastAPI is the correct choice for a system that is heavily AI/ML integrated. Python's ecosystem for this specific use case (graph manipulation, vector operations, LLM orchestration) is vastly superior to Node.js.
- **Process management:** Gunicorn with uvicorn workers. Managed by Docker Compose with `restart: always`.

### Celery + Redis (background task workers)
- **Why Celery:** The three engines run as Celery workers consuming from Redis queues. Celery handles retries, priority queues, task routing, and failure handling. Each engine is a separate Celery worker process that can be scaled independently.
- **Beat scheduler:** Celery Beat runs the cron jobs (nightly GraphRAG crawl, Supermemory batch pull, snapshot packager, Notion polling).

## 4.6 External Integrations

### Google Calendar API
- **Cost:** $0 (free quota is essentially unlimited for personal use)
- **Use:** Read existing events (to avoid scheduling conflicts), write new time blocks from Engine 3.
- **Auth:** OAuth 2.0 with refresh token stored in PostgreSQL per user.

### Notion API
- **Cost:** $0 (free tier supports API access)
- **Use:** Bidirectional sync of tasks, goals, projects. Notion is the intentional input surface — where the user manages work deliberately. The OS reads from and writes back to Notion.
- **Polling:** Every 60 seconds via Celery Beat task (Notion does not yet have native outbound webhooks). Detects changes via `last_edited_time` comparison.

### Telegram Bot API
- **Cost:** $0
- **Use:** Mobile interface for when the user prefers messaging over the PWA. Voice notes via Telegram are transcribed via Groq Whisper and fed into Engine 1. Proactive pokes from Engine 2 are sent via Telegram. The bot also serves as an alert channel for system health.

### Supermemory API
- **Cost:** $0 (free tier)
- **Use:** The intake funnel for web content. Bookmarks, articles, tweets saved from the phone are sent to Supermemory. A nightly Celery Beat task pulls new items, asks Ollama "why did the user save this?", tags them, and writes them to both Obsidian and PostgreSQL.

### rclone → Google Drive
- **Cost:** $0 (Google Drive has 15 GB free; backups are compressed)
- **Use:** Nightly automated backup of PostgreSQL dump, Neo4j dump, and Qdrant snapshot to Google Drive. Runs via cron on the Oracle VM. Ensures no data loss if Oracle's block storage fails.

---

# 5. System Architecture Overview

Locus is three engines connected by a message queue (Redis), with an offline layer on each device and a cloud intelligence layer on Oracle VM.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INPUT SOURCES                                       │
│  PWA (user-typed) · Telegram voice/text · Notion tasks · Obsidian notes     │
│  Google Calendar events · Supermemory bookmarks · AI Gateway chats          │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼ (all sources → Redis queue)
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENGINE 1: LOGGING ENGINE                                 │
│  Normalize → Extract entities/mood/intent → Tag with frontmatter            │
│  Write to PostgreSQL (behavioral_events) · Write to Obsidian (.md)          │
│  Transcribe voice (Groq Whisper) · Route AI Gateway chats to Obsidian       │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │ (enriched events → Redis queue)
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               ENGINE 2: GRAPHRAG + PERSONALITY ENGINE                       │
│  Nightly crawl of Obsidian vault → Update Qdrant vectors                    │
│  Build/update Neo4j personality graph (multi-dimensional nodes)             │
│  Reflection engine: detect loops, contradictions, avoidance, spikes         │
│  Signal filter: separate high-value patterns from noise                     │
│  Output: insights, pokes, personality snapshot                              │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │ (behavioral signals → Redis queue)
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              ENGINE 3: SCHEDULING + RECOMMENDATION ENGINE                   │
│  Master System: intake → decompose → score → route → calendar write         │
│  Recommendation engine: books, blogs, LinkedIn drafts, daily reads          │
│  Proactive pokes via Telegram + PWA push notifications                      │
└─────────────────────────────────────────────────────────────────────────────┘
                          │ (feedback loop)
                          ▼ (completions, deviations → back to Engine 1)
```

## 5.1 Oracle VM Service Map

All services run in Docker Compose with `restart: always`. No service is optional — if one fails, Docker restarts it automatically within seconds.

```
Oracle ARM A1 (4 OCPU, 24 GB RAM, 200 GB disk)
│
├── fastapi-app          (FastAPI + uvicorn)          Port 8000  ~500MB RAM
├── celery-worker-e1     (Engine 1 Celery worker)                ~300MB RAM
├── celery-worker-e2     (Engine 2 Celery worker)                ~500MB RAM
├── celery-worker-e3     (Engine 3 Celery worker)                ~300MB RAM
├── celery-beat          (Cron scheduler)                        ~200MB RAM
├── postgres             (PostgreSQL 15 + pgvector)  Port 5432  ~1.5GB RAM
├── qdrant               (Qdrant vector DB)           Port 6333  ~2GB RAM
├── neo4j                (Neo4j Community)            Port 7474  ~3GB RAM
├── redis                (Redis + AOF persistence)   Port 6379  ~512MB RAM
├── ollama               (Ollama LLM server)          Port 11434 ~9.5GB RAM
│   ├── llama3.1:8b      (~6GB when loaded)
│   ├── phi3.5           (~3GB when loaded)
│   └── nomic-embed-text (~500MB always loaded)
└── syncthing            (File sync daemon)           Port 8384  ~150MB RAM

Total peak RAM: ~18GB (leaves 6GB headroom for Oracle OS + burst)
```

```
Oracle AMD #1 (1/8 OCPU, 1 GB RAM)
└── caddy                (Reverse proxy + HTTPS)     Ports 80,443
    └── cloudflared      (Cloudflare Tunnel client)

Oracle AMD #2 (1/8 OCPU, 1 GB RAM)
└── uptime-kuma          (Service monitoring)         Port 3001
```

---

# 6. Oracle VM Infrastructure

## 6.1 Provisioning Steps (Do This Once, Never Again)

This is the exact sequence for setting up the Oracle VM. It is written in this document because it must be done correctly once and never touched again.

### Step 1: Create the ARM A1 Instance
- Oracle Cloud Console → Compute → Instances → Create Instance
- Shape: VM.Standard.A1.Flex, 4 OCPU, 24 GB RAM
- Image: Ubuntu 22.04 LTS (Canonical)
- Storage: Boot volume 200 GB
- Network: Create a new VCN with public subnet, assign a public IP
- SSH key: Upload your public key. Download the private key. Store securely.

### Step 2: Configure Firewall
Oracle uses two firewalls: the OS-level iptables and the VCN Security List. Both must be opened.

```bash
# On the VM — open ports in iptables
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 8384 -j ACCEPT  # Syncthing UI (restrict to your IP)
sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT    # SSH

# Save iptables rules
sudo netfilter-persistent save

# In Oracle Console → Networking → Security Lists → Add Ingress Rules
# TCP: 80, 443 (from 0.0.0.0/0)
# TCP: 22 (from your IP only)
```

### Step 3: Harden the VM

```bash
# Disable password SSH login (keys only)
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Install fail2ban (blocks brute force)
sudo apt install fail2ban -y
sudo systemctl enable fail2ban

# Set timezone
sudo timedatectl set-timezone Asia/Kolkata  # Adjust to your timezone

# Auto security updates
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### Step 4: Install Docker

```bash
# One-line Docker install (official script)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

### Step 5: Install and Configure Cloudflare Tunnel

> **Pre-requisite:** Before running `cloudflared tunnel login`, your domain must already be added to Cloudflare (dash.cloudflare.com → Add a site) and showing status **Active**. The login page shows a domain picker — if no domain is added, the list is empty and you cannot proceed. The confirmed domain for this project is `locusapp.online`, already active on Cloudflare.

```bash
# Install cloudflared (ARM64 — specific to Oracle A1 instance architecture)
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared-linux-arm64.deb

# Verify installation
cloudflared --version
# Expected: cloudflared version 2026.3.0 or newer
```

**Authenticate with your Cloudflare account:**

```bash
cloudflared tunnel login
```

This prints a URL in the terminal. Open it in your browser on your laptop. A page titled "Authorize Cloudflare Tunnel" will appear with a list of your domains. Click `locusapp.online`. The terminal will confirm:

```
You have successfully logged in.
Credentials saved to: /home/ubuntu/.cloudflared/cert.pem
```

**Create the named tunnel:**

```bash
cloudflared tunnel create locus-tunnel
```

This prints a tunnel ID (UUID) and saves credentials to `/home/ubuntu/.cloudflared/<tunnel-id>.json`. Note the tunnel ID — you need it in the next step.

**Create the tunnel config file** (replace `<TUNNEL-ID>` with the UUID printed above):

```bash
cat > ~/.cloudflared/config.yml << EOF
tunnel: <TUNNEL-ID>
credentials-file: /home/ubuntu/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: api.locusapp.online
    service: http://localhost:3000
  - service: http_status:404
EOF
```

**Verify the config was written correctly:**

```bash
cat ~/.cloudflared/config.yml
```

**Add the DNS CNAME record on Cloudflare:**

```bash
cloudflared tunnel route dns locus-tunnel api.locusapp.online
```

Expected output:
```
INF Added CNAME api.locusapp.online which will route to this tunnel tunnelID=<your-tunnel-id>
```

**Install cloudflared as a systemd service** (auto-starts on every reboot):

```bash
# Must pass the full config path — sudo does not expand ~ correctly
sudo cloudflared --config /home/ubuntu/.cloudflared/config.yml service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

**Verify it is running:**

```bash
sudo systemctl status cloudflared
```

Look for `Active: active (running)` and log lines showing `Registered tunnel connection` with `location=bom0X`. Four registered connections means the tunnel is fully live. The `bom` prefix refers to Cloudflare's Mumbai edge — this is normal for a Singapore-region VM and adds negligible latency.

**Confirmed working values (for reference):**

| Field | Value |
|---|---|
| Tunnel name | `locus-tunnel` |
| Tunnel ID | `61aaf41c-b590-4a7c-baaf-2805bedca731` |
| Credentials file | `/home/ubuntu/.cloudflared/61aaf41c-b590-4a7c-baaf-2805bedca731.json` |
| Config file (runtime) | `/etc/cloudflared/config.yml` (copied here by the service installer) |
| API hostname | `api.locusapp.online` |
| Service status | `active (running)`, enabled on boot ✅ |

---

## 6.2 Confirmed VM Details & Phase 0 Status

### VM Specifications (Confirmed)

| Field | Value |
|---|---|
| Public IP | `140.238.245.25` |
| Region | `ap-singapore-1` (Singapore) |
| Shape | VM.Standard.A1.Flex |
| OCPU | 4 |
| RAM | 24 GB |
| Storage | 200 GB block volume |
| OS | Ubuntu 22.04.5 LTS (aarch64 / ARM64) |
| Timezone | Asia/Kolkata (IST, UTC+5:30) |

> **Note on region:** Mumbai (`ap-mumbai-1`) was attempted first but returned "Out of host capacity" — a common issue with Oracle's free tier ARM instances in India. Singapore was the next available region with ARM A1 capacity. All services function identically. Latency from India to Singapore is ~60–80ms, acceptable for a personal OS.

### SSH Access

```bash
ssh -i "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\infra\ssh-key-2026-03-27.key" ubuntu@140.238.245.25
```

SSH key location on Shivam's laptop:
```
C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\infra\ssh-key-2026-03-27.key
```

> ⚠️ Back this key up to Google Drive immediately. If lost, you cannot SSH into the VM and recovery requires Oracle's browser-based console (slow and painful).

### AMD Instances (Confirmed)

| Instance | Hostname | Public IP | Internal IP | Role |
|---|---|---|---|---|
| AMD Micro #1 | `locus-caddy` | `80.225.201.193` | `10.0.0.28` | Caddy reverse proxy (currently unused — see note) |
| AMD Micro #2 | `locus-monitor` | `80.225.249.205` | `10.0.0.38` | Uptime Kuma monitoring |

> **Note on Caddy:** Caddy was set up on `locus-caddy` but is not actively needed — `api.locusapp.online` is already handled by the Cloudflare Tunnel with full HTTPS. Caddy caused SSL certificate conflicts since Cloudflare proxies the domain. It is installed and disabled for now. The root domain `locusapp.online` will be served via Cloudflare Pages when the PWA frontend is built in Phase 2.

### Uptime Kuma (Confirmed)

Running on `locus-monitor` at `http://80.225.249.205:3001`.

Monitors configured:
- **Locus API (internal):** `http://10.0.0.91:3000/status` — keyword `connected` — 60s interval
- **Locus API (public):** `https://api.locusapp.online/status` — 60s interval

> The internal IP monitor (`10.0.0.91`) is the reliable one — Oracle instances communicate over the internal VCN network without DNS resolution issues.

### rclone Google Drive Backup (Confirmed)

- rclone configured with remote named `gdrive`
- Backup script at `/opt/locus/infra/scripts/backup.sh`
- Cron job: runs at 3 AM daily
- Backs up PostgreSQL dump to `gdrive:locus-backups/YYYYMMDD/postgres.sql.gz`
- Neo4j dump skipped while database is running (known limitation — fix in later phase)
- Verified: backup appears in Google Drive ✅

### Syncthing (Confirmed)

- Running as Docker container `locus-syncthing`
- Web UI at `http://140.238.245.25:8384` (port open in iptables + VCN)
- Vault folder label: `Appledore`, path: `/vault`
- Both phones added as remote devices
- VM Device ID: `2LOZKYW-LOGD7EI-RJULSS6-CTOZSDK-CTT4IKD-ITWSS7G-MKCVVGF-YLETWQZ`

### Git Repository (Confirmed)

- GitHub repo: `https://github.com/Shivamxp23/locus-os` (private)
- First commit: `chore: Phase 0 — full infra scaffold, schema, backend skeleton`
- Branch: `main`

### Known Issues & Fixes Applied

| Issue | Fix Applied |
|---|---|
| `redbeat` package not available on ARM64 | Removed from `requirements.txt`, Celery beat uses default scheduler |
| `POSTGRES_PASSWORD` contained `#` character, broke DATABASE_URL | Changed password to one without special characters |
| `personality_snapshots` UNIQUE constraint used `::DATE` cast (not allowed in index) | Removed constraint, table created without it |
| Syncthing `/vault` permission denied | Fixed with `docker exec -u root locus-syncthing chmod 777 /vault` |
| Uptime Kuma Docker container couldn't resolve `locusapp.online` DNS | Use internal Oracle IP `http://10.0.0.91:3000/status` instead |
| Caddy SSL cert conflicts with Cloudflare proxy | Caddy disabled — Cloudflare Tunnel handles `api.locusapp.online` directly |

### Phase 0 Checklist

| Task | Status |
|---|---|
| Oracle ARM A1 instance provisioned (4 OCPU, 24 GB, 200 GB) | ✅ Done |
| Ubuntu updated + upgraded | ✅ Done |
| Docker v29.3.1 installed and running | ✅ Done |
| `ubuntu` user added to docker group | ✅ Done |
| Node.js 20 installed | ✅ Done |
| Git installed | ✅ Done |
| cloudflared v2026.3.0 installed | ✅ Done |
| Firewall: ports 80, 443, 22, 3000 open via iptables | ✅ Done |
| Oracle VCN Security List: ports 80, 443, 3000, 3001, 8384 open | ✅ Done |
| SSH hardened: password auth disabled, keys only | ✅ Done |
| fail2ban installed and enabled | ✅ Done |
| Timezone set to Asia/Kolkata | ✅ Done |
| Cloudflare Tunnel live at `api.locusapp.online` | ✅ Done |
| 2× Oracle AMD micro instances provisioned | ✅ Done |
| Docker Compose with all services running | ✅ Done |
| PostgreSQL schema applied | ✅ Done |
| Default user seeded (`soni820034@gmail.com`) | ✅ Done |
| Ollama models pulled (llama3.1:8b, phi3.5, nomic-embed-text) | ✅ Done |
| rclone configured + backup script running via cron | ✅ Done |
| Syncthing running, vault shared with both phones | ✅ Done |
| Uptime Kuma running on AMD #2, monitors configured | ✅ Done |
| Git repo pushed to GitHub (`locus-os`) | ✅ Done |
| `https://api.locusapp.online/status` returns `postgres: connected` | ✅ Done |
| Caddy on AMD #1 | ⚠️ Installed but disabled (not needed — see note above) |
| `/status` verified from iPhone and Samsung | ✅ Done |

---

### Step 6: Docker Compose — Full Configuration

Create `/opt/locus/docker-compose.yml`:

> **Note:** Remove the `version: '3.9'` line — it's obsolete in Docker Compose v2 and causes a warning. Also `redbeat` is not available on ARM64 — use Celery's default beat scheduler instead (remove `--scheduler redbeat.RedBeatScheduler` from the beat command). The `fastapi` service maps port `3000:8000` (external:internal) so the Cloudflare Tunnel pointing to `localhost:3000` works correctly.

```yaml

networks:
  locus-net:
    driver: bridge

volumes:
  postgres-data:
  qdrant-data:
  neo4j-data:
  redis-data:
  ollama-data:
  syncthing-data:
  obsidian-vault:

services:

  postgres:
    image: pgvector/pgvector:pg15
    container_name: locus-postgres
    restart: always
    environment:
      POSTGRES_DB: locus
      POSTGRES_USER: locus
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - locus-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U locus"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: locus-redis
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - locus-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    container_name: locus-qdrant
    restart: always
    volumes:
      - qdrant-data:/qdrant/storage
    networks:
      - locus-net

  neo4j:
    image: neo4j:5-community
    container_name: locus-neo4j
    restart: always
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_memory_heap_max__size: 2G
      NEO4J_dbms_memory_pagecache_size: 1G
    volumes:
      - neo4j-data:/data
    networks:
      - locus-net

  ollama:
    image: ollama/ollama:latest
    container_name: locus-ollama
    restart: always
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - locus-net
    deploy:
      resources:
        limits:
          memory: 12G

  fastapi:
    build: ./backend
    container_name: locus-api
    restart: always
    environment:
      DATABASE_URL: postgresql+asyncpg://locus:${POSTGRES_PASSWORD}@postgres:5432/locus
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      QDRANT_URL: http://qdrant:6333
      NEO4J_URL: bolt://neo4j:7687
      OLLAMA_URL: http://ollama:11434
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      GROQ_API_KEY: ${GROQ_API_KEY}
      SECRET_KEY: ${SECRET_KEY}
    volumes:
      - obsidian-vault:/vault
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - locus-net
    ports:
      - "8000:8000"

  celery-e1:
    build: ./backend
    container_name: locus-celery-e1
    restart: always
    command: celery -A app.celery worker -Q engine1 --concurrency=2 -n engine1@%h
    environment: *fastapi-env
    volumes:
      - obsidian-vault:/vault
    depends_on:
      - fastapi
    networks:
      - locus-net

  celery-e2:
    build: ./backend
    container_name: locus-celery-e2
    restart: always
    command: celery -A app.celery worker -Q engine2 --concurrency=1 -n engine2@%h
    environment: *fastapi-env
    depends_on:
      - fastapi
    networks:
      - locus-net

  celery-e3:
    build: ./backend
    container_name: locus-celery-e3
    restart: always
    command: celery -A app.celery worker -Q engine3 --concurrency=2 -n engine3@%h
    environment: *fastapi-env
    depends_on:
      - fastapi
    networks:
      - locus-net

  celery-beat:
    build: ./backend
    container_name: locus-beat
    restart: always
    command: celery -A app.celery beat --scheduler redbeat.RedBeatScheduler
    environment: *fastapi-env
    depends_on:
      - fastapi
    networks:
      - locus-net

  syncthing:
    image: syncthing/syncthing:latest
    container_name: locus-syncthing
    restart: always
    volumes:
      - obsidian-vault:/vault
      - syncthing-data:/var/syncthing
    networks:
      - locus-net
    ports:
      - "22000:22000/tcp"
      - "22000:22000/udp"
      - "21027:21027/udp"
```

### Step 7: Scheduled Backups

```bash
# Add to crontab (crontab -e)
# 3 AM daily: backup all databases to Google Drive
0 3 * * * /opt/locus/scripts/backup.sh

# backup.sh content:
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/tmp/locus-backup-$DATE

mkdir -p $BACKUP_DIR

# PostgreSQL dump
docker exec locus-postgres pg_dump -U locus locus | gzip > $BACKUP_DIR/postgres.sql.gz

# Neo4j dump
docker exec locus-neo4j neo4j-admin database dump neo4j --to-path=/tmp
docker cp locus-neo4j:/tmp/neo4j.dump $BACKUP_DIR/neo4j.dump

# Qdrant snapshot
curl -X POST http://localhost:6333/collections/behavioral_logs/snapshots
# (then download and copy)

# Upload to Google Drive via rclone
rclone copy $BACKUP_DIR gdrive:locus-backups/$DATE

# Cleanup
rm -rf $BACKUP_DIR

# Keep only last 30 days on Google Drive
rclone delete gdrive:locus-backups --min-age 30d
```

---

# 7. Engine 1 — The Logging Engine

Engine 1 is the foundation. It is the only engine that accepts raw external data. Everything starts here.

## 7.1 Responsibilities

- Accept data from all input sources
- Normalize all inputs to a standard schema
- Extract entities, mood, intent, and topic tags using Ollama phi3.5
- Write normalized events to PostgreSQL (`behavioral_events` table)
- Write formatted Markdown files to the Obsidian vault
- Transcribe voice inputs via Groq Whisper
- Route all LLM conversations through the AI Gateway and log them
- Detect deferred tasks and increment deferral counters
- Publish enriched events to the Redis `engine2-queue` for personality processing

## 7.2 Input Sources

| Source | Mechanism | Frequency | Raw format |
|---|---|---|---|
| PWA task creation | REST API → Redis | Real-time | JSON |
| PWA note/journal | REST API → Redis | Real-time | Text |
| Telegram voice note | Telegram Bot webhook → Groq Whisper → Redis | Real-time | Audio → Text |
| Telegram text message | Telegram Bot webhook → Redis | Real-time | Text |
| Notion task changes | Celery Beat poll every 60s | Near-real-time | Notion API JSON |
| Notion task completion | Celery Beat poll every 60s | Near-real-time | Notion API JSON |
| Google Calendar events | Celery Beat poll every 15min | Near-real-time | Google Calendar JSON |
| Supermemory bookmarks | Celery Beat nightly 2 AM | Batch | Supermemory API JSON |
| AI Gateway chats | REST API intercept → Redis | Real-time | Chat JSON |
| Obsidian vault changes | Syncthing file watcher | Near-real-time | Markdown |

## 7.3 Normalization Pipeline

Every input goes through this exact pipeline before being written anywhere:

```
RAW INPUT
    │
    ▼
[Step 1: Schema normalization]
    - Convert to BehavioralEvent schema (see §13 for full schema)
    - Assign UUID, user_id, source, raw_content
    - Set created_at (device timestamp), received_at (server timestamp)
    │
    ▼
[Step 2: Entity extraction — phi3.5]
    Prompt: "Extract from this text: topics (list), mood_indicator 
    (-1 to 1 float), intent (create|complete|defer|reflect|consume|query),
    goal_tags (from user's active goals list), energy_required (1-10).
    Return only JSON."
    │
    ▼
[Step 3: Frontmatter generation]
    - Generate YAML frontmatter for Obsidian
    - date, source, engine, tags, mood_score, goal_tags, ai_processed
    │
    ▼
[Step 4: Obsidian write]
    - Determine target file based on source and date
    - Acquire file lock (.lock sidecar file)
    - Append to appropriate section (never overwrite user content above ## AI annotations)
    - Release lock
    │
    ▼
[Step 5: PostgreSQL write]
    - INSERT into behavioral_events with all extracted fields
    - UPDATE related task record if applicable (deferral_count, completion)
    │
    ▼
[Step 6: Publish to engine2-queue]
    - Push enriched BehavioralEvent to Redis queue
    - Engine 2 worker consumes at its own pace
```

## 7.4 The AI Gateway

The AI Gateway is a transparent proxy for all LLM API calls. When the user opens the PWA and chats with an AI, the request goes through the Locus API (not directly to OpenAI/Gemini). The gateway:

1. Accepts the message from the PWA
2. Routes to the appropriate LLM (Ollama → Gemini → Groq, in priority order)
3. Streams the response back to the PWA
4. Logs the entire conversation (question + response) to PostgreSQL and Obsidian
5. Extracts insights from the conversation asynchronously

This means the user never uses the public ChatGPT or Gemini interfaces. All AI conversations happen through Locus, are logged, and feed the personality engine. The user gets a unified chat experience across all models from a single interface.

```python
# AI Gateway routing logic (simplified)
async def route_llm_request(prompt: str, user_id: str) -> AsyncGenerator:
    # Try Ollama first (free, always available if VM is up)
    try:
        async for chunk in ollama_generate(prompt, model="llama3.1:8b"):
            yield chunk
        return
    except OllamaUnavailable:
        pass
    
    # Try Gemini (free API, higher quality)
    try:
        async for chunk in gemini_generate(prompt):
            yield chunk
        return
    except GeminiRateLimited:
        pass
    
    # Fall back to Groq
    async for chunk in groq_generate(prompt, model="llama-3.1-8b-instant"):
        yield chunk
```

## 7.5 Obsidian Vault Structure

```
/vault (canonical on Oracle VM, synced to all devices via Syncthing)
│
├── OS-managed zone/ (Engine 1 writes, user reads)
│   ├── Logs/
│   │   └── YYYY-MM-DD.md     (daily behavioral log — tasks, mood, deviations)
│   ├── Chats/
│   │   └── YYYY-MM-DD.md     (all AI Gateway conversations)
│   ├── Tasks/
│   │   ├── active.md         (Notion mirror, updated every 60s)
│   │   └── completed.md      (archived completions)
│   ├── Reflections/
│   │   └── YYYY-MM.md        (Engine 2 annotations, one file per month)
│   ├── Schedule/
│   │   └── YYYY-MM-DD.md     (Engine 3 calendar blocks)
│   └── Reads/
│       └── YYYY-MM-DD.md     (Supermemory pulls + recommendations)
│
└── Personal zone/ (user writes, Engine 2 reads and annotates)
    ├── Notes/                (freeform notes)
    ├── Journal/              (personal journal entries)
    └── Ideas/                (brainstorming, concepts)
```

### Vault Write Rules (ABSOLUTE)
1. Engine 1 is the only writer to OS-managed zone files
2. Engine 2 and Engine 3 append ONLY to the `## AI annotations` section at the bottom of existing files — they never touch content above this section
3. All writes use a `.lock` sidecar file to prevent concurrent write corruption
4. The Personal zone is written only by the user (via Obsidian app). Engines read but never write to these files
5. Syncthing syncs the vault between Oracle VM and devices. Syncthing is **read-only on the device side for OS-managed zone files** — device-side changes to personal zone files sync bidirectionally

### Markdown File Format — Daily Log (example)

```markdown
---
date: 2026-03-25
source: multi
engine: logging
mood_score: 7.2
energy_score: 6.8
dominant_topic: filmmaking
goal_tags: [portfolio, creative, short-term]
ai_processed: true
tasks_completed: 4
tasks_deferred: 1
---

# Daily log — March 25, 2026

## Tasks completed
- [x] Draft essay outline (9:15 AM, 28 min)
- [x] Read "Cinematography and Light" chapter 3 (11:02 AM)
- [x] LinkedIn draft review (2:34 PM)
- [x] 30-min run (6:00 PM)

## Tasks deferred
- [ ] Edit portfolio video → deferred to tomorrow (deferral_count: 2)

## Voice notes
- 10:23 AM: "Had an idea about using natural light differently in the intro sequence..."

## AI annotations
<!-- Engine 2 writes below this line only. Do not edit this section. -->
**[Engine 2 · 2026-03-25 03:01 AM]**
Pattern detected: filmmaking-related tasks complete at 2.3× average speed vs. other categories.
Mood spike (+1.4) correlated with cinematography content consumption.
Recommendation: increase filmmaking content allocation from 20% → 30% of creative block time.
```

---

# 8. Engine 2 — The GraphRAG & Personality Engine

Engine 2 is the intelligence core of Locus. It is what separates Locus from every other productivity tool that has ever existed.

## 8.1 Responsibilities

- Nightly crawl of the entire Obsidian vault
- Generate and update Qdrant vector embeddings for all behavioral data
- Build and maintain the Neo4j personality graph
- Run the Reflection Engine: detect patterns, loops, contradictions, avoidance, and growth
- Apply the Signal Filter: separate high-value signals from noise
- Generate the nightly Personality Snapshot (compressed bundle for offline use)
- Output insights, pokes, and reflections to the user via Telegram and PWA
- Seed the Recommendation Engine with goal-aligned content suggestions

## 8.2 The Memory System — Four Layers

### Layer 1: Semantic Memory (Qdrant)
What you think. What your ideas mean. Stores 768-dimensional embeddings of every Obsidian note, behavioral log entry, AI chat, and Supermemory item. Enables semantic search: "find everything related to the feeling of creative block" — returns results by meaning, not by keyword.

### Layer 2: Relational Graph (Neo4j)
How things connect. The personality graph. Nodes represent interests, goals, habits, people, emotions, and behavioral patterns. Relationships represent reinforcement, contradiction, causation, and temporal sequence. This is the structure that enables insight generation.

### Layer 3: Temporal Layer (PostgreSQL time-series tables)
When patterns happen. Stores time-series data: daily mood scores, energy levels, task completion rates, topic frequency over time, habit streaks. Enables pattern detection across time: "your creativity spikes 3 days after consuming new film content" — this is temporal analysis.

### Layer 4: Behavioral Layer (PostgreSQL behavioral_events)
How you act versus how you intend. Every declared intention (goal set) versus actual behavior (output produced). This layer detects the gaps — declared goals with no corresponding behavioral output are the most important signals in the system.

## 8.3 The Personality Graph — Node Schema

Each node in Neo4j has the following structure. This is the multi-dimensional model at the heart of Locus.

```cypher
// Interest node example
CREATE (n:Interest {
  id: 'filmmaking',
  user_id: 'user_abc',
  label: 'Filmmaking',
  
  // Intensity dimensions
  intensity: 8.3,          // 0-10, how strong this interest currently is
  recency: 9.1,            // 0-10, how recently active (decays over time)
  consistency: 7.2,        // 0-10, how consistently present over 90 days
  
  // Emotional dimensions
  emotional_weight: 8.7,   // 0-10, emotional charge (positive or negative)
  emotional_valence: 1.0,  // -1 to 1, positive=joy/excitement, negative=anxiety/avoidance
  
  // Behavioral dimensions
  declared_priority: 9.0,  // 0-10, what user says this matters
  behavioral_priority: 7.4,// 0-10, what user's actions show this matters
  action_gap: 1.6,         // declared_priority - behavioral_priority (flags hypocrisy)
  
  // Temporal dimensions
  first_seen: datetime('2025-08-12'),
  last_active: datetime('2026-03-24'),
  peak_times: ['09:00-11:00', '20:00-22:00'],  // when engagement is highest
  
  // Category
  category: 'Creative',    // Creative | Career | Health | Relationships | Finance | Learning
  connected_to: ['Career', 'Identity', 'Skill'],  // semantic clusters
  
  // Metadata
  updated_at: datetime()
})
```

```cypher
// Goal node example
CREATE (n:Goal {
  id: 'goal_portfolio_2026',
  user_id: 'user_abc',
  label: 'Build a professional filmmaking portfolio',
  horizon: 'short-term',       // short-term | long-term | lifetime
  declared_at: datetime(),
  deadline: date('2026-12-31'),
  progress_score: 0.23,        // 0-1, computed from linked task completions
  active: true,
  stale: false,                // true if no linked task completed in 14 days
  stale_since: null
})
```

```cypher
// Behavioral pattern node example
CREATE (n:Pattern {
  id: 'pattern_avoidance_editing',
  user_id: 'user_abc',
  label: 'Avoids editing tasks when mood < 6',
  pattern_type: 'avoidance',   // avoidance | loop | contradiction | spike | habit
  confidence: 0.87,            // 0-1, how confident the system is this is real
  occurrences: 11,             // how many times detected
  first_detected: datetime(),
  last_detected: datetime(),
  trigger_condition: 'mood_score < 6.0',
  affected_categories: ['Creative'],
  intervention_suggested: 'schedule editing blocks only when mood > 7'
})
```

### Core Relationships

```cypher
// Interest connects to Goal
(filmmaking:Interest)-[:SERVES]->(portfolio_goal:Goal)

// Pattern affects Interest
(avoidance_pattern:Pattern)-[:SUPPRESSES]->(filmmaking:Interest)

// Goals reinforce each other
(portfolio_goal:Goal)-[:REINFORCES]->(career_goal:Goal)

// Interests contradict each other (competing for time)
(filmmaking:Interest)-[:COMPETES_WITH]->(tech_learning:Interest)

// Behavioral pattern is triggered by context
(avoidance_pattern:Pattern)-[:TRIGGERED_BY]->(low_mood:Context)

// Time-based interest decay
(filmmaking:Interest)-[:WAS_STRONGER_THAN {date: date()}]->(filmmaking:Interest)
```

## 8.4 The Reflection Engine

The Reflection Engine runs nightly as a Celery Beat task at 3:30 AM (after the GraphRAG crawl completes). It runs a battery of Cypher queries against Neo4j and produces structured insights.

### Detection Type 1: Avoidance Loops

```cypher
// Find tasks deferred 3+ times in the same category
MATCH (u:User {id: $user_id})-[:HAS_TASK]->(t:Task)
WHERE t.deferral_count >= 3
  AND t.category IN ['Creative', 'Career']
WITH t, t.deferral_count as count
ORDER BY count DESC
RETURN t.title, count, t.goal_link
```
Output: "You've deferred 'Edit portfolio video' 8 times. This task connects to your 'Professional Portfolio' goal. Historical data shows you avoid editing tasks when your energy score is below 6.5. Last 8 deferrals all occurred on days where energy_score was 5.1–6.3."

### Detection Type 2: Behavioral Contradictions

```cypher
// Find interests with high declared priority but low behavioral output
MATCH (i:Interest {user_id: $user_id})
WHERE i.action_gap > 2.5  // declared much higher than behavioral
RETURN i.label, i.declared_priority, i.behavioral_priority, i.action_gap
ORDER BY i.action_gap DESC
```
Output: "You rate 'Health & Fitness' as 9/10 important. Your behavioral data rates it 4.2/10 — a gap of 4.8 points. Zero fitness-related tasks completed in the last 14 days despite 3 fitness goals declared."

### Detection Type 3: Interest Spikes

```cypher
// Find interests with rapidly increasing recent activity vs 30-day baseline
MATCH (e:BehavioralEvent {user_id: $user_id})
WHERE e.created_at > datetime() - duration('P7D')
  AND e.topic_tags CONTAINS $interest
WITH count(e) as recent_count

MATCH (e2:BehavioralEvent {user_id: $user_id})
WHERE e2.created_at > datetime() - duration('P37D')
  AND e2.created_at < datetime() - duration('P7D')
  AND e2.topic_tags CONTAINS $interest
WITH recent_count, count(e2)/4 as baseline_count
WHERE recent_count > baseline_count * 2
RETURN $interest as topic, recent_count, baseline_count
```
Output: "Your engagement with 'Documentary filmmaking' has spiked 340% in the last 7 days vs. your 30-day baseline. This may indicate an emerging interest worth acting on. Recommendation: schedule one deep work block this week for exploratory documentary research."

### Detection Type 4: Goal Staleness

```cypher
// Find goals with no behavioral activity in 14+ days
MATCH (g:Goal {user_id: $user_id, active: true})
WHERE g.last_task_completed < datetime() - duration('P14D')
  OR g.last_task_completed IS NULL
RETURN g.label, g.declared_at, g.last_task_completed
```

## 8.5 The Signal Filter

Not every behavioral event is worth processing into the personality graph. The Signal Filter assigns a weight to every event before it influences the graph.

| Signal type | Weight multiplier | Rationale |
|---|---|---|
| Repeated behavior (5+ times) | 3.0× | Patterns are more informative than single events |
| Completed task with quality note | 2.5× | Intentional completion with reflection |
| Emotional spike (mood > 8 or < 3) | 2.0× | High emotional charge creates stronger memory traces |
| Long-form journal entry | 1.8× | Deep reflection is high-signal |
| Task deferral (1st) | 0.3× | One deferral could be anything |
| Task deferral (3rd+) | 2.5× | Pattern of avoidance is high-signal |
| Casual Telegram message | 0.5× | Low intentionality |
| Supermemory save | 1.0× | Intentional save, but not yet processed |
| Supermemory save (with reflection tag) | 1.8× | User annotated why they saved it |

## 8.6 The Nightly Snapshot Packager

At 3:00 AM, after the vault crawl and personality graph update are complete, a Celery task packages the Personality Snapshot and pushes it to all devices via Syncthing.

```python
# Snapshot package contents (~15-30 MB compressed)
snapshot = {
    "generated_at": datetime.utcnow().isoformat(),
    "user_id": user_id,
    
    # Top 200 personality graph nodes (interests, goals, patterns)
    "personality_nodes": neo4j_export_top_nodes(limit=200),
    
    # 7-day forward schedule
    "schedule_7day": engine3_get_schedule(days=7),
    
    # Today's recommendations (books, articles, blogs)
    "recommendations": engine3_get_recommendations(limit=20),
    
    # Latest insights from Reflection Engine
    "insights": reflection_engine_latest(limit=10),
    
    # Behavioral summary (30-day stats)
    "behavioral_summary": {
        "avg_mood": ...,
        "avg_energy": ...,
        "tasks_completed_30d": ...,
        "top_3_topics": [...],
        "habit_streaks": {...},
        "goal_progress": {...}
    }
}

# Also export Qdrant vector index snapshot for offline search
qdrant_export_snapshot(collection="behavioral_logs", path="/vault/snapshots/")

# Compress and write to vault (Syncthing picks it up)
with gzip.open('/vault/snapshots/latest.json.gz', 'wb') as f:
    f.write(json.dumps(snapshot).encode())
```

---

# 9. Engine 3 — The Scheduling & Recommendation Engine

Engine 3 is the output layer. It takes what Engine 2 knows about you and translates it into actionable daily structure.

## 9.1 Responsibilities

- Receive tasks from the Master System via Redis queue
- Decompose complex goals into concrete subtasks (via Ollama Llama 3.1 8B)
- Score every subtask on four axes (goal alignment, urgency, energy required, current state)
- Route subtasks to the appropriate time block type
- Write scheduled blocks to Google Calendar via Google Calendar API
- Update Notion task properties with priority scores and scheduled times
- Generate daily reading recommendations aligned to active goals
- Draft LinkedIn posts from daily logs and behavioral patterns
- Send proactive pokes via Telegram and PWA push notifications
- Detect and respond to schedule deviations in real-time

## 9.2 The Recommendation Engine

The recommendation engine runs as a nightly Celery task. It queries Neo4j for the user's active interests and goal trajectories, then curates a personalized reading list.

```python
# Recommendation pipeline
async def generate_daily_recommendations(user_id: str) -> list[Recommendation]:
    
    # Step 1: Get top active interests from Neo4j
    interests = neo4j.run("""
        MATCH (i:Interest {user_id: $user_id})
        WHERE i.recency > 5 AND i.intensity > 6
        RETURN i.label, i.intensity, i.category
        ORDER BY i.intensity * i.recency DESC
        LIMIT 10
    """, user_id=user_id)
    
    # Step 2: Get active goals
    goals = neo4j.run("""
        MATCH (g:Goal {user_id: $user_id, active: true, stale: false})
        RETURN g.label, g.horizon, g.progress_score
    """, user_id=user_id)
    
    # Step 3: Build recommendation prompt for Llama 3.1 8B
    prompt = f"""
    User's active interests: {interests}
    User's active goals: {goals}
    User's behavioral patterns: {patterns}
    
    Generate 5 book recommendations, 5 article/blog topics, and 3 podcast episode topics
    that would maximally serve this person's growth at this specific moment.
    For each recommendation, explain in one sentence why it's relevant to their current state.
    Return as JSON array with fields: type, title, author, relevance_reason, category.
    """
    
    recs = await ollama_generate(prompt, model="llama3.1:8b", format="json")
    return parse_recommendations(recs)
```

## 9.3 LinkedIn Content Engine

The content engine generates LinkedIn drafts from the user's own ideas, insights, and behavioral data. The user is never starting from a blank page.

```python
# LinkedIn draft generation pipeline
async def generate_linkedin_draft(user_id: str) -> ContentDraft:
    
    # Pull last 7 days of Obsidian logs
    recent_logs = obsidian_read_range(user_id, days=7)
    
    # Pull recent AI chat topics from the AI Gateway
    recent_chats = db.query("""
        SELECT topic_tags, summary FROM ai_conversations
        WHERE user_id = $1 AND created_at > NOW() - INTERVAL '7 days'
    """, user_id)
    
    # Pull recent insights from Engine 2
    recent_insights = db.query("""
        SELECT content FROM personality_insights
        WHERE user_id = $1 AND created_at > NOW() - INTERVAL '3 days'
    """, user_id)
    
    # Find the most compelling thread
    prompt = f"""
    Here are this person's activities, insights, and thoughts from the last 7 days:
    {recent_logs}
    {recent_chats}
    {recent_insights}
    
    Identify the single most compelling insight or narrative thread that could become
    a LinkedIn post. Draft the post in a personal, authentic, non-corporate voice.
    The post should feel like the person is sharing a genuine realization, not marketing.
    Include a specific personal example. No bullet points. No corporate language.
    Target: 150-250 words. Return the draft only.
    """
    
    draft = await ollama_generate(prompt, model="llama3.1:8b")
    
    # Save to Notion Content Queue DB with status: Draft
    notion_create_content_item(user_id, draft, platform="LinkedIn")
    
    return ContentDraft(content=draft, status="Draft", requires_approval=True)
```

---

# 10. The Master System — Task Intelligence

The Master System is the execution core of Engine 3. Every task that enters Locus passes through five stages.

## 10.1 Stage 1: Intake

A task enters from any source. The Master System receives it via the Redis `engine3-queue`, normalizes it, and assigns it a standard schema.

```python
class Task(BaseModel):
    task_id: str                    # UUID
    user_id: str                    # User isolation
    title: str                      # The task as the user wrote it
    source: TaskSource              # notion | pwa | telegram | graphrag_poke
    intent: TaskIntent              # create | complete | defer | recurring
    goal_link: str | None           # Links to Goals table
    project_link: str | None        # Links to Projects table
    deadline: date | None           # Optional hard deadline
    deferral_count: int = 0         # Auto-incremented on each deferral
    priority_score: float | None    # Assigned in Stage 3
    scheduled_block: datetime | None # Assigned in Stage 4
    created_at: datetime
    updated_at: datetime
```

## 10.2 Stage 2: Decomposition

Complex goals are decomposed into concrete, actionable subtasks. Simple tasks skip this stage.

```python
async def decompose_task(task: Task) -> list[Subtask]:
    
    # Simple tasks skip decomposition
    if task.estimated_minutes and task.estimated_minutes < 60:
        return [Subtask.from_task(task)]
    
    prompt = f"""
    Break down this task into concrete, actionable subtasks:
    Task: "{task.title}"
    Goal context: {task.goal_context}
    
    Rules:
    - Each subtask must be completable in one sitting (< 90 min)
    - Each subtask must have a clear definition of done
    - Identify dependencies between subtasks
    - Estimate time for each subtask in minutes
    - Identify whether each subtask requires deep focus, creative energy, or is administrative
    
    Return JSON array with fields: title, estimated_minutes, 
    depends_on (list of subtask indices), energy_type (deep|creative|shallow).
    """
    
    subtasks_json = await ollama_generate(prompt, model="llama3.1:8b", format="json")
    return parse_subtasks(subtasks_json, parent_task_id=task.task_id)
```

## 10.3 Stage 3: Priority Scoring

Every subtask is scored on four axes. The scores are fed by Engine 2's personality data.

```python
def compute_priority_score(subtask: Subtask, user_state: UserState) -> float:
    
    # Axis 1: Goal alignment (0-10)
    # How strongly does this subtask serve an active goal?
    goal_intensity = neo4j.get_goal_intensity(subtask.goal_link, subtask.user_id)
    goal_alignment = goal_intensity  # 0-10
    
    # Axis 2: Urgency (0-10)
    # Based on deadline proximity. Non-linear: exponential increase as deadline approaches.
    if subtask.deadline:
        days_remaining = (subtask.deadline - date.today()).days
        urgency = max(0, 10 - (days_remaining / 3))  # 10 at 0 days, 0 at 30 days
    else:
        urgency = 3.0  # Default for undated tasks
    
    # Axis 3: Energy match (0-10)
    # How well does the required energy type match the user's current/scheduled energy?
    energy_match = compute_energy_match(
        required=subtask.energy_type,
        user_pattern=user_state.energy_pattern,  # from Engine 2
        scheduled_time=subtask.target_slot
    )
    
    # Axis 4: Behavioral momentum (0-10)
    # Is the user currently in a streak for this category? Momentum amplifies.
    momentum = neo4j.get_category_momentum(subtask.category, subtask.user_id)
    
    # Weighted composite score
    priority = (
        goal_alignment * 0.35 +
        urgency * 0.25 +
        energy_match * 0.25 +
        momentum * 0.15
    )
    
    return round(priority, 2)
```

## 10.4 Stage 4: Time Block Routing

Subtasks are assigned to time block types based on their score profile and the user's energy model.

| Time block type | When scheduled | What goes here |
|---|---|---|
| Deep work | Peak energy hours (from behavioral data) | High energy required + high goal alignment |
| Creative | Mid-morning or after rest | Creative energy type + filmmaking/writing/design |
| Shallow | Low energy hours | Administrative, quick, low cognitive load |
| Review | End of day | Reflection, planning, email, checking |

```python
def route_to_time_block(subtask: Subtask, user_energy_model: EnergyModel) -> TimeBlock:
    
    # Get user's personal peak hours from behavioral data
    # e.g., "This user completes deep work tasks 2.3× faster 9-11 AM vs 3-5 PM"
    peak_deep_hours = user_energy_model.peak_deep_work_hours
    peak_creative_hours = user_energy_model.peak_creative_hours
    
    if subtask.energy_type == 'deep' and subtask.priority_score > 7.0:
        target_hours = peak_deep_hours
        block_type = 'deep_work'
    elif subtask.energy_type == 'creative':
        target_hours = peak_creative_hours
        block_type = 'creative'
    elif subtask.priority_score < 4.0 or subtask.energy_type == 'shallow':
        target_hours = user_energy_model.low_energy_hours
        block_type = 'shallow'
    else:
        target_hours = user_energy_model.mid_energy_hours
        block_type = 'deep_work'
    
    # Find the next available slot in Google Calendar
    slot = google_calendar.find_next_available_slot(
        user_id=subtask.user_id,
        preferred_hours=target_hours,
        duration_minutes=subtask.estimated_minutes,
        lookahead_days=7
    )
    
    return TimeBlock(
        subtask_id=subtask.id,
        block_type=block_type,
        start_time=slot.start,
        end_time=slot.end
    )
```

## 10.5 Stage 5: Calendar Write + Feedback Loop

```python
async def write_to_calendar_and_notion(subtask: Subtask, block: TimeBlock):
    
    # Write to Google Calendar
    google_calendar.create_event(
        user_id=subtask.user_id,
        title=f"[Locus] {subtask.title}",
        start=block.start_time,
        end=block.end_time,
        description=f"Goal: {subtask.goal_link}\nPriority: {subtask.priority_score}/10",
        color_id=BLOCK_TYPE_COLORS[block.block_type]
    )
    
    # Update Notion task with schedule and priority
    notion.update_task(
        task_id=subtask.notion_id,
        priority_score=subtask.priority_score,
        scheduled_block=block.start_time,
        engine_comment=subtask.engine_annotations
    )
    
    # The feedback loop: when the calendar block ends, Engine 1 checks completion
    # Schedule a completion check job
    celery.apply_async(
        task='check_block_completion',
        args=[subtask.id, subtask.user_id],
        eta=block.end_time + timedelta(minutes=15)
    )

async def check_block_completion(subtask_id: str, user_id: str):
    # Was the Notion task marked done?
    # Was the Google Calendar event accepted/completed?
    # If not: increment deferral count, re-route, notify via Telegram
    # If yes: log completion event, update personality graph momentum
```

## 10.6 The Deferral Detector

The deferral detector is one of the most behaviorally insightful components in the system. Every task deferral increments a counter. At thresholds, the system responds:

| Deferral count | System action |
|---|---|
| 1 | No action. Single deferral is noise. |
| 2 | Soft flag. Re-evaluate priority score. |
| 3 | Write Engine 2 comment to Notion task. Alert via Telegram: "You've deferred this 3 times." |
| 5 | Deep analysis: cross-reference with mood scores on deferral days, energy levels, time of day. Generate insight. |
| 8+ | Flag as potential avoidance pattern in Neo4j. Suggest either: (a) break it down further, (b) schedule for a different time, (c) acknowledge the goal might not be active anymore. |

---

# 11. LLM Architecture & Hierarchy

## 11.1 The Full LLM Stack

```
TASK ARRIVES
    │
    ├─── Is user online AND Oracle VM reachable?
    │    │
    │    YES ─── Complexity check:
    │    │        Simple task (extraction, tagging, quick format)
    │    │        → Ollama phi3.5 on Oracle VM (~1-3s)
    │    │
    │    │        Complex task (insight gen, decomposition, drafting)
    │    │        → Ollama llama3.1:8b on Oracle VM (~5-15s)
    │    │
    │    │        Very long context OR API preferred
    │    │        → Gemini 2.0 Flash API (~2-5s)
    │    │
    │    │        Gemini rate limited?
    │    │        → Groq API with llama-3.1-8b-instant (~1-3s)
    │    │
    │    NO ──── User is offline → WebLLM Phi-3.5-mini in browser
    │             All tasks handled on device (~5-20s)
    │
    └─── Is it an embedding task?
         Online → nomic-embed-text on Oracle VM
         Offline → Transformers.js all-MiniLM in browser
```

## 11.2 Model Responsibilities Table

| Model | Location | Task types | Context window |
|---|---|---|---|
| Llama 3.1 8B (Ollama) | Oracle VM | Insight generation, LinkedIn drafts, complex decomposition, reflection writing | 128K tokens |
| Phi-3.5 (Ollama) | Oracle VM | Entity extraction, tagging, normalization, quick Q&A | 128K tokens |
| nomic-embed-text (Ollama) | Oracle VM | All embedding generation (online) | 8K tokens |
| Gemini 2.0 Flash | API | Very long context tasks, fallback reasoning | 1M tokens |
| Groq (llama-3.1-8b-instant) | API | Fast fallback, Whisper voice transcription | 131K tokens |
| Phi-3.5-mini (WebLLM) | Browser | All offline AI tasks | 128K tokens |
| all-MiniLM-L6-v2 (Transformers.js) | Browser | Offline embedding generation | 512 tokens |

## 11.3 Context Management

The LLM receives a carefully constructed context for every request. It never receives raw data dumps. Context is assembled by a `ContextBuilder` class:

```python
class ContextBuilder:
    def build(self, task_type: str, user_id: str) -> str:
        """Build a rich but token-efficient context for the LLM."""
        
        # Always included (small, high-density)
        user_summary = self.get_user_summary(user_id)  # ~200 tokens
        # e.g., "User is a 24yo filmmaker in India. Top goals: portfolio, career in film.
        #         Current mood: 7.2/10. Energy: 6.8/10. Top interests: filmmaking, tech, philosophy."
        
        # Task-specific context
        if task_type == 'task_decomposition':
            context = self.get_goal_context(user_id)   # ~300 tokens
        elif task_type == 'insight_generation':
            context = self.get_30day_behavioral_summary(user_id)  # ~500 tokens
        elif task_type == 'recommendation':
            context = self.get_interest_graph(user_id)  # ~400 tokens
        elif task_type == 'linkedin_draft':
            context = self.get_recent_logs(user_id, days=7)  # ~600 tokens
        
        return f"{user_summary}\n\n{context}"
```

## 11.4 Agentic Task Execution

Locus has autonomous agentic capabilities. When a user says "set up a Telegram bot that monitors my habit streak and pokes me if I miss 2 days," the system:

1. Parses the request as an agentic task
2. Llama 3.1 8B generates the implementation plan
3. Generates the code (Python bot script)
4. Saves it to the Oracle VM filesystem
5. Runs it in a Docker container
6. Registers the task in the Celery Beat scheduler
7. Confirms to the user via Telegram/PWA

```python
class AgenticExecutor:
    """Locus can build and deploy its own tools."""
    
    async def execute_agentic_task(self, request: str, user_id: str):
        
        # Classify the request
        classification = await self.classify_agentic_request(request)
        # e.g., {type: "automation", requires: ["code_generation", "deployment"]}
        
        if classification.type == "automation":
            # Generate code
            code = await ollama_generate(
                prompt=f"Write a Python script that: {request}",
                model="llama3.1:8b"
            )
            
            # Validate and test in sandbox
            result = self.run_in_sandbox(code)
            
            if result.success:
                # Deploy to Oracle VM
                self.deploy_as_celery_task(code, schedule=classification.schedule)
                
                # Notify user
                await telegram_send(user_id, f"Done. I've set up: {classification.description}")
            else:
                # Report failure with specific error
                await telegram_send(user_id, f"I ran into an issue: {result.error}. Let me try a different approach.")
```

---

# 12. Offline-First Architecture

## 12.1 The Four Offline Tiers

Locus operates in four modes depending on connectivity. The transition between modes is automatic and seamless.

### Tier 1: Fully Online
Oracle VM reachable. All engines at full power. Cloud LLMs available as fallbacks. Full GraphRAG, live Notion sync, Google Calendar writes.

### Tier 2: Mac/Desktop Offline
No internet but Mac available. Ollama + Mistral 7B runs locally on Mac (Apple Silicon handles 7B models excellently). Local Qdrant loaded from nightly `vector_index.bin`. Full Obsidian vault available. Task decomposition and scheduling work offline. Everything queues and syncs on reconnect.

### Tier 3: iPhone Offline (Most Common — Plane, Subway, Bad Signal)
No internet, iPhone only. WebLLM (Phi-3.5-mini) available if pre-downloaded. IndexedDB has full task/goal/project cache, 30 days of metrics, last personality snapshot, 7-day cached schedule, latest recommendations. The user can: log tasks (queued), dictate voice notes (saved locally, queued for transcription), mark tasks complete (queued), browse cached schedule and insights, ask questions about their cached data (via WebLLM), decompose new goals into tasks (via WebLLM).

### Tier 4: Complete Airplane Mode
Identical to Tier 3 on iPhone. On a Mac this is Tier 2. The nightly snapshot from the night before the flight contains all data needed. The snapshot is less than 8 hours old for any morning flight.

## 12.2 The Offline Write Queue

Every write operation that cannot reach the server is queued in IndexedDB and retried on reconnect.

```typescript
// Dexie.js schema for the offline queue
interface OfflineQueueItem {
  id: string;              // UUID
  created_at: number;      // Unix timestamp (device time)
  type: 'task_create' | 'task_complete' | 'task_defer' | 'log_entry' | 
        'voice_note' | 'goal_update' | 'habit_check';
  payload: object;         // The full data object
  sync_status: 'pending' | 'syncing' | 'synced' | 'failed';
  retry_count: number;     // Auto-incremented on failure
  last_retry: number | null;
}

// Sync service — runs when connectivity is detected
class SyncService {
  async flush(): Promise<void> {
    const pending = await db.offlineQueue
      .where('sync_status').equals('pending')
      .sortBy('created_at');  // Chronological order — critical for correctness
    
    for (const item of pending) {
      try {
        await this.syncItem(item);
        await db.offlineQueue.update(item.id, { sync_status: 'synced' });
      } catch (error) {
        await db.offlineQueue.update(item.id, {
          sync_status: 'failed',
          retry_count: item.retry_count + 1,
          last_retry: Date.now()
        });
      }
    }
    
    // After flush, request a fresh snapshot
    await this.requestSnapshotRefresh();
  }
}
```

## 12.3 WebLLM Integration

```typescript
// WebLLM setup in the PWA
import * as webllm from "@mlc-ai/web-llm";

class OfflineAI {
  private engine: webllm.MLCEngine | null = null;
  private modelId = "Phi-3.5-mini-instruct-q4f16_1-MLC";
  
  async download(onProgress: (progress: number) => void): Promise<void> {
    // Only called when user clicks "Download for offline AI" in Settings
    this.engine = await webllm.CreateMLCEngine(
      this.modelId,
      {
        initProgressCallback: (progress) => {
          onProgress(progress.progress * 100);
        }
      }
    );
    // Model is cached in OPFS (Origin Private File System)
    // Survives app restarts. Never re-downloads unless user clears browser data.
    localStorage.setItem('webllm_downloaded', 'true');
  }
  
  async isAvailable(): Promise<boolean> {
    return localStorage.getItem('webllm_downloaded') === 'true';
  }
  
  async generate(prompt: string, context: OfflineContext): Promise<string> {
    if (!this.engine) {
      await this.load(); // Load from OPFS cache (fast, ~2-3 seconds)
    }
    
    const systemPrompt = this.buildSystemPrompt(context);
    
    const response = await this.engine.chat.completions.create({
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: prompt }
      ],
      temperature: 0.7,
      max_tokens: 800
    });
    
    return response.choices[0].message.content;
  }
  
  private buildSystemPrompt(context: OfflineContext): string {
    // Inject the cached personality snapshot as context
    return `You are Locus, a personal AI assistant. Here is what you know about this user:
    
Active goals: ${JSON.stringify(context.snapshot.goals.slice(0, 5))}
Top interests: ${JSON.stringify(context.snapshot.top_interests.slice(0, 8))}
Current mood: ${context.snapshot.behavioral_summary.avg_mood}/10
Energy level: ${context.snapshot.behavioral_summary.avg_energy}/10
Recent patterns: ${JSON.stringify(context.snapshot.insights.slice(0, 3))}

Answer based only on this data. Do not make up information you don't have.`;
  }
}
```

## 12.4 Service Worker Configuration

```javascript
// sw.js — Service Worker for offline PWA
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';

// Precache all app shell assets (JS, CSS, HTML)
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// App shell — always serve from cache first
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new CacheFirst({ cacheName: 'pages-cache' })
);

// API calls — network first, fall back to cache
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 5,
    plugins: [{ cacheWillUpdate: async ({ response }) => 
      response.status === 200 ? response : null 
    }]
  })
);

// Static assets — cache first
registerRoute(
  ({ request }) => ['style', 'script', 'image'].includes(request.destination),
  new StaleWhileRevalidate({ cacheName: 'assets-cache' })
);

// Background sync — flush offline queue when connection returns
self.addEventListener('sync', (event) => {
  if (event.tag === 'offline-queue-flush') {
    event.waitUntil(flushOfflineQueue());
  }
});
```

---

# 13. Database Schemas — Complete DDL

## 13.1 PostgreSQL — Full Schema

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               TEXT UNIQUE NOT NULL,
    display_name        TEXT NOT NULL,
    timezone            TEXT NOT NULL DEFAULT 'UTC',
    
    -- Genesis interview state
    genesis_completed   BOOLEAN DEFAULT FALSE,
    genesis_data        JSONB,                    -- Raw genesis interview answers
    
    -- OAuth tokens (encrypted at rest)
    google_access_token         TEXT,
    google_refresh_token        TEXT,
    google_token_expiry         TIMESTAMPTZ,
    notion_access_token         TEXT,
    telegram_chat_id            TEXT,
    
    -- Preferences
    preferences         JSONB DEFAULT '{}',       -- UI preferences, notification settings
    
    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    last_active         TIMESTAMPTZ,
    is_active           BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- GOALS
-- ============================================================
CREATE TABLE goals (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    horizon             TEXT CHECK (horizon IN ('week', 'month', 'quarter', 'year', 'lifetime')),
    progress_score      FLOAT DEFAULT 0.0 CHECK (progress_score BETWEEN 0 AND 1),
    
    -- Graph node reference
    neo4j_node_id       TEXT,                     -- ID of the corresponding Neo4j Goal node
    
    -- Notion reference
    notion_page_id      TEXT,
    
    -- State
    is_active           BOOLEAN DEFAULT TRUE,
    is_stale            BOOLEAN DEFAULT FALSE,
    stale_since         TIMESTAMPTZ,
    
    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    last_task_completed TIMESTAMPTZ,
    deadline            DATE
);

CREATE INDEX idx_goals_user_id ON goals(user_id);
CREATE INDEX idx_goals_active ON goals(user_id, is_active);

-- ============================================================
-- TASKS
-- ============================================================
CREATE TABLE tasks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    
    -- Hierarchy
    parent_task_id      UUID REFERENCES tasks(id),  -- For subtasks
    goal_id             UUID REFERENCES goals(id),
    project_id          UUID REFERENCES projects(id),
    
    -- Source tracking
    source              TEXT CHECK (source IN ('pwa', 'notion', 'telegram', 'graphrag', 'manual')),
    notion_page_id      TEXT,
    
    -- Status
    status              TEXT DEFAULT 'pending' 
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'deferred', 'cancelled')),
    
    -- Engine 3 outputs
    priority_score      FLOAT,                    -- 0-10 composite score from Stage 3
    energy_type         TEXT CHECK (energy_type IN ('deep', 'creative', 'shallow', 'review')),
    estimated_minutes   INTEGER,
    scheduled_at        TIMESTAMPTZ,              -- Calendar block start time
    
    -- Behavioral tracking
    deferral_count      INTEGER DEFAULT 0,
    deferral_flag       TEXT,                     -- Engine 2 annotation on deferral pattern
    
    -- Completion
    completed_at        TIMESTAMPTZ,
    completion_duration_minutes INTEGER,          -- Actual vs estimated (feeds behavioral model)
    
    -- AI annotations
    engine_annotations  TEXT,                     -- Latest Engine 2 comment
    
    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    deadline            TIMESTAMPTZ
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(user_id, status);
CREATE INDEX idx_tasks_goal_id ON tasks(goal_id);
CREATE INDEX idx_tasks_scheduled ON tasks(user_id, scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_tasks_deferral ON tasks(user_id, deferral_count) WHERE deferral_count >= 3;

-- ============================================================
-- PROJECTS
-- ============================================================
CREATE TABLE projects (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    goal_id             UUID REFERENCES goals(id),
    status              TEXT DEFAULT 'active' 
                        CHECK (status IN ('planning', 'active', 'on_hold', 'completed')),
    notion_page_id      TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- BEHAVIORAL EVENTS — The core logging table
-- ============================================================
CREATE TABLE behavioral_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Source and classification
    source              TEXT NOT NULL,            -- pwa | notion | telegram | obsidian | supermemory | ai_gateway | calendar
    event_type          TEXT NOT NULL,            -- task_create | task_complete | task_defer | note_write | voice_log | chat | bookmark_save
    intent              TEXT,                     -- create | complete | defer | reflect | consume | query
    
    -- Content
    raw_content         TEXT,                     -- Original input before normalization
    normalized_content  TEXT,                     -- After normalization
    summary             TEXT,                     -- Phi3.5-generated one-line summary
    
    -- Extracted signals
    topic_tags          TEXT[],                   -- ['filmmaking', 'portfolio', 'editing']
    mood_indicator      FLOAT,                    -- -1 to 1 (negative to positive)
    energy_required     INTEGER,                  -- 1-10
    goal_tags           TEXT[],                   -- Which goals this event relates to
    
    -- Signal weight
    signal_weight       FLOAT DEFAULT 1.0,        -- From Signal Filter (0.3 to 3.0)
    
    -- References
    task_id             UUID REFERENCES tasks(id),
    goal_id             UUID REFERENCES goals(id),
    
    -- Embedding (pgvector) — for small-scale semantic search
    embedding           VECTOR(768),
    
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL,     -- Device timestamp
    received_at         TIMESTAMPTZ DEFAULT NOW(), -- Server receipt timestamp
    obsidian_path       TEXT,                     -- Path to the Obsidian .md file this was written to
    processed_by_e2     BOOLEAN DEFAULT FALSE     -- Has Engine 2 processed this event?
);

CREATE INDEX idx_behavioral_events_user ON behavioral_events(user_id);
CREATE INDEX idx_behavioral_events_type ON behavioral_events(user_id, event_type);
CREATE INDEX idx_behavioral_events_created ON behavioral_events(user_id, created_at DESC);
CREATE INDEX idx_behavioral_events_e2 ON behavioral_events(processed_by_e2) WHERE processed_by_e2 = FALSE;
CREATE INDEX idx_behavioral_events_embedding ON behavioral_events USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- DAILY METRICS — Aggregated daily snapshot
-- ============================================================
CREATE TABLE daily_metrics (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    
    -- Scores (all computed nightly by Engine 2)
    mood_score          FLOAT,                    -- 1-10, inferred from behavioral events
    energy_score        FLOAT,                    -- 1-10, inferred from task completion timing
    focus_score         FLOAT,                    -- 1-10, ratio of deep work to total time
    productivity_score  FLOAT,                    -- 1-10, task completion rate
    
    -- Counts
    tasks_completed     INTEGER DEFAULT 0,
    tasks_deferred      INTEGER DEFAULT 0,
    tasks_created       INTEGER DEFAULT 0,
    deep_work_minutes   INTEGER DEFAULT 0,
    creative_minutes    INTEGER DEFAULT 0,
    
    -- Dominant activity
    dominant_topic      TEXT,                     -- Most frequent topic tag today
    dominant_category   TEXT,                     -- Creative | Career | Health | etc.
    
    -- Obsidian link
    obsidian_log_path   TEXT,
    
    UNIQUE(user_id, date)
);

CREATE INDEX idx_daily_metrics_user_date ON daily_metrics(user_id, date DESC);

-- ============================================================
-- HABITS
-- ============================================================
CREATE TABLE habits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    frequency           TEXT CHECK (frequency IN ('daily', 'weekdays', 'weekly', 'custom')),
    custom_days         INTEGER[],                -- Day of week (0=Mon) for custom frequency
    goal_id             UUID REFERENCES goals(id),
    current_streak      INTEGER DEFAULT 0,
    longest_streak      INTEGER DEFAULT 0,
    last_completed      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    is_active           BOOLEAN DEFAULT TRUE
);

CREATE TABLE habit_completions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id            UUID NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL,
    completed_at        TIMESTAMPTZ DEFAULT NOW(),
    notes               TEXT
);

-- ============================================================
-- PERSONALITY INSIGHTS — Engine 2 outputs
-- ============================================================
CREATE TABLE personality_insights (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    insight_type        TEXT NOT NULL,            -- avoidance | contradiction | spike | loop | growth
    title               TEXT NOT NULL,
    content             TEXT NOT NULL,            -- Full insight text for display
    confidence          FLOAT NOT NULL,           -- 0-1
    supporting_events   UUID[],                   -- behavioral_event IDs that support this
    action_suggestion   TEXT,                     -- What the system recommends doing about it
    read_by_user        BOOLEAN DEFAULT FALSE,
    dismissed           BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AI CONVERSATIONS — AI Gateway logs
-- ============================================================
CREATE TABLE ai_conversations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_used          TEXT NOT NULL,            -- llama3.1:8b | gemini-2.0-flash | phi3.5 | etc.
    model_source        TEXT NOT NULL,            -- ollama | gemini | groq | webllm
    
    -- Conversation content
    messages            JSONB NOT NULL,           -- Full message array [{role, content}]
    topic_tags          TEXT[],                   -- Extracted from conversation content
    summary             TEXT,                     -- One-line summary of what was discussed
    
    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    obsidian_path       TEXT,                     -- Written to Chats/YYYY-MM-DD.md
    token_count         INTEGER
);

-- ============================================================
-- CONTENT QUEUE — LinkedIn drafts and other content
-- ============================================================
CREATE TABLE content_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform            TEXT CHECK (platform IN ('linkedin', 'twitter', 'newsletter', 'blog')),
    status              TEXT DEFAULT 'draft' 
                        CHECK (status IN ('draft', 'pending_approval', 'approved', 'published', 'rejected')),
    content             TEXT NOT NULL,
    title               TEXT,
    
    -- Provenance — what source data was used
    source_event_ids    UUID[],
    source_insight_ids  UUID[],
    source_obsidian_paths TEXT[],
    
    -- Feedback loop
    approved_at         TIMESTAMPTZ,
    published_at        TIMESTAMPTZ,
    rejection_reason    TEXT,
    
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    notion_page_id      TEXT
);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================
CREATE TABLE recommendations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rec_type            TEXT CHECK (rec_type IN ('book', 'article', 'podcast', 'video', 'course', 'blog')),
    title               TEXT NOT NULL,
    author              TEXT,
    url                 TEXT,
    relevance_reason    TEXT NOT NULL,            -- Why the system recommends this
    interest_tags       TEXT[],                   -- Which interests drove this recommendation
    goal_tags           TEXT[],
    
    -- Engagement tracking
    status              TEXT DEFAULT 'recommended' 
                        CHECK (status IN ('recommended', 'saved', 'reading', 'completed', 'dismissed')),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    user_rating         INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- OFFLINE SYNC EVENTS — Server-side record of synced items
-- ============================================================
CREATE TABLE sync_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id           TEXT NOT NULL,            -- Identifies which device sent the sync
    client_event_id     TEXT NOT NULL,            -- UUID from the client's offline queue
    event_type          TEXT NOT NULL,
    payload             JSONB NOT NULL,
    synced_at           TIMESTAMPTZ DEFAULT NOW(),
    conflict_detected   BOOLEAN DEFAULT FALSE,
    conflict_resolution TEXT,                     -- How the conflict was resolved
    
    UNIQUE(user_id, client_event_id)              -- Idempotent sync (duplicate events ignored)
);

-- ============================================================
-- PERSONALITY SNAPSHOTS — Nightly bundles for offline use
-- ============================================================
CREATE TABLE personality_snapshots (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generated_at        TIMESTAMPTZ DEFAULT NOW(),
    snapshot_data       JSONB NOT NULL,           -- Full snapshot JSON
    version             INTEGER DEFAULT 1,
    
    -- Keep only last 7 snapshots per user
    UNIQUE(user_id, generated_at::DATE)
);
```

---

# 14. Neo4j Graph Schema

## 14.1 Node Types

```cypher
// All nodes include user_id for multi-user isolation
// All queries must include WHERE n.user_id = $user_id

// User node (root of the graph)
(:User {id, email, display_name, created_at})

// Interest nodes
(:Interest {
  id, user_id, label, category,
  intensity,              // 0-10 current strength
  recency,                // 0-10 decay-adjusted recency
  consistency,            // 0-10 consistency over 90 days
  emotional_weight,       // 0-10
  emotional_valence,      // -1 to 1
  declared_priority,      // 0-10 what user says
  behavioral_priority,    // 0-10 what actions show
  action_gap,             // declared - behavioral
  first_seen, last_active,
  peak_times,             // string[] e.g., ["09:00-11:00"]
  connected_to,           // string[] semantic clusters
  updated_at
})

// Goal nodes
(:Goal {
  id, user_id, label, horizon,
  progress_score,         // 0-1
  active, stale,
  declared_at, deadline,
  last_task_completed
})

// Behavioral Pattern nodes
(:Pattern {
  id, user_id, label,
  pattern_type,           // avoidance | loop | contradiction | spike | habit
  confidence,             // 0-1
  occurrences,
  first_detected, last_detected,
  trigger_condition,
  affected_categories,
  intervention_suggested
})

// Context nodes (situational factors)
(:Context {
  id, user_id, label,
  context_type            // mood_state | time_of_day | location | energy_level
})

// Topic nodes (emerging from behavioral data)
(:Topic {
  id, user_id, label,
  domain,                 // Science | Art | Tech | Philosophy | etc.
  times_encountered,
  first_seen, last_seen
})

// Skill nodes
(:Skill {
  id, user_id, label,
  current_level,          // 1-10
  target_level,           // 1-10 (from goals)
  practice_frequency,     // events per week
  growth_rate             // level/week estimated
})
```

## 14.2 Relationship Types

```cypher
// User → everything
(:User)-[:HAS_INTEREST]->(:Interest)
(:User)-[:HAS_GOAL]->(:Goal)
(:User)-[:HAS_PATTERN]->(:Pattern)
(:User)-[:HAS_SKILL]->(:Skill)

// Goal relationships
(:Interest)-[:SERVES]->(:Goal)         // Interest contributes to this goal
(:Skill)-[:REQUIRED_BY]->(:Goal)       // Skill needed to achieve this goal
(:Goal)-[:REINFORCES]->(:Goal)         // Achieving one strengthens another
(:Goal)-[:BLOCKS]->(:Goal)            // Conflict between goals

// Pattern relationships
(:Pattern)-[:SUPPRESSES]->(:Interest)  // This pattern prevents engagement
(:Pattern)-[:TRIGGERED_BY]->(:Context) // Pattern appears in this context
(:Pattern)-[:AFFECTS]->(:Goal)         // Pattern impacts goal progress

// Interest relationships
(:Interest)-[:COMPETES_WITH]->(:Interest) // Compete for time/energy
(:Interest)-[:AMPLIFIES]->(:Interest)     // Engagement in one boosts another
(:Interest)-[:EVOLVED_FROM]->(:Interest)  // Historical interest trajectory

// Topic relationships
(:Topic)-[:FEEDS]->(:Interest)         // This topic content fuels this interest
(:Topic)-[:RELATES_TO]->(:Topic)       // Semantic topic proximity

// Skill relationships
(:Skill)-[:ENABLES]->(:Skill)          // Learning one enables another
(:Interest)-[:REQUIRES]->(:Skill)      // Pursuing this interest requires this skill
```

## 14.3 Key Cypher Queries

```cypher
// Engine 3 priority scoring: get all active interest intensities for a user
MATCH (u:User {id: $user_id})-[:HAS_INTEREST]->(i:Interest)
WHERE i.active = true AND i.recency > 3
RETURN i.label, i.intensity, i.behavioral_priority, i.action_gap, i.peak_times
ORDER BY i.intensity * i.recency DESC

// Reflection engine: find high-action-gap interests (declared vs behavioral contradiction)
MATCH (u:User {id: $user_id})-[:HAS_INTEREST]->(i:Interest)
WHERE i.action_gap > 2.5
RETURN i.label, i.declared_priority, i.behavioral_priority, i.action_gap
ORDER BY i.action_gap DESC

// Find interests that would serve multiple active goals simultaneously
MATCH (i:Interest {user_id: $user_id})-[:SERVES]->(g:Goal {active: true, stale: false})
WITH i, count(g) as goal_count, collect(g.label) as goals
WHERE goal_count >= 2
RETURN i.label, goal_count, goals
ORDER BY goal_count DESC

// Find patterns that are actively suppressing high-priority interests
MATCH (p:Pattern {user_id: $user_id})-[:SUPPRESSES]->(i:Interest)
WHERE i.intensity > 6 AND p.confidence > 0.7
RETURN p.label, p.intervention_suggested, i.label, i.intensity, p.confidence

// Interest evolution: how has an interest changed over the last 90 days
MATCH (u:User {id: $user_id})-[:HAS_INTEREST]->(i:Interest {label: $interest_label})
RETURN i.intensity as current_intensity,
       i.consistency as consistency,
       i.first_seen as first_seen,
       i.last_active as last_active
```

---

# 15. Qdrant Vector Collections

## 15.1 Collections

```python
# Collection: behavioral_logs
# Purpose: Semantic search over all behavioral events
# Vectors: 768-dim from nomic-embed-text (online) / 384-dim all-MiniLM (offline, normalized)
behavioral_logs_config = {
    "collection_name": "behavioral_logs",
    "vectors_config": {
        "content": VectorParams(size=768, distance=Distance.COSINE)
    },
    "payload_schema": {
        "user_id": "keyword",          # CRITICAL: always filter by user_id
        "event_type": "keyword",
        "source": "keyword",
        "topic_tags": "keyword",
        "mood_indicator": "float",
        "created_at": "datetime",
        "signal_weight": "float",
        "obsidian_path": "keyword"
    }
}

# Collection: obsidian_notes
# Purpose: Semantic search over the full Obsidian vault
obsidian_notes_config = {
    "collection_name": "obsidian_notes",
    "vectors_config": {
        "content": VectorParams(size=768, distance=Distance.COSINE)
    },
    "payload_schema": {
        "user_id": "keyword",
        "file_path": "keyword",
        "zone": "keyword",             # os_managed | personal
        "date": "datetime",
        "tags": "keyword",
        "mood_score": "float"
    }
}

# Collection: recommendations
# Purpose: Semantic search over recommended content to avoid duplicates
recommendations_config = {
    "collection_name": "recommendations",
    "vectors_config": {
        "title": VectorParams(size=768, distance=Distance.COSINE)
    },
    "payload_schema": {
        "user_id": "keyword",
        "rec_type": "keyword",
        "created_at": "datetime"
    }
}
```

## 15.2 Query Examples

```python
# Semantic search: "find all content about creative blocks from the last 30 days"
query_embedding = ollama_embed("creative blocks and resistance to creative work")

results = qdrant.search(
    collection_name="behavioral_logs",
    query_vector=("content", query_embedding),
    query_filter=Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="created_at", range=DatetimeRange(
                gte=datetime.now() - timedelta(days=30)
            ))
        ]
    ),
    limit=20,
    with_payload=True
)

# Find content semantically similar to current interest spike
# (used for recommendation deduplication)
results = qdrant.search(
    collection_name="recommendations",
    query_vector=("title", new_rec_embedding),
    query_filter=Filter(must=[
        FieldCondition(key="user_id", match=MatchValue(value=user_id))
    ]),
    limit=5,
    score_threshold=0.85  # Don't recommend if > 85% similar to something already recommended
)
```

---

# 16. Redis Key Patterns & Queue Design

## 16.1 Queue Names (Celery)

```
engine1        - Engine 1 (Logging) task queue
engine2        - Engine 2 (Personality) task queue  
engine3        - Engine 3 (Scheduling) task queue
high_priority  - Urgent tasks that jump queues (e.g., real-time voice transcription)
```

## 16.2 Key Naming Conventions

```
# Notion polling state (what was the last_edited_time we saw per page)
notion:last_edit:{user_id}:{notion_page_id}  →  ISO timestamp string

# File write locks (prevent concurrent Obsidian writes)
lock:obsidian:{user_id}:{file_path_hash}  →  "1" (with 30s TTL)

# API rate limit counters
ratelimit:gemini:{user_id}  →  integer (requests in current minute, TTL=60s)
ratelimit:groq:{user_id}    →  integer

# Sync status per device
sync:device:{user_id}:{device_id}:last_sync  →  ISO timestamp

# Temporary task decomposition state (in-flight Llama requests)
inflight:decompose:{task_id}  →  JSON status object (TTL=300s)

# Session tokens (JWT refresh)
session:{user_id}:{session_id}  →  "valid" (TTL=30 days)

# Nightly snapshot generation lock (prevent duplicate runs)
lock:snapshot:{user_id}  →  "1" (TTL=3600s)

# Telegram conversation state (for multi-turn bot interactions)
telegram:state:{user_id}:{chat_id}  →  JSON conversation state (TTL=1800s)
```

---

# 17. IndexedDB Schema (Offline Layer)

## 17.1 Dexie.js Database Definition

```typescript
import Dexie, { Table } from 'dexie';

class LocusDB extends Dexie {
  // Tables
  tasks!: Table<TaskCache>;
  goals!: Table<GoalCache>;
  habits!: Table<HabitCache>;
  daily_metrics!: Table<DailyMetricsCache>;
  personality_snapshot!: Table<PersonalitySnapshot>;
  offline_queue!: Table<OfflineQueueItem>;
  schedule_cache!: Table<ScheduleBlock>;
  recommendations_cache!: Table<RecommendationCache>;
  insights_cache!: Table<InsightCache>;
  
  constructor() {
    super('LocusDB');
    
    this.version(1).stores({
      tasks: '&id, user_id, status, goal_id, scheduled_at, updated_at',
      goals: '&id, user_id, is_active, horizon',
      habits: '&id, user_id, is_active, last_completed',
      daily_metrics: '&[user_id+date], user_id, date',
      personality_snapshot: '&id, user_id, generated_at',
      offline_queue: '++local_id, id, sync_status, type, created_at',
      schedule_cache: '&id, user_id, start_time, block_type',
      recommendations_cache: '&id, user_id, rec_type, status, created_at',
      insights_cache: '&id, user_id, insight_type, read_by_user, created_at'
    });
  }
}

// Types
interface OfflineQueueItem {
  local_id?: number;        // Auto-incremented primary key
  id: string;               // UUID (same as what server will use)
  created_at: number;       // Unix ms
  type: string;
  payload: object;
  sync_status: 'pending' | 'syncing' | 'synced' | 'failed';
  retry_count: number;
  last_retry: number | null;
  device_id: string;        // Identifies this device
}

interface PersonalitySnapshot {
  id: string;
  user_id: string;
  generated_at: string;
  personality_nodes: PersonalityNode[];
  schedule_7day: ScheduleBlock[];
  recommendations: RecommendationCache[];
  insights: InsightCache[];
  behavioral_summary: BehavioralSummary;
}

export const db = new LocusDB();
```

---

# 18. API Design — Complete Endpoint Reference

## 18.1 Authentication

Locus uses JWT (JSON Web Tokens) with refresh token rotation. All endpoints except `/auth/*` require a valid JWT in the Authorization header.

```
POST /auth/register          Create a new user account
POST /auth/login             Email + password login → {access_token, refresh_token}
POST /auth/refresh           Refresh expired access token
POST /auth/logout            Invalidate refresh token
POST /auth/google            Google OAuth callback
GET  /auth/me                Get current user profile
```

## 18.2 Tasks

```
GET    /api/tasks                    List tasks (filterable by status, goal, date)
POST   /api/tasks                    Create task (triggers Engine 3 pipeline)
GET    /api/tasks/{id}               Get single task with all properties
PATCH  /api/tasks/{id}               Update task (triggers re-scoring if title changes)
DELETE /api/tasks/{id}               Soft delete
POST   /api/tasks/{id}/complete      Mark complete (triggers feedback loop)
POST   /api/tasks/{id}/defer         Defer to next available slot (increments deferral_count)
GET    /api/tasks/{id}/subtasks      Get decomposed subtasks
POST   /api/tasks/{id}/decompose     Manually trigger LLM decomposition
```

## 18.3 Goals

```
GET    /api/goals                    List goals
POST   /api/goals                    Create goal (seeds Neo4j node)
GET    /api/goals/{id}               Get goal with linked tasks and progress
PATCH  /api/goals/{id}               Update goal
GET    /api/goals/{id}/insights      Get Engine 2 insights for this goal
POST   /api/goals/{id}/progress      Update progress (0-1 float)
```

## 18.4 Scheduling

```
GET    /api/schedule                 Get schedule (next 7 days by default)
GET    /api/schedule/today           Today's blocks
POST   /api/schedule/generate        Manually trigger Engine 3 full reschedule
PATCH  /api/schedule/{block_id}      Move a block (updates Google Calendar)
DELETE /api/schedule/{block_id}      Remove a block
```

## 18.5 Intelligence (Engine 2)

```
GET    /api/insights                 Get latest personality insights
POST   /api/insights/{id}/read       Mark insight as read
POST   /api/insights/{id}/dismiss    Dismiss (negative feedback to Engine 2)
GET    /api/personality              Get full personality summary
GET    /api/personality/graph        Get graph nodes for visualization
GET    /api/recommendations          Get today's recommendations
POST   /api/recommendations/{id}/save    Save recommendation for later
POST   /api/recommendations/{id}/complete  Mark as read/completed
POST   /api/recommendations/{id}/dismiss   Dismiss recommendation
```

## 18.6 AI Gateway

```
POST   /api/ai/chat                  Send message to AI Gateway (streams response)
GET    /api/ai/conversations         List conversation history
GET    /api/ai/conversations/{id}    Get full conversation
POST   /api/ai/voice                 Upload voice note (→ Groq Whisper → Engine 1)
```

## 18.7 Content

```
GET    /api/content                  Get content queue (LinkedIn drafts etc.)
POST   /api/content/generate         Manually trigger LinkedIn draft generation
POST   /api/content/{id}/approve     Approve draft (moves to approved status)
POST   /api/content/{id}/reject      Reject with reason (feedback to Engine 2)
PATCH  /api/content/{id}             Edit draft content
```

## 18.8 Sync (Offline Support)

```
POST   /api/sync/flush               Flush offline queue (batch endpoint)
                                     Accepts array of OfflineQueueItem objects
                                     Returns {processed, conflicts, errors}
GET    /api/sync/snapshot            Download latest personality snapshot
GET    /api/sync/status              Check if user has pending sync items server-side
```

## 18.9 Integrations

```
GET    /api/integrations/status      Status of all connected integrations
POST   /api/integrations/notion/sync Manual trigger Notion full sync
POST   /api/integrations/calendar/sync Manual trigger calendar sync
GET    /api/integrations/notion/databases  List available Notion databases
POST   /api/integrations/notion/connect/{db_id}  Connect a Notion database
```

## 18.10 System & Agentic

```
GET    /api/system/health            Health check (all services)
GET    /api/system/logs              Recent system logs (admin only)
POST   /api/agentic/execute          Execute an agentic task
                                     Body: {request: string, confirm: boolean}
                                     Returns: {plan: string, code?: string, status: string}
GET    /api/agentic/tasks            List running agentic tasks
DELETE /api/agentic/tasks/{id}       Cancel an agentic task
```

## 18.11 WebSocket Events

The PWA maintains a WebSocket connection to the server for real-time updates.

```typescript
// Events the server emits to the client
interface ServerEvent {
  type: 
    | 'insight_ready'          // New personality insight available
    | 'schedule_updated'       // Engine 3 updated the schedule
    | 'task_decomposed'        // Subtasks ready after decomposition
    | 'content_draft_ready'    // New LinkedIn draft generated
    | 'sync_complete'          // Offline queue flushed successfully
    | 'recommendation_ready'   // New recommendations available
    | 'poke'                   // Proactive notification from Engine 2
    | 'system_alert';          // System health alert
  payload: object;
  timestamp: string;
}
```

---

# 19. Frontend Architecture — PWA

## 19.1 Project Structure

```
/frontend
├── public/
│   ├── manifest.json          # PWA manifest (name, icons, theme color)
│   └── sw.js                  # Service Worker entry point (built by Workbox)
│
├── src/
│   ├── main.tsx               # React entry point
│   ├── App.tsx                # Root component + routing
│   │
│   ├── pages/                 # Top-level route pages
│   │   ├── Dashboard.tsx      # Home — today's schedule, metrics, pokes
│   │   ├── Tasks.tsx          # Task inbox (all tasks, filterable)
│   │   ├── Goals.tsx          # Goals with progress visualization
│   │   ├── Intelligence.tsx   # Insights, personality graph, reflections
│   │   ├── Schedule.tsx       # 7-day calendar view
│   │   ├── Content.tsx        # LinkedIn drafts queue
│   │   ├── Reads.tsx          # Recommendations
│   │   ├── Chat.tsx           # AI Gateway chat interface
│   │   ├── Habits.tsx         # Habit tracker
│   │   └── Settings.tsx       # Integrations, preferences, offline AI download
│   │
│   ├── components/            # Reusable UI components
│   │   ├── ui/                # Base design system components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── ...
│   │   │
│   │   ├── task/              # Task-specific components
│   │   │   ├── TaskCard.tsx
│   │   │   ├── TaskDecomposition.tsx
│   │   │   └── PriorityScore.tsx
│   │   │
│   │   ├── intelligence/      # Engine 2 UI components
│   │   │   ├── InsightCard.tsx
│   │   │   ├── PersonalityGraph.tsx   # D3.js/vis.js graph visualization
│   │   │   └── ReflectionCard.tsx
│   │   │
│   │   ├── schedule/          # Calendar components
│   │   │   ├── WeekView.tsx
│   │   │   ├── DayView.tsx
│   │   │   └── TimeBlock.tsx
│   │   │
│   │   └── layout/            # Layout components
│   │       ├── BottomNav.tsx  # Mobile navigation
│   │       ├── Sidebar.tsx    # Desktop navigation
│   │       ├── Header.tsx
│   │       └── OfflineBanner.tsx  # Shows when offline
│   │
│   ├── stores/                # Zustand state stores
│   │   ├── userStore.ts       # User profile, auth state
│   │   ├── offlineStore.ts    # Connectivity state, sync queue status
│   │   ├── snapshotStore.ts   # Loaded personality snapshot
│   │   └── uiStore.ts         # UI state (modal open, active page, etc.)
│   │
│   ├── hooks/                 # Custom React hooks
│   │   ├── useOffline.ts      # Detects offline state, manages queue
│   │   ├── useWebLLM.ts       # WebLLM initialization and generation
│   │   ├── useSync.ts         # Sync service
│   │   ├── useWebSocket.ts    # Real-time server events
│   │   └── useSnapshot.ts     # Load and query personality snapshot
│   │
│   ├── services/              # API and offline service layer
│   │   ├── api.ts             # All API calls (online mode)
│   │   ├── offline.ts         # Offline queue and IndexedDB operations
│   │   ├── webllm.ts          # WebLLM wrapper
│   │   ├── sync.ts            # Sync service (queue flush, snapshot download)
│   │   └── db.ts              # Dexie.js database instance
│   │
│   ├── lib/                   # Utilities
│   │   ├── formulas.ts        # CAPACITY, TASK_SCORE, and other pure JS formulas
│   │   ├── dates.ts           # Date utilities
│   │   └── analytics.ts       # Local analytics (no external tracking)
│   │
│   └── types/                 # TypeScript type definitions
│       ├── api.ts             # API response types
│       ├── db.ts              # IndexedDB types
│       └── models.ts          # Domain model types
│
├── vite.config.ts             # Vite configuration + PWA plugin (vite-plugin-pwa)
├── tailwind.config.ts         # Tailwind CSS configuration
└── tsconfig.json
```

## 19.2 Key Frontend Patterns

### Online/Offline Routing

Every user action goes through an action router that determines where to send it:

```typescript
class ActionRouter {
  async execute<T>(action: Action<T>): Promise<ActionResult<T>> {
    const isOnline = navigator.onLine;
    
    if (isOnline) {
      try {
        // Try server first
        const result = await api.execute(action);
        // Update local cache optimistically
        await db[action.table].put(result.data);
        return { source: 'server', data: result.data };
      } catch (error) {
        if (error instanceof NetworkError) {
          // Fall through to offline
        } else {
          throw error;  // Real error, propagate
        }
      }
    }
    
    // Offline: execute locally and queue
    const localResult = await this.executeLocally(action);
    await db.offline_queue.add({
      id: generateUUID(),
      type: action.type,
      payload: action.payload,
      sync_status: 'pending',
      created_at: Date.now(),
      retry_count: 0,
      last_retry: null,
      device_id: getDeviceId()
    });
    
    // Register background sync
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration) {
      const sw = await navigator.serviceWorker.ready;
      await sw.sync.register('offline-queue-flush');
    }
    
    return { source: 'local', data: localResult };
  }
}
```

### The Offline Intelligence Layer

When offline, AI requests are routed to WebLLM with the personality snapshot as context:

```typescript
async function getIntelligence(query: string): Promise<string> {
  const snapshot = await db.personality_snapshot
    .orderBy('generated_at')
    .last();
  
  if (navigator.onLine) {
    // Full server intelligence
    return await api.ai.query(query);
  } else if (await webllm.isAvailable()) {
    // Local WebLLM with cached context
    return await webllm.generate(query, {
      snapshot,
      context_type: 'offline_intelligence'
    });
  } else {
    // Pure JS fallback — formula-based answers
    return formulaEngine.answer(query, snapshot);
  }
}
```

## 19.3 The Genesis Interview (Onboarding)

The first time a user opens Locus after account creation, they go through the Genesis Interview — a deep, conversational onboarding experience that seeds the personality graph.

The Genesis Interview is not a form. It is a conversation. The AI Gateway (or WebLLM offline) conducts the interview. The questions are dynamic — the AI asks follow-up questions based on previous answers. The interview takes 15–30 minutes.

The interview covers:
1. Long-term life vision (3–5 year goals across all life domains)
2. Short-term goals (this quarter)
3. Core values (what matters most, with examples)
4. Behavioral self-assessment (energy patterns, avoidance tendencies, creative cycles)
5. Constraints (time, resources, obligations)
6. Growth edges (what you want to improve)
7. Anti-goals (things you explicitly do not want)

The output of the Genesis Interview is a structured JSON document that populates:
- Initial Neo4j Interest nodes (seeded from declared interests)
- Initial Neo4j Goal nodes
- Initial UserPreferences in PostgreSQL
- The `genesis_data` field on the users table

This is the starting point. Over the following weeks, inferred data progressively overrides declared data as the system learns from actual behavior.

---

# 20. All External Integrations

## 20.1 Google Calendar

```python
# Integration flow
class GoogleCalendarIntegration:
    
    def __init__(self, user: User):
        self.credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)
    
    async def find_free_slots(
        self, 
        date: date, 
        duration_minutes: int,
        preferred_hours: list[tuple[int,int]]  # e.g., [(9,11), (14,16)]
    ) -> list[datetime]:
        """Find available calendar slots on a given day."""
        
        # Get all events for the day
        events = self.service.events().list(
            calendarId='primary',
            timeMin=datetime.combine(date, time(0)).isoformat() + 'Z',
            timeMax=datetime.combine(date, time(23,59)).isoformat() + 'Z',
            singleEvents=True
        ).execute()
        
        busy_slots = [(e['start']['dateTime'], e['end']['dateTime']) for e in events['items']]
        
        # Find free slots in preferred hours that don't overlap with busy
        return find_free_in_preferred(busy_slots, preferred_hours, duration_minutes)
    
    async def create_locus_block(self, subtask: Subtask, block: TimeBlock) -> str:
        """Create a Locus time block in Google Calendar."""
        
        event = {
            'summary': f"[Locus] {subtask.title}",
            'description': f"Goal: {subtask.goal_title}\nPriority: {subtask.priority_score}/10\nType: {block.block_type}",
            'start': {'dateTime': block.start_time.isoformat()},
            'end': {'dateTime': block.end_time.isoformat()},
            'colorId': BLOCK_TYPE_COLOR_IDS[block.block_type],  # Different colors per block type
            'extendedProperties': {
                'private': {
                    'locus_task_id': subtask.id,
                    'locus_block_type': block.block_type
                }
            }
        }
        
        result = self.service.events().insert(calendarId='primary', body=event).execute()
        return result['id']
```

## 20.2 Notion Integration

```python
class NotionIntegration:
    
    POLL_INTERVAL_SECONDS = 60
    
    async def poll_for_changes(self, user: User):
        """Poll Notion for changes. Called by Celery Beat every 60s."""
        
        databases = await self.get_connected_databases(user.id)
        
        for db in databases:
            pages = await self.notion.databases.query(
                database_id=db.notion_db_id,
                filter={"timestamp": "last_edited_time", "last_edited_time": {"after": db.last_polled}}
            )
            
            for page in pages.results:
                # Check if this is new or changed
                last_known = await redis.get(f"notion:last_edit:{user.id}:{page.id}")
                
                if last_known != page.last_edited_time:
                    # Something changed — publish to Engine 1 queue
                    await redis_queue.publish('engine1', {
                        'type': 'notion_page_changed',
                        'user_id': user.id,
                        'page': page.dict()
                    })
                    
                    await redis.set(f"notion:last_edit:{user.id}:{page.id}", page.last_edited_time)
            
            await db.update(last_polled=datetime.utcnow())
    
    async def write_task_properties(self, task: Task, user: User):
        """Write Engine 3 outputs back to Notion task page."""
        
        await self.notion.pages.update(
            page_id=task.notion_page_id,
            properties={
                "Priority Score": {"number": task.priority_score},
                "Scheduled Block": {"date": {"start": task.scheduled_at.isoformat()}},
                "Engine Comment": {"rich_text": [{"text": {"content": task.engine_annotations or ""}}]}
            }
        )
```

## 20.3 Telegram Bot

```python
class LocusTelegramBot:
    """
    The Telegram bot serves as a mobile interface and notification channel.
    It handles:
    - Voice note ingestion (→ Groq Whisper → Engine 1)
    - Quick task creation via text
    - Proactive pokes from Engine 2
    - System health alerts
    - Conversational AI via the AI Gateway
    """
    
    @bot.message_handler(content_types=['voice'])
    async def handle_voice_note(message):
        user = await get_user_by_telegram_id(message.chat.id)
        
        # Download voice file from Telegram
        file_info = await bot.get_file(message.voice.file_id)
        voice_data = await bot.download_file(file_info.file_path)
        
        # Transcribe via Groq Whisper
        transcription = await groq.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("voice.ogg", voice_data, "audio/ogg")
        )
        
        # Route to Engine 1
        await redis_queue.publish('engine1', {
            'type': 'voice_note',
            'user_id': user.id,
            'source': 'telegram',
            'content': transcription.text,
            'raw_audio_path': f"/vault/voice/{uuid4()}.ogg"  # Saved for reference
        })
        
        await bot.reply_to(message, f"Got it. Logged: \"{transcription.text[:100]}...\"")
    
    async def send_proactive_poke(self, user: User, insight: PersonalityInsight):
        """Engine 2 calls this to send proactive insights to the user."""
        
        message = f"*Locus Insight*\n\n{insight.content}"
        
        if insight.action_suggestion:
            message += f"\n\n_Suggestion: {insight.action_suggestion}_"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("Got it", callback_data=f"insight_read:{insight.id}"),
            InlineKeyboardButton("Dismiss", callback_data=f"insight_dismiss:{insight.id}")
        )
        
        await bot.send_message(
            user.telegram_chat_id, 
            message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
```

## 20.4 Supermemory Integration

```python
class SupermemoryIntegration:
    """Nightly batch pull of saved content from Supermemory."""
    
    async def pull_and_process(self, user: User):
        """Called by Celery Beat at 2:00 AM."""
        
        # Get items saved since last pull
        items = await supermemory_api.get_memories(
            api_key=user.supermemory_api_key,
            after=user.supermemory_last_pulled
        )
        
        for item in items:
            # Ask Ollama: why did this user save this?
            reflection_prompt = f"""
            A person saved this content: "{item.title}" - {item.url}
            Content preview: {item.content[:500]}
            
            Their active interests are: {user_interest_summary}
            Their active goals are: {user_goal_summary}
            
            In 2 sentences: why might they have saved this? 
            What interest or goal does it connect to?
            """
            
            reflection = await ollama_generate(reflection_prompt, model="phi3.5")
            
            # Write to Obsidian Reads/
            obsidian_write(
                user_id=user.id,
                path=f"Reads/{date.today().isoformat()}.md",
                content=format_supermemory_entry(item, reflection),
                mode='append'
            )
            
            # Publish to Engine 1 for full processing
            await redis_queue.publish('engine1', {
                'type': 'bookmark_save',
                'user_id': user.id,
                'source': 'supermemory',
                'content': f"{item.title}: {reflection}",
                'url': item.url,
                'tags': item.tags
            })
        
        await user.update(supermemory_last_pulled=datetime.utcnow())
```

---

# 21. Security & Multi-User Architecture

## 21.1 Authentication

- JWT access tokens (15 minute expiry) + refresh tokens (30 day expiry, rotation on use)
- Refresh tokens stored in PostgreSQL (`user_sessions` table) and in Redis for fast validation
- All API endpoints validate JWT and extract `user_id` from the token
- Google OAuth 2.0 for calendar and optional SSO
- Passwords hashed with bcrypt (cost factor 12)

## 21.2 Multi-User Isolation (Non-Negotiable Rules)

Every single data access in the system follows these rules without exception:

1. **Every database table has a `user_id` column** — this is enforced at the schema level (foreign key to `users.id`)
2. **Every SQL query includes `WHERE user_id = $user_id`** — never query without this filter
3. **Every Qdrant search includes a `user_id` payload filter** — see §15.2
4. **Every Neo4j Cypher query includes `user_id: $user_id` in node matches**
5. **Every Redis key includes the user_id** — see §16.2
6. **Every Obsidian vault path is user-namespaced**: `/vault/{user_id}/...`
7. **The FastAPI middleware extracts `user_id` from JWT and injects it into every request context** — controllers never receive `user_id` from the request body (prevents impersonation)

```python
# FastAPI dependency that injects authenticated user into every route
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Every route uses this dependency
@router.get("/api/tasks")
async def get_tasks(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # user_id comes from the JWT — never from request params
    tasks = await db.execute(
        select(Task).where(Task.user_id == current_user.id)
    )
    return tasks.scalars().all()
```

## 21.3 Data Encryption

- All Google OAuth tokens encrypted at rest (AES-256 via SQLAlchemy-Encrypted)
- Notion access tokens encrypted at rest
- PostgreSQL connection is over TLS within Docker network
- Cloudflare Tunnel encrypts all traffic between client and Oracle VM
- Vault files are not encrypted at rest (Obsidian compatibility requirement) — full disk encryption on Oracle VM's block storage is enabled at the Oracle level

## 21.4 API Security

- Rate limiting per user per endpoint via Redis counters
- CORS restricted to `locus.yourdomain.com` only
- All user inputs sanitized via Pydantic validators
- File path traversal prevention for Obsidian vault writes
- SQL injection impossible via SQLAlchemy parameterized queries

---

# 22. Monitoring & Reliability

## 22.1 Uptime Kuma (AMD instance #2)

Monitors all critical services every 60 seconds:
- Oracle ARM API (`https://locus.yourdomain.com/api/system/health`)
- PostgreSQL (TCP check on port 5432)
- Redis (TCP check on port 6379)
- Neo4j (HTTP check on port 7474)
- Qdrant (HTTP check on port 6333)
- Ollama (HTTP check on port 11434)
- Cloudflare Tunnel (HTTPS endpoint response)

Sends Telegram alert to the admin user if any service is down for > 2 minutes.

## 22.2 Celery Flower

Celery Flower dashboard (available on the internal Docker network, not exposed publicly) shows:
- Active/completed/failed tasks per queue
- Worker health
- Task execution times
- Queue depths

## 22.3 Health Check Endpoint

```python
@app.get("/api/system/health")
async def health_check():
    """Comprehensive health check called by Uptime Kuma."""
    status = {}
    
    try:
        await db.execute("SELECT 1")
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {str(e)}"
    
    try:
        await redis_client.ping()
        status["redis"] = "ok"
    except:
        status["redis"] = "error"
    
    try:
        qdrant_health = await qdrant_client.get_cluster_info()
        status["qdrant"] = "ok"
    except:
        status["qdrant"] = "error"
    
    try:
        neo4j_driver.verify_connectivity()
        status["neo4j"] = "ok"
    except:
        status["neo4j"] = "error"
    
    try:
        ollama_models = await httpx.get("http://ollama:11434/api/tags")
        status["ollama"] = "ok" if ollama_models.status_code == 200 else "error"
    except:
        status["ollama"] = "error"
    
    all_ok = all(v == "ok" for v in status.values())
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "services": status,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

# 23. Build Order & Phased Roadmap

## Phase 0: Infrastructure (Week 1) — COMPLETE ✅
**All infrastructure is live. Phase 1 can begin.**

- [x] Create Oracle ARM A1 instance (4 OCPU, 24 GB RAM, 200 GB) ✅
- [x] Create 2× Oracle AMD micro instances ✅
- [x] SSH hardening, firewall configuration ✅
- [x] Docker + Docker Compose installation ✅
- [x] Cloudflare Tunnel setup — `api.locusapp.online` live ✅
- [x] Caddy on AMD #1 — installed, disabled (not needed, see §6.2) ⚠️
- [x] Uptime Kuma on AMD #2 — running at `http://80.225.249.205:3001` ✅
- [x] Docker Compose with PostgreSQL, Redis, Neo4j, Qdrant, Ollama ✅
- [x] Pull Ollama models: `llama3.1:8b`, `phi3.5`, `nomic-embed-text` ✅
- [x] Run database schema migrations ✅
- [x] Seed default user ✅
- [x] Configure Syncthing for Obsidian vault ✅
- [x] Configure rclone backups to Google Drive ✅
- [x] Uptime Kuma monitors configured ✅
- [x] Git repo pushed to GitHub (`locus-os`) ✅
- [x] Test `/status` endpoint from iPhone 16 Pro Max + Samsung A32 ✅

**Phase 0 is complete when:** `https://api.locusapp.online/status` returns `{ "status": "ok", "postgres": "connected" }` from both phones.

## Phase 1: Engine 1 — Logging Foundation (Weeks 2–4)
**Critical: build this before anything else. Without clean data, everything is noise.**

### Known Issues & Fixes Applied

| Issue | Fix Applied |
|---|---|
| `goals_horizon_check` constraint rejected `short-term` | Valid values: `week`, `month`, `quarter`, `year`, `lifetime` |
| `redbeat` package not available on ARM64 | Removed from `requirements.txt`, Celery beat uses default scheduler |
| `POSTGRES_PASSWORD` contained `#` character, broke DATABASE_URL | Changed password to one without special characters |
| `personality_snapshots` UNIQUE constraint used `::DATE` cast (not allowed in index) | Removed constraint, table created without it |
| Syncthing `/vault` permission denied | Fixed with `docker exec -u root locus-syncthing chmod 777 /vault` |
| Uptime Kuma Docker container couldn't resolve `locusapp.online` DNS | Use internal Oracle IP `http://10.0.0.91:3000/status` instead |
| Caddy SSL cert conflicts with Cloudflare proxy | Caddy disabled — Cloudflare Tunnel handles `api.locusapp.online` directly |
| Obsidian vault writes lacked file locking | Added `portalocker` with `.lock` sidecar files in `_write_obsidian` |
| Celery Beat `--scheduler redbeat.RedBeatScheduler` not available | Removed flag, uses default Celery beat scheduler |
| Docker Compose `version: '3.9'` obsolete | Removed, Docker Compose v2 ignores it with warning |
| `fastapi` service port mapping mismatch | Fixed to `3000:8000` matching Cloudflare Tunnel config |
| Celery app import path mismatch | Fixed from `app.celery` to `app.workers.celery_app` in docker-compose commands |
| Syncthing folder not shared with laptop | Added device `3UG4ZOS-...` to Syncthing mesh, shared Appledore folder |
| Google Calendar events logged without deduplication | Calendar polling logs events every 15 min; dedup needed in later phase |

### Phase 1 Checklist

| Task | Status | Evidence |
|---|---|---|
| FastAPI skeleton with auth (JWT + register/login) | ✅ Done | `/status`, `/auth/register`, `/auth/login`, `/auth/me` all functional |
| PostgreSQL schema creation (all 14 tables from §13) | ✅ Done | `users`, `goals`, `projects`, `tasks`, `behavioral_events`, `personality_insights`, `personality_snapshots`, `daily_metrics`, `ai_conversations`, `content_items`, `recommendations`, `habits`, `habit_completions`, `sync_events` |
| Basic Celery worker setup (engine1 queue) | ✅ Done | `locus-celery-e1` running, consuming from `engine1` queue via Redis |
| Task CRUD API endpoints | ✅ Done | GET/POST/PATCH `/api/tasks`, complete, defer all verified |
| Goal CRUD API endpoints | ✅ Done | GET/POST `/api/goals` verified (horizon constraint: week/month/quarter/year/lifetime) |
| Engine 1 normalization pipeline (§7.3) | ✅ Done | 293 behavioral events logged, entity extraction (intent/summary/topics/mood) working |
| Obsidian vault write functions (with locking) | ✅ Done | `portalocker.LOCK_EX` with `.lock` sidecar files, vault at `/vault/{user_id}/OS-managed zone/Logs/` |
| Groq Whisper voice transcription | ✅ Done | `transcribe_voice` service at `/api/ai/voice`, Groq Whisper API integrated |
| Telegram bot (voice + text ingestion) | ✅ Done | Webhook at `/api/telegram/webhook`, text + voice → Engine 1 pipeline |
| Notion polling (60s Celery Beat) | ✅ Done | `poll_notion_for_all_users` scheduled every 60s, Redis keys updating |
| Google Calendar OAuth + event read | ✅ Done | OAuth flow at `/auth/google`, 272 calendar events logged to PostgreSQL |
| AI Gateway (Ollama → Gemini → Groq fallback) | ✅ Done | `/api/ai/chat` routes: Ollama → Gemini → Groq, 4 conversations logged |
| Behavioral event logging to PostgreSQL + Qdrant | ✅ Done | 293 events in PostgreSQL, 170 vectors in Qdrant `behavioral_logs` |
| Syncthing vault sync (VM ↔ phones ↔ laptop) | ✅ Done | 4-device mesh: VM, iPhone, Samsung A32, Laptop — Appledore folder shared |

**Phase 1 is complete when:** You can add a task via Telegram, see it in PostgreSQL, see it in the Obsidian vault, and have it appear in the PWA.

**Verification (2026-04-01):**
- ✅ Telegram message → PostgreSQL: 3 telegram events in `behavioral_events`
- ✅ PostgreSQL → Obsidian vault: Engine 1 writes to `/vault/{user_id}/OS-managed zone/Logs/YYYY-MM-DD.md`
- ✅ PWA tasks API: Tasks retrievable via `GET /api/tasks` with auth
- ✅ Full E2E pipeline verified: 48/48 automated checks passed
- BONUS - Syncthing is synced with the VM, Phones and local machine

## Phase 2: PWA Foundation + Offline (Weeks 5–7)

### Known Issues & Fixes Applied

| Issue | Fix Applied |
|---|---|
| JWT token expired after 15 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` set to 525600 (1 year) for single-user mode |
| Settings page showed all integrations as "Connected" regardless of status | Removed hardcoded badges; all three now use real API response from `/api/integrations/status` |
| Notion showed as "Not connected" despite system-level API key being active | Updated integrations endpoint to check system-level `NOTION_API_KEY` + database IDs, not per-user OAuth token |
| Notion database IDs missing from `.env` | Added `NOTION_TASKS_DB_ID` and `NOTION_NOTES_DB_ID` to `/opt/locus/.env` |
| PWA user lacked Google Calendar and Telegram tokens | Copied integration tokens from main user (`soni820034@gmail.com`) to PWA user (`locus@locus.dev`) |
| PWA task creates not appearing in Obsidian vault | Verified pipeline working: PWA → Celery E1 → PostgreSQL + Obsidian (user-specific vault directories) |

### Phase 2 Checklist

| Task | Status | Evidence |
|---|---|---|
| Vite + React project setup with TypeScript | ✅ Done | `frontend/` directory, Vite 6, React 18, TypeScript 5.6 |
| Tailwind CSS + design system components | ✅ Done | `tailwind.config.ts` with spec colors (#FAFAF8, #5B4FD4, #1A1A1A, etc.) |
| PWA configuration (manifest, Service Worker) | ✅ Done | `vite-plugin-pwa` generates `manifest.webmanifest` + `sw.js` + `workbox-*.js` |
| Authentication screens (login, register) | ✅ Done | Single-user mode: auto-auth with 365-day JWT, no login screen |
| Dashboard page (today's tasks + schedule) | ✅ Done | Task counts, pending tasks, active goals, online/offline status |
| Task management pages (inbox, create, detail) | ✅ Done | Create, list, complete, defer with offline queue support |
| Goals page | ✅ Done | Create, list, progress bars, horizon filter (week/month/quarter/year/lifetime) |
| Dexie.js IndexedDB setup (full schema from §17) | ✅ Done | 9 tables: tasks, goals, habits, daily_metrics, personality_snapshot, offline_queue, schedule_cache, recommendations_cache, insights_cache |
| Offline queue (ActionRouter pattern from §19.2) | ✅ Done | `useOffline` hook: server-first with local fallback, queues to IndexedDB, registers background sync |
| Service Worker (cache-first app shell, network-first API) | ✅ Done | Workbox runtime caching: `NetworkFirst` for `/api/*`, `NetworkOnly` for `/auth/*` |
| WebLLM integration | ⚠️ Partial | `@mlc-ai/web-llm` installed, `useWebLLM` hook scaffolded, download button pending |
| Sync service (queue flush on reconnect) | ✅ Done | `flushQueue()` sends pending items to `/api/sync/flush`, updates sync status |
| Offline banner UI | ✅ Done | `OfflineBanner` component: shows warning bar when `navigator.onLine` is false |
| Cloudflare Pages deployment (GitHub Actions CI/CD) | ✅ Done | Live at `https://locusapp.online`, auto-deploys via `.github/workflows/deploy.yml` |
| Integration status accuracy (Notion/GCal/Telegram) | ✅ Done | System-level Notion check, per-user GCal + Telegram, all verified via API |
| Data consistency: PWA → PostgreSQL → Obsidian | ✅ Done | E2E test verified: task created via API → PostgreSQL `tasks` table → `behavioral_events` → Obsidian `.md` file |

**Phase 2 is complete when:** The app works fully offline on your iPhone 16 Pro Max. You can log tasks, mark completions, and ask basic AI questions without internet. Everything syncs when you reconnect.

**Verification (2026-04-01):**
- ✅ PWA live at `https://locusapp.online` (Cloudflare Pages, custom domain)
- ✅ Single-user mode: auto-authenticated, no login screen
- ✅ All 3 integrations connected: Notion (system-level), Google Calendar (OAuth), Telegram (webhook)
- ✅ E2E pipeline verified: task "E2E pipeline test task" → PostgreSQL → Obsidian vault
- ✅ Offline queue functional: tasks queue locally when offline, sync on reconnect
- ✅ Service Worker caching: app shell cached, API uses network-first strategy
- ⚠️ WebLLM download button: scaffolded but not fully implemented (Phase 3 priority)
- BONUS: Added end-to-end data sync (Obsidian <--> Notion <--> PostgreSQL)

## Phase 3: Engine 2 — Personality Intelligence (Weeks 8–12)

- [ ] Neo4j driver setup + initial graph schema
- [ ] Nightly vault crawl → Qdrant embedding update
- [ ] Graph node creation from behavioral events
- [ ] Interest node intensity calculations
- [ ] Goal node staleness detection
- [ ] Reflection Engine: avoidance detection
- [ ] Reflection Engine: behavioral contradiction detection  
- [ ] Reflection Engine: interest spike detection
- [ ] Signal Filter implementation
- [ ] Personality Snapshot packager (nightly cron)
- [ ] Insight storage and API endpoints
- [ ] Personality graph visualization in PWA (D3.js/vis.js)
- [ ] WebSocket events for real-time insight delivery
- [ ] Proactive Telegram pokes from Engine 2

**Phase 3 is complete when:** After 2 weeks of logging, the system generates its first accurate insight about your behavioral patterns.

## Phase 4: Engine 3 — Scheduling + Recommendations (Weeks 13–16)

- [ ] Master System Stages 1–5 (§10.1–10.5)
- [ ] Ollama task decomposition
- [ ] Priority scoring (four-axis composite)
- [ ] Time block routing (energy model)
- [ ] Google Calendar write (create blocks)
- [ ] Deferral detector + escalating responses
- [ ] Schedule UI in PWA (week view, day view)
- [ ] Recommendation engine (nightly generation)
- [ ] Reads page in PWA
- [ ] LinkedIn content engine
- [ ] Content Queue page in PWA
- [ ] Supermemory integration

**Phase 4 is complete when:** The system automatically schedules your tasks, sends you daily reading recommendations, and drafts LinkedIn posts from your own ideas.

## Phase 5: Agentic Capabilities + Polish (Weeks 17–20)

- [ ] AgenticExecutor (§11.4)
- [ ] Agentic task API endpoints
- [ ] Genesis Interview polish (conversational AI onboarding)
- [ ] Full Settings page (all integrations, preferences)
- [ ] Push notifications via Web Push API
- [ ] Performance optimization (lazy loading, pagination)
- [ ] Multi-user testing (second account, verify isolation)
- [ ] Security audit (pen test key flows)
- [ ] Documentation for handoff

---

# 24. Design System — For Designers

## 24.1 Brand Identity

**Name:** Locus

**Tagline:** *Your intelligence. Organized.*

**Brand personality:** 
- Calm confidence — not flashy, not corporate
- Intelligent without being clinical
- Personal without being casual
- Ambitious without being overwhelming
- The feeling: a very smart friend who knows you deeply and helps you get out of your own way

**What Locus is NOT visually:**
- Not dark-mode "hacker" aesthetic (too alienating)
- Not pastel productivity-app aesthetic (too shallow for what this does)
- Not corporate SaaS blue-and-white (too generic)
- Not cluttered with widgets and dashboards (too much noise)

## 24.2 Visual Identity

**Primary palette:**
- Background: Near-white `#FAFAF8` (warm white, not cold stark white)
- Surface: `#F4F3F0` (slightly warmer surface for cards)
- Primary accent: `#1A1A1A` (near-black — most actions, headings)
- Secondary accent: `#5B4FD4` (deep purple — AI-generated content, insights, Engine 2 outputs)
- Success: `#1D9E75` (teal-green — completions, positive signals)
- Warning: `#BA7517` (amber — deferrals, caution signals)
- Danger: `#C0392B` (muted red — errors, overdue items)
- Text primary: `#1A1A1A`
- Text secondary: `#6B6B6B`
- Text tertiary: `#9B9B9B`
- Border default: `rgba(0,0,0,0.08)`

**The purple distinction:** Anything generated by Locus's AI (insights, LinkedIn drafts, recommendations, personality graph annotations) has a subtle left border or accent in the purple (`#5B4FD4`). This creates a clear visual language: *purple = Locus speaking to you*. The user can always distinguish their own content from AI-generated content.

**Typography:**
- Headings: `Inter` or `DM Sans` — variable weight, optical size
- Body: `Inter` — clean, highly legible at small sizes
- Monospace (code, timestamps, scores): `JetBrains Mono`
- Type scale: 11px / 12px / 13px / 14px / 16px / 18px / 22px / 28px / 36px
- Base line height: 1.6 for body, 1.2 for headings

**Spacing scale:** 4px base unit. All spacing is multiples of 4: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96.

**Border radius:**
- Small elements (badges, chips): 4px
- Medium elements (inputs, buttons): 8px
- Large elements (cards): 12px
- Full round (avatars, circular indicators): 9999px

**Shadows:**
- Avoid heavy shadows. Use borders and background fills to create depth.
- The one exception: modals and drawers use a single subtle shadow: `0 8px 32px rgba(0,0,0,0.08)`

## 24.3 Mobile-First Design Principles

The primary use case is a phone. Every screen must work perfectly at 390px wide (iPhone 14/15/16 base width) before being adapted for desktop.

**Bottom navigation (mobile):** 5 icons maximum. Suggested: Dashboard, Tasks, Intelligence, Schedule, Chat. Everything else accessible from Settings or contextual menus.

**Touch targets:** Minimum 44×44px for all interactive elements. This is Apple's minimum. Do not go below this.

**Safe areas:** Respect iOS safe areas (notch, Dynamic Island, home indicator). Use CSS `env(safe-area-inset-*)`.

**Gestures:**
- Swipe right on a task card → complete
- Swipe left on a task card → defer
- Long press on a task → context menu (move, edit, delete)
- Pull to refresh on lists

## 24.4 Key Screens — Design Direction

**Dashboard (Home):**
A calm, focused overview of today. At a glance: today's CAPACITY score (with context), the 3 most important tasks right now (not a full list — just 3), a poke or insight from Locus, and quick access to log anything. No overwhelming metrics. No 12-widget dashboard. Calm, focused, actionable.

**Task Inbox:**
Clean list view. Tasks grouped by: Today → Upcoming → Someday. Each task card shows: title, priority score (as a small colored dot), time estimate, goal tag, and energy type. The deferral count is shown for tasks deferred 2+ times (as a warning badge). Swipe gestures for complete/defer.

**Intelligence (Engine 2 Output):**
The most distinctive screen. Three sections:
1. Latest insights (insight cards with the purple left border)
2. Personality graph (interactive node-link visualization — tap a node to see detail)
3. 30-day behavioral chart (mood, energy, productivity over time)

The personality graph visualization should feel alive and organic — not like a database diagram. Nodes are sized by intensity. Relationships are curved lines. Color-coded by category. Tap any node for full detail panel.

**AI Chat:**
A clean chat interface with model selector (Ollama, Gemini, Groq, or Auto). The AI Gateway routes automatically in Auto mode. Previous conversations are searchable. Voice input button prominent. The offline WebLLM mode shows a small indicator ("Running locally").

**Schedule:**
Week view by default. Time blocks are color-coded by type: Blue (deep work), Orange (creative), Gray (shallow), Purple (review). Tapping a block shows the task, priority score, and options to move/cancel. Blocks created by Locus show a small "L" logo. Blocks from Google Calendar show naturally.

## 24.5 Micro-interactions & Motion

- All state transitions: 150ms ease-out
- Card hover (desktop): subtle elevation (`box-shadow` change), no movement
- Task complete animation: checkmark draws in, card fades and slides out (200ms)
- Insight arrival: subtle pulse on the intelligence tab icon
- Offline mode transition: top banner slides down smoothly (100ms)
- Loading states: skeleton screens (not spinners) — match the shape of content
- No bounce animations, no spring physics, no particle effects — Locus is composed, not playful

## 24.6 Dark Mode

Full dark mode support is required. The dark palette:
- Background: `#111110`
- Surface: `#1C1C1A`
- Primary accent: `#FAFAF8` (inverted)
- Purple accent: `#7B70EE` (lightened for dark background)
- Success: `#2DB88A`
- Text primary: `#F0EFEC`
- Text secondary: `#A0A09A`
- Border: `rgba(255,255,255,0.08)`

The system follows the device's dark/light mode setting automatically. A manual override is available in Settings.

---

# 25. Agentic Capabilities — The OS Builds Its Own Tools

Locus is not just a system that shows you information. It is a system that can act autonomously on your behalf. This is the highest-capability feature of Locus and distinguishes it from every productivity tool that has ever existed.

## 25.1 What Agentic Means in Locus

When you say "set up a system that monitors my reading habit and pokes me every morning with today's recommendation," Locus does not give you a tutorial on how to do this. It does it. It writes the code, deploys it as a Celery task, tests it, and confirms.

The `AgenticExecutor` (§11.4) handles this. Its scope:

- **Automation creation:** Build and deploy recurring Celery tasks
- **Integration scripts:** Write Python scripts to pull data from new sources
- **Custom alert rules:** "Tell me if my mood score drops below 5 for 3 consecutive days"
- **Data analysis:** "Analyze my last 90 days of behavioral data and find patterns I haven't noticed"
- **Content workflows:** "Create a weekly newsletter draft from my Obsidian notes every Sunday"
- **Goal-specific tools:** "Track every time I work on my portfolio and show me total hours per week"

## 25.2 Agentic Safety Model

Agentic tasks are classified by risk level:

| Risk level | Examples | Approval required? |
|---|---|---|
| Read-only | "Analyze my last 30 days of data" | No — executes immediately |
| Local write | "Add a task for me every Monday: Review weekly goals" | Soft confirm (Telegram/PWA "Locus wants to create a recurring task — confirm?") |
| Code generation + deploy | "Build a Telegram bot that tracks my sleep" | Hard confirm — user must explicitly approve the generated code before deployment |
| External API calls | "Post my LinkedIn draft automatically when I approve it" | Hard confirm + explicit scope acknowledgment |

No agentic task writes to a database, file system, or external API without the appropriate confirmation level.

## 25.3 The Agentic Loop

```
User request: "I want a daily report of my completed tasks sent to me at 9 PM"

Step 1: Parse & classify
→ Type: automation
→ Requires: code_generation, celery_deployment
→ Risk: local_write (writes to Telegram, reads from PostgreSQL)
→ Approval: soft confirm

Step 2: Generate implementation
→ Llama 3.1 8B generates Python Celery task
→ Task: query tasks completed today, format as Telegram message, send at 21:00

Step 3: Validate
→ Run in sandbox (Docker container with no external access)
→ Verify output looks correct with mock data

Step 4: Present to user
→ "I'll create a daily 9 PM task summary. Here's what it'll look like:
   [Example output]
   Should I set this up?"

Step 5: Deploy on confirmation
→ Register as Celery Beat task with cron `0 21 * * *`
→ Store in `agentic_tasks` table with user_id, code_hash, schedule
→ Confirm to user: "Done. You'll get your first report tonight at 9 PM."
```

---

# Appendix A: Local Project Directory Structure

This is the directory structure on Shivam's laptop. All Locus project files live here.

**Root path:**
```
C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\
```

**Current structure:**
```
5_Locus\
│
├── .env                          # Local environment variables (never commit to git)
├── .gitignore                    # Git ignore rules
├── LOCUS_SPEC_v3.md              # ← This document. Single source of truth.
├── notes                         # Scratch notes (informal, not versioned)
├── ssh-key-2026-03-27.key        # SSH private key for Oracle VM — KEEP SAFE
├── ssh-key-2026-03-27.key.pub    # SSH public key (already uploaded to Oracle)
│
└── .archived planning docs\      # All pre-spec planning documents — do not edit
        life_os_architecture.html
        LOCUS_ARCHITECTURE.md
        LOCUS_BRAND_DESIGN_SYSTEM.md
        locus_design_system.html
        LOCUS_IMPLEMENTATION_PLAN.md
        LOCUS_MASTER_DOCUMENT.md
        LOCUS_PRD.md
        obsidian_sync_architecture.html
        PCOS_BIBLE_v3.md
        Prompt.txt
```

**What will be added as development progresses:**
```
5_Locus\
├── backend\                      # FastAPI app, Celery workers, all Python code
│   ├── app\
│   │   ├── main.py
│   │   ├── api\                  # Route handlers
│   │   ├── engines\              # Engine 1, 2, 3 worker logic
│   │   ├── models\               # SQLAlchemy models
│   │   └── services\             # LLM, Obsidian, Notion, etc.
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend\                     # Vite + React PWA
│   ├── src\
│   ├── public\
│   ├── index.html
│   └── vite.config.ts
│
├── infra\
│   ├── docker-compose.yml        # Deployed on Oracle VM at /opt/locus/
│   ├── schema.sql                # PostgreSQL DDL (one-time apply)
│   └── ssh-key-2026-03-27.key   # SSH key (already at root — move here eventually)
│
└── LOCUS_SPEC_v3.md
```

> **SSH key note:** The SSH key is currently at the project root for easy access. It should eventually be moved to `infra\` to keep infrastructure files together. The key must never be committed to git — confirm `.gitignore` includes `*.key`.

---

# Appendix B: Environment Variables

```bash
# Core
SECRET_KEY=<64-character random string>
ENVIRONMENT=production

# Database
POSTGRES_PASSWORD=<strong password>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=locus
POSTGRES_USER=locus
DATABASE_URL=postgresql+asyncpg://locus:${POSTGRES_PASSWORD}@postgres:5432/locus

# Redis
REDIS_PASSWORD=<strong password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Neo4j
NEO4J_PASSWORD=<strong password>
NEO4J_URL=bolt://neo4j:7687

# Qdrant
QDRANT_URL=http://qdrant:6333

# Ollama
OLLAMA_URL=http://ollama:11434

# LLM APIs
GEMINI_API_KEY=<from Google AI Studio>
GROQ_API_KEY=<from console.groq.com>

# Google OAuth
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=https://api.locusapp.online/auth/google/callback

# Notion
NOTION_CLIENT_ID=<from Notion integration settings>
NOTION_CLIENT_SECRET=<from Notion integration settings>

# Telegram
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_WEBHOOK_URL=https://api.locusapp.online/api/telegram/webhook

# Supermemory
SUPERMEMORY_API_KEY=<from supermemory.ai>

# Cloudflare
CLOUDFLARE_TUNNEL_TOKEN=61aaf41c-b590-4a7c-baaf-2805bedca731

# Backup
RCLONE_GDRIVE_TOKEN=<rclone google drive token>
BACKUP_GDRIVE_PATH=gdrive:locus-backups
```

---

# Appendix C: File Naming & Versioning Conventions

- All code follows snake_case for Python, camelCase for TypeScript
- Database migrations use sequential numbering: `001_initial_schema.sql`, `002_add_habits.sql`
- API versions are path-prefixed: `/api/v1/...` (start with v1, increment on breaking changes)
- Git branches: `main` (production), `dev` (integration), `feature/<name>` (features)
- Docker images tagged with git commit SHA + semantic version
- All database backups named `locus-backup-YYYY-MM-DD.tar.gz`
- Personality snapshots stored as `snapshot-YYYY-MM-DD.json.gz`

---

# Appendix D: Glossary

| Term | Definition |
|---|---|
| PCOS | Personal Cognitive Operating System — what Locus is |
| Engine 1 | The Logging Engine — all data intake and normalization |
| Engine 2 | The GraphRAG + Personality Engine — behavioral intelligence |
| Engine 3 | The Scheduling + Recommendation Engine — output generation |
| Master System | The 5-stage pipeline within Engine 3 for task processing |
| Behavioral Event | Any logged user action (task create, complete, defer, note write, etc.) |
| Personality Snapshot | Nightly compressed bundle of personality data pushed to devices |
| Signal Filter | The weighting system that separates high-value behavioral signals from noise |
| Action Gap | The difference between declared priority and behavioral priority for an interest |
| Genesis Interview | The conversational onboarding session that seeds the initial personality graph |
| Agentic Task | An autonomous action Locus takes to build or deploy a tool on the user's behalf |
| OS-managed Zone | The portion of the Obsidian vault written by Locus's engines (read-only for user) |
| Personal Zone | The portion of the Obsidian vault written by the user (read-only for engines) |
| Offline Queue | The IndexedDB table storing all write operations made while offline |
| WebLLM | Browser-native LLM inference via WebGPU (Phi-3.5-mini) |
| AI Gateway | Locus's transparent proxy for all LLM API calls — logs all conversations |
| Time Block | A scheduled period in Google Calendar assigned by Engine 3 |
| Deferral Detector | The system that detects when a task is being repeatedly avoided |

---

*Document version 3.0 — Frozen. Prepared for engineering, design, and executive review.*
*All decisions in this document are final pending explicit version increment.*
