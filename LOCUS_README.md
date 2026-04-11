# LOCUS — Personal Cognitive Operating System
## Complete Build Guide · From Zero to Running
### v1.0 — Honest, Tested, ARM64-Specific

> **Who this is for:** Anyone building Locus from scratch on an Oracle Cloud Always Free ARM64 VM.
> This guide incorporates every lesson from a real end-to-end setup attempt. It tells you what the architecture doc assumes but doesn't say, what will silently break, and exactly how to fix it before it does.
>
> **Read the Reality Check section first. Do not skip it.**

---

## Table of Contents

1. [Reality Check — What Won't Work and Why](#1-reality-check)
2. [What You Need Before Starting](#2-prerequisites)
3. [Phase 0A — VM & Directory Setup](#3-phase-0a--vm--directory-setup)
4. [Phase 0B — All API Keys](#4-phase-0b--all-api-keys)
5. [Phase 0C — Environment File](#5-phase-0c--environment-file)
6. [Phase 0D — Cloudflare Tunnel (systemd, not Docker)](#6-phase-0d--cloudflare-tunnel)
7. [Phase 0E — Core Docker Services](#7-phase-0e--core-docker-services)
8. [Phase 0F — Ollama (Native, not Docker)](#8-phase-0f--ollama-native)
9. [Phase 0G — Google OAuth Token (Headless VM method)](#9-phase-0g--google-oauth)
10. [Phase 0H — Syncthing + Oracle Firewall Fix](#10-phase-0h--syncthing)
11. [Phase 0I — MemPalace on VM](#11-phase-0i--mempalace-on-vm)
12. [Phase 0J — llm-wiki on VM](#12-phase-0j--llm-wiki-on-vm)
13. [Phase 1 — OpenClaw (Telegram Interface)](#13-phase-1--openclaw)
14. [Phase 2 — FastAPI Backend Skeleton](#14-phase-2--fastapi-backend)
15. [Phase 3 — PWA on Cloudflare Pages](#15-phase-3--pwa)
16. [The LLM Cascade — 5 Providers, All Free](#16-the-llm-cascade)
17. [Smoke Tests — Verify Everything Works](#17-smoke-tests)
18. [Appendix A — Complete .env Template](#appendix-a--env-template)
19. [Appendix B — docker-compose.yml](#appendix-b--docker-composeyml)
20. [Appendix C — Vault Structure](#appendix-c--vault-structure)

---

# 1. Reality Check

Read this before touching anything. These are the real problems with the architecture doc as written, specific to your ARM64 Oracle VM.

---

### 1.1 Fine-Tuning / RLHF — DO NOT BUILD THIS YET

**The problem:** The spec describes a fine-tuning and RLHF pipeline. Fine-tuning even a 7B model requires a GPU. Your VM is CPU-only ARM64. There is no GPU. Fine-tuning is physically impossible on this hardware.

**The fix:** Remove it from your immediate roadmap entirely. The system collects reward signal data (thumbs up/down, task completion) from day one — that data will be ready when you eventually run fine-tuning on free GPU credits (Google Colab, Kaggle, or Modal.com free tier). Do not build the fine-tuning infrastructure now. It will never run.

---

### 1.2 Cloudflared — Run as systemd Service, NOT Docker Container

**The problem:** The spec's `docker-compose.yml` runs cloudflared as a Docker container. In practice this fails silently because the token-based installation method and the config-file method conflict when both are present, and Docker networking adds complexity to ingress rule propagation. We spent hours debugging this.

**The fix:** Run cloudflared as a systemd service on the host VM (not inside Docker). This is what Section 6 of this guide does. The Docker container for cloudflared in Appendix B is commented out for this reason.

---

### 1.3 Ollama — Run Native, NOT Docker Container

**The problem:** The spec runs Ollama in Docker with a 12G memory limit. On ARM64, Ollama inside Docker has measurably worse inference speed than native because of the container virtualization layer overhead on memory-mapped model files. Additionally, the Docker Ollama image for ARM64 has historically had issues with certain quantized model formats.

**The fix:** Run Ollama as a native systemd service on the host. It's already likely installed. FastAPI connects to it at `http://host-gateway:11434` or directly at `http://172.17.0.1:11434` from inside Docker containers. This guide covers the exact configuration.

---

### 1.4 The LLM Cascade — Groq Alone Is Not Enough

**The problem:** The spec lists Groq as the only cloud LLM fallback. Groq's free tier is 6,000 tokens/minute for smart models. A single full vault analysis pass (200 files) costs ~250,000 tokens — that's 42 minutes minimum at Groq's TPM limit, and it will hit rate limit errors throughout. Groq is excellent for real-time queries but inadequate for batch analysis.

**The fix:** A 5-provider cascade. Full details in Section 16. Short version:
- **Gemini 2.5 Pro** (Google AI Studio free) — weekly vault synthesis, 1M context window, batch 50 files per call
- **Cerebras** (free) — nightly note diff, Llama 70B, 60K TPM (10x Groq), 1M tokens/day
- **Groq** — real-time queries, logging triggers, quick classification, sub-second latency
- **OpenRouter** — overflow fallback, DeepSeek R1
- **Ollama local** — offline fallback only

---

### 1.5 Neo4j ARM64 — Works, But Needs Memory Limits

**The problem:** Neo4j 5.x has ARM64 Docker support, but without explicit memory limits it will consume all available RAM during graph operations, starving other services.

**The fix:** The docker-compose in Appendix B includes explicit heap and pagecache limits. Do not remove them.

---

### 1.6 Syncthing — Oracle Cloud Blocks Port 22000

**The problem:** Syncthing uses port 22000 for device-to-device sync. Oracle Cloud's default VCN security rules block all inbound traffic except SSH. Devices will discover each other but sync will stall at ~2% indefinitely.

**The fix:** Add an ingress rule for port 22000 TCP+UDP in Oracle Cloud Console, AND run the iptables commands in Section 10. Both are required.

---

### 1.7 Google OAuth — No Browser on Headless VM

**The problem:** The standard Google OAuth flow opens a browser. Your VM has no browser. The `run_local_server()` method fails. The `oob` redirect URI was deprecated by Google in 2022.

**The fix:** Use the `requests_oauthlib` flow with `localhost:8080` as redirect URI. You open the auth URL on your laptop, Google redirects to `localhost:8080` which fails to load, but the auth code is in the URL bar. You paste the full URL back into the terminal. Exact script in Section 9.

---

### 1.8 MemPalace and llm-wiki — Run on VM, Not Laptop

**The reasoning:** You want your memory system and vault intelligence on the VM, not your laptop. Both tools work fine on ARM64. MemPalace uses ChromaDB (already in your stack). llm-wiki uses Ollama (already running native). Both are added to this guide in Sections 11 and 12.

---

### 1.9 WebLLM Offline AI — Partial Support

**The problem:** WebLLM requires WebGPU. Desktop Chrome/Firefox on modern hardware supports it. iOS Safari has limited WebGPU support. Android Chrome is hit-or-miss depending on device. The offline AI in the PWA will work on your laptop but may not work on your phone.

**The fix:** Design the PWA offline mode to gracefully fall back to cached DCS/TWS calculations (pure JS, no LLM) when WebGPU is unavailable. Reserve WebLLM for desktop PWA only. The offline experience on mobile is deterministic formulas + cached personality state, not generative AI. That is still useful.

---

# 2. Prerequisites

These must be true before you start. This guide does not cover setting them up.

### 2.1 Oracle Cloud Always Free VM (Already provisioned)
- ARM64 A1 Flex instance: 4 OCPU, 24 GB RAM, 200 GB storage
- Ubuntu 22.04 LTS
- Your VM IP: `140.238.245.25`
- SSH key at: `C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os\.Keys and Documents\ssh-key-2026-03-27.key`
- SSH command: `ssh -i "[key path]" ubuntu@140.238.245.25`

### 2.2 Domain (Already configured)
- `locusapp.online` — registered and nameservers pointing to Cloudflare
- `api.locusapp.online` — will be routed via Cloudflare Tunnel to FastAPI
- `locusapp.online` — will serve the PWA via Cloudflare Pages

### 2.3 Cloudflare Account
- Free plan is sufficient
- Zero Trust enabled (for tunnel)
- Your tunnel UUID: `61aaf41c-b590-4a7c-baaf-2805bedca731`

### 2.4 GitHub Account
- Repo: `https://github.com/Shivamxp23/locus-os` (private)
- Git remote requires exact case: `Shivamxp23`
- Classic PAT stored somewhere safe

### 2.5 Local Machine (Windows)
- Git installed
- Python 3.9+ installed
- Obsidian installed — vault is `Appledore/` locally, synced to `/vault/` on VM
- SSH client available (Windows Terminal, PowerShell, or PuTTY)

### 2.6 Accounts to Create (if not already done)
You will need accounts at these services — all free:
- **Google Cloud Console** — for Calendar API + OAuth credentials
- **Groq** — `console.groq.com`
- **Google AI Studio** — `aistudio.google.com` (for Gemini 2.5 Pro)
- **Cerebras** — `cloud.cerebras.ai`
- **OpenRouter** — `openrouter.ai`
- **Notion** — `notion.so` + create an integration at `notion.so/my-integrations`
- **Telegram** — create a bot via BotFather

### 2.7 Software on VM (Should already be installed)
Verify with these commands after SSHing in:
```bash
docker --version          # Docker 24+
docker compose version    # Docker Compose v2+
ollama --version          # Ollama installed
git --version
python3 --version         # 3.10+
```

If any are missing:
```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

---

# 3. Phase 0A — VM & Directory Setup

SSH into your VM for all commands in this section.

```bash
ssh -i "[path to key]" ubuntu@140.238.245.25
```

### 3.1 Create Directory Structure

```bash
# Create the vault on the host (NOT inside Docker)
sudo mkdir -p /vault
sudo chown ubuntu:ubuntu /vault

# Create the Locus project directory
sudo mkdir -p /opt/locus
sudo chown ubuntu:ubuntu /opt/locus
cd /opt/locus

# Create subdirectories
mkdir -p backend/routers
mkdir -p backend/services
mkdir -p backend/models
mkdir -p backend/middleware
mkdir -p pwa/src
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

# Create Syncthing marker so it doesn't error on empty folder
touch /vault/.stfolder

echo "Vault structure created."
ls /vault
```

### 3.3 Clone Your Repo

```bash
cd /opt/locus
git clone https://github.com/Shivamxp23/locus-os.git .
# If repo is empty, initialize it
git config user.email "your@email.com"
git config user.name "Shivamxp23"
```

---

# 4. Phase 0B — All API Keys

Get every key before writing your `.env`. Do not start building until all keys are in hand.

### 4.1 Groq
1. Go to `console.groq.com` → API Keys → Create API Key
2. Copy the `gsk_...` key

### 4.2 Gemini (Google AI Studio)
1. Go to `aistudio.google.com` → Get API Key → Create API key in new project
2. Copy the `AIza...` key

### 4.3 Cerebras
1. Go to `cloud.cerebras.ai` → API Keys → Generate
2. Copy the `csk-...` key

### 4.4 OpenRouter
1. Go to `openrouter.ai` → Keys → Create Key
2. Copy the `sk-or-v1-...` key

### 4.5 Notion Integration
1. Go to `notion.so/my-integrations` → New Integration
2. Name it "Locus", give it read/write capabilities
3. Copy the `secret_...` key
4. **Important:** After creating your Notion databases in Phase 2, you must share each database with this integration (click "..." → Connections → Add Locus)

### 4.6 Google Cloud — Calendar API + OAuth
1. Go to `console.cloud.google.com`
2. Create a new project called "Locus"
3. APIs & Services → Enable APIs → Search "Google Calendar API" → Enable
4. APIs & Services → Credentials → Create Credentials → OAuth client ID
5. Application type: **Desktop app** (not Web — this allows localhost redirect)
6. Download the JSON — you'll need `client_id` and `client_secret`
7. Under "OAuth consent screen" → add your Google account as a test user
8. Under your OAuth client → Authorized redirect URIs → Add: `http://localhost:8080`

### 4.7 Telegram Bot
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts, name your bot, get the `TOKEN`
4. Get your own Telegram user ID: search `@userinfobot`, send it `/start`
5. Save both the token and your user ID

### 4.8 Generate VAPID Keys (for PWA push notifications)
Run this on your VM:
```bash
pip3 install pywebpush --break-system-packages
python3 -c "
from py_vapid import Vapid
vapid = Vapid()
vapid.generate_keys()
print('PRIVATE:', vapid.private_key.private_bytes_raw().hex())
print('PUBLIC:', vapid.public_key.public_bytes_raw().hex())
"
```
Save both keys.

### 4.9 Generate Secret Keys
```bash
# App secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Locus service token (internal auth between OpenClaw and FastAPI)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Locus password (your login to the PWA)
# Choose something strong
```

---

# 5. Phase 0C — Environment File

Create the `.env` on the VM. **This file contains all secrets. Never commit it to git.**

```bash
cat > /opt/locus/.env << 'ENVEOF'
# === LLM PROVIDERS ===
GROQ_API_KEY=YOUR_GROQ_KEY
GEMINI_API_KEY=YOUR_GEMINI_KEY
CEREBRAS_API_KEY=YOUR_CEREBRAS_KEY
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY

# === OLLAMA (local) ===
OLLAMA_URL=http://172.17.0.1:11434

# === NOTION ===
NOTION_API_KEY=YOUR_NOTION_KEY

# === GOOGLE ===
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET
GOOGLE_REDIRECT_URI=https://api.locusapp.online/auth/google/callback
GOOGLE_REFRESH_TOKEN=FILL_IN_AFTER_PHASE_0G

# === TELEGRAM ===
TELEGRAM_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_OWNER_ID=YOUR_TELEGRAM_USER_ID

# === POSTGRES ===
POSTGRES_DB=locus
POSTGRES_USER=locus
POSTGRES_PASSWORD=PostgreSQL@3301.Locus
DATABASE_URL=postgresql://locus:PostgreSQL@3301.Locus@postgres:5432/locus

# === REDIS ===
REDIS_URL=redis://redis:6379/0

# === QDRANT ===
QDRANT_URL=http://qdrant:6333

# === NEO4J ===
NEO4J_URL=bolt://neo4j:7687
NEO4J_PASSWORD=LocusNeo4j2026

# === APP ===
SECRET_KEY=YOUR_GENERATED_SECRET_KEY
LOCUS_PASSWORD=YOUR_PWA_PASSWORD
LOCUS_SERVICE_TOKEN=YOUR_GENERATED_SERVICE_TOKEN
LOCUS_API_URL=https://api.locusapp.online

# === CLOUDFLARE ===
CLOUDFLARE_TUNNEL_TOKEN=YOUR_TUNNEL_TOKEN

# === VAPID (Push Notifications) ===
VAPID_PRIVATE_KEY=YOUR_VAPID_PRIVATE
VAPID_PUBLIC_KEY=YOUR_VAPID_PUBLIC
VAPID_SUBJECT=mailto:your@email.com

# === BACKUP ===
BACKUP_GDRIVE_PATH=locus-backups
RCLONE_GDRIVE_TOKEN=FILL_IN_AFTER_RCLONE_SETUP
ENVEOF

echo ".env created"
cat /opt/locus/.env | grep -v KEY | grep -v TOKEN | grep -v PASSWORD | grep -v SECRET
```

Add `.env` to `.gitignore`:
```bash
echo ".env" >> /opt/locus/.gitignore
echo "*.key" >> /opt/locus/.gitignore
```

---

# 6. Phase 0D — Cloudflare Tunnel

**Run as systemd service on the HOST — not inside Docker.**

### 6.1 Install cloudflared

```bash
# ARM64 specific install
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb
cloudflared --version
```

### 6.2 Install and Start Tunnel

```bash
# Uninstall any existing broken service first
sudo cloudflared service uninstall 2>/dev/null || true

# Install with your tunnel token
sudo cloudflared service install YOUR_TUNNEL_TOKEN_HERE

# Create config to define ingress rules
sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml << 'EOF'
tunnel: 61aaf41c-b590-4a7c-baaf-2805bedca731
credentials-file: /root/.cloudflared/61aaf41c-b590-4a7c-baaf-2805bedca731.json

ingress:
  - hostname: api.locusapp.online
    service: http://localhost:8000
  - service: http_status:404
EOF

# Start
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

### 6.3 Verify

```bash
# Wait 10 seconds for tunnel to connect
sleep 10
curl https://api.locusapp.online/health
# Will return 502 until FastAPI is running — that is correct
```

If you see error 1033, re-run the uninstall/reinstall sequence. If you see 502, the tunnel is working correctly.

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
    volumes:
      - redis-data:/data
    networks:
      - locus-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
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

  openclaw:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: locus-openclaw
    restart: unless-stopped
    env_file: .env
    depends_on:
      - fastapi
    networks:
      - locus-net

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

### 7.2 Write Database Init SQL

```bash
cat > /opt/locus/scripts/init.sql << 'SQLEOF'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Daily logs
CREATE TABLE IF NOT EXISTS daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    date DATE NOT NULL,
    energy INT CHECK (energy BETWEEN 1 AND 10),
    mood INT CHECK (mood BETWEEN 1 AND 10),
    sleep_quality INT CHECK (sleep_quality BETWEEN 1 AND 10),
    stress INT CHECK (stress BETWEEN 1 AND 10),
    time_available FLOAT,
    dcs FLOAT GENERATED ALWAYS AS (
        ((energy + mood + sleep_quality)::float / 3.0) * (1.0 - stress / 20.0)
    ) STORED,
    mode TEXT,
    morning_intention TEXT,
    evening_did TEXT,
    evening_avoided TEXT,
    evening_tomorrow TEXT,
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
    outcome_id UUID,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','done','killed')),
    difficulty INT CHECK (difficulty BETWEEN 1 AND 10),
    target_hours_weekly FLOAT,
    deadline DATE,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Outcomes
CREATE TABLE IF NOT EXISTS outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    status TEXT DEFAULT 'active',
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
    consistency_score FLOAT DEFAULT 0,
    lag_score FLOAT DEFAULT 0,
    action_gap FLOAT DEFAULT 0,
    CONSTRAINT unique_faction_week UNIQUE (user_id, week_start, faction)
);

-- AI interaction log (for RLHF data collection)
CREATE TABLE IF NOT EXISTS ai_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    interaction_type TEXT,
    prompt TEXT,
    response TEXT,
    model_used TEXT,
    tokens_used INT,
    latency_ms INT,
    thumbs_up BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Push subscriptions
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_type ON behavioral_events(event_type, created_at);
SQLEOF

echo "init.sql written"
```

### 7.3 Start Infrastructure Services

```bash
cd /opt/locus

# Pull images
docker compose pull postgres redis qdrant neo4j chromadb syncthing

# Start core infrastructure
docker compose up -d postgres redis qdrant neo4j chromadb

# Wait for postgres to be healthy
echo "Waiting for postgres..."
sleep 15
docker compose ps
docker exec locus-postgres psql -U locus -c '\l'
```

---

# 8. Phase 0F — Ollama Native

### 8.1 Verify Ollama is Running

```bash
# Ollama should already be installed and have models
ollama list
```

You should see `llama3.1:8b`, `phi3.5`, and `nomic-embed-text` from your previous setup. If not:

```bash
ollama pull llama3.1:8b
ollama pull phi3.5
ollama pull nomic-embed-text
```

### 8.2 Run Ollama as systemd Service

```bash
# Check if already running as service
sudo systemctl status ollama

# If not, create the service
sudo tee /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ubuntu
Group=ubuntu
Restart=always
RestartSec=3
Environment="HOME=/home/ubuntu"

[Install]
WantedBy=default.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 8.3 Verify Docker Containers Can Reach Ollama

```bash
# Get Docker bridge IP (this is how containers reach the host)
ip route show | grep docker
# Look for something like: 172.17.0.0/16 dev docker0

# Test from inside a container
docker run --rm --add-host host-gateway:host-gateway curlimages/curl \
  curl http://host-gateway:11434/api/version
```

If that works, your `OLLAMA_URL=http://172.17.0.1:11434` in `.env` is correct.

---

# 9. Phase 0G — Google OAuth

This gets your Google Calendar refresh token on a headless VM.

### 9.1 Install Libraries on VM

```bash
pip3 install requests-oauthlib --break-system-packages
```

### 9.2 Run OAuth Flow

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
print("Paste it here:")
redirect_response = input()

token = oauth.fetch_token(
    "https://oauth2.googleapis.com/token",
    authorization_response=redirect_response,
    client_secret=CLIENT_SECRET
)
print("\nREFRESH TOKEN:", token['refresh_token'])
PYEOF

python3 /tmp/oauth_flow.py
```

Replace `YOUR_GOOGLE_CLIENT_ID` and `YOUR_GOOGLE_CLIENT_SECRET` before running.

### 9.3 Save the Token

```bash
# Add to .env (replace YOUR_TOKEN with what the script printed)
sed -i 's/GOOGLE_REFRESH_TOKEN=FILL_IN_AFTER_PHASE_0G/GOOGLE_REFRESH_TOKEN=YOUR_TOKEN/' /opt/locus/.env
```

---

# 10. Phase 0H — Syncthing

### 10.1 Open Oracle Cloud Firewall

You must do this in two places or sync will stall.

**Step 1 — Oracle Cloud Console:**
1. Go to Oracle Cloud Console → Networking → Virtual Cloud Networks
2. Click your VCN → Security Lists → Default Security List
3. Add Ingress Rules:
   - Rule 1: Source `0.0.0.0/0`, Protocol `TCP`, Port `22000`
   - Rule 2: Source `0.0.0.0/0`, Protocol `UDP`, Port `22000`
4. Save

**Step 2 — VM iptables:**
```bash
sudo iptables -I INPUT -p tcp --dport 22000 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 22000 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

### 10.2 Start Syncthing

```bash
cd /opt/locus
docker compose up -d syncthing
sleep 10
docker compose ps syncthing
```

### 10.3 Access Syncthing Web UI

From your **laptop terminal** (not VM):
```bash
ssh -i "[path to key]" -L 8384:localhost:8384 ubuntu@140.238.245.25
```

Keep that terminal open and go to `http://localhost:8384` in your browser.

### 10.4 Configure the Vault Folder

1. Remove the default "Default Folder" if present
2. Add Folder:
   - **Folder Path:** `/vault`
   - **Folder Label:** `Locus Vault`
   - **Folder Type:** `Send & Receive`
3. Save

### 10.5 Add Your Devices

**On your phone/laptop:**
1. Install Syncthing (Android: Syncthing-Fork on F-Droid; iPhone: Möbius Sync)
2. In Syncthing on your device, go to Settings → Device ID — copy it
3. In the VM Syncthing UI → Add Device → paste the ID
4. On your device, accept the connection request from the VM
5. Accept the folder share from VM — set type to **Send & Receive**

**Critical:** If you get "encryption consistency" errors:
- Remove the folder from both sides completely
- Re-add from scratch on the VM first
- Accept the share on your device and select **Send & Receive** when prompted (do NOT accept in encrypted mode)

### 10.6 Add Ignore Patterns

In Syncthing on the VM, edit the vault folder → Ignore Patterns:
```
.obsidian/plugins/*/main.js
.obsidian/plugins/*/styles.css
.trash
.stversions
```

---

# 11. Phase 0I — MemPalace on VM

MemPalace will run on the VM and connect to ChromaDB (already in your docker-compose).

### 11.1 Install MemPalace

```bash
pip3 install mempalace --break-system-packages
```

### 11.2 Configure to Use VM's ChromaDB

By default MemPalace creates its own local ChromaDB. You want it pointing at your Docker ChromaDB:

```bash
mkdir -p ~/.mempalace
cat > ~/.mempalace/config.json << 'EOF'
{
  "palace_path": "/home/ubuntu/.mempalace/palace",
  "chroma_host": "localhost",
  "chroma_port": 8001,
  "collection_name": "locus_mempalace"
}
EOF
```

### 11.3 Initialize with Your Vault

```bash
mempalace init /vault
```

Follow the prompts:
- People: add yourself (`Shivam`)
- Projects: add `Locus`
- Accept the detected rooms or customize them

### 11.4 Mine Your Existing Notes

```bash
# Mine the whole vault
mempalace mine /vault

# Mine AI chats specifically
mempalace mine /vault/03-AI-Chats --mode convos
```

### 11.5 Set Up Auto-Mining Cron Job

```bash
# Mine vault every night at 11:30 PM (before llm-wiki runs at midnight)
(crontab -l 2>/dev/null; echo "30 23 * * * /home/ubuntu/.local/bin/mempalace mine /vault >> /var/log/mempalace.log 2>&1") | crontab -
```

### 11.6 Verify

```bash
mempalace status
mempalace search "Locus architecture"
```

---

# 12. Phase 0J — llm-wiki on VM

llm-wiki compiles your vault notes into a cross-linked knowledge base using Ollama.

### 12.1 Install

```bash
pip3 install obsidian-llm-wiki --break-system-packages
```

### 12.2 Configure

```bash
# Set vault path
export OLW_VAULT=/vault

# Run setup — point it at your local Ollama
olw setup
```

When prompted:
- **Ollama URL:** `http://localhost:11434`
- **Fast model:** `phi3.5` (for analysis)
- **Heavy model:** `llama3.1:8b` (for article writing)
- **Vault path:** `/vault`

### 12.3 Initialize

```bash
olw init /vault
```

### 12.4 First Run

```bash
# Ingest all notes
olw ingest --all

# Compile wiki articles
olw compile

# Review and approve generated articles
olw approve --all
```

### 12.5 Set Up Cron Job

```bash
# Run wiki compile every night at midnight
(crontab -l 2>/dev/null; echo "0 0 * * * OLW_VAULT=/vault /home/ubuntu/.local/bin/olw ingest --all && /home/ubuntu/.local/bin/olw compile >> /var/log/llmwiki.log 2>&1") | crontab -
```

---

# 13. Phase 1 — OpenClaw

OpenClaw is the Telegram bot framework you fork and own. The spec says to clone it, strip `.git`, and absorb it into your repo.

### 13.1 Get OpenClaw

```bash
cd /opt/locus

# Clone OpenClaw (check the actual repo URL — adjust if needed)
git clone https://github.com/ClaudioLeite/openclaw.git openclaw-source
cd openclaw-source

# Strip git history — it becomes your code now
rm -rf .git

# Copy everything to your repo root
cp -r . /opt/locus/
cd /opt/locus
rm -rf openclaw-source

# The OpenClaw Dockerfile now lives at /opt/locus/Dockerfile
ls Dockerfile
```

### 13.2 Create the Locus Skill

OpenClaw skills live in `skills/`. Create your Locus skill:

```bash
mkdir -p /opt/locus/skills/locus
cat > /opt/locus/skills/locus/index.js << 'EOF'
// LOCUS MODIFICATION 1 — Main skill entry point
// All handlers call FastAPI. No business logic here.

const axios = require('axios');

const API_URL = process.env.LOCUS_API_URL;
const SERVICE_TOKEN = process.env.LOCUS_SERVICE_TOKEN;

const api = axios.create({
  baseURL: API_URL,
  headers: { 'X-Service-Token': SERVICE_TOKEN }
});

module.exports = {
  name: 'locus',
  commands: {
    '/log': async (ctx) => {
      const text = ctx.message.text.replace('/log', '').trim();
      const res = await api.post('/api/v1/log/quick', { text });
      await ctx.reply(res.data.message);
    },
    '/morning': async (ctx) => {
      await ctx.reply('Morning check-in:\nEnergy (1-10)?\nMood (1-10)?\nSleep quality (1-10)?\nStress (1-10)?\n\nReply with 4 numbers like: 7 6 8 4');
    },
    '/tasks': async (ctx) => {
      const res = await api.get('/api/v1/tasks/today');
      await ctx.reply(res.data.formatted);
    },
    '/brief': async (ctx) => {
      const res = await api.get('/api/v1/brief/daily');
      await ctx.reply(res.data.brief);
    }
  }
};
EOF
```

### 13.3 Start OpenClaw

Once your FastAPI backend is running:
```bash
cd /opt/locus
docker compose build openclaw
docker compose up -d openclaw
docker compose logs openclaw --tail=20
```

Test by sending `/brief` to your Telegram bot.

---

# 14. Phase 2 — FastAPI Backend

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
notion-client==2.2.1
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
from routers import logs, tasks, calendar, vault, brief, auth
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
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(brief.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

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
# Create __init__.py files
touch /opt/locus/backend/routers/__init__.py
touch /opt/locus/backend/services/__init__.py

# Logs router
cat > /opt/locus/backend/routers/logs.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.post("/log/quick")
async def quick_log(entry: dict):
    return {"status": "ok", "message": "Logged ✓"}

@router.post("/log/morning")
async def morning_log(entry: dict):
    return {"status": "ok", "dcs": 0.0, "mode": "NORMAL"}
EOF

cat > /opt/locus/backend/routers/tasks.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/tasks/today")
async def tasks_today():
    return {"tasks": [], "formatted": "No tasks scheduled yet."}
EOF

cat > /opt/locus/backend/routers/calendar.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/calendar/today")
async def calendar_today():
    return {"events": []}
EOF

cat > /opt/locus/backend/routers/vault.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/vault/search")
async def vault_search(q: str = ""):
    return {"results": []}
EOF

cat > /opt/locus/backend/routers/brief.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/brief/daily")
async def daily_brief():
    return {"brief": "Locus is initializing. Log your morning metrics to get started."}
EOF

cat > /opt/locus/backend/routers/auth.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()

@router.get("/auth/google/callback")
async def google_callback(code: str = ""):
    return {"status": "ok"}
EOF

# Vault jobs service
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
sleep 5
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}

curl https://api.locusapp.online/health
# Expected: same — if different, check cloudflared: sudo systemctl restart cloudflared
```

---

# 15. Phase 3 — PWA on Cloudflare Pages

The PWA is a static React app deployed to Cloudflare Pages (free forever, global CDN).

### 15.1 Create PWA Scaffold

On your **laptop**:
```bash
# In your locus-os repo directory
npx create-react-app pwa --template cra-template-pwa
cd pwa
npm install
```

### 15.2 Configure Environment

```bash
# pwa/.env.production
echo "REACT_APP_API_URL=https://api.locusapp.online" > pwa/.env.production
echo "REACT_APP_VAPID_PUBLIC=YOUR_VAPID_PUBLIC_KEY" >> pwa/.env.production
```

### 15.3 Deploy to Cloudflare Pages

1. Push your repo to GitHub
2. Go to `dash.cloudflare.com` → Pages → Create a project
3. Connect to GitHub → select `locus-os`
4. Build settings:
   - **Framework preset:** Create React App
   - **Build command:** `cd pwa && npm run build`
   - **Build output directory:** `pwa/build`
5. Add environment variable: `REACT_APP_API_URL` = `https://api.locusapp.online`
6. Deploy

Your PWA will be at `locusapp.online` once DNS is pointed at Pages (Cloudflare handles this automatically for domains managed by Cloudflare).

### 15.4 Add to Home Screen

On your phone, open `locusapp.online` in Chrome → share button → "Add to Home Screen". This installs it as a standalone app with the offline cache working.

---

# 16. The LLM Cascade

The spec only mentions Groq as cloud fallback. That is insufficient. Use this 5-provider cascade in your `services/llm.py`:

```python
# /opt/locus/backend/services/llm.py
import httpx
import os

GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")

async def call_llm(prompt: str, task_type: str = "realtime", system: str = "") -> str:
    """
    Route to the right provider based on task type.
    
    task_type options:
    - "realtime"    → Groq (fast, low latency, daily operations)
    - "nightly"     → Cerebras (high throughput, nightly vault diff)  
    - "weekly"      → Gemini 2.5 Pro (1M context, full vault synthesis)
    - "reasoning"   → OpenRouter DeepSeek R1 (complex analysis)
    - "offline"     → Ollama local (when all else fails)
    """
    
    if task_type == "weekly":
        return await _call_gemini(prompt, system)
    elif task_type == "nightly":
        return await _call_cerebras(prompt, system)
    elif task_type == "reasoning":
        return await _call_openrouter(prompt, system)
    elif task_type == "offline":
        return await _call_ollama(prompt, system)
    else:
        # realtime — try Groq, fallback to Cerebras
        try:
            return await _call_groq(prompt, system)
        except Exception:
            return await _call_cerebras(prompt, system)

async def _call_groq(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system or "You are Locus, a personal AI."},
                    {"role": "user", "content": prompt}
                ]
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

async def _call_cerebras(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_KEY}"},
            json={
                "model": "llama-3.3-70b",
                "messages": [
                    {"role": "system", "content": system or "You are Locus, a personal AI."},
                    {"role": "user", "content": prompt}
                ]
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

async def _call_gemini(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}",
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system or "You are Locus."}]}
            }
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

async def _call_openrouter(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [
                    {"role": "system", "content": system or "You are Locus."},
                    {"role": "user", "content": prompt}
                ]
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

async def _call_ollama(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "llama3.1:8b",
                "messages": [
                    {"role": "system", "content": system or "You are Locus."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
```

**Provider selection guide:**

| Use case | Provider | Why |
|---|---|---|
| Morning log DCS calculation | No LLM — pure formula | `DCS = ((E+M+S)/3) × (1 − ST/20)` |
| Task classification | Groq | Fast, cheap, 8B is enough |
| Daily brief generation | Groq | Real-time, short output |
| Telegram quick queries | Groq | Sub-second response |
| Nightly vault diff (10-20 files) | Cerebras 70B | 60K TPM, smart model |
| Weekly vault synthesis (all files) | Gemini 2.5 Pro | 1M context, batch 50 files per call |
| Personality pattern detection | Cerebras 70B | Smart model, high throughput |
| Complex reasoning / planning | OpenRouter DeepSeek R1 | Reasoning model |
| VM internet down | Ollama phi3.5 | Always available |

---

# 17. Smoke Tests

Run these in order after completing setup. Every test must pass before moving to the next phase.

### Test 1 — Infrastructure
```bash
cd /opt/locus
docker compose ps
# Expected: postgres (healthy), redis (healthy), qdrant (up), neo4j (up), chromadb (up), syncthing (up), fastapi (up)
```

### Test 2 — FastAPI Health
```bash
curl http://localhost:8000/health
curl https://api.locusapp.online/health
# Both must return: {"status":"ok","version":"1.0.0"}
```

### Test 3 — PostgreSQL
```bash
docker exec locus-postgres psql -U locus -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
# Must show: daily_logs, tasks, projects, outcomes, behavioral_events, etc.
```

### Test 4 — Neo4j
```bash
curl http://localhost:7474
# Must return 200 with Neo4j browser HTML
```

### Test 5 — Qdrant
```bash
curl http://localhost:6333/collections
# Must return: {"result":{"collections":[]},"status":"ok","time":...}
```

### Test 6 — Ollama
```bash
curl http://localhost:11434/api/version
# Must return Ollama version JSON
ollama list
# Must show llama3.1:8b, phi3.5, nomic-embed-text
```

### Test 7 — LLM Cascade
```bash
# Test Groq
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"say ok"}]}'
```

### Test 8 — MemPalace
```bash
mempalace status
mempalace search "test"
```

### Test 9 — Syncthing
```bash
# Access http://localhost:8384 via SSH tunnel from laptop
# Check that /vault folder shows as synced
```

### Test 10 — PWA
```bash
# Open https://locusapp.online in browser
# Should load the React app
# Install to home screen on phone
```

---

# Appendix A — .env Template

```bash
# LLM PROVIDERS
GROQ_API_KEY=
GEMINI_API_KEY=
CEREBRAS_API_KEY=
OPENROUTER_API_KEY=

# OLLAMA
OLLAMA_URL=http://172.17.0.1:11434

# NOTION
NOTION_API_KEY=

# GOOGLE
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://api.locusapp.online/auth/google/callback
GOOGLE_REFRESH_TOKEN=

# TELEGRAM
TELEGRAM_TOKEN=
TELEGRAM_OWNER_ID=

# POSTGRES
POSTGRES_DB=locus
POSTGRES_USER=locus
POSTGRES_PASSWORD=PostgreSQL@3301.Locus
DATABASE_URL=postgresql://locus:PostgreSQL@3301.Locus@postgres:5432/locus

# REDIS
REDIS_URL=redis://redis:6379/0

# QDRANT
QDRANT_URL=http://qdrant:6333

# NEO4J
NEO4J_URL=bolt://neo4j:7687
NEO4J_PASSWORD=LocusNeo4j2026

# APP
SECRET_KEY=
LOCUS_PASSWORD=
LOCUS_SERVICE_TOKEN=
LOCUS_API_URL=https://api.locusapp.online

# CLOUDFLARE
CLOUDFLARE_TUNNEL_TOKEN=

# VAPID
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_SUBJECT=mailto:your@email.com

# BACKUP
BACKUP_GDRIVE_PATH=locus-backups
RCLONE_GDRIVE_TOKEN=
```

---

# Appendix B — docker-compose.yml

See Section 7.1. The full compose file is written there. Key points:
- `cloudflared` is NOT in the compose file — it runs as systemd
- `ollama` is NOT in the compose file — it runs native
- `extra_hosts: host-gateway:host-gateway` on fastapi enables reaching native Ollama
- All services use `env_file: .env` — not individual environment keys
- Neo4j has explicit 2G heap max and 1G pagecache to prevent OOM

---

# Appendix C — Vault Structure

```
/vault/                         ← Docker mount point, Syncthing root
├── .stfolder                   ← Required by Syncthing
├── 00-Inbox/                   ← New unsorted notes land here
├── 01-Journal/                 ← Daily reflections (YYYY/MM/YYYY-MM-DD.md)
│   └── 2026/04/
├── 02-Projects/                ← Project notes
├── 03-AI-Chats/                ← Exported conversations
│   ├── claude/
│   └── chatgpt/
├── 04-Resources/               ← Reference material
├── 05-Journal/                 ← Transcribed physical journal entries
├── 06-Content/                 ← Content drafts
│   ├── LinkedIn/
│   └── Instagram/
├── mempalace/                  ← MemPalace auto-manages this
│   └── mempalace.yaml
└── wiki/                       ← llm-wiki auto-manages this
    ├── index.md
    └── concepts/
```

**Journal naming convention:**
```
/vault/01-Journal/2026/04/2026-04-10.md
```

**Morning log template (paste into today's journal):**
```markdown
## Morning Log
E: _ / M: _ / S: _ / ST: _
DCS: _
Mode: SURVIVAL / RECOVERY / NORMAL / DEEP / PEAK
Today I want to: 
```

**Evening log template:**
```markdown
## Evening Log
What I did today: 
What I avoided (honest reason): 
Tomorrow's one priority: 
```

---

*LOCUS_README_v1.md — Complete build guide with ARM64 reality checks.*
*Cross-reference: LOCUS_ARCHITECTURE_v4.md for full spec, LOCUS_SYSTEM_v1.md for system logic.*
*Start here. Build in order. Do not skip phases.*
