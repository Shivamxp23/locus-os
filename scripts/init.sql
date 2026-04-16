CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    checkin_type TEXT CHECK (checkin_type IN ('morning','afternoon','evening','night')),
    mood INT CHECK (mood BETWEEN 1 AND 10),
    energy INT CHECK (energy BETWEEN 1 AND 10),
    focus INT CHECK (focus BETWEEN 1 AND 10),
    stress INT CHECK (stress BETWEEN 1 AND 10),
    sleep_hours FLOAT,
    sleep_quality INT CHECK (sleep_quality BETWEEN 1 AND 10),
    exercise_minutes INT DEFAULT 0,
    journal TEXT,
    dcs FLOAT,
    mode TEXT,
    intention TEXT,
    did_today TEXT,
    avoided TEXT,
    avoided_reason TEXT,
    tomorrow_priority TEXT,
    reflection TEXT,
    sleep_intention TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date, checkin_type)
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    priority INT DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    urgency INT DEFAULT 5 CHECK (urgency BETWEEN 1 AND 10),
    difficulty INT DEFAULT 5 CHECK (difficulty BETWEEN 1 AND 10),
    estimated_hours FLOAT DEFAULT 1.0,
    actual_hours FLOAT,
    quality INT CHECK (quality BETWEEN 1 AND 10),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done','deferred','killed')),
    deferral_count INT DEFAULT 0,
    scheduled_date DATE,
    completed_at TIMESTAMPTZ,
    parent_project_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','completed','abandoned','done','killed')),
    start_date DATE DEFAULT CURRENT_DATE,
    target_date DATE,
    difficulty INT CHECK (difficulty BETWEEN 1 AND 10),
    target_hours_weekly FLOAT,
    deadline DATE,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS behavioral_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    data TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS personality_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    snapshot_date DATE NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_date UNIQUE (user_id, snapshot_date)
);

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

CREATE TABLE IF NOT EXISTS captures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    text TEXT NOT NULL,
    source TEXT CHECK (source IN ('pwa','telegram')),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(date, checkin_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_type ON behavioral_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_captures_processed ON captures(processed, created_at);
