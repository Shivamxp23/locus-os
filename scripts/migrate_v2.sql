-- /opt/locus/scripts/migrate_v2.sql
-- Run this on the VM after deploying v2:
--   docker exec -i locus-postgres psql -U locus -d locus < scripts/migrate_v2.sql

-- ── Outcomes table (Goal Stack hierarchy) ──
CREATE TABLE IF NOT EXISTS outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','completed','abandoned')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Add outcome_id to projects if not exists ──
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='projects' AND column_name='outcome_id'
    ) THEN
        ALTER TABLE projects ADD COLUMN outcome_id UUID REFERENCES outcomes(id);
    END IF;
END $$;

-- ── Add TWS computed column to tasks (if not exists) ──
-- PostgreSQL doesn't support stored generated columns easily, so we use a trigger
CREATE OR REPLACE FUNCTION compute_tws() RETURNS TRIGGER AS $$
BEGIN
    NEW.tws = ROUND(((NEW.priority * 0.4) + (NEW.urgency * 0.4) + (NEW.difficulty * 0.2))::numeric, 2);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tws_trigger ON tasks;
CREATE TRIGGER tws_trigger
    BEFORE INSERT OR UPDATE OF priority, urgency, difficulty ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION compute_tws();

-- ── Add TWS column if missing ──
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='tasks' AND column_name='tws'
    ) THEN
        ALTER TABLE tasks ADD COLUMN tws FLOAT;
    END IF;
END $$;

-- ── Update existing tasks that have NULL tws ──
UPDATE tasks SET tws = ROUND(((priority * 0.4) + (urgency * 0.4) + (difficulty * 0.2))::numeric, 2)
WHERE tws IS NULL;

-- ── Indexes for new queries ──
CREATE INDEX IF NOT EXISTS idx_tasks_faction ON tasks(faction);
CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_project ON tasks(parent_project_id);
CREATE INDEX IF NOT EXISTS idx_projects_outcome ON projects(outcome_id);
CREATE INDEX IF NOT EXISTS idx_projects_faction ON projects(faction);
CREATE INDEX IF NOT EXISTS idx_outcomes_faction ON outcomes(faction);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_created ON behavioral_events(created_at);

-- ── Seed default outcomes (Shivam's 4-faction life outcomes) ──
INSERT INTO outcomes (user_id, title, description, faction) VALUES
    ('shivam', 'Physical & Mental Resilience', 'Sustainable health foundation: sleep, exercise, stress management, consistency', 'health'),
    ('shivam', 'Financial Independence', 'Build revenue streams, grow Monevo, career capital', 'leverage'),
    ('shivam', 'Technical Mastery', 'CS fundamentals, systems design, AI/ML, full-stack development', 'craft'),
    ('shivam', 'Creative Expression', 'Cinematography, filmmaking, storytelling, philosophy writing', 'expression')
ON CONFLICT DO NOTHING;

SELECT 'Migration v2 complete' AS status;
