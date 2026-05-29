-- ============================================
-- GEVER MANAGEMENT SYSTEM - Database Schema
-- גבר יזמות ייעוץ עסקי והשקעות
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TASKS - משימות
-- ============================================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    created_by TEXT DEFAULT 'chairman',        -- מי יצר
    assigned_to TEXT NOT NULL,                  -- איזה מחלקה
    status TEXT DEFAULT 'pending'               -- pending | in_progress | review | approved | rejected | published
        CHECK (status IN ('pending','in_progress','review','approved','rejected','published')),
    priority TEXT DEFAULT 'normal'
        CHECK (priority IN ('low','normal','high','urgent')),
    language TEXT DEFAULT 'he',
    metadata JSONB DEFAULT '{}',               -- מידע נוסף
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- DELIVERABLES - תוצרים
-- ============================================
CREATE TABLE IF NOT EXISTS deliverables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    department TEXT NOT NULL,                   -- המחלקה שהגישה
    agent_role TEXT NOT NULL,                   -- תפקיד הסוכן
    content TEXT NOT NULL,                      -- התוכן שנוצר
    content_type TEXT DEFAULT 'text'
        CHECK (content_type IN ('text','html','markdown','json','code','image_prompt')),
    version INTEGER DEFAULT 1,
    chairman_feedback TEXT,
    status TEXT DEFAULT 'pending_review'
        CHECK (status IN ('pending_review','approved','rejected','revision_requested')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- MEETINGS - פגישות/דיונים
-- ============================================
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    meeting_type TEXT DEFAULT 'department'
        CHECK (meeting_type IN ('board','management','department','emergency')),
    participants JSONB DEFAULT '[]',            -- רשימת משתתפים
    agenda TEXT,                                -- סדר יום
    transcript JSONB DEFAULT '[]',             -- תמליל הדיון
    decisions JSONB DEFAULT '[]',              -- החלטות שהתקבלו
    action_items JSONB DEFAULT '[]',           -- משימות שנפתחו
    status TEXT DEFAULT 'scheduled'
        CHECK (status IN ('scheduled','in_progress','completed','cancelled')),
    scheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- PUBLICATIONS - פרסומים
-- ============================================
CREATE TABLE IF NOT EXISTS publications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deliverable_id UUID REFERENCES deliverables(id),
    task_id UUID REFERENCES tasks(id),
    platform TEXT NOT NULL
        CHECK (platform IN ('facebook','instagram','tiktok','all')),
    content TEXT NOT NULL,
    media_urls JSONB DEFAULT '[]',
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    platform_post_id TEXT,                      -- ID מהפלטפורמה
    status TEXT DEFAULT 'scheduled'
        CHECK (status IN ('scheduled','published','failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- AGENT MESSAGES - הודעות בין סוכנים
-- ============================================
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    message TEXT NOT NULL,
    message_type TEXT DEFAULT 'task'
        CHECK (message_type IN ('task','feedback','question','report','decision')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CHAIRMAN INSTRUCTIONS - הוראות יו"ר
-- ============================================
CREATE TABLE IF NOT EXISTS chairman_instructions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instruction TEXT NOT NULL,
    language TEXT DEFAULT 'he',
    processed BOOLEAN DEFAULT FALSE,
    task_id UUID REFERENCES tasks(id),          -- המשימה שנוצרה
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_deliverables_task_id ON deliverables(task_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_status ON deliverables(status);
CREATE INDEX IF NOT EXISTS idx_publications_status ON publications(status);
CREATE INDEX IF NOT EXISTS idx_agent_messages_task_id ON agent_messages(task_id);

-- ============================================
-- AUTO UPDATE updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deliverables_updated_at BEFORE UPDATE ON deliverables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
