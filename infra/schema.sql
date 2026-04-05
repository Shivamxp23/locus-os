CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    hashed_password TEXT,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    genesis_completed BOOLEAN DEFAULT FALSE,
    genesis_data JSONB,
    google_access_token TEXT,
    google_refresh_token TEXT,
    google_token_expiry TIMESTAMPTZ,
    notion_access_token TEXT,
    telegram_chat_id TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    horizon TEXT CHECK (horizon IN ('week','month','quarter','year','lifetime')),
    progress_score FLOAT DEFAULT 0.0 CHECK (progress_score BETWEEN 0 AND 1),
    neo4j_node_id TEXT,
    notion_page_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_stale BOOLEAN DEFAULT FALSE,
    stale_since TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_task_completed TIMESTAMPTZ,
    deadline DATE
);
CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_active ON goals(user_id, is_active);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    goal_id UUID REFERENCES goals(id),
    status TEXT DEFAULT 'active' CHECK (status IN ('planning','active','on_hold','completed')),
    notion_page_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    parent_task_id UUID REFERENCES tasks(id),
    goal_id UUID REFERENCES goals(id),
    project_id UUID REFERENCES projects(id),
    source TEXT CHECK (source IN ('pwa','notion','telegram','graphrag','manual')),
    notion_page_id TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','in_progress','completed','deferred','cancelled')),
    priority_score FLOAT,
    energy_type TEXT CHECK (energy_type IN ('deep','creative','shallow','review')),
    estimated_minutes INTEGER,
    scheduled_at TIMESTAMPTZ,
    deferral_count INTEGER DEFAULT 0,
    deferral_flag TEXT,
    completed_at TIMESTAMPTZ,
    completion_duration_minutes INTEGER,
    engine_annotations TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deadline TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks(goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks(user_id, scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_deferral ON tasks(user_id, deferral_count) WHERE deferral_count >= 3;

CREATE TABLE IF NOT EXISTS behavioral_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    intent TEXT,
    raw_content TEXT,
    normalized_content TEXT,
    summary TEXT,
    topic_tags TEXT[],
    mood_indicator FLOAT,
    energy_required INTEGER,
    goal_tags TEXT[],
    signal_weight FLOAT DEFAULT 1.0,
    task_id UUID REFERENCES tasks(id),
    goal_id UUID REFERENCES goals(id),
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    obsidian_path TEXT,
    processed_by_e2 BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_user ON behavioral_events(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_type ON behavioral_events(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_created ON behavioral_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_e2 ON behavioral_events(processed_by_e2) WHERE processed_by_e2 = FALSE;

CREATE TABLE IF NOT EXISTS daily_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    mood_score FLOAT, energy_score FLOAT, focus_score FLOAT, productivity_score FLOAT,
    tasks_completed INTEGER DEFAULT 0, tasks_deferred INTEGER DEFAULT 0,
    tasks_created INTEGER DEFAULT 0, deep_work_minutes INTEGER DEFAULT 0,
    creative_minutes INTEGER DEFAULT 0, dominant_topic TEXT, dominant_category TEXT,
    obsidian_log_path TEXT,
    UNIQUE(user_id, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_user_date ON daily_metrics(user_id, date DESC);

CREATE TABLE IF NOT EXISTS habits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    frequency TEXT CHECK (frequency IN ('daily','weekdays','weekly','custom')),
    custom_days INTEGER[],
    goal_id UUID REFERENCES goals(id),
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_completed TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS habit_completions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id UUID NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS personality_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    insight_type TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence FLOAT,
    neo4j_node_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    delivery_channel TEXT CHECK (delivery_channel IN ('telegram','pwa','both'))
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_used TEXT NOT NULL,
    model_source TEXT NOT NULL,
    messages JSONB NOT NULL,
    topic_tags TEXT[],
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    obsidian_path TEXT,
    token_count INTEGER
);

CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT CHECK (platform IN ('linkedin','twitter','newsletter','blog')),
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft','pending_approval','approved','published','rejected')),
    content TEXT NOT NULL, title TEXT,
    source_event_ids UUID[], source_insight_ids UUID[], source_obsidian_paths TEXT[],
    approved_at TIMESTAMPTZ, published_at TIMESTAMPTZ, rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(), notion_page_id TEXT
);

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rec_type TEXT CHECK (rec_type IN ('book','article','podcast','video','course','blog')),
    title TEXT NOT NULL, author TEXT, url TEXT,
    relevance_reason TEXT NOT NULL,
    interest_tags TEXT[], goal_tags TEXT[],
    status TEXT DEFAULT 'recommended' CHECK (status IN ('recommended','saved','reading','completed','dismissed')),
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL, client_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL, payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    conflict_detected BOOLEAN DEFAULT FALSE, conflict_resolution TEXT,
    UNIQUE(user_id, client_event_id)
);

CREATE TABLE IF NOT EXISTS personality_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    snapshot_data JSONB NOT NULL,
    version INTEGER DEFAULT 1
);

-- F-001: Morning Metric Logging & F-007: Evening Protocol Logging
CREATE TABLE IF NOT EXISTS daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    energy_score INTEGER CHECK (energy_score BETWEEN 1 AND 10),
    mood_score INTEGER CHECK (mood_score BETWEEN 1 AND 10),
    sleep_score INTEGER CHECK (sleep_score BETWEEN 1 AND 10),
    stress_score INTEGER CHECK (stress_score BETWEEN 1 AND 10),
    time_available FLOAT,
    dcs_score FLOAT,
    mode TEXT CHECK (mode IN ('SURVIVAL','RECOVERY','NORMAL','DEEP_WORK','PEAK')),
    morning_logged_at TIMESTAMPTZ,
    evening_logged_at TIMESTAMPTZ,
    what_i_did TEXT,
    what_i_avoided TEXT,
    tomorrow_priority TEXT,
    UNIQUE(user_id, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_logs(user_id, date DESC);

-- F-010: Link Dump Logging
CREATE TABLE IF NOT EXISTS saved_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_saved_links_user ON saved_links(user_id);

-- F-011: Rough Note / Idea Capture
CREATE TABLE IF NOT EXISTS raw_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    note_type TEXT CHECK (note_type IN ('idea','note','journal')),
    enriched_content TEXT,
    suggested_faction TEXT,
    suggested_project_id UUID,
    obsidian_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_raw_notes_user ON raw_notes(user_id);

-- F-093: Audit Log
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    payload_hash TEXT,
    response_status INTEGER,
    duration_ms INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

-- F-100: LLM Training Data for Fine-tuning
CREATE TABLE IF NOT EXISTS llm_training_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model_used TEXT NOT NULL,
    model_source TEXT NOT NULL,
    reward INTEGER CHECK (reward IN (-1, 0, 1)),
    feedback_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_llm_training_user ON llm_training_data(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_training_reward ON llm_training_data(reward) WHERE reward IS NOT NULL;

-- F-025, F-034: Faction Weekly Metrics
CREATE TABLE IF NOT EXISTS faction_weekly_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    faction TEXT NOT NULL CHECK (faction IN ('health','leverage','craft','expression')),
    week_start DATE NOT NULL,
    target_hours FLOAT DEFAULT 0,
    actual_hours FLOAT DEFAULT 0,
    completion_rate FLOAT DEFAULT 0,
    consistency_score FLOAT DEFAULT 0,
    momentum_score FLOAT,
    lag_score FLOAT DEFAULT 0,
    action_gap FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, faction, week_start)
);
CREATE INDEX IF NOT EXISTS idx_faction_metrics_user_week ON faction_weekly_metrics(user_id, week_start DESC);

-- F-041, F-042: AI Reports
CREATE TABLE IF NOT EXISTS ai_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL CHECK (report_type IN ('weekly_pattern','weekly_self','monthly','quarterly')),
    title TEXT,
    content TEXT NOT NULL,
    week_start DATE,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    delivery_channel TEXT CHECK (delivery_channel IN ('telegram','pwa','both'))
);
CREATE INDEX IF NOT EXISTS idx_ai_reports_user ON ai_reports(user_id, generated_at DESC);
