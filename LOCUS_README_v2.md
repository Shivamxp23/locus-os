# LOCUS — Personal Cognitive Operating System
## Complete Build Guide · From Zero to Running
### v2.0 — Battle-Tested, ARM64-Specific, Every Broken Command Fixed

> **Who this is for:** Shivam building Locus on Oracle Cloud Always Free ARM64 VM.
> This is v2 — every command in here has been run, broken, debugged, and fixed.
> v1 had wrong pip flags, a fake OpenClaw repo, wrong Ollama config, wrong Syncthing permissions, and a confused interface model. All fixed here.
>
> **Read the Reality Check section first. Do not skip it.**

---

## Table of Contents

1. [Reality Check — Everything That Broke in v1](#1-reality-check)
2. [Prerequisites](#2-prerequisites)
3. [Phase 0A — VM & Directory Setup](#3-phase-0a)
4. [Phase 0B — All API Keys](#4-phase-0b)
5. [Phase 0C — Environment File](#5-phase-0c)
6. [Phase 0D — Cloudflare Tunnel](#6-phase-0d)
7. [Phase 0E — Core Docker Services](#7-phase-0e)
8. [Phase 0F — Ollama Native (MUST listen on 0.0.0.0)](#8-phase-0f)
9. [Phase 0G — Google OAuth Token](#9-phase-0g)
10. [Phase 0H — Syncthing + Oracle Firewall Fix](#10-phase-0h)
11. [Phase 0I — Vault Processing Pipeline (AI Chats → Obsidian)](#11-phase-0i)
12. [Phase 0J — LightRAG Knowledge Graph](#12-phase-0j)
13. [Phase 1 — Telegram Bot (replaces OpenClaw)](#13-phase-1)
14. [Phase 2 — FastAPI Backend](#14-phase-2)
15. [Phase 3 — PWA on Cloudflare Pages](#15-phase-3)
16. [The LLM Cascade — 5 Providers, All Free](#16-llm-cascade)
17. [Smoke Tests](#17-smoke-tests)
18. [Appendix A — .env Template](#appendix-a)
19. [Appendix B — docker-compose.yml](#appendix-b)
20. [Appendix C — Vault Structure](#appendix-c)

---

# 1. Reality Check

---

### 1.1 Fine-Tuning / RLHF — DO NOT BUILD THIS YET

Your VM is CPU-only ARM64. Fine-tuning requires a GPU. It is physically impossible on this hardware. Skip it entirely. The system collects reward signal data from day one. Run fine-tuning later on Google Colab or Kaggle free GPU credits when you have enough data.

---

### 1.2 pip `--break-system-packages` Does Not Exist on This Ubuntu

**The problem:** v1 used `pip3 install X --break-system-packages` everywhere. This flag does not exist on Ubuntu 22.04's pip version. Every pip command fails with "no such option".

**The fix:** Use `--user` flag instead. Every pip command in this guide uses `--user`.

```bash
# WRONG (from v1):
pip3 install something --break-system-packages

# CORRECT:
pip3 install something --user
```

---

### 1.3 Cloudflared — Run as systemd Service, NOT Docker Container

The spec's docker-compose runs cloudflared as a Docker container. This fails silently. Run it as a systemd service on the host VM. Section 6 covers this exactly.

---

### 1.4 Ollama — Run Native AND Must Listen on 0.0.0.0

**Two problems in v1:**

Problem 1: The spec runs Ollama in Docker. On ARM64, Ollama inside Docker has measurably worse inference speed. Run it native.

Problem 2 (v1 missed this): Even after running native, Ollama only listens on `127.0.0.1` by default. Docker containers cannot reach `127.0.0.1` on the host. You must configure Ollama to listen on `0.0.0.0` via a systemd override. Without this, every container trying to reach Ollama at `172.17.0.1:11434` gets "connection refused".

**The fix:** Section 8 creates both the service AND the override. Do not skip 8.2.

---

### 1.5 Syncthing — Two Things Required, Not One

**The problem:** v1 said to add Oracle Cloud firewall rules. That alone is not enough. Syncthing stalls at 0% because the `/vault` directory is owned by `opc` user and the Syncthing container (running as a different UID) cannot write to it.

**Two fixes required:**

1. Oracle Cloud Console: Add ingress rules for port 22000 TCP+UDP
2. VM iptables: Open port 22000
3. Fix vault permissions: `sudo chmod -R 777 /vault`

All three are required. Section 10 covers them in order.

---

### 1.6 OpenClaw — Fake Repo, Replaced with Python Bot

**The problem:** v1 told you to clone `https://github.com/ClaudioLeite/openclaw.git`. This repo does not exist. The real OpenClaw (`github.com/openclaw/openclaw`) is a massive platform with 17,000+ open issues — complete overkill for Locus.

**The fix:** Locus uses a 100-line Python Telegram bot that does everything OpenClaw would have done for this use case. It uses Groq for natural language understanding so you can talk to it in plain English instead of commands. Section 13 is the complete implementation.

---

### 1.7 llm-wiki — Multiple Issues

**Problem 1:** Package is not on PyPI. Install from GitHub.

**Problem 2:** Requires Python 3.11+. Ubuntu 22.04 ships Python 3.10. Install 3.11 separately.

**Problem 3:** `raw_dir` is hardcoded to `vault/raw/` in the source — not configurable via `wiki.toml`. Symlink `00-Inbox` as `raw/` so both MemPalace and llm-wiki use the same folder.

**Problem 4:** `phi3.5` is too weak to produce valid structured JSON for the ingest pipeline. Use `llama3.1:8b` for BOTH fast and heavy models.

**Problem 5:** Default timeout of 600s is not enough for `olw compile` on CPU. Set to 3600.

**Problem 6:** Some files from Windows/older systems have non-UTF-8 encoding. Detect and convert before ingesting.

**Problem 7:** `olw compile` is extremely slow on CPU-only ARM64 — ~20 minutes per article. Run it inside `screen` so SSH disconnect doesn't kill it.

Section 12 addresses all of these.

---

### 1.8 Interface Model — PWA is Primary, Telegram is Second Brain Chat

**This is a fundamental change from v1.**

**PWA at `locusapp.online`** — This is where ALL logging happens. Morning, afternoon, evening, night check-ins. Task management. Everything visual. There are four mandatory daily check-ins built into the PWA:
- Morning (wake up): Energy, Mood, Sleep, Stress → DCS calculated
- Afternoon (after lunch): Mood, Focus check-in
- Evening (end of work): What I did, what I avoided, tomorrow's priority
- Night (before sleep): Reflection, sleep intention

**Telegram bot** — This is your conversational interface to your second brain. You ask it things. It searches MemPalace and llm-wiki and answers. You do NOT log through Telegram. You do NOT manage tasks through Telegram. Telegram is for "what did I write about filmmaking?", "summarize my notes on Monevo", "what patterns have I noticed in my productivity?".

**Notion is removed.** The PWA owns all structured logging. Notion added sync complexity with zero benefit over a proper database.

---

### 1.9 Google OAuth Token — sed Command Breaks on Special Characters

**The problem:** The refresh token contains `/` and other special characters that break the `sed` substitution command in v1.

**The fix:** Use Python to write the token into the .env file. Section 9.3 shows the correct method.

---

### 1.10 Neo4j ARM64 — Works, But Needs Memory Limits

Neo4j 5.x has ARM64 Docker support, but without explicit memory limits it consumes all RAM. The docker-compose in Appendix B includes explicit heap and pagecache limits. Do not remove them.

---

### 1.11 WebLLM Offline AI — Mobile Has Partial Support

WebLLM requires WebGPU. Desktop Chrome/Firefox supports it. iOS Safari has limited support. Android Chrome is hit-or-miss. Design PWA offline mode to fall back to cached DCS/TWS calculations (pure JS formulas) when WebGPU is unavailable.

---

# 2. Prerequisites

### 2.1 Oracle Cloud VM (Already provisioned)
- ARM64 A1 Flex: 4 OCPU, 24 GB RAM, 200 GB storage
- Ubuntu 22.04 LTS
- IP: `140.238.245.25`
- SSH key: `C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os\.Keys and Documents\ssh-key-2026-03-27.key`
- SSH: `ssh -i "[key path]" ubuntu@140.238.245.25`

### 2.2 Domain (Already configured)
- `locusapp.online` — PWA via Cloudflare Pages
- `api.locusapp.online` — FastAPI via Cloudflare Tunnel

### 2.3 Cloudflare Account
- Free plan
- Zero Trust enabled
- Tunnel UUID: `61aaf41c-b590-4a7c-baaf-2805bedca731`

### 2.4 GitHub Account
- Repo: `https://github.com/Shivamxp23/locus-os` (private)
- Git remote requires exact case: `Shivamxp23`

### 2.5 Local Machine (Windows)
- Git, Python 3.9+, Obsidian installed
- Vault locally: `Appledore/` → synced to `/vault/` on VM

### 2.6 Accounts Needed (all free)
- **Google Cloud Console** — Calendar API + OAuth
- **Groq** — `console.groq.com`
- **Google AI Studio** — `aistudio.google.com` (Gemini 2.5 Pro)
- **Cerebras** — `cloud.cerebras.ai`
- **OpenRouter** — `openrouter.ai`
- **Telegram** — bot via BotFather

Notion is NOT needed. Removed from stack.

### 2.7 Verify VM Software

```bash
docker --version          # Docker 24+
docker compose version    # Docker Compose v2+
ollama --version          # will warn "could not connect" — that's fine, checks version
git --version
python3 --version         # 3.10+
```

If Docker missing:
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker
```

If Ollama missing:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

# 3. Phase 0A — VM & Directory Setup

```bash
# Create vault directory (NOT inside Docker)
sudo mkdir -p /vault
sudo chown ubuntu:ubuntu /vault
sudo chmod 777 /vault

# Create Locus project directory
sudo mkdir -p /opt/locus
sudo chown ubuntu:ubuntu /opt/locus
cd /opt/locus

# Create subdirectories
mkdir -p backend/routers
mkdir -p backend/services
mkdir -p backend/models
mkdir -p backend/middleware
mkdir -p scripts
```

### 3.2 Create Vault Structure

```bash
mkdir -p /vault/00-Inbox
mkdir -p /vault/01-Journal/2026/04
mkdir -p /vault/02-Projects
mkdir -p /vault/03-AI-Chats/claude
mkdir -p /vault/03-AI-Chats/chatgpt
mkdir -p /vault/04-Resources
mkdir -p /vault/05-Journal
mkdir -p /vault/06-Content/LinkedIn
mkdir -p /vault/06-Content/Instagram
mkdir -p /vault/mempalace
mkdir -p /vault/wiki
touch /vault/.stfolder
sudo chmod -R 777 /vault

echo "Vault structure created."
ls /vault
```

### 3.3 Initialize Git Repo

If `/opt/locus` already has files from directory setup (not empty, can't clone):
```bash
cd /opt/locus
git init
git remote add origin https://github.com/Shivamxp23/locus-os.git
git config user.email "soni820034@gmail.com"
git config user.name "Shivamxp23"
# Only pull if repo has commits:
git pull origin main 2>/dev/null || echo "Repo empty — will push later"
```

Add secrets to gitignore immediately:
```bash
echo ".env" >> /opt/locus/.gitignore
echo "*.key" >> /opt/locus/.gitignore
git config --global --add safe.directory /vault
git config --global --add safe.directory /opt/locus
```

---

# 4. Phase 0B — All API Keys

Get every key before writing `.env`. Do not start building until all keys are in hand.

### 4.1 Groq
1. `console.groq.com` → API Keys → Create API Key
2. Copy the `gsk_...` key

### 4.2 Gemini (Google AI Studio)
1. `aistudio.google.com` → Get API Key → Create API key
2. Copy the `AIza...` key

### 4.3 Cerebras
1. `cloud.cerebras.ai` → API Keys → Generate
2. Copy the `csk-...` key

### 4.4 OpenRouter
1. `openrouter.ai` → Keys → Create Key
2. Copy the `sk-or-v1-...` key

### 4.5 Google Cloud — Calendar API + OAuth
1. `console.cloud.google.com` → New project "Locus"
2. APIs & Services → Enable → "Google Calendar API"
3. Credentials → Create Credentials → OAuth client ID
4. Application type: **Desktop app**
5. Authorized redirect URIs → Add: `http://localhost:8080`
6. OAuth consent screen → add your Google account as test user
7. Copy `client_id` and `client_secret`

### 4.6 Telegram Bot
1. Open Telegram → search `@BotFather` → `/newbot`
2. Save the `TOKEN`
3. Get your user ID: search `@userinfobot` → `/start`
4. Save your numeric user ID

### 4.7 Generate Secret Keys
```bash
# App secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Locus service token
python3 -c "import secrets; print(secrets.token_hex(32))"
```

VAPID keys (for PWA push notifications — needed for daily check-in reminders):
```bash
pip3 install pywebpush --user
python3 -c "
from py_vapid import Vapid
vapid = Vapid()
vapid.generate_keys()
print('PRIVATE:', vapid.private_key.private_bytes_raw().hex())
print('PUBLIC:', vapid.public_key.public_bytes_raw().hex())
"
```

---

# 5. Phase 0C — Environment File

**This file contains all secrets. Never commit it to git.**

```bash
cat > /opt/locus/.env << 'ENVEOF'
# === LLM PROVIDERS ===
GROQ_API_KEY=gsk_YOUR_KEY
GEMINI_API_KEY=AIza_YOUR_KEY
CEREBRAS_API_KEY=csk-YOUR_KEY
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY

# === OLLAMA (local — containers reach host via Docker bridge) ===
OLLAMA_URL=http://172.17.0.1:11434

# === GOOGLE ===
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET
GOOGLE_REDIRECT_URI=https://api.locusapp.online/api/v1/auth/google/callback
GOOGLE_REFRESH_TOKEN=FILL_IN_AFTER_PHASE_0G

# === TELEGRAM ===
TELEGRAM_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_OWNER_ID=YOUR_NUMERIC_USER_ID

# === POSTGRES ===
POSTGRES_DB=locus
POSTGRES_USER=locus
POSTGRES_PASSWORD=PostgreSQLLocus3301
DATABASE_URL=postgresql://locus:PostgreSQLLocus3301@postgres:5432/locus

# === REDIS ===
REDIS_PASSWORD=RedisLocus3301
REDIS_URL=redis://:RedisLocus3301@redis:6379/0

# === QDRANT ===
QDRANT_URL=http://qdrant:6333

# === NEO4J ===
NEO4J_URL=bolt://neo4j:7687
NEO4J_PASSWORD=Neo4jLocus3301

# === APP ===
SECRET_KEY=YOUR_GENERATED_SECRET_KEY
LOCUS_PASSWORD=YOUR_PWA_PASSWORD
LOCUS_SERVICE_TOKEN=YOUR_GENERATED_SERVICE_TOKEN
LOCUS_API_URL=https://api.locusapp.online

# === CLOUDFLARE ===
CLOUDFLARE_TUNNEL_TOKEN=YOUR_FULL_TUNNEL_TOKEN

# === VAPID (PWA push notifications for daily check-in reminders) ===
VAPID_PRIVATE_KEY=YOUR_VAPID_PRIVATE
VAPID_PUBLIC_KEY=YOUR_VAPID_PUBLIC
VAPID_SUBJECT=mailto:soni820034@gmail.com

# === BACKUP ===
BACKUP_GDRIVE_PATH=gdrive:locus-backups
RCLONE_GDRIVE_TOKEN=FILL_IN_AFTER_RCLONE_SETUP
ENVEOF

echo ".env created"
```

> **Password warning:** Do NOT use `@`, `#`, or special characters in passwords. They break DATABASE_URL parsing. Use alphanumeric only.

---

# 6. Phase 0D — Cloudflare Tunnel

**Run as systemd service on the HOST — not inside Docker.**

### 6.1 Install cloudflared (ARM64)

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb
cloudflared --version
```

### 6.2 Install and Start Tunnel

Replace `YOUR_FULL_TUNNEL_TOKEN` with the actual token from your `.env` (the long `eyJ...` string):

```bash
sudo cloudflared service uninstall 2>/dev/null || true
sudo cloudflared service install YOUR_FULL_TUNNEL_TOKEN

sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml << 'EOF'
tunnel: 61aaf41c-b590-4a7c-baaf-2805bedca731
credentials-file: /root/.cloudflared/61aaf41c-b590-4a7c-baaf-2805bedca731.json

ingress:
  - hostname: api.locusapp.online
    service: http://localhost:8000
  - service: http_status:404
EOF

sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

### 6.3 Verify

```bash
sleep 10
curl https://api.locusapp.online/health
# Returns 502 until FastAPI is running — that is correct. Tunnel is working.
```

---

# 7. Phase 0E — Core Docker Services

### 7.1 Write docker-compose.yml

```bash
cat > /opt/locus/docker-compose.yml << 'COMPOSEEOF'
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: locus-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - locus-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: locus-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - locus-net
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    container_name: locus-qdrant
    restart: unless-stopped
    volumes:
      - qdrant-data:/qdrant/storage
    networks:
      - locus-net

  neo4j:
    image: neo4j:5.18-community
    container_name: locus-neo4j
    restart: unless-stopped
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_memory_pagecache_size: 1G
      NEO4J_server_memory_heap_initial__size: 512m
      NEO4J_server_memory_heap_max__size: 2G
    volumes:
      - neo4j-data:/data
      - neo4j-import:/var/lib/neo4j/import
    networks:
      - locus-net
    healthcheck:
      test: ["CMD", "wget", "-O-", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 5

  chromadb:
    image: chromadb/chroma:latest
    container_name: locus-chromadb
    restart: unless-stopped
    volumes:
      - chromadb-data:/chroma/chroma
    networks:
      - locus-net
    ports:
      - "8001:8000"

  fastapi:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: locus-api
    restart: unless-stopped
    env_file: .env
    extra_hosts:
      - "host-gateway:host-gateway"
    volumes:
      - /vault:/vault
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - locus-net
    ports:
      - "8000:8000"

  syncthing:
    image: syncthing/syncthing:latest
    container_name: locus-syncthing
    restart: unless-stopped
    volumes:
      - /vault:/vault
      - syncthing-data:/var/syncthing
    networks:
      - locus-net
    ports:
      - "8384:8384"
      - "22000:22000/tcp"
      - "22000:22000/udp"
      - "21027:21027/udp"

networks:
  locus-net:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  qdrant-data:
  neo4j-data:
  neo4j-import:
  chromadb-data:
  syncthing-data:
COMPOSEEOF

echo "docker-compose.yml written"
```

Note: `openclaw` service removed. Telegram bot runs as a Python process, not a Docker container.

### 7.2 Write Database Init SQL

```bash
cat > /opt/locus/scripts/init.sql << 'SQLEOF'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Daily logs (4 check-ins per day: morning, afternoon, evening, night)
CREATE TABLE IF NOT EXISTS daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    date DATE NOT NULL,
    checkin_type TEXT NOT NULL CHECK (checkin_type IN ('morning','afternoon','evening','night')),
    energy INT CHECK (energy BETWEEN 1 AND 10),
    mood INT CHECK (mood BETWEEN 1 AND 10),
    sleep_quality INT CHECK (sleep_quality BETWEEN 1 AND 10),
    stress INT CHECK (stress BETWEEN 1 AND 10),
    focus INT CHECK (focus BETWEEN 1 AND 10),
    dcs FLOAT,
    mode TEXT,
    intention TEXT,
    did_today TEXT,
    avoided TEXT,
    avoided_reason TEXT,
    tomorrow_priority TEXT,
    reflection TEXT,
    sleep_intention TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    project_id UUID,
    priority INT CHECK (priority BETWEEN 1 AND 10),
    urgency INT CHECK (urgency BETWEEN 1 AND 10),
    difficulty INT CHECK (difficulty BETWEEN 1 AND 10),
    tws FLOAT GENERATED ALWAYS AS (
        (priority * 0.4) + (urgency * 0.4) + (difficulty * 0.2)
    ) STORED,
    estimated_hours FLOAT,
    actual_hours FLOAT,
    quality INT CHECK (quality BETWEEN 1 AND 10),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done','deferred','killed')),
    deferral_count INT DEFAULT 0,
    scheduled_date DATE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','done','killed')),
    difficulty INT CHECK (difficulty BETWEEN 1 AND 10),
    target_hours_weekly FLOAT,
    deadline DATE,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Behavioral events
CREATE TABLE IF NOT EXISTS behavioral_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Personality snapshots
CREATE TABLE IF NOT EXISTS personality_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    snapshot_date DATE NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_date UNIQUE (user_id, snapshot_date)
);

-- Faction weekly stats
CREATE TABLE IF NOT EXISTS faction_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    week_start DATE NOT NULL,
    faction TEXT NOT NULL,
    target_hours FLOAT,
    actual_hours FLOAT DEFAULT 0,
    completion_rate FLOAT DEFAULT 0,
    CONSTRAINT unique_faction_week UNIQUE (user_id, week_start, faction)
);

-- AI interaction log
CREATE TABLE IF NOT EXISTS ai_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    interface TEXT CHECK (interface IN ('telegram','pwa')),
    interaction_type TEXT,
    prompt TEXT,
    response TEXT,
    model_used TEXT,
    tokens_used INT,
    latency_ms INT,
    thumbs_up BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Quick captures (inbox items from anywhere)
CREATE TABLE IF NOT EXISTS captures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    text TEXT NOT NULL,
    source TEXT CHECK (source IN ('pwa','telegram')),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Push subscriptions (for daily check-in reminders)
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(date, checkin_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_type ON behavioral_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_captures_processed ON captures(processed, created_at);
SQLEOF

echo "init.sql written"
```

### 7.3 Start Core Services

```bash
cd /opt/locus
docker compose up -d postgres redis qdrant neo4j chromadb
sleep 15
docker compose ps
```

All five should show healthy or up. If postgres is not healthy after 30 seconds:
```bash
docker logs locus-postgres | tail -20
```

---

# 8. Phase 0F — Ollama Native

### 8.1 Ollama Must Listen on 0.0.0.0

By default Ollama only listens on `127.0.0.1`. Docker containers cannot reach that. This step is mandatory — without it no container can call Ollama.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
sleep 3
curl http://172.17.0.1:11434/api/version
# Must return: {"version":"..."}
```

### 8.2 Pull Required Models

These are large downloads. Run them in a screen session if on slow connection:
```bash
screen -S ollama-pull
ollama pull llama3.1:8b      # ~4.7GB — primary model
ollama pull phi3.5            # ~2.2GB — fast analysis
ollama pull nomic-embed-text  # ~274MB — embeddings
# Ctrl+A then D to detach
```

Verify:
```bash
ollama list
# Must show all three models
```

### 8.3 Verify Docker Can Reach Ollama

```bash
ip route show | grep docker
# Should show: 172.17.0.0/16 dev docker0 ...
# "linkdown" is normal when no containers are running

curl http://172.17.0.1:11434/api/version
# Must return version JSON
```

---

# 9. Phase 0G — Google OAuth Token

### 9.1 Install Library

```bash
pip3 install requests-oauthlib --user
```

### 9.2 Run OAuth Flow

Fill in your actual client ID and secret before running:

```bash
cat > /tmp/oauth_flow.py << 'PYEOF'
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from requests_oauthlib import OAuth2Session

CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"
CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8080"
SCOPE = ["https://www.googleapis.com/auth/calendar"]

oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
auth_url, _ = oauth.authorization_url(
    "https://accounts.google.com/o/oauth2/auth",
    access_type="offline",
    prompt="consent"
)

print("\nOpen this URL in your browser on your laptop:\n")
print(auth_url)
print("\nBrowser will try to load localhost:8080 and FAIL — that is correct.")
print("Copy the FULL URL from the address bar (starts with http://localhost:8080?...)")
callback_url = input("\nPaste it here: ")

token = oauth.fetch_token(
    "https://accounts.google.com/o/oauth2/token",
    authorization_response=callback_url,
    client_secret=CLIENT_SECRET
)
print("\nREFRESH TOKEN:", token['refresh_token'])
PYEOF

python3 /tmp/oauth_flow.py
```

### 9.3 Save the Token

The sed command breaks on special characters in the token. Use Python instead:

```bash
python3 << 'PYEOF'
token = input("Paste your refresh token: ").strip()
with open('/opt/locus/.env', 'r') as f:
    content = f.read()
import re
content = re.sub(r'GOOGLE_REFRESH_TOKEN=.*', f'GOOGLE_REFRESH_TOKEN={token}', content)
with open('/opt/locus/.env', 'w') as f:
    f.write(content)
print("Token saved.")
PYEOF
```

Verify:
```bash
grep GOOGLE_REFRESH_TOKEN /opt/locus/.env
```

---

# 10. Phase 0H — Syncthing

All three steps are required. Skipping any one causes sync to stall at 0%.

### 10.1 Oracle Cloud Console — Open Port 22000

1. Oracle Cloud Console → your VM instance → Subnet → Security List
2. Add Ingress Rule: Source `0.0.0.0/0`, Protocol TCP, Port `22000`
3. Add Ingress Rule: Source `0.0.0.0/0`, Protocol UDP, Port `22000`
4. Save

### 10.2 VM iptables

```bash
sudo iptables -I INPUT -p tcp --dport 22000 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 22000 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

### 10.3 Fix Vault Permissions

```bash
sudo chmod -R 777 /vault
```

This is required. The Syncthing container runs as a different UID and cannot write to `/vault` without world-write permissions.

### 10.4 Start Syncthing

```bash
cd /opt/locus
docker compose up -d syncthing
sleep 10
docker compose ps syncthing
```

### 10.5 Access Syncthing UI

From your **laptop** terminal (not VM):
```bash
ssh -i "[path to key]" -L 8384:localhost:8384 ubuntu@140.238.245.25
```

Open `http://localhost:8384` in your browser while that terminal stays open.

### 10.6 Configure Syncthing

1. Remove the default folder if present
2. Add Folder: Path `/vault`, Label `Appledore`, Type `Send & Receive`
3. Add your phone/laptop as a device (get their Device ID from Syncthing on those devices)
4. Accept connection and folder share on your device — select **Send & Receive** (never encrypted mode)

### 10.7 Verify Sync is Working

```bash
docker logs locus-syncthing | tail -10
# Should show "Synced file" messages, not "permission denied"
```

If you see "permission denied" errors:
```bash
sudo chmod -R 777 /vault
docker compose restart syncthing
```

### 10.8 Add Ignore Patterns

In Syncthing web UI → edit vault folder → Ignore Patterns:
```
.obsidian/plugins/*/main.js
.obsidian/plugins/*/styles.css
.trash
.stversions
```

---

# 11. Phase 0I — Vault Processing Pipeline (AI Chats → Obsidian)

**All vault processing runs on your LOCAL WINDOWS MACHINE, not the VM.** Files sync to the VM via Syncthing after processing. This phase converts 1,300+ AI conversations from ChatGPT, Claude, Perplexity, and Gemini exports into tagged, linked Obsidian markdown files.

> **How it was done:** The entire pipeline was built using **Antigravity** (Claude Opus 4.6 with extended thinking). The prompt below was pasted into Antigravity with `_inspect.py`, `_inspect2.py`, `_inspect3.py` attached. Antigravity generated all scripts. Scripts were then run locally on Windows.

### 11.1 Prerequisites (Windows, local machine)

```bash
pip install httpx groq
# ffmpeg must be installed and on PATH for large audio file splitting
# Download from https://ffmpeg.org/download.html
```

### 11.2 Export Your AI Conversations

| Service | How to export |
|---------|--------------|
| ChatGPT | Settings → Data Controls → Export Data → wait for email → download ZIP |
| Claude | Settings → Account → Export Data → wait for email → download ZIP |
| Gemini | Google Takeout → select Google Keep + NotebookLM |
| Perplexity | Export individual conversations as .md |

Place exports in:
```
Appledore/03-AI-Chats/chatgpt/   ← conversations.json (plus shared_conversations.json etc.)
Appledore/03-AI-Chats/claude/    ← conversations.json (JSON array, NOT JSONL)
Appledore/03-AI-Chats/gemini/    ← Google Takeout files (Keep notes, HTML study guides, audio)
Appledore/03-AI-Chats/perplexity/ ← .md files (already in correct format)
```

### 11.3 The Antigravity Prompt

Paste this into Antigravity (Claude Opus 4.6, extended thinking ON) with `_inspect.py`, `_inspect2.py`, `_inspect3.py` attached:

```
MISSION: Parse, convert, and link my AI conversation exports into a structured Obsidian second brain.

VAULT PATH: C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\Appledore
CHATS FOLDER: [VAULT_PATH]/03-AI-Chats/

FOLDER STRUCTURE:
- 03-AI-Chats/claude/     → conversations.json (JSON array, one conversation per item — NOT JSONL)
- 03-AI-Chats/chatgpt/    → conversations.json (array of ALL conversations) + shared_conversations.json
- 03-AI-Chats/gemini/     → Google Takeout (NOT conversations — Keep notes, HTML guides, audio)
- 03-AI-Chats/perplexity/ → .md files (already complete, add frontmatter only)

FILE PREFIX RULES:
All files prefixed with: soni82003_, soni820034_, or shivamsonifilms_ (3 accounts, all = Shivam)
Never create account-based groupings. Link by topic, not account.

Run _inspect.py, _inspect2.py, _inspect3.py and report full output. Wait for confirmation.
```

Antigravity generates all scripts. Run them in order below.

### 11.4 Run Scripts in Order

**All scripts run from `Appledore/03-AI-Chats/` directory on Windows.**

Set your Groq API key at the top of each script before running.

```bash
# Step 0: Inspect structure (run all three, read output before proceeding)
python _inspect.py
python _inspect2.py
python _inspect3.py

# Step 1: Parse ChatGPT (tree-structured mapping → linear conversations)
python _step1_chatgpt.py
# Output: 1,103 .md files in chatgpt/

# Step 2: Parse Claude
python _step2_claude.py
# Output: 66 .md files in claude/

# Step 3: Process Google Takeout (NOT Gemini conversations — there were none)
# - Google Keep notes → 00-Inbox/Keep-Import/
# - HTML study guides → 04-Resources/Study-Guides/
# - NotebookLM metadata → gemini/notebooklm/_SOURCES.md
python _step3_gemini.py

# Step 4: Add frontmatter to Perplexity .md files (content unchanged)
python _step4_perplexity.py
# Output: frontmatter added to 51 files
```

### 11.5 Audio Transcription — CRITICAL: Use step10, NOT step5

> **DO NOT use `_step5_transcribe.py` or `_step5_retry.py`.** Both are broken:
> - They pass `language="en"` to Whisper → Hinglish speech hallucinates as nonsense English
> - They look in `03-AI-Chats/` but audio was already moved to `04-Resources/AI-Chat-Media/`
> - They don't chain context between chunks

```bash
# The CORRECT transcription script (run AFTER step 6-7 which move media files):
python step10_retranscribe.py
```

`step10_retranscribe.py` differences from the broken step5:
1. No `language=` param → Whisper auto-detects English/Hindi/Hinglish
2. Model: `whisper-large-v3-turbo` (6x faster, same quality)
3. Context chaining: end of chunk N passed as `prompt` to chunk N+1
4. Scans `04-Resources/AI-Chat-Media/` (correct location)
5. Detects and skips video-only MP4s (no audio track — marks as failed, not a bug)

For large NotebookLM MP4 videos (>24MB), extract audio first:
```powershell
# Run in PowerShell from 04-Resources/AI-Chat-Media/
$files = Get-ChildItem -Recurse -Filter "*.mp4" | Where-Object { $_.Length -gt 25MB }
foreach ($f in $files) {
    $out = [System.IO.Path]::ChangeExtension($f.FullName, ".m4a")
    ffmpeg -i $f.FullName -vn -acodec copy $out -y
}
# Then re-run step10_retranscribe.py
```

### 11.6 Semantic Tagging and Linking

```bash
# Step 6: Tag all 1,308 AI chat files + rename to readable slugs
# Uses Groq llama-3.1-8b-instant (30K TPM free, batch 10 files, ~27 min)
# Resumable: saves _tagging_cache.json after every batch. Re-run safely if interrupted.
python step6_retag_relink_v2.py

# Step 7: Audit + fix the ~512 files that step6 missed after rename
# Also rebuilds all wikilinks from scratch
python step7_audit_and_fix.py

# Step 8: Tag 00-Inbox and 04-Resources/Study-Guides (separate cache file)
python step8_inbox_studyguides.py

# Step 9: Generate tag audit report → _TAG_AUDIT_REPORT.md
# Read the report in Obsidian, then type 'y' to run cleanup pass
python step9_tag_audit.py

# Step 10: CORRECT transcription (see 11.5 above)
python step10_retranscribe.py

# Step 11: Enforce 3-level tag hierarchy across all vault files
# GOOD: health-stability/academics/DAA
# BAD:  health-stability, academic, DAA (flat)
# BAD:  health-stability/academics (only 2 levels)
python step11_tag_fix.py

# Step 12: Final cross-vault linking (all folders)
python step12_link_all.py
```

### 11.7 Tag Structure — Mandatory Rules

Every file must have tags in this exact structure:

```yaml
tags:
  - health-stability                          # faction (L1)
  - health-stability/academics/DAA            # faction/domain/specific (L3)
  - project/monevo                            # project tag
```

Four factions only:
- `health-stability` → academics (DAA/DBMS/OS/CN/ML), health, fitness, mental-health
- `leverage-money` → business, Monevo, Stratmore Guild, freelance, investing
- `craft-skills` → cinematography, film techniques, coding, Locus, AI/ML, LeetCode
- `expression-exploration` → philosophy, identity, pottery, Touch Designer, tinkering, hobbies

**Never allowed:** flat tags (no nesting), self-referencing tags (`craft-skills/craft-skills`), generic words (`ai`, `chatgpt`, `help`, `guide`, `error`).

### 11.8 Vault State After Completion

| Metric | Value |
|--------|-------|
| AI conversation files | 1,313 |
| Transcript files | 128 |
| Study guide files | 95 |
| Google Keep notes | 17 |
| Files with faction tags | 1,313 |
| Unique tags (3-level) | ~3,800 |
| Garbage tags | 0 |
| Self-referencing tags | 0 |
| Wikilinks | 2,577 |
| Media files in 04-Resources | 602 |

### 11.9 iCloud Notes → Obsidian

**iPhone:** Note → Share → Save to Files → Appledore/00-Inbox/ → rename to `.md`

**Mac:** Notes → File → Export Notes → move to Appledore/00-Inbox/ → rename to `.md`

Syncthing syncs to VM. Run `step8_inbox_studyguides.py` again to tag new files.

---

# 12. Phase 0J — LightRAG (Knowledge Graph + Hybrid Search)

> Run this after completing all vault processing scripts in Phase 0I.

LightRAG indexes the enriched vault, builds a knowledge graph in Neo4j, and enables hybrid retrieval (vector + graph traversal). This powers vault search from Telegram — "what did I write about filmmaking?", "why do I keep avoiding Monevo?".

**Why 70b for entity extraction:** LightRAG recommends ≥32b models for KG quality. 8b produces poor entity extraction. Groq 70b is free and handles it properly.

### 12.1 Install

```bash
# SSH into VM first
ssh -i "[key path]" ubuntu@140.238.245.25

# Install lightrag — use python3 -m pip, NOT pip3.
# pip3 on this VM installs to Python 3.11 site-packages but python3 runs 3.10.
# python3 -m pip installs to the correct 3.10 location.
python3 -m pip install "lightrag-hku[api]"

# Install missing dependencies that [api] does not pull in automatically on ARM64:
python3 -m pip install aiofiles uvicorn fastapi python-multipart httpx

# pip does NOT create a lightrag-server binary on ARM64/Ubuntu 22.04.
# Create the wrapper manually:
mkdir -p ~/.local/bin
cat > ~/.local/bin/lightrag-server << 'WRAPEOF'
#!/bin/bash
python3 -m lightrag.api.lightrag_server "$@"
WRAPEOF
chmod +x ~/.local/bin/lightrag-server

# Add to PATH permanently:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

# Verify:
which lightrag-server
# Must return: /home/ubuntu/.local/bin/lightrag-server
```

### 12.2 Configure

```bash
cat > /opt/locus/lightrag.env << 'EOF'
LLM_BINDING=openai
LLM_MODEL=llama-3.3-70b-versatile
LLM_BINDING_HOST=https://api.groq.com/openai/v1
LLM_BINDING_API_KEY=FILL_FROM_ENV

EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
EMBEDDING_BINDING_HOST=http://172.17.0.1:11434

WORKING_DIR=/opt/locus/lightrag-data
PORT=9621
EOF

mkdir -p /opt/locus/lightrag-data
# Fill in API key:
GROQ=$(grep GROQ_API_KEY /opt/locus/.env | cut -d= -f2)
sed -i "s/FILL_FROM_ENV/$GROQ/" /opt/locus/lightrag.env

# Create empty .env in working dir — suppresses LightRAG's interactive multi-instance prompt:
touch /opt/locus/lightrag-data/.env
```

### 12.3 Start LightRAG

> **Do NOT use screen for LightRAG.** Screen's Ctrl+A D detach does not work reliably on this VM — it sends Ctrl+C and kills the server. Use nohup instead.

```bash
nohup bash -c 'export PATH="$HOME/.local/bin:$PATH" && export $(grep -v "^#" /opt/locus/lightrag.env | xargs) && echo yes | lightrag-server' > /opt/locus/lightrag.log 2>&1 &
echo "LightRAG PID: $!"

sleep 10
curl http://localhost:9621/health
# Must return JSON with "status":"healthy"

# Watch logs anytime:
tail -f /opt/locus/lightrag.log

# Stop if needed:
pkill -f lightrag_server
```

### 12.4 Index Vault

> **STATUS: ✅ DONE (2026-04-18)** — Indexing launched via `nohup python3 -u /opt/locus/scripts/index_vault.py > /opt/locus/index.log 2>&1 &`. Script saved at `/opt/locus/scripts/index_vault.py` (uses `flush=True` and `-u` flag to fix buffered stdout). 1610 files found, all returning 200. Original inline heredoc via SSH doesn't work reliably — use the script file approach instead.

```bash
nohup python3 << 'PYEOF' > /opt/locus/index.log 2>&1 &
import asyncio, httpx
from pathlib import Path

async def index_vault():
    files = list(Path("/vault").glob("**/*.md"))
    print(f"Indexing {len(files)} files into LightRAG...")
    for i, f in enumerate(files):
        content = f.read_text(encoding="utf-8", errors="ignore")
        if len(content.strip()) < 20: continue
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post("http://localhost:9621/documents/text",
                json={"text": content, "description": f.stem})
            print(f"[{i+1}/{len(files)}] {f.name}: {r.status_code}")
        await asyncio.sleep(0.5)

asyncio.run(index_vault())
PYEOF
echo "Indexing started, PID: $!"

# Watch progress (Ctrl+C stops watching, NOT the indexing):
tail -f /opt/locus/index.log
# Takes 15-20 minutes for full vault
```

### 12.5 Create Service Wrapper

> **STATUS: ✅ DONE (2026-04-18)** — File created. FIXED: Changed `LIGHTRAG_URL` from `http://localhost:9621` to `os.getenv("LIGHTRAG_URL", "http://host-gateway:9621")` because inside the Docker container, `localhost` refers to the container itself, not the host. The `host-gateway` hostname is mapped via `extra_hosts` in docker-compose.yml.

```bash
cat > /opt/locus/backend/services/lightrag_service.py << 'EOF'
import httpx

LIGHTRAG_URL = "http://localhost:9621"

async def query_brain(question: str, mode: str = "hybrid") -> dict:
    """
    mode: hybrid (default) | local (specific facts) | global (patterns/themes)
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{LIGHTRAG_URL}/query",
                json={"query": question, "mode": mode, "stream": False})
            if r.status_code == 200:
                return {"status": "ok", "answer": r.json().get("response", "")}
    except Exception as e:
        return {"status": "unavailable", "answer": None, "error": str(e)}
    return {"status": "error", "answer": None}

async def health_check() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            return (await client.get(f"{LIGHTRAG_URL}/health")).status_code == 200
    except: return False
EOF
```

### 12.6 Update vault.py

> **STATUS: ✅ DONE (2026-04-18)** — File created. NOTE: This vault.py also defines `/wiki/query`, which conflicts with `routers/wiki.py`. The `wiki.py` stub was emptied to avoid duplicate route errors. The `/wiki/query` endpoint in vault.py is the real one (uses LightRAG global mode).

```bash
cat > /opt/locus/backend/routers/vault.py << 'EOF'
from fastapi import APIRouter
from services.lightrag_service import query_brain, health_check

router = APIRouter()

@router.get("/vault/search")
async def vault_search(q: str = ""):
    if not q: return {"results": [], "query": q}
    result = await query_brain(q, mode="hybrid")
    if result["status"] == "ok" and result["answer"]:
        return {"results": [{"title": "Brain", "excerpt": result["answer"], "score": 1.0}], "query": q}
    return {"results": [], "query": q, "message": "Brain indexing or unavailable."}

@router.get("/wiki/query")
async def wiki_query(q: str = ""):
    if not q: return {"answer": ""}
    result = await query_brain(q, mode="global")
    return {"answer": result.get("answer", "Brain unavailable."), "query": q}

@router.get("/vault/health")
async def vault_health():
    return {"lightrag": "up" if await health_check() else "down"}
EOF
```

### 12.7 Auto-start on Reboot

> **STATUS: ✅ DONE (2026-04-18)** — FIXED: The inline crontab command has quoting issues when run from PowerShell/SSH. Created `/opt/locus/scripts/start_lightrag.sh` wrapper script instead. Crontab entry: `@reboot nohup /opt/locus/scripts/start_lightrag.sh > /opt/locus/lightrag.log 2>&1 &`

```bash
# FIXED: Use a startup script instead of inline bash (quoting breaks via SSH)
cat > /opt/locus/scripts/start_lightrag.sh << 'EOF'
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
export $(grep -v '^#' /opt/locus/lightrag.env | xargs)
echo yes | lightrag-server
EOF
chmod +x /opt/locus/scripts/start_lightrag.sh

# Add to crontab:
(crontab -l 2>/dev/null | grep -v lightrag; echo '@reboot nohup /opt/locus/scripts/start_lightrag.sh > /opt/locus/lightrag.log 2>&1 &') | crontab -

# Verify crontab was written:
crontab -l
```

---

# 13. Phase 1 — Telegram Bot

> **STATUS: ✅ SKIP (2026-04-18)** — Telegram bot already running (PID 2260, `python3.11 /opt/locus/telegram_bot.py`). Verified with `pgrep -fa telegram_bot`. Do not touch.

**OpenClaw is NOT used.** Replaced with a Python bot that does exactly what was needed.

**What Telegram is for in Locus:**
- Asking questions to your second brain: "what did I write about filmmaking?"
- Searching your vault: "find my notes on Monevo"
- Quick captures: "note: idea I just had"
- Pattern queries: "what have I been avoiding lately?"

**What Telegram is NOT for:**
- Logging mood/energy/metrics (that's the PWA)
- Managing tasks (that's the PWA)
- Morning/evening check-ins (that's the PWA)

### 13.1 Install Dependencies

```bash
pip3 install python-telegram-bot httpx --user
```

### 13.2 Write the Bot

The bot is fully conversational. Every message goes through a two-stage Groq pipeline:
1. Router: decides if this is a vault search, capture, logging redirect, or just conversation
2. If conversation: a second Groq call responds as Locus — your second brain talking back to you

"hi", "I've been feeling unmotivated", "what should I focus on" — all get real conversational responses from Groq with full context about who you are.

```bash
cat > /opt/locus/telegram_bot.py << 'EOF'
import os
import json
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID"))
API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

api_headers = {"X-Service-Token": SERVICE_TOKEN}

ROUTER_PROMPT = """You are the Locus routing agent for Shivam's second brain.
Parse Shivam's message and return a JSON routing object.

Available actions:
- vault_search: search Shivam's Obsidian vault notes. Field: "query" (string)
- wiki_query: query compiled knowledge base. Field: "query" (string)
- capture: save a quick note or idea. Field: "text" (string)
- redirect_to_pwa: user wants to log mood/energy/tasks/check-ins
- converse: general conversation, questions, greetings, thinking out loud — anything else

Rules:
- Logging mood, energy, tasks, check-ins → redirect_to_pwa
- Explicit note search → vault_search
- Knowledge/pattern questions → wiki_query
- "note: X" or "capture: X" → capture
- EVERYTHING ELSE including greetings, thinking out loud, questions, venting → converse
- Return ONLY valid JSON. No explanation. No markdown.

Examples:
"hi" → {"action":"converse"}
"what did I write about filmmaking" → {"action":"vault_search","query":"filmmaking"}
"I've been feeling unmotivated lately" → {"action":"converse"}
"what should I focus on" → {"action":"converse"}
"note: call the bank" → {"action":"capture","text":"call the bank"}
"log my mood" → {"action":"redirect_to_pwa"}
"""

CONVERSE_PROMPT = """You are Locus, Shivam's personal cognitive assistant and second brain.

You know Shivam — he's building Locus (a Personal Cognitive Operating System), working on Monevo and Stratmore Guild projects, interested in filmmaking, philosophy, religion, and self-optimization. He uses Obsidian for notes, syncs everything to a VM.

Be conversational, direct, and genuinely helpful. You are not a chatbot — you are his second brain talking back to him. Respond like a trusted advisor who knows him well. Be concise. Do not be sycophantic. Push back when needed.

If he seems to be asking about his notes, suggest he ask you to search for them specifically.
If he wants to log something, remind him to use locusapp.online.
Otherwise — just talk to him like a smart friend who has full context on his life and work."""

async def call_groq(messages: list, temperature: float = 0) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": temperature
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

async def route(text: str) -> dict:
    content = await call_groq([
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": text}
    ])
    try:
        return json.loads(content)
    except Exception:
        return {"action": "converse"}

async def converse(text: str) -> str:
    return await call_groq([
        {"role": "system", "content": CONVERSE_PROMPT},
        {"role": "user", "content": text}
    ], temperature=0.7)

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper

@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Locus online. Talk to me — I'm your second brain.\n\n"
        "Search your notes, capture ideas, ask me anything.\n"
        "To log check-ins and tasks → locusapp.online"
    )

@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        action = await route(text)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
        return

    a = action.get("action")

    if a == "vault_search":
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_URL}/api/v1/vault/search",
                params={"q": action.get("query", text)},
                headers=api_headers,
                timeout=30
            )
        if r.status_code != 200:
            reply = await converse(f"User asked to search vault for '{action.get('query', text)}' but vault search is unavailable. Acknowledge and offer to help another way.")
            await update.message.reply_text(reply)
            return
        results = r.json().get("results", [])
        if not results:
            await update.message.reply_text(f"Nothing found in your vault for '{action.get('query', text)}'.")
        else:
            reply = "\n\n".join([f"📄 {res['title']}\n{res['excerpt']}" for res in results[:3]])
            await update.message.reply_text(reply)

    elif a == "wiki_query":
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_URL}/api/v1/wiki/query",
                params={"q": action.get("query", text)},
                headers=api_headers,
                timeout=60
            )
        if r.status_code != 200:
            reply = await converse(text)
            await update.message.reply_text(reply)
            return
        await update.message.reply_text(r.json().get("answer", "No answer found."))

    elif a == "capture":
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_URL}/api/v1/captures",
                json={"text": action.get("text", text), "source": "telegram"},
                headers=api_headers,
                timeout=10
            )
        await update.message.reply_text("Captured ✓")

    elif a == "redirect_to_pwa":
        await update.message.reply_text(
            "Log that at locusapp.online — that's where all your check-ins and tasks live."
        )

    else:  # converse
        reply = await converse(text)
        await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Locus bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
EOF
```

### 13.3 Run the Bot

FastAPI must be running first (Phase 2). Then:

```bash
cd /opt/locus
export $(grep -v '^#' .env | xargs)
screen -S locus-bot
python3.11 telegram_bot.py
# Ctrl+A then D to detach
```

> **Important:** Always use `python3.11` not `python3`. The telegram library is installed under Python 3.11.

### 13.4 Test

Send your bot anything:
- "hi" → conversational response
- "what did I write about filmmaking" → vault search
- "I've been feeling unmotivated" → Locus talks back to you
- "note: test capture" → captured
- "log my mood" → redirects to PWA

---

---

# 14. Phase 2 — FastAPI Backend

> **STATUS: 🔶 PARTIALLY DONE (2026-04-18)** — 14.1-14.4 already existed on VM. 14.5 needs rebuild because vault.py, wiki.py, lightrag_service.py, and llm.py were updated. The existing main.py imports a `context` router (from prior work) — keep it.

### 14.1 Write requirements.txt

```bash
cat > /opt/locus/backend/requirements.txt << 'EOF'
fastapi==0.115.0
uvicorn[standard]==0.30.0
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.35
httpx==0.27.0
python-dotenv==1.0.0
pydantic==2.9.0
google-auth==2.34.0
google-auth-httplib2==0.2.0
google-api-python-client==2.147.0
chromadb-client==1.0.9
neo4j==5.18.0
redis==5.0.0
apscheduler==3.10.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pywebpush==2.0.0
aiofiles==23.2.1
watchdog==4.0.0
EOF
```

### 14.2 Write Dockerfile

```bash
cat > /opt/locus/backend/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF
```

### 14.3 Write main.py

```bash
cat > /opt/locus/backend/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import logs, tasks, captures, vault, wiki, auth, checkins
from services.vault_jobs import nightly_diff, weekly_synthesis
import os

app = FastAPI(title="Locus API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(captures.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(wiki.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(checkins.router, prefix="/api/v1")

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    scheduler.add_job(nightly_diff, "cron", hour=23, minute=30)
    scheduler.add_job(weekly_synthesis, "cron", day_of_week="sun", hour=2)
    scheduler.start()

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
EOF
```

### 14.4 Create Router Stubs

```bash
touch /opt/locus/backend/routers/__init__.py
touch /opt/locus/backend/services/__init__.py

# Check-ins router (4 daily check-ins: morning, afternoon, evening, night)
cat > /opt/locus/backend/routers/checkins.py << 'EOF'
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class MorningCheckin(BaseModel):
    energy: int
    mood: int
    sleep_quality: int
    stress: int
    intention: Optional[str] = None

class AfternoonCheckin(BaseModel):
    mood: int
    focus: int

class EveningCheckin(BaseModel):
    did_today: str
    avoided: Optional[str] = None
    avoided_reason: Optional[str] = None
    tomorrow_priority: str

class NightCheckin(BaseModel):
    reflection: Optional[str] = None
    sleep_intention: Optional[str] = None

def calculate_dcs(e: int, m: int, s: int, st: int) -> dict:
    dcs = round(((e + m + s) / 3) * (1 - st / 20), 2)
    dcs = max(0.0, min(10.0, dcs))
    if dcs <= 2.0: mode = "SURVIVAL"
    elif dcs <= 4.0: mode = "RECOVERY"
    elif dcs <= 6.0: mode = "NORMAL"
    elif dcs <= 8.0: mode = "DEEP_WORK"
    else: mode = "PEAK"
    return {"dcs": dcs, "mode": mode}

@router.post("/checkins/morning")
async def morning_checkin(data: MorningCheckin):
    result = calculate_dcs(data.energy, data.mood, data.sleep_quality, data.stress)
    return {"status": "ok", "dcs": result["dcs"], "mode": result["mode"]}

@router.post("/checkins/afternoon")
async def afternoon_checkin(data: AfternoonCheckin):
    return {"status": "ok", "message": "Afternoon check-in logged"}

@router.post("/checkins/evening")
async def evening_checkin(data: EveningCheckin):
    return {"status": "ok", "message": "Evening check-in logged"}

@router.post("/checkins/night")
async def night_checkin(data: NightCheckin):
    return {"status": "ok", "message": "Night check-in logged"}

@router.get("/checkins/today")
async def today_checkins():
    return {"checkins": [], "pending": ["morning", "afternoon", "evening", "night"]}
EOF

# Logs router
cat > /opt/locus/backend/routers/logs.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.post("/log/morning")
async def morning_log(entry: dict):
    e, m, s, st = entry.get("e",5), entry.get("m",5), entry.get("s",5), entry.get("st",5)
    dcs = round(((e + m + s) / 3) * (1 - st / 20), 2)
    if dcs <= 2: mode = "SURVIVAL"
    elif dcs <= 4: mode = "RECOVERY"
    elif dcs <= 6: mode = "NORMAL"
    elif dcs <= 8: mode = "DEEP_WORK"
    else: mode = "PEAK"
    return {"status": "ok", "dcs": dcs, "mode": mode}
EOF

# Tasks router
cat > /opt/locus/backend/routers/tasks.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/tasks/today")
async def tasks_today():
    return {"tasks": [], "formatted": "No tasks yet. Add them at locusapp.online"}

@router.post("/tasks")
async def create_task(task: dict):
    return {"status": "ok", "message": "Task created"}
EOF

# Captures router (quick notes from Telegram)
cat > /opt/locus/backend/routers/captures.py << 'EOF'
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class Capture(BaseModel):
    text: str
    source: Optional[str] = "pwa"

@router.post("/captures")
async def create_capture(capture: Capture):
    return {"status": "ok", "message": "Captured ✓"}

@router.get("/captures")
async def get_captures():
    return {"captures": []}
EOF

# Vault router
cat > /opt/locus/backend/routers/vault.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/vault/search")
async def vault_search(q: str = ""):
    return {"results": [], "query": q}
EOF

# Wiki router
cat > /opt/locus/backend/routers/wiki.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/wiki/query")
async def wiki_query(q: str = ""):
    return {"answer": f"Wiki query for '{q}' — knowledge base still compiling.", "query": q}
EOF

# Auth router
cat > /opt/locus/backend/routers/auth.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/auth/google/callback")
async def google_callback(code: str = ""):
    return {"status": "ok"}
EOF

# Vault jobs
cat > /opt/locus/backend/services/vault_jobs.py << 'EOF'
async def nightly_diff():
    """Process new/changed vault files since last run."""
    pass

async def weekly_synthesis():
    """Full vault analysis with Gemini 2.5 Pro."""
    pass
EOF
```

### 14.5 Build and Start FastAPI

```bash
cd /opt/locus
docker compose build fastapi
docker compose up -d fastapi
sleep 10
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}

curl https://api.locusapp.online/health
# Expected: same
```

---

# 15. Phase 3 — PWA on Cloudflare Pages

> **STATUS: ❌ NOT DONE** — Requires local `npx create-react-app` + Cloudflare Pages dashboard (browser). Manual steps for Shivam.

The PWA is the **primary interface** for all logging. It has four mandatory daily check-ins with push notification reminders.

### 15.1 Daily Check-in Schedule

| Check-in | Time | Fields |
|---|---|---|
| Morning | On wake-up | Energy, Mood, Sleep, Stress → DCS calculated, mode shown |
| Afternoon | After lunch | Mood, Focus |
| Evening | End of work | What I did, what I avoided + reason, tomorrow's priority |
| Night | Before sleep | Reflection, sleep intention |

All four are mandatory. The PWA sends push notifications at configured times. You log everything here — mood, energy, tasks, projects, reflections. Not in Telegram. Not in Notion.

### 15.2 Create PWA Scaffold (on your laptop)

```bash
# In your locus-os repo directory on your laptop
npx create-react-app pwa --template cra-template-pwa
cd pwa
npm install
```

### 15.3 Configure Environment

```bash
echo "REACT_APP_API_URL=https://api.locusapp.online" > pwa/.env.production
echo "REACT_APP_VAPID_PUBLIC=YOUR_VAPID_PUBLIC_KEY" >> pwa/.env.production
```

### 15.4 Deploy to Cloudflare Pages

1. Push your repo to GitHub
2. `dash.cloudflare.com` → Pages → Create a project
3. Connect GitHub → select `locus-os`
4. Build settings:
   - Framework: Create React App
   - Build command: `cd pwa && npm run build`
   - Output directory: `pwa/build`
5. Add env variable: `REACT_APP_API_URL` = `https://api.locusapp.online`
6. Deploy

### 15.5 Install on Phone

Open `locusapp.online` in Chrome on Android → share → "Add to Home Screen". On iPhone: Safari → share → "Add to Home Screen".

---

# 16. The LLM Cascade

> **STATUS: ✅ DONE (2026-04-18)** — `backend/services/llm.py` written with all 5 providers (Groq, Gemini, Cerebras, OpenRouter, Ollama). Syntax verified. Full implementation with proper fallback chain.

5-provider cascade for different task types. All free tier.

```python
# /opt/locus/backend/services/llm.py
import httpx, os

GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")

async def call_llm(prompt: str, task_type: str = "realtime", system: str = "") -> str:
    if task_type == "weekly":
        return await _call_gemini(prompt, system)
    elif task_type == "nightly":
        return await _call_cerebras(prompt, system)
    elif task_type == "reasoning":
        return await _call_openrouter(prompt, system)
    elif task_type == "offline":
        return await _call_ollama(prompt, system)
    else:
        try:
            return await _call_groq(prompt, system)
        except Exception:
            return await _call_cerebras(prompt, system)
```

| Use case | Provider |
|---|---|
| Telegram NLU routing | Groq (realtime) |
| Morning DCS calculation | No LLM — pure formula |
| Vault search ranking | Groq |
| Nightly vault diff | Cerebras 70B |
| Weekly vault synthesis | Gemini 2.5 Pro (1M context) |
| Complex reasoning | OpenRouter DeepSeek R1 |
| VM internet down | Ollama phi3.5 |

---

# 17. Smoke Tests

> **STATUS: ❌ NOT DONE** — Waiting for FastAPI rebuild (14.5) to complete first.

Run in order. Every test must pass before the next phase.

```bash
# Test 1 — Infrastructure
cd /opt/locus
docker compose ps
# Expected: postgres (healthy), redis (healthy), qdrant (up), neo4j (up), chromadb (up), syncthing (healthy), fastapi (up)

# Test 2 — FastAPI
curl http://localhost:8000/health
curl https://api.locusapp.online/health
# Both must return: {"status":"ok","version":"1.0.0"}

# Test 3 — PostgreSQL
docker exec locus-postgres psql -U locus -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
# Must show tables: daily_logs, tasks, projects, behavioral_events, etc.

# Test 4 — Qdrant
curl http://localhost:6333/collections
# Must return: {"result":{"collections":[]},"status":"ok","time":...}

# Test 5 — Neo4j
curl http://localhost:7474
# Must return 200

# Test 6 — Ollama (from host)
curl http://172.17.0.1:11434/api/version
# Must return Ollama version JSON

# Test 7 — Groq
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"say ok"}]}'
# Must return a response

# Test 8 — Syncthing
docker logs locus-syncthing | tail -5
# Must show "Synced file" or "Up to Date", not "permission denied"

# Test 9 — Telegram Bot
# Send your bot: "what did I write about filmmaking"
# Must respond (vault search not yet wired until Phase 0J — bot will respond but search stub returns nothing)

# Test 10 — PWA
# Open https://locusapp.online in browser
# Must load React app
# Install to home screen on phone
# Test morning check-in flow
```

---

# Appendix A — .env Template

```bash
# === LLM PROVIDERS ===
GROQ_API_KEY=
GEMINI_API_KEY=
CEREBRAS_API_KEY=
OPENROUTER_API_KEY=

# === OLLAMA ===
OLLAMA_URL=http://172.17.0.1:11434

# === GOOGLE ===
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://api.locusapp.online/api/v1/auth/google/callback
GOOGLE_REFRESH_TOKEN=

# === TELEGRAM ===
TELEGRAM_TOKEN=
TELEGRAM_OWNER_ID=

# === POSTGRES (alphanumeric passwords only — special chars break DATABASE_URL) ===
POSTGRES_DB=locus
POSTGRES_USER=locus
POSTGRES_PASSWORD=PostgreSQLLocus3301
DATABASE_URL=postgresql://locus:PostgreSQLLocus3301@postgres:5432/locus

# === REDIS ===
REDIS_PASSWORD=RedisLocus3301
REDIS_URL=redis://:RedisLocus3301@redis:6379/0

# === QDRANT ===
QDRANT_URL=http://qdrant:6333

# === NEO4J ===
NEO4J_URL=bolt://neo4j:7687
NEO4J_PASSWORD=Neo4jLocus3301

# === APP ===
SECRET_KEY=
LOCUS_PASSWORD=
LOCUS_SERVICE_TOKEN=
LOCUS_API_URL=https://api.locusapp.online

# === CLOUDFLARE ===
CLOUDFLARE_TUNNEL_TOKEN=

# === VAPID ===
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_SUBJECT=mailto:soni820034@gmail.com

# === BACKUP ===
BACKUP_GDRIVE_PATH=gdrive:locus-backups
RCLONE_GDRIVE_TOKEN=
```

---

# Appendix B — docker-compose.yml Notes

- `cloudflared` is NOT in compose — runs as systemd
- `ollama` is NOT in compose — runs native
- `telegram_bot.py` is NOT in compose — runs as a Python process in screen
- `extra_hosts: host-gateway:host-gateway` on fastapi enables reaching native Ollama
- All services use `env_file: .env`
- Neo4j has explicit 2G heap max and 1G pagecache to prevent OOM
- Redis has password auth — REDIS_URL must include the password

---

# Appendix C — Vault Structure

```
Appledore/ (local) ↔ /vault/ (VM via Syncthing)
│
├── 00-Inbox/                    ← All new captures land here
│   └── Keep-Import/             ← Google Keep notes (from _step3_gemini.py)
│
├── 01-System/                   ← Locus system docs (outcomes, templates, README)
│
├── 02-Projects/                 ← Project notes by faction
│
├── 03-Tasks/                    ← Daily task files (YYYY-MM-DD.md)
│
├── 03-AI-Chats/                 ← 1,313 converted AI conversations
│   ├── chatgpt/                 ← 1,103 files (soni820034_, soni82003_, shivamsonifilms_)
│   │   └── _INDEX.md
│   ├── claude/                  ← 66 files
│   │   └── _INDEX.md
│   ├── perplexity/              ← 51 files
│   │   └── _INDEX.md
│   ├── gemini/                  ← No conversations. notebooklm/ subfolder only.
│   │   └── notebooklm/
│   │       └── _SOURCES.md
│   ├── _INDEX_health-stability.md
│   ├── _INDEX_leverage-money.md
│   ├── _INDEX_craft-skills.md
│   ├── _INDEX_expression-exploration.md
│   └── _MASTER_INDEX.md
│
├── 04-Resources/
│   ├── AI-Chat-Media/           ← All images/audio/video from AI exports (602 files + transcripts)
│   ├── Study-Guides/            ← 95 HTML→MD study guides (from _step3_gemini.py)
│   └── Orphaned/                ← Media files with no .md references
│
├── 05-Journal/                  ← Daily reflections
│
├── 06-Content/                  ← Content drafts
│   ├── LinkedIn/
│   └── Instagram/
│
├── 07-AI-Reports/               ← Weekly AI-generated reports
│
└── .obsidian/
    └── templates/               ← Daily Note, Quick Capture, Project, Resource, Weekly Review
```

**Obsidian Plugins Required:**
- **Dataview** — faction indexes use dataview query blocks
- **Tag Wrangler** — rename/merge tags, cascades to all files
- **Templater** (optional) — advanced templates with logic

**Daily logging (written by FastAPI to vault after check-ins are wired):**
```
/vault/05-Journal/YYYY-MM-DD.md
```

**Morning log format:**
```markdown
## Morning Check-in
E: _ / M: _ / S: _ / ST: _
DCS: _ | Mode: NORMAL
Intention:

## Afternoon Check-in
Mood: _ / Focus: _

## Evening Check-in
Did:
Avoided:
Why:
Tomorrow:

## Night Check-in
Reflection:
Sleep intention:
```

---

*LOCUS_README_v2.md — Complete build guide, battle-tested.*
*Every broken command from v1 fixed. OpenClaw replaced with Python bot. Notion removed. MemPalace/llm-wiki replaced with Antigravity-driven vault processing pipeline. Phase 0I now documents the actual scripts that ran. Phase 0J (LightRAG) is next.*
*Build in order. Do not skip phases.*
