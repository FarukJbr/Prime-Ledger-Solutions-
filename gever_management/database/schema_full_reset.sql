-- ============================================================
-- GEVER MANAGEMENT SYSTEM - FULL RESET & REBUILD
-- גבר יזמות ייעוץ עסקי והשקעות
-- הרץ את כל הקוד הזה ב-SQL Editor של Supabase
-- ============================================================

-- ── שלב 1: מחיקת כל הטבלאות הקיימות ──────────────────────
DROP TABLE IF EXISTS activities          CASCADE;
DROP TABLE IF EXISTS discussions         CASCADE;
DROP TABLE IF EXISTS employees           CASCADE;
DROP TABLE IF EXISTS departments         CASCADE;
DROP TABLE IF EXISTS board_members       CASCADE;
DROP TABLE IF EXISTS chairman_instructions CASCADE;
DROP TABLE IF EXISTS agent_messages      CASCADE;
DROP TABLE IF EXISTS publications        CASCADE;
DROP TABLE IF EXISTS deliverables        CASCADE;
DROP TABLE IF EXISTS tasks               CASCADE;

-- ── שלב 2: מחיקת פונקציות קיימות ─────────────────────────
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ── שלב 3: הפעלת UUID extension ───────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
-- טבלה 1: TASKS - משימות
-- ============================================================
CREATE TABLE tasks (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title        TEXT NOT NULL,
    description  TEXT NOT NULL,
    created_by   TEXT DEFAULT 'chairman',
    assigned_to  TEXT NOT NULL,
    status       TEXT DEFAULT 'pending'
                 CHECK (status IN ('pending','in_progress','review','approved','rejected','published')),
    priority     TEXT DEFAULT 'normal'
                 CHECK (priority IN ('low','normal','high','urgent')),
    language     TEXT DEFAULT 'he',
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 2: DELIVERABLES - תוצרים
-- ============================================================
CREATE TABLE deliverables (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id          UUID REFERENCES tasks(id) ON DELETE CASCADE,
    department       TEXT NOT NULL,
    agent_role       TEXT NOT NULL,
    content          TEXT NOT NULL,
    content_type     TEXT DEFAULT 'text'
                     CHECK (content_type IN ('text','html','markdown','json','code','image_prompt')),
    version          INTEGER DEFAULT 1,
    chairman_feedback TEXT,
    status           TEXT DEFAULT 'pending_review'
                     CHECK (status IN ('pending_review','approved','rejected','revision_requested')),
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 3: MEETINGS - פגישות
-- ============================================================
CREATE TABLE meetings (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title        TEXT NOT NULL,
    meeting_type TEXT DEFAULT 'department'
                 CHECK (meeting_type IN ('board','management','department','emergency')),
    participants JSONB DEFAULT '[]',
    agenda       TEXT,
    transcript   JSONB DEFAULT '[]',
    decisions    JSONB DEFAULT '[]',
    action_items JSONB DEFAULT '[]',
    status       TEXT DEFAULT 'scheduled'
                 CHECK (status IN ('scheduled','in_progress','completed','cancelled')),
    scheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 4: PUBLICATIONS - פרסומים
-- ============================================================
CREATE TABLE publications (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deliverable_id   UUID REFERENCES deliverables(id),
    task_id          UUID REFERENCES tasks(id),
    platform         TEXT NOT NULL
                     CHECK (platform IN ('facebook','instagram','tiktok','all')),
    content          TEXT NOT NULL,
    media_urls       JSONB DEFAULT '[]',
    scheduled_at     TIMESTAMPTZ,
    published_at     TIMESTAMPTZ,
    platform_post_id TEXT,
    status           TEXT DEFAULT 'scheduled'
                     CHECK (status IN ('scheduled','published','failed')),
    error_message    TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 5: AGENT_MESSAGES - הודעות בין סוכני AI
-- ============================================================
CREATE TABLE agent_messages (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id      UUID REFERENCES tasks(id) ON DELETE CASCADE,
    from_agent   TEXT NOT NULL,
    to_agent     TEXT NOT NULL,
    message      TEXT NOT NULL,
    message_type TEXT DEFAULT 'task'
                 CHECK (message_type IN ('task','feedback','question','report','decision')),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 6: CHAIRMAN_INSTRUCTIONS - הוראות יו"ר
-- ============================================================
CREATE TABLE chairman_instructions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instruction TEXT NOT NULL,
    language    TEXT DEFAULT 'he',
    processed   BOOLEAN DEFAULT FALSE,
    task_id     UUID REFERENCES tasks(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 7: BOARD_MEMBERS - חברי דירקטוריון
-- ============================================================
CREATE TABLE board_members (
    id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name      TEXT NOT NULL,
    title_he  TEXT NOT NULL,
    title_en  TEXT NOT NULL,
    role      TEXT NOT NULL
              CHECK (role IN ('chairman','director','ceo','deputy_ceo')),
    expertise TEXT,
    is_ai     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 8: DEPARTMENTS - מחלקות
-- ============================================================
CREATE TABLE departments (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code         TEXT UNIQUE NOT NULL,
    name_he      TEXT NOT NULL,
    name_en      TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    manager_title TEXT NOT NULL,
    description  TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 9: EMPLOYEES - עובדים
-- ============================================================
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    title_he        TEXT NOT NULL,
    title_en        TEXT NOT NULL,
    department_code TEXT REFERENCES departments(code),
    is_manager      BOOLEAN DEFAULT FALSE,
    is_ai           BOOLEAN DEFAULT TRUE,
    personality     TEXT,
    expertise       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 10: DISCUSSIONS - דיונים
-- ============================================================
CREATE TABLE discussions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title            TEXT NOT NULL,
    discussion_type  TEXT DEFAULT 'team'
                     CHECK (discussion_type IN ('team','management','board','committee','employee')),
    task_id          UUID REFERENCES tasks(id),
    participants     JSONB DEFAULT '[]',
    messages         JSONB DEFAULT '[]',
    status           TEXT DEFAULT 'active'
                     CHECK (status IN ('active','completed','archived')),
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- טבלה 11: ACTIVITIES - יומן פעילות
-- ============================================================
CREATE TABLE activities (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_type  TEXT NOT NULL
                   CHECK (activity_type IN (
                       'task_created','task_completed','meeting_held',
                       'discussion','deliverable_submitted',
                       'deliverable_approved','published'
                   )),
    title          TEXT NOT NULL,
    description    TEXT,
    department     TEXT,
    employee_name  TEXT,
    task_id        UUID REFERENCES tasks(id),
    deliverable_id UUID REFERENCES deliverables(id),
    meeting_id     UUID REFERENCES meetings(id),
    metadata       JSONB DEFAULT '{}',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- אינדקסים לביצועים
-- ============================================================
CREATE INDEX idx_tasks_status         ON tasks(status);
CREATE INDEX idx_tasks_assigned_to    ON tasks(assigned_to);
CREATE INDEX idx_tasks_created_at     ON tasks(created_at DESC);
CREATE INDEX idx_deliverables_task    ON deliverables(task_id);
CREATE INDEX idx_deliverables_status  ON deliverables(status);
CREATE INDEX idx_publications_status  ON publications(status);
CREATE INDEX idx_agent_messages_task  ON agent_messages(task_id);
CREATE INDEX idx_activities_created   ON activities(created_at DESC);
CREATE INDEX idx_discussions_status   ON discussions(status);


-- ============================================================
-- פונקציה לעדכון updated_at אוטומטי
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_deliverables_updated_at
    BEFORE UPDATE ON deliverables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_discussions_updated_at
    BEFORE UPDATE ON discussions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- DATA: חברי דירקטוריון
-- ============================================================
INSERT INTO board_members (name, title_he, title_en, role, expertise, is_ai) VALUES
    ('פארוק ג''אבר',    'יו"ר דירקטוריון', 'Chairman of the Board', 'chairman', 'Entrepreneurship, Business Strategy, Investments', FALSE),
    ('אהרן לוי',        'דירקטור',          'Board Director',         'director', 'Financial Strategy, Risk Management, M&A',         TRUE),
    ('ד"ר שרה כהן',    'דירקטורית',        'Board Director',         'director', 'Business Strategy, Market Expansion, Growth',       TRUE),
    ('יורם אברהם',      'דירקטור',          'Board Director',         'director', 'Corporate Law, Governance, Regulatory Affairs',     TRUE);


-- ============================================================
-- DATA: מחלקות
-- ============================================================
INSERT INTO departments (code, name_he, name_en, manager_name, manager_title, description) VALUES
    ('ceo',        'הנהלה',              'Management',          'דוד אזולאי',         'מנכ"ל',            'ניהול כללי ותיאום החברה'),
    ('cfo',        'כספים',              'Finance',             'רונית אברהמי',       'מנהלת כספים',       'תכנון פיננסי וניהול כספי'),
    ('marketing',  'שיווק ופרסום',        'Marketing',           'דניאל כהן',          'מנהל שיווק',        'קמפיינים שיווקיים ואסטרטגיית מותג'),
    ('sales',      'מכירות',             'Sales',               'מיכל לוי',           'מנהלת מכירות',      'מכירות ורכישת לקוחות'),
    ('legal',      'משפטי',              'Legal',               'עו"ד יוסי מזרחי',    'יועץ משפטי',        'ייעוץ משפטי וחוזים'),
    ('cto',        'טכנולוגיה',           'Technology',          'אריאל בן-ישראל',     'מנהל טכנולוגיה',    'פיתוח וטכנולוגיה'),
    ('content',    'תוכן ועיצוב',         'Content & Design',    'נועה שלום',          'מנהלת תוכן',        'יצירת תוכן ועיצוב'),
    ('pr',         'יח"צ ושירות לקוחות', 'PR & Customer Service','שירה בן-אמי',        'מנהלת יח"צ',        'יחסי ציבור ושירות לקוחות'),
    ('compliance', 'ציות',               'Compliance',          'עמית הרשקוביץ',      'קצין ציות',         'ציות רגולטורי וניהול סיכונים');


-- ============================================================
-- DATA: עובדים
-- ============================================================
INSERT INTO employees (name, title_he, title_en, department_code, is_manager, personality, expertise) VALUES

-- ── הנהלה ──────────────────────────────────────────────────
('דוד אזולאי',
 'מנכ"ל', 'CEO', 'ceo', TRUE,
 'ישיר, מקצועי, לא מבזבז מילים. מקבל החלטות מהיר ובטוח בעצמו.',
 'Strategy, Operations, Leadership'),

('יעל ברק',
 'עוזרת מנכ"ל', 'CEO Assistant', 'ceo', FALSE,
 'מסודרת, יעילה, תמיד מוכנה עם המידע הנכון.',
 'Administration, Coordination, Scheduling'),

-- ── כספים ──────────────────────────────────────────────────
('רונית אברהמי',
 'מנהלת כספים', 'CFO', 'cfo', TRUE,
 'זהירה ומדויקת. מספרים ועובדות בלבד. לא מסכימה לסיכון מיותר.',
 'Finance, Budgeting, Investments, Forecasting'),

('גיא שפירא',
 'רואה חשבון', 'Accountant', 'cfo', FALSE,
 'מדויק, שקט, עובד לפי הספר. מוצא טעויות שאחרים מפספסים.',
 'Accounting, Tax, Financial Reports'),

('הילה כץ',
 'אנליסטית פיננסית', 'Financial Analyst', 'cfo', FALSE,
 'חדה ואנליטית. מוצאת הזדמנויות במספרים.',
 'Financial Analysis, Market Research, Forecasting'),

-- ── שיווק ──────────────────────────────────────────────────
('דניאל כהן',
 'מנהל שיווק', 'Marketing Manager', 'marketing', TRUE,
 'יצירתי, נלהב, לפעמים יותר מדי. אוהב רעיונות גדולים ואמיץ.',
 'Marketing Strategy, Brand Management, Campaigns'),

('משה מתן',
 'מומחה דיגיטל', 'Digital Specialist', 'marketing', FALSE,
 'מומחה ברשתות חברתיות. תמיד עם הטרנד האחרון ומביא נתונים.',
 'Social Media, SEO, Digital Advertising, Analytics'),

('ליאת שמיר',
 'מנהלת קמפיינים', 'Campaign Manager', 'marketing', FALSE,
 'ממוקדת תוצאות. עובדת לפי נתונים ולא לפי תחושות.',
 'Campaign Management, PPC, Email Marketing'),

-- ── מכירות ─────────────────────────────────────────────────
('מיכל לוי',
 'מנהלת מכירות', 'Sales Manager', 'sales', TRUE,
 'אסרטיבית, ממוקדת תוצאות. לא מוותרת על עסקה.',
 'Sales Strategy, Negotiation, CRM, Team Management'),

('יובל גרינברג',
 'נציג מכירות בכיר', 'Senior Sales Rep', 'sales', FALSE,
 'קשוב ללקוחות. בונה אמון לאט אבל בטוח.',
 'B2B Sales, Client Relations, Cold Outreach'),

('תמר אביב',
 'מנהלת לקוחות', 'Account Manager', 'sales', FALSE,
 'שומרת על קשר חמים עם לקוחות ותמיד שם בשבילם.',
 'Account Management, Customer Retention, Upselling'),

-- ── משפטי ──────────────────────────────────────────────────
('עו"ד יוסי מזרחי',
 'יועץ משפטי', 'Legal Advisor', 'legal', TRUE,
 'פורמלי ומדוקדק. תמיד מוסיף אזהרות: "צריך לבדוק את זה לפני..."',
 'Corporate Law, Contracts, Business Regulation'),

('עו"ד דינה פרץ',
 'עורכת דין', 'Attorney', 'legal', FALSE,
 'קוראת כל מילה בחוזה. לא עוברת על שום דבר בלי לבדוק.',
 'Contract Review, Intellectual Property, Labor Law'),

-- ── טכנולוגיה ──────────────────────────────────────────────
('אריאל בן-ישראל',
 'מנהל טכנולוגיה', 'CTO', 'cto', TRUE,
 'טכני, קצר, מדבר בקוד. "זה פשוט - שלושה שלבים..."',
 'System Architecture, AI/ML, Development, Cloud'),

('עידן גולדברג',
 'מפתח בכיר', 'Senior Developer', 'cto', FALSE,
 'אוהב אתגרים טכניים. עובד לילות כשיש בעיה מעניינת.',
 'Python, React, Node.js, APIs, Databases'),

('מאיה רוזן',
 'מנהלת QA', 'QA Manager', 'cto', FALSE,
 'כל באג מפריע לה אישית. לא מאשרת שחרור בלי בדיקה מלאה.',
 'Quality Assurance, Testing, Automation, Bug Tracking'),

-- ── תוכן ועיצוב ────────────────────────────────────────────
('נועה שלום',
 'מנהלת תוכן', 'Content Manager', 'content', TRUE,
 'אמנותית ופרפקציוניסטית. "עוד קצת ואז זה מושלם."',
 'Content Strategy, Copywriting, Brand Voice, Editing'),

('ירון פלד',
 'מעצב גרפי', 'Graphic Designer', 'content', FALSE,
 'ויזואלי. מדבר בצבעים, פונטים וגריד.',
 'Graphic Design, Branding, UI/UX, Motion Graphics'),

('עדי אלון',
 'כותבת תוכן', 'Content Writer', 'content', FALSE,
 'יצירתית. מוצאת את הסיפור בכל דבר ויודעת לספר אותו.',
 'Copywriting, SEO Content, Blog, Social Content'),

-- ── יח"צ ושירות לקוחות ─────────────────────────────────────
('שירה בן-אמי',
 'מנהלת יח"צ', 'PR Manager', 'pr', TRUE,
 'חברותית ואמפתית. תמיד חושבת על הרגשת הלקוח.',
 'PR, Crisis Management, Media Relations, Brand Image'),

('אסף נחמיאס',
 'נציג שירות בכיר', 'Senior CS Rep', 'pr', FALSE,
 'סבלני ואכפתי. תמיד מוצא פתרון גם למצבים קשים.',
 'Customer Service, Complaint Resolution, Retention'),

('כרמל ביטון',
 'מנהלת מדיה', 'Media Manager', 'pr', FALSE,
 'מכירה כל עיתונאי ואת הסיפורים שהם אוהבים.',
 'Media Relations, Press Releases, Journalism'),

-- ── ציות ───────────────────────────────────────────────────
('עמית הרשקוביץ',
 'קצין ציות', 'CCO', 'compliance', TRUE,
 'שמרני ואחראי. תמיד אומר "רגע, בדקתי את התקנות..."',
 'Compliance, Risk Management, Regulatory Affairs'),

('נגה פישר',
 'מנתחת סיכונים', 'Risk Analyst', 'compliance', FALSE,
 'חדה. רואה סיכונים לפני שהם קורים.',
 'Risk Assessment, Scenario Analysis, Due Diligence'),

('בועז שם-טוב',
 'מומחה רגולציה', 'Regulatory Expert', 'compliance', FALSE,
 'מכיר כל תקנה בעל פה. לא אוהב הפתעות.',
 'Regulations, Compliance Auditing, Legal Updates');


-- ============================================================
-- אימות - בדיקה שהכל נוצר
-- ============================================================
SELECT 'board_members' AS table_name, COUNT(*) AS rows FROM board_members
UNION ALL
SELECT 'departments',  COUNT(*) FROM departments
UNION ALL
SELECT 'employees',    COUNT(*) FROM employees
UNION ALL
SELECT 'tasks',        COUNT(*) FROM tasks
UNION ALL
SELECT 'deliverables', COUNT(*) FROM deliverables
UNION ALL
SELECT 'discussions',  COUNT(*) FROM discussions
UNION ALL
SELECT 'activities',   COUNT(*) FROM activities
UNION ALL
SELECT 'meetings',     COUNT(*) FROM meetings;
