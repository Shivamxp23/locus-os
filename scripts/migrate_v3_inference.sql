-- migrate_v3_inference.sql
-- Run on VM:  docker exec -i locus-postgres psql -U locus -d locus < scripts/migrate_v3_inference.sql

-- ═══════════════════════════════════════════════
--  SYSTEM 2: Detected Patterns (Multi-Horizon)
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS detected_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    horizon INT NOT NULL CHECK (horizon BETWEEN 1 AND 5),
    pattern_type TEXT NOT NULL,  -- avoidance, momentum, energy, mood, faction_neglect, goal_drift, exam_behavior, creative_burst, etc.
    description TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    first_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_confirmed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmation_count INT NOT NULL DEFAULT 1,
    supporting_event_ids JSONB DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'false_positive')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_detected_patterns_status ON detected_patterns(status, confidence);
CREATE INDEX IF NOT EXISTS idx_detected_patterns_type ON detected_patterns(pattern_type, last_confirmed_at);
CREATE INDEX IF NOT EXISTS idx_detected_patterns_horizon ON detected_patterns(horizon);

-- ═══════════════════════════════════════════════
--  SYSTEM 2: User Identity Profile (single row)
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_identity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'shivam' UNIQUE,
    stated_life_goals JSONB DEFAULT '{}'::jsonb,
    active_factions JSONB DEFAULT '{"health": 0.25, "leverage": 0.25, "craft": 0.25, "expression": 0.25}'::jsonb,
    known_behavioral_tendencies JSONB DEFAULT '{}'::jsonb,
    peak_performance_windows JSONB DEFAULT '{}'::jsonb,
    known_stressors JSONB DEFAULT '[]'::jsonb,
    known_energizers JSONB DEFAULT '[]'::jsonb,
    communication_style_preference JSONB DEFAULT '{"tone": "direct", "no_sycophancy": true, "push_back_allowed": true, "blunt": true}'::jsonb,
    exam_behavioral_signature JSONB DEFAULT '{}'::jsonb,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    update_source TEXT DEFAULT 'manual' CHECK (update_source IN ('manual', 'ai_inference', 'both')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed the initial identity row
INSERT INTO user_identity (user_id, stated_life_goals, known_stressors, known_energizers, peak_performance_windows, known_behavioral_tendencies)
VALUES (
    'shivam',
    '{"goals": ["Technical mastery in CS/AI/ML", "Financial independence via Monevo", "Creative filmmaking and storytelling", "Physical and mental resilience"]}'::jsonb,
    '["exam_periods", "sleep_deficit", "task_overload", "deadline_pressure"]'::jsonb,
    '["deep_coding_sessions", "filmmaking", "late_night_flow_states", "completing_deferred_tasks"]'::jsonb,
    '{"late_night": 0.82, "evening": 0.65, "afternoon": 0.45, "morning": 0.31}'::jsonb,
    '{"impulse_work": 0.7, "deadline_driven": 0.85, "avoidance_creative_when_stressed": 0.6, "late_night_preference": 0.8}'::jsonb
)
ON CONFLICT (user_id) DO NOTHING;

-- ═══════════════════════════════════════════════
--  SYSTEM 2/3: State Snapshots (every 6 hours)
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS state_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_created ON state_snapshots(created_at);

-- ═══════════════════════════════════════════════
--  SYSTEM 3: Daily Synthesis
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS daily_synthesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    synthesis_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_of_day_synthesis TEXT,
    key_insight TEXT,
    recommended_framing TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, synthesis_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_synthesis_date ON daily_synthesis(synthesis_date);

-- ═══════════════════════════════════════════════
--  HEBBIAN: Reward Signals
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS reward_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    interaction_id TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('thumbs_up', 'thumbs_down')),
    pathways JSONB DEFAULT '[]'::jsonb,
    source TEXT DEFAULT 'telegram' CHECK (source IN ('telegram', 'pwa', 'inner_loop')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reward_signals_created ON reward_signals(created_at);

-- ═══════════════════════════════════════════════
--  SYSTEM 3: Morning Briefing Queue
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS morning_briefing_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    observation_text TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    source TEXT DEFAULT 'inner_loop',
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_morning_briefing_delivered ON morning_briefing_queue(delivered, created_at);

SELECT 'Migration v3 (Inference Engine) complete' AS status;
