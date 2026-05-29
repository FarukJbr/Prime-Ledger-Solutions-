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
-- BOARD MEMBERS - חברי דירקטוריון
-- ============================================
CREATE TABLE IF NOT EXISTS board_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    title_he TEXT NOT NULL,
    title_en TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('chairman','director','ceo','deputy_ceo')),
    expertise TEXT,
    is_ai BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- DEPARTMENTS - מחלקות
-- ============================================
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT UNIQUE NOT NULL,
    name_he TEXT NOT NULL,
    name_en TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    manager_title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- EMPLOYEES - עובדים
-- ============================================
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    title_he TEXT NOT NULL,
    title_en TEXT NOT NULL,
    department_code TEXT REFERENCES departments(code),
    is_manager BOOLEAN DEFAULT FALSE,
    is_ai BOOLEAN DEFAULT TRUE,
    personality TEXT,
    expertise TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- DISCUSSIONS - דיונים
-- ============================================
CREATE TABLE IF NOT EXISTS discussions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    discussion_type TEXT DEFAULT 'team' CHECK (discussion_type IN ('team','management','board','committee','employee')),
    task_id UUID REFERENCES tasks(id),
    participants JSONB DEFAULT '[]',
    messages JSONB DEFAULT '[]',
    status TEXT DEFAULT 'active' CHECK (status IN ('active','completed','archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ACTIVITIES - פעילות
-- ============================================
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_type TEXT NOT NULL CHECK (activity_type IN ('task_created','task_completed','meeting_held','discussion','deliverable_submitted','deliverable_approved','published')),
    title TEXT NOT NULL,
    description TEXT,
    department TEXT,
    employee_name TEXT,
    task_id UUID REFERENCES tasks(id),
    deliverable_id UUID REFERENCES deliverables(id),
    meeting_id UUID REFERENCES meetings(id),
    metadata JSONB DEFAULT '{}',
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
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_discussions_status ON discussions(status);

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

CREATE TRIGGER update_discussions_updated_at BEFORE UPDATE ON discussions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SEED DATA: Board Members - חברי דירקטוריון
-- ============================================
INSERT INTO board_members (name, title_he, title_en, role, expertise, is_ai)
SELECT * FROM (VALUES
    ('פארוק ג''אבר', 'יו"ר דירקטוריון', 'Chairman of the Board', 'chairman', 'Entrepreneurship, Business Strategy, Investments', FALSE),
    ('אהרן לוי', 'דירקטור', 'Board Director', 'director', 'Financial Strategy, Risk Management, M&A', TRUE),
    ('ד"ר שרה כהן', 'דירקטורית', 'Board Director', 'director', 'Business Strategy, Market Expansion, Growth', TRUE),
    ('יורם אברהם', 'דירקטור', 'Board Director', 'director', 'Corporate Law, Governance, Regulatory Affairs', TRUE)
) AS v(name, title_he, title_en, role, expertise, is_ai)
WHERE NOT EXISTS (SELECT 1 FROM board_members LIMIT 1);

-- ============================================
-- SEED DATA: Departments - מחלקות
-- ============================================
INSERT INTO departments (code, name_he, name_en, manager_name, manager_title, description)
SELECT * FROM (VALUES
    ('ceo', 'הנהלה', 'Management', 'דוד אזולאי', 'מנכ"ל', 'General management and company coordination'),
    ('cfo', 'כספים', 'Finance', 'רונית אברהמי', 'מנהלת כספים', 'Financial planning and management'),
    ('marketing', 'שיווק ופרסום', 'Marketing & Advertising', 'דניאל כהן', 'מנהל שיווק', 'Marketing campaigns and brand strategy'),
    ('sales', 'מכירות', 'Sales', 'מיכל לוי', 'מנהלת מכירות', 'Sales and client acquisition'),
    ('legal', 'משפטי', 'Legal', 'עו"ד יוסי מזרחי', 'יועץ משפטי', 'Legal advisory and compliance'),
    ('cto', 'טכנולוגיה', 'Technology', 'אריאל בן-ישראל', 'מנהל טכנולוגיה', 'Technology and development'),
    ('content', 'תוכן ועיצוב', 'Content & Design', 'נועה שלום', 'מנהלת תוכן', 'Content creation and design'),
    ('pr', 'יח"צ ושירות לקוחות', 'PR & Customer Service', 'שירה בן-אמי', 'מנהלת יח"צ', 'Public relations and customer service'),
    ('compliance', 'ציות', 'Compliance', 'עמית הרשקוביץ', 'קצין ציות', 'Regulatory compliance and risk')
) AS v(code, name_he, name_en, manager_name, manager_title, description)
WHERE NOT EXISTS (SELECT 1 FROM departments LIMIT 1);

-- ============================================
-- SEED DATA: Employees - עובדים
-- ============================================
INSERT INTO employees (name, title_he, title_en, department_code, is_manager, personality, expertise)
SELECT * FROM (VALUES
    ('דוד אזולאי', 'מנכ"ל', 'CEO', 'ceo', TRUE, 'ישיר, מקצועי, לא מבזבז מילים. מקבל החלטות מהיר.', 'Strategy, Operations, Leadership'),
    ('יעל ברק', 'עוזרת מנכ"ל', 'CEO Assistant', 'ceo', FALSE, 'מסודרת, יעילה, תמיד מוכנה.', 'Administration, Coordination'),
    ('רונית אברהמי', 'מנהלת כספים', 'CFO', 'cfo', TRUE, 'זהירה, מספרים ועובדות בלבד. לא מסכימה לסיכון מיותר.', 'Finance, Budgeting, Investments'),
    ('גיא שפירא', 'רואה חשבון', 'Accountant', 'cfo', FALSE, 'מדויק, שקט, עובד לפי ספר.', 'Accounting, Tax, Reports'),
    ('הילה כץ', 'אנליסטית פיננסית', 'Financial Analyst', 'cfo', FALSE, 'חדה, מוצאת הזדמנויות במספרים.', 'Analysis, Forecasting'),
    ('דניאל כהן', 'מנהל שיווק', 'Marketing Manager', 'marketing', TRUE, 'יצירתי, נלהב, לפעמים יותר מדי. אוהב רעיונות גדולים.', 'Marketing, Campaigns, Brand'),
    ('משה מתן', 'מומחה דיגיטל', 'Digital Specialist', 'marketing', FALSE, 'מומחה ברשתות חברתיות, תמיד עם הטרנד האחרון.', 'Social Media, SEO, Analytics'),
    ('ליאת שמיר', 'מנהלת קמפיינים', 'Campaign Manager', 'marketing', FALSE, 'ממוקדת תוצאות, עובדת לפי נתונים.', 'Campaign Management, PPC'),
    ('מיכל לוי', 'מנהלת מכירות', 'Sales Manager', 'sales', TRUE, 'אסרטיבית, ממוקדת תוצאות. לא מוותרת על עסקה.', 'Sales, Negotiation, CRM'),
    ('יובל גרינברג', 'נציג מכירות בכיר', 'Senior Sales Rep', 'sales', FALSE, 'קשוב ללקוחות, בונה אמון לאט.', 'Client Relations, B2B'),
    ('תמר אביב', 'מנהלת לקוחות', 'Account Manager', 'sales', FALSE, 'שומרת על קשר חמים עם לקוחות.', 'Account Management'),
    ('עו"ד יוסי מזרחי', 'יועץ משפטי', 'Legal Advisor', 'legal', TRUE, 'פורמלי, תמיד מוסיף אזהרות. "צריך לבדוק את זה לפני..."', 'Corporate Law, Contracts'),
    ('עו"ד דינה פרץ', 'עורכת דין', 'Attorney', 'legal', FALSE, 'מדוקדקת, קוראת כל מילה בחוזה.', 'Contract Review, IP Law'),
    ('אריאל בן-ישראל', 'מנהל טכנולוגיה', 'CTO', 'cto', TRUE, 'טכני, קצר, מדבר בקוד. "זה פשוט - שלושה שלבים..."', 'Architecture, AI, Development'),
    ('עידן גולדברג', 'מפתח בכיר', 'Senior Developer', 'cto', FALSE, 'אוהב אתגרים טכניים, עובד לילות.', 'Python, React, APIs'),
    ('מאיה רוזן', 'מנהלת QA', 'QA Manager', 'cto', FALSE, 'כל באג מפריע לה אישית.', 'Testing, Quality Assurance'),
    ('נועה שלום', 'מנהלת תוכן', 'Content Manager', 'content', TRUE, 'אמנותית, פרפקציוניסטית. "עוד קצת ואז זה מושלם."', 'Content Strategy, Copywriting'),
    ('ירון פלד', 'מעצב גרפי', 'Graphic Designer', 'content', FALSE, 'ויזואלי, מדבר בצבעים ופונטים.', 'Graphic Design, Branding'),
    ('עדי אלון', 'כותבת תוכן', 'Content Writer', 'content', FALSE, 'יצירתית, מוצאת את הסיפור בכל דבר.', 'Copywriting, SEO Content'),
    ('שירה בן-אמי', 'מנהלת יח"צ', 'PR Manager', 'pr', TRUE, 'חברותית, אמפתית. תמיד חושבת על הרגשת הלקוח.', 'PR, Crisis Management, Media'),
    ('אסף נחמיאס', 'נציג שירות בכיר', 'Senior CS Rep', 'pr', FALSE, 'סבלני, תמיד מוצא פתרון.', 'Customer Service, Complaints'),
    ('כרמל ביטון', 'מנהלת מדיה', 'Media Manager', 'pr', FALSE, 'קשרי מדיה ועיתונאים.', 'Media Relations, Press'),
    ('עמית הרשקוביץ', 'קצין ציות', 'CCO', 'compliance', TRUE, 'שמרני, תמיד אומר "רגע, בדקתי את התקנות..."', 'Compliance, Risk, Regulation'),
    ('נגה פישר', 'מנתחת סיכונים', 'Risk Analyst', 'compliance', FALSE, 'חדה, רואה סיכונים לפני שקורים.', 'Risk Assessment'),
    ('בועז שם-טוב', 'מומחה רגולציה', 'Regulatory Expert', 'compliance', FALSE, 'מכיר כל תקנה בעל פה.', 'Regulations, Audit')
) AS v(name, title_he, title_en, department_code, is_manager, personality, expertise)
WHERE NOT EXISTS (SELECT 1 FROM employees LIMIT 1);
