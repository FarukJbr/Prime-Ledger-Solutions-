"""
Jabr AI Company Management System - api.py
גבר יזמות ייעוץ עסקי והשקעות
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import httpx
import os
import json
import secrets
from datetime import datetime
from typing import Optional
import asyncio

# ─── Config ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_ANON_KEY", "")
COMPANY_NAME      = os.getenv("COMPANY_NAME", "גבר יזמות ייעוץ עסקי והשקעות")
DASHBOARD_USER    = os.getenv("DASHBOARD_USER", "chairman")
DASHBOARD_PASS    = os.getenv("DASHBOARD_PASSWORD", "Prime@2024!")

app = FastAPI(title="Jabr Management System")
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Auth ──────────────────────────────────────────────────────────────────────
def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), DASHBOARD_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), DASHBOARD_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return credentials.username

# ─── Supabase helpers ──────────────────────────────────────────────────────────
async def sb_get(table: str, params: str = ""):
    if not SUPABASE_URL:
        return []
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{SUPABASE_URL}/rest/v1/{table}?{params}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else []

async def sb_insert(table: str, data: dict):
    if not SUPABASE_URL:
        return {"id": "mock"}
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=data,
            timeout=10,
        )
        result = r.json()
        return result[0] if isinstance(result, list) and result else result

async def sb_update(table: str, row_id: str, data: dict):
    if not SUPABASE_URL:
        return {}
    async with httpx.AsyncClient() as c:
        r = await c.patch(
            f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            },
            json=data,
            timeout=10,
        )
        return r.json()

# ─── Claude AI helper ──────────────────────────────────────────────────────────
AGENT_PERSONAS = {
    "ceo":        ("מנכ\"ל", "אתה מנכ\"ל חברת " + COMPANY_NAME + ". אתה מתאם בין מחלקות, מחלק משימות, ומסכם תוצאות. אתה מקצועי, תכליתי, ומוביל לתוצאות."),
    "cfo":        ("מנהל כספים (CFO)", "אתה מנהל הכספים של " + COMPANY_NAME + ". אתה עוסק בתזרים מזומנים, תקציבים, ניתוח עלויות, ודוחות פיננסיים."),
    "marketing":  ("מנהל שיווק", "אתה מנהל השיווק של " + COMPANY_NAME + ". אתה אחראי על קמפיינים, תוכן שיווקי, אסטרטגיה ומיתוג."),
    "sales":      ("מנהל מכירות", "אתה מנהל המכירות של " + COMPANY_NAME + ". אתה מנהל לקוחות, מוביל מכירות, ומציע הצעות מחיר."),
    "legal":      ("יועץ משפטי", "אתה היועץ המשפטי של " + COMPANY_NAME + ". אתה עוסק בחוזים, רגולציה, וייעוץ משפטי עסקי."),
    "cto":        ("מנהל טכנולוגיה (CTO)", "אתה מנהל הטכנולוגיה של " + COMPANY_NAME + ". אתה אחראי על מערכות, פיתוח, ותשתיות טכנולוגיות."),
    "content":    ("מנהל תוכן ועיצוב", "אתה מנהל התוכן והעיצוב של " + COMPANY_NAME + ". אתה יוצר תוכן, פוסטים, עיצובים ומצגות."),
    "pr":         ("מנהל יח\"צ", "אתה מנהל יחסי הציבור של " + COMPANY_NAME + ". אתה אחראי על תדמית, קשרי תקשורת, ופרסומות."),
    "compliance": ("קצין ציות", "אתה קצין הציות של " + COMPANY_NAME + ". אתה עוסק בעמידה בתקנות, בקרת סיכונים, ואחריות תאגידית."),
    "hr":         ("מנהל משאבי אנוש", "אתה מנהל משאבי האנוש של " + COMPANY_NAME + ". אתה אחראי על גיוס, העסקה, רווחת עובדים ונהלים."),
    "chairman":   ("יו\"ר דירקטוריון", "אתה יו\"ר הדירקטוריון של " + COMPANY_NAME + ". אתה מנחה אסטרטגיה ומפקח על הנהלת החברה."),
}

async def ask_claude(role: str, user_message: str, context: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        return f"[{AGENT_PERSONAS.get(role, ('עובד',''))[0]}]: מערכת AI לא מחוברת - נא להגדיר ANTHROPIC_API_KEY"
    
    title, system = AGENT_PERSONAS.get(role, ("עובד AI", "אתה עובד AI מקצועי."))
    full_system = system
    if context:
        full_system += f"\n\nהקשר נוסף:\n{context}"
    
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-opus-4-6",
                "max_tokens": 1500,
                "system": full_system,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
        return f"שגיאת API: {r.status_code}"

# ─── API Routes ────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats(user=Depends(verify_auth)):
    tasks    = await sb_get("tasks",       "select=count")
    done     = await sb_get("tasks",       "select=count&status=eq.done")
    inprog   = await sb_get("tasks",       "select=count&status=eq.in_progress")
    pending  = await sb_get("tasks",       "select=count&status=eq.pending_approval")
    depts    = await sb_get("departments", "select=count")
    employees= await sb_get("employees",   "select=count")
    
    def cnt(x):
        if isinstance(x, list) and x and isinstance(x[0], dict):
            return x[0].get("count", 0)
        return 0
    
    return {
        "tasks_total":    cnt(tasks),
        "tasks_done":     cnt(done),
        "tasks_inprog":   cnt(inprog),
        "tasks_pending":  cnt(pending),
        "departments":    cnt(depts) or 9,
        "employees":      cnt(employees),
    }

@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None, dept: Optional[str] = None, user=Depends(verify_auth)):
    q = "order=created_at.desc&limit=50"
    if status: q += f"&status=eq.{status}"
    if dept:   q += f"&department=eq.{dept}"
    return await sb_get("tasks", q)

@app.post("/api/tasks")
async def create_task(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    task = {
        "title":       body.get("title", ""),
        "description": body.get("description", ""),
        "department":  body.get("department", "ceo"),
        "priority":    body.get("priority", "medium"),
        "status":      "pending",
        "created_by":  user,
        "created_at":  datetime.utcnow().isoformat(),
    }
    result = await sb_insert("tasks", task)
    return result

@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, user=Depends(verify_auth)):
    await sb_update("tasks", task_id, {"status": "approved", "approved_at": datetime.utcnow().isoformat()})
    return {"ok": True}

@app.get("/api/departments")
async def get_departments(user=Depends(verify_auth)):
    rows = await sb_get("departments", "order=name.asc")
    if not rows:
        return [
            {"id":"ceo","name":"מנכ\"ל","icon":"👑","head":"Claude CEO"},
            {"id":"cfo","name":"כספים","icon":"💰","head":"Claude CFO"},
            {"id":"marketing","name":"שיווק","icon":"📣","head":"Claude Marketing"},
            {"id":"sales","name":"מכירות","icon":"📈","head":"Claude Sales"},
            {"id":"legal","name":"משפטי","icon":"⚖️","head":"Claude Legal"},
            {"id":"cto","name":"טכנולוגיה","icon":"💻","head":"Claude CTO"},
            {"id":"content","name":"תוכן ועיצוב","icon":"🎨","head":"Claude Content"},
            {"id":"pr","name":"יח\"צ","icon":"📢","head":"Claude PR"},
            {"id":"compliance","name":"ציות","icon":"🛡️","head":"Claude Compliance"},
        ]
    return rows

@app.get("/api/employees")
async def get_employees(dept: Optional[str] = None, user=Depends(verify_auth)):
    q = "order=department.asc"
    if dept: q += f"&department=eq.{dept}"
    rows = await sb_get("employees", q)
    if not rows:
        base = [
            {"id":"1","name":"מנכ\"ל AI","role":"מנכ\"ל","department":"ceo","status":"active"},
            {"id":"2","name":"CFO AI","role":"מנהל כספים","department":"cfo","status":"active"},
            {"id":"3","name":"Marketing AI","role":"מנהל שיווק","department":"marketing","status":"active"},
            {"id":"4","name":"Sales AI","role":"מנהל מכירות","department":"sales","status":"active"},
            {"id":"5","name":"Legal AI","role":"יועץ משפטי","department":"legal","status":"active"},
            {"id":"6","name":"CTO AI","role":"מנהל טכנולוגיה","department":"cto","status":"active"},
            {"id":"7","name":"Content AI","role":"מנהל תוכן","department":"content","status":"active"},
            {"id":"8","name":"PR AI","role":"מנהל יח\"צ","department":"pr","status":"active"},
            {"id":"9","name":"Compliance AI","role":"קצין ציות","department":"compliance","status":"active"},
        ]
        return [e for e in base if not dept or e["department"] == dept]
    return rows

@app.get("/api/meetings")
async def get_meetings(user=Depends(verify_auth)):
    rows = await sb_get("meetings", "order=created_at.desc&limit=20")
    return rows

@app.post("/api/meetings")
async def create_meeting(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    topic   = body.get("topic", "ישיבת הנהלה")
    agenda  = body.get("agenda", "")
    dept_list = body.get("departments", ["ceo", "cfo", "marketing"])
    
    # Ask each department
    responses = {}
    for dept in dept_list[:4]:  # limit to 4 to avoid timeout
        msg = f"ישיבת הנהלה בנושא: {topic}\n\nסדר יום: {agenda}\n\nמה עמדתך ותרומתך לנושא זה?"
        responses[dept] = await ask_claude(dept, msg)
    
    meeting = {
        "topic":     topic,
        "agenda":    agenda,
        "responses": json.dumps(responses, ensure_ascii=False),
        "status":    "completed",
        "created_at": datetime.utcnow().isoformat(),
    }
    result = await sb_insert("meetings", meeting)
    return {"meeting": result, "responses": responses}

@app.post("/api/instruct")
async def send_instruction(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    instruction = body.get("instruction", "")
    if not instruction:
        raise HTTPException(400, "נא לכתוב הוראה")
    
    # CEO distributes
    ceo_prompt = f"""קיבלת הוראה מיו"ר הדירקטוריון:
"{instruction}"

1. נתח את ההוראה
2. פרט אילו מחלקות צריכות לטפל
3. תאר את תוכנית הפעולה
4. הצג ציר זמן מוצע"""
    
    ceo_resp = await ask_claude("ceo", ceo_prompt)
    
    result = {
        "instruction": instruction,
        "ceo_response": ceo_resp,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    await sb_insert("instructions", {
        "text":         instruction,
        "ceo_response": ceo_resp,
        "status":       "processing",
        "created_at":   datetime.utcnow().isoformat(),
    })
    
    return result

@app.post("/api/chat/{dept}")
async def dept_chat(dept: str, req: Request, user=Depends(verify_auth)):
    body = await req.json()
    message  = body.get("message", "")
    history  = body.get("history", [])
    
    context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-6:]])
    response = await ask_claude(dept, message, context)
    
    await sb_insert("chat_messages", {
        "department":  dept,
        "user_message": message,
        "ai_response":  response,
        "created_at":   datetime.utcnow().isoformat(),
    })
    
    return {"response": response, "department": dept}

@app.get("/api/chat/{dept}/history")
async def dept_chat_history(dept: str, user=Depends(verify_auth)):
    return await sb_get("chat_messages", f"department=eq.{dept}&order=created_at.desc&limit=30")

@app.get("/api/reports")
async def get_reports(dept: Optional[str] = None, user=Depends(verify_auth)):
    q = "order=created_at.desc&limit=20"
    if dept: q += f"&department=eq.{dept}"
    return await sb_get("reports", q)

@app.post("/api/reports/generate")
async def generate_report(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    report_type = body.get("type", "weekly")
    dept        = body.get("department", "ceo")
    
    prompt = f"צור דוח {report_type} מקיף עבור מחלקת {AGENT_PERSONAS.get(dept,('',''))[0]}. כלול: סיכום פעילות, הישגים, אתגרים, ותוכנית לשבוע הבא. הדוח צריך להיות מפורט ומקצועי."
    
    content = await ask_claude(dept, prompt)
    
    report = {
        "title":      f"דוח {report_type} - {AGENT_PERSONAS.get(dept,('מחלקה',''))[0]}",
        "department": dept,
        "content":    content,
        "type":       report_type,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = await sb_insert("reports", report)
    return {"report": report, "id": result.get("id") if result else None}

@app.get("/api/approvals")
async def get_approvals(user=Depends(verify_auth)):
    return await sb_get("tasks", "status=eq.pending_approval&order=created_at.desc")

@app.post("/api/strategy/goals")
async def set_strategic_goals(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    goals = body.get("goals", "")
    
    prompt = f"""יו"ר הדירקטוריון הציב יעדים אסטרטגיים חדשים:
{goals}

כמנכ"ל, צור תוכנית אסטרטגית מפורטת הכוללת:
1. פירוט היעדים לפי מחלקות
2. לוח זמנים לביצוע
3. מדדי הצלחה (KPIs) לכל יעד
4. סיכוני ביצוע ואיך להתמודד
5. תקציב מוצע"""
    
    plan = await ask_claude("ceo", prompt)
    
    await sb_insert("strategic_goals", {
        "goals":   goals,
        "plan":    plan,
        "status":  "active",
        "created_at": datetime.utcnow().isoformat(),
    })
    
    return {"goals": goals, "plan": plan}

@app.get("/api/strategy/goals")
async def get_strategic_goals(user=Depends(verify_auth)):
    return await sb_get("strategic_goals", "order=created_at.desc&limit=10")

# ─── Main Dashboard HTML ───────────────────────────────────────────────────────

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>גבר – מערכת ניהול AI</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap');

  :root {
    --bg:       #0d0f14;
    --surface:  #161921;
    --card:     #1c2030;
    --border:   #252a3a;
    --accent:   #6c63ff;
    --accent2:  #a78bfa;
    --gold:     #f5c842;
    --green:    #22d3a0;
    --red:      #f87171;
    --orange:   #fb923c;
    --text:     #e8eaf0;
    --muted:    #8892a4;
    --radius:   12px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    font-family: 'Heebo', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── Header ── */
  .header {
    background: linear-gradient(135deg, #1a0a4a 0%, #0d1a3a 50%, #0a1520 100%);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .header-logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .header-logo .icon {
    width: 38px; height: 38px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
  }
  .header-logo .name {
    font-weight: 700;
    font-size: 16px;
    line-height: 1.2;
  }
  .header-logo .sub {
    font-size: 11px;
    color: var(--muted);
    font-weight: 400;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .badge-online {
    background: rgba(34,211,160,0.15);
    color: var(--green);
    border: 1px solid rgba(34,211,160,0.3);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
  }
  .btn-exit {
    background: rgba(248,113,113,0.15);
    color: var(--red);
    border: 1px solid rgba(248,113,113,0.3);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    cursor: pointer;
    font-family: inherit;
  }

  /* ── Tabs ── */
  .tabs-bar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    display: flex;
    gap: 2px;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .tabs-bar::-webkit-scrollbar { display: none; }
  .tab-btn {
    background: none;
    border: none;
    color: var(--muted);
    font-family: inherit;
    font-size: 13px;
    font-weight: 500;
    padding: 14px 16px;
    cursor: pointer;
    white-space: nowrap;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active {
    color: var(--accent2);
    border-bottom-color: var(--accent2);
  }

  /* ── Content ── */
  .content { padding: 24px; max-width: 1400px; margin: 0 auto; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* ── Stats Row ── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 16px;
    text-align: center;
  }
  .stat-num {
    font-size: 32px;
    font-weight: 800;
    color: var(--accent2);
    line-height: 1;
    margin-bottom: 6px;
  }
  .stat-label { font-size: 12px; color: var(--muted); }

  /* ── Cards ── */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
  }
  .card-title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* ── Instruction Box ── */
  .instruct-area {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--text);
    font-family: inherit;
    font-size: 14px;
    padding: 14px;
    resize: vertical;
    min-height: 90px;
    direction: rtl;
    outline: none;
  }
  .instruct-area:focus { border-color: var(--accent); }

  /* ── Buttons ── */
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .btn:hover { opacity: 0.85; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-sm {
    padding: 6px 14px;
    font-size: 12px;
  }
  .btn-green {
    background: linear-gradient(135deg, #059669, var(--green));
  }
  .btn-outline {
    background: none;
    border: 1px solid var(--border);
    color: var(--text);
  }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent2); }

  /* ── Response Box ── */
  .response-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-top: 14px;
    font-size: 13px;
    line-height: 1.7;
    white-space: pre-wrap;
    display: none;
  }
  .response-box.show { display: block; }
  .response-label {
    font-size: 11px;
    color: var(--accent2);
    font-weight: 600;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* ── Dept Grid ── */
  .dept-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
  }
  .dept-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
  }
  .dept-card:hover {
    border-color: var(--accent);
    background: rgba(108,99,255,0.08);
    transform: translateY(-2px);
  }
  .dept-card.selected {
    border-color: var(--accent2);
    background: rgba(167,139,250,0.12);
  }
  .dept-icon { font-size: 28px; margin-bottom: 8px; }
  .dept-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
  .dept-head { font-size: 11px; color: var(--muted); }

  /* ── Chat ── */
  .chat-layout {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 16px;
    height: 600px;
  }
  .chat-sidebar {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow-y: auto;
  }
  .chat-agent-btn {
    width: 100%;
    background: none;
    border: none;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    padding: 12px 14px;
    cursor: pointer;
    text-align: right;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 0.15s;
  }
  .chat-agent-btn:hover { background: rgba(108,99,255,0.1); }
  .chat-agent-btn.active {
    background: rgba(167,139,250,0.15);
    color: var(--accent2);
    font-weight: 600;
  }
  .chat-main {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
  }
  .chat-header {
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    font-weight: 600;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .msg {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.6;
  }
  .msg-user {
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    align-self: flex-start;
    border-radius: 12px 12px 12px 2px;
  }
  .msg-ai {
    background: var(--card);
    border: 1px solid var(--border);
    align-self: flex-end;
    border-radius: 12px 12px 2px 12px;
  }
  .chat-input-row {
    padding: 14px;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 10px;
  }
  .chat-input {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    padding: 10px 14px;
    direction: rtl;
    outline: none;
  }
  .chat-input:focus { border-color: var(--accent); }

  /* ── Tasks ── */
  .task-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .task-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .dot-pending    { background: var(--orange); }
  .dot-inprog     { background: var(--accent2); }
  .dot-done       { background: var(--green); }
  .dot-approval   { background: var(--gold); }
  .task-info { flex: 1; }
  .task-title { font-size: 13px; font-weight: 600; }
  .task-meta  { font-size: 11px; color: var(--muted); margin-top: 3px; }
  .tag {
    background: rgba(108,99,255,0.15);
    color: var(--accent2);
    border: 1px solid rgba(108,99,255,0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    white-space: nowrap;
  }
  .tag-gold   { background: rgba(245,200,66,0.15); color: var(--gold); border-color: rgba(245,200,66,0.3); }
  .tag-green  { background: rgba(34,211,160,0.15); color: var(--green); border-color: rgba(34,211,160,0.3); }
  .tag-orange { background: rgba(251,146,60,0.15); color: var(--orange); border-color: rgba(251,146,60,0.3); }

  /* ── Form ── */
  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }
  .form-group { margin-bottom: 12px; }
  label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
  input[type=text], select, textarea {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    padding: 10px 12px;
    direction: rtl;
    outline: none;
  }
  input[type=text]:focus, select:focus, textarea:focus { border-color: var(--accent); }
  select option { background: var(--card); }

  /* ── Strategy ── */
  .goal-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
  }
  .goal-text { font-size: 13px; line-height: 1.6; }
  .goal-plan {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--muted);
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
  }

  /* ── Meeting ── */
  .meeting-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    margin-bottom: 12px;
  }
  .meeting-topic { font-weight: 600; margin-bottom: 8px; }
  .meeting-responses { margin-top: 12px; }
  .dept-response {
    border-right: 3px solid var(--accent);
    padding: 8px 12px;
    margin-bottom: 8px;
    background: rgba(108,99,255,0.05);
    border-radius: 0 6px 6px 0;
    font-size: 12px;
  }
  .dept-response-name { font-size: 11px; color: var(--accent2); font-weight: 600; margin-bottom: 4px; }

  /* ── Loading ── */
  .spinner {
    display: inline-block;
    width: 16px; height: 16px;
    border: 2px solid rgba(167,139,250,0.3);
    border-top-color: var(--accent2);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .content { padding: 16px; }
    .chat-layout { grid-template-columns: 1fr; height: auto; }
    .chat-sidebar { display: flex; overflow-x: auto; height: 60px; }
    .chat-agent-btn { border-bottom: none; border-left: 1px solid var(--border); white-space: nowrap; }
    .chat-main { height: 500px; }
    .form-row { grid-template-columns: 1fr; }
    .dept-grid { grid-template-columns: repeat(3, 1fr); }
  }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-logo">
    <div class="icon">🏢</div>
    <div>
      <div class="name">גבר יזמות ייעוץ עסקי</div>
      <div class="sub">AI Company Management System</div>
    </div>
  </div>
  <div class="header-right">
    <div class="badge-online">● מחובר</div>
    <button class="btn-exit" onclick="window.location.reload()">↩ יציאה</button>
  </div>
</div>

<!-- Tabs -->
<div class="tabs-bar" id="tabsBar">
  <button class="tab-btn active" onclick="switchTab('home',this)">🏠 ראשי</button>
  <button class="tab-btn" onclick="switchTab('instruct',this)">📋 הוראות</button>
  <button class="tab-btn" onclick="switchTab('tasks',this)">⚙️ משימות</button>
  <button class="tab-btn" onclick="switchTab('chat',this)">💬 צ׳אט</button>
  <button class="tab-btn" onclick="switchTab('depts',this)">🏬 מחלקות</button>
  <button class="tab-btn" onclick="switchTab('meetings',this)">📅 ישיבות</button>
  <button class="tab-btn" onclick="switchTab('reports',this)">📊 דוחות</button>
  <button class="tab-btn" onclick="switchTab('strategy',this)">🎯 אסטרטגיה</button>
  <button class="tab-btn" onclick="switchTab('approvals',this)">👁 אישורים</button>
  <button class="tab-btn" onclick="switchTab('settings',this)">⚙ הגדרות</button>
</div>

<!-- Content -->
<div class="content">

  <!-- ── HOME ── -->
  <div class="tab-panel active" id="panel-home">
    <div class="stats-grid" id="statsGrid">
      <div class="stat-card"><div class="stat-num" id="s-depts">—</div><div class="stat-label">מחלקות</div></div>
      <div class="stat-card"><div class="stat-num" id="s-emp">—</div><div class="stat-label">עובדים</div></div>
      <div class="stat-card"><div class="stat-num" id="s-tasks">—</div><div class="stat-label">משימות</div></div>
      <div class="stat-card"><div class="stat-num" id="s-done">—</div><div class="stat-label">הושלמו</div></div>
      <div class="stat-card"><div class="stat-num" id="s-inprog">—</div><div class="stat-label">בעבודה</div></div>
      <div class="stat-card"><div class="stat-num" id="s-pending">—</div><div class="stat-label">ממתין לאישור</div></div>
    </div>

    <div class="card">
      <div class="card-title">📝 הוראה חדשה ליו"ר</div>
      <textarea class="instruct-area" id="homeInstruct" placeholder="כתוב כאן את ההוראה שלך... לדוגמה: צור קמפיין שיווקי לרגל חג הפסח"></textarea>
      <div style="margin-top:10px;display:flex;gap:10px;align-items:center">
        <button class="btn" onclick="sendInstruction()" id="btnInstruct">🚀 שלח לצוות</button>
        <span id="loadInstruct" style="display:none"><span class="spinner"></span> המנכ"ל מטפל...</span>
      </div>
      <div class="response-box" id="instructResult">
        <div class="response-label">👑 תגובת המנכ"ל</div>
        <div id="instructText"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">👁 ממתינים לאישור</div>
      <div id="homeApprovals"><div style="color:var(--muted);font-size:13px">אין תוצרים ממתינים</div></div>
    </div>

    <div class="card">
      <div class="card-title">⚙️ משימות בעבודה</div>
      <div id="homeTasksInprog"><div style="color:var(--muted);font-size:13px">אין משימות פעילות</div></div>
    </div>

    <div class="card">
      <div class="card-title">🏬 מחלקות הניהול</div>
      <div class="dept-grid" id="homeDepts"></div>
    </div>
  </div>

  <!-- ── INSTRUCT ── -->
  <div class="tab-panel" id="panel-instruct">
    <div class="card">
      <div class="card-title">📋 שליחת הוראה לצוות</div>
      <div class="form-group">
        <label>ההוראה שלך</label>
        <textarea class="instruct-area" id="mainInstruct" placeholder="תאר בפירוט מה אתה רוצה שהצוות יעשה..." style="min-height:120px"></textarea>
      </div>
      <button class="btn" onclick="sendMainInstruction()" id="btnMainInstruct">🚀 שלח למנכ"ל</button>
      <span id="loadMainInstruct" style="display:none;margin-right:12px"><span class="spinner"></span> מעבד...</span>
      
      <div class="response-box" id="mainInstructResult">
        <div class="response-label">👑 תוכנית הפעולה של המנכ"ל</div>
        <div id="mainInstructText" style="white-space:pre-wrap;font-size:13px;line-height:1.7"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📜 היסטוריית הוראות</div>
      <div id="instructHistory"><div style="color:var(--muted);font-size:13px">טוען...</div></div>
    </div>
  </div>

  <!-- ── TASKS ── -->
  <div class="tab-panel" id="panel-tasks">
    <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
      <button class="btn btn-outline btn-sm" onclick="loadTasks()">↻ רענן</button>
      <button class="btn btn-sm" onclick="showNewTaskForm()">+ משימה חדשה</button>
    </div>

    <div class="card" id="newTaskForm" style="display:none">
      <div class="card-title">+ משימה חדשה</div>
      <div class="form-group">
        <label>כותרת המשימה</label>
        <input type="text" id="taskTitle" placeholder="כותרת...">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>מחלקה</label>
          <select id="taskDept">
            <option value="ceo">מנכ"ל</option>
            <option value="cfo">כספים</option>
            <option value="marketing">שיווק</option>
            <option value="sales">מכירות</option>
            <option value="legal">משפטי</option>
            <option value="cto">טכנולוגיה</option>
            <option value="content">תוכן ועיצוב</option>
            <option value="pr">יח"צ</option>
            <option value="compliance">ציות</option>
          </select>
        </div>
        <div class="form-group">
          <label>עדיפות</label>
          <select id="taskPriority">
            <option value="low">נמוך</option>
            <option value="medium" selected>בינוני</option>
            <option value="high">גבוה</option>
            <option value="urgent">דחוף</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>תיאור</label>
        <textarea id="taskDesc" placeholder="תאר את המשימה..." style="min-height:80px;width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:inherit;font-size:13px;padding:10px;direction:rtl;outline:none;resize:vertical"></textarea>
      </div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-sm btn-green" onclick="createTask()">✓ צור משימה</button>
        <button class="btn btn-sm btn-outline" onclick="hideNewTaskForm()">ביטול</button>
      </div>
    </div>

    <div id="tasksList"><div style="color:var(--muted);font-size:13px">טוען משימות...</div></div>
  </div>

  <!-- ── CHAT ── -->
  <div class="tab-panel" id="panel-chat">
    <div class="chat-layout">
      <div class="chat-sidebar" id="chatSidebar">
        <button class="chat-agent-btn active" onclick="selectAgent('ceo','👑 מנכ\\"ל',this)">👑 מנכ"ל</button>
        <button class="chat-agent-btn" onclick="selectAgent('cfo','💰 CFO',this)">💰 CFO</button>
        <button class="chat-agent-btn" onclick="selectAgent('marketing','📣 שיווק',this)">📣 שיווק</button>
        <button class="chat-agent-btn" onclick="selectAgent('sales','📈 מכירות',this)">📈 מכירות</button>
        <button class="chat-agent-btn" onclick="selectAgent('legal','⚖️ משפטי',this)">⚖️ משפטי</button>
        <button class="chat-agent-btn" onclick="selectAgent('cto','💻 CTO',this)">💻 CTO</button>
        <button class="chat-agent-btn" onclick="selectAgent('content','🎨 תוכן',this)">🎨 תוכן</button>
        <button class="chat-agent-btn" onclick="selectAgent('pr','📢 יח\\"צ',this)">📢 יח"צ</button>
        <button class="chat-agent-btn" onclick="selectAgent('compliance','🛡️ ציות',this)">🛡️ ציות</button>
      </div>
      <div class="chat-main">
        <div class="chat-header" id="chatHeader">👑 שיחה עם המנכ"ל</div>
        <div class="chat-messages" id="chatMessages">
          <div class="msg msg-ai">שלום! אני המנכ"ל של גבר. איך אוכל לעזור לך היום?</div>
        </div>
        <div class="chat-input-row">
          <button class="btn btn-sm" onclick="sendChat()" id="btnSendChat">שלח</button>
          <input type="text" class="chat-input" id="chatInput" placeholder="כתוב הודעה..." onkeydown="if(event.key==='Enter')sendChat()">
        </div>
      </div>
    </div>
  </div>

  <!-- ── DEPARTMENTS ── -->
  <div class="tab-panel" id="panel-depts">
    <div class="dept-grid" id="deptsGrid" style="margin-bottom:20px"></div>
    <div class="card" id="deptDetail" style="display:none">
      <div class="card-title" id="deptDetailTitle">פרטי מחלקה</div>
      <div id="deptDetailContent"></div>
    </div>
  </div>

  <!-- ── MEETINGS ── -->
  <div class="tab-panel" id="panel-meetings">
    <div class="card">
      <div class="card-title">📅 כינוס ישיבה חדשה</div>
      <div class="form-group">
        <label>נושא הישיבה</label>
        <input type="text" id="meetingTopic" placeholder="נושא...">
      </div>
      <div class="form-group">
        <label>סדר יום</label>
        <textarea id="meetingAgenda" placeholder="פרט את סדר היום..." style="min-height:80px;width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:inherit;font-size:13px;padding:10px;direction:rtl;outline:none;resize:vertical"></textarea>
      </div>
      <div class="form-group">
        <label>מחלקות משתתפות</label>
        <div style="display:flex;flex-wrap:wrap;gap:8px" id="meetingDepts">
          <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--text)"><input type="checkbox" value="ceo" checked> מנכ"ל</label>
          <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--text)"><input type="checkbox" value="cfo"> כספים</label>
          <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--text)"><input type="checkbox" value="marketing"> שיווק</label>
          <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--text)"><input type="checkbox" value="legal"> משפטי</label>
          <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--text)"><input type="checkbox" value="cto"> טכנולוגיה</label>
          <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--text)"><input type="checkbox" value="content"> תוכן</label>
        </div>
      </div>
      <button class="btn" onclick="createMeeting()" id="btnMeeting">📅 כנס ישיבה</button>
      <span id="loadMeeting" style="display:none;margin-right:12px"><span class="spinner"></span> מכנס...</span>
      <div class="response-box" id="meetingResult"></div>
    </div>

    <div class="card">
      <div class="card-title">📜 ישיבות קודמות</div>
      <div id="meetingsList"><div style="color:var(--muted);font-size:13px">טוען...</div></div>
    </div>
  </div>

  <!-- ── REPORTS ── -->
  <div class="tab-panel" id="panel-reports">
    <div class="card">
      <div class="card-title">📊 הפק דוח</div>
      <div class="form-row">
        <div class="form-group">
          <label>מחלקה</label>
          <select id="reportDept">
            <option value="ceo">מנכ"ל</option>
            <option value="cfo">כספים</option>
            <option value="marketing">שיווק</option>
            <option value="sales">מכירות</option>
            <option value="legal">משפטי</option>
            <option value="cto">טכנולוגיה</option>
          </select>
        </div>
        <div class="form-group">
          <label>סוג דוח</label>
          <select id="reportType">
            <option value="weekly">שבועי</option>
            <option value="monthly">חודשי</option>
            <option value="quarterly">רבעוני</option>
            <option value="summary">סיכום</option>
          </select>
        </div>
      </div>
      <button class="btn" onclick="generateReport()" id="btnReport">📊 הפק דוח</button>
      <span id="loadReport" style="display:none;margin-right:12px"><span class="spinner"></span> מכין...</span>
      <div class="response-box" id="reportResult">
        <div class="response-label" id="reportLabel">דוח</div>
        <div id="reportText" style="white-space:pre-wrap;font-size:13px;line-height:1.7"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📁 דוחות קודמים</div>
      <div id="reportsList"><div style="color:var(--muted);font-size:13px">טוען...</div></div>
    </div>
  </div>

  <!-- ── STRATEGY ── -->
  <div class="tab-panel" id="panel-strategy">
    <div class="card">
      <div class="card-title">🎯 הצבת יעדים אסטרטגיים</div>
      <div class="form-group">
        <label>היעדים האסטרטגיים</label>
        <textarea id="stratGoals" placeholder="תאר את היעדים האסטרטגיים לתקופה הקרובה..." style="min-height:120px;width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:inherit;font-size:13px;padding:10px;direction:rtl;outline:none;resize:vertical"></textarea>
      </div>
      <button class="btn" onclick="setGoals()" id="btnGoals">🎯 שלח למנכ"ל לתכנון</button>
      <span id="loadGoals" style="display:none;margin-right:12px"><span class="spinner"></span> מכין תוכנית...</span>
      <div class="response-box" id="goalsResult">
        <div class="response-label">📋 תוכנית אסטרטגית</div>
        <div id="goalsText" style="white-space:pre-wrap;font-size:13px;line-height:1.7"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">📌 יעדים קודמים</div>
      <div id="goalsList"><div style="color:var(--muted);font-size:13px">טוען...</div></div>
    </div>
  </div>

  <!-- ── APPROVALS ── -->
  <div class="tab-panel" id="panel-approvals">
    <div class="card">
      <div class="card-title">👁 ממתינים לאישורך</div>
      <div id="approvalsList"><div style="color:var(--muted);font-size:13px">טוען...</div></div>
    </div>
  </div>

  <!-- ── SETTINGS ── -->
  <div class="tab-panel" id="panel-settings">
    <div class="card">
      <div class="card-title">⚙ הגדרות מערכת</div>
      <div style="display:grid;gap:10px;font-size:13px">
        <div style="padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:flex;justify-content:space-between">
          <span>Anthropic API</span>
          <span id="anthropicStatus" style="color:var(--muted)">בודק...</span>
        </div>
        <div style="padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:flex;justify-content:space-between">
          <span>Supabase</span>
          <span id="supabaseStatus" style="color:var(--muted)">בודק...</span>
        </div>
        <div style="padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:flex;justify-content:space-between">
          <span>שם החברה</span>
          <span style="color:var(--accent2)">גבר יזמות ייעוץ עסקי</span>
        </div>
        <div style="padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:flex;justify-content:space-between">
          <span>מחלקות פעילות</span>
          <span id="deptCount" style="color:var(--green)">—</span>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">🗄 מסד נתונים – טבלאות נדרשות</div>
      <p style="font-size:12px;color:var(--muted);margin-bottom:12px">הרץ את ה-SQL הבא ב-Supabase SQL Editor כדי ליצור את כל הטבלאות:</p>
      <pre style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;font-size:11px;overflow-x:auto;white-space:pre;color:var(--accent2)">CREATE TABLE IF NOT EXISTS tasks (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, title text, description text, department text, status text DEFAULT 'pending', priority text DEFAULT 'medium', created_by text, created_at timestamptz DEFAULT now(), approved_at timestamptz);
CREATE TABLE IF NOT EXISTS instructions (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, text text, ceo_response text, status text, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS meetings (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, topic text, agenda text, responses jsonb, status text, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS reports (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, title text, department text, content text, type text, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS chat_messages (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, department text, user_message text, ai_response text, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS strategic_goals (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, goals text, plan text, status text, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS departments (id text PRIMARY KEY, name text, icon text, head text);
CREATE TABLE IF NOT EXISTS employees (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, name text, role text, department text, status text DEFAULT 'active');</pre>
    </div>
  </div>

</div><!-- /content -->

<script>
// ── State ──────────────────────────────────────────────────────
let currentAgent = 'ceo';
let chatHistory  = [];
let currentAgentName = '👑 מנכ"ל';

// ── Tab Switch ─────────────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('panel-' + name);
  if (panel) panel.classList.add('active');
  if (btn)  btn.classList.add('active');

  // Lazy load
  const loaders = {
    home:      () => { loadStats(); loadHomeDepts(); loadHomeApprovals(); loadHomeTasksInprog(); },
    tasks:     loadTasks,
    depts:     loadDepts,
    meetings:  loadMeetings,
    reports:   loadReports,
    strategy:  loadGoals,
    approvals: loadApprovals,
    settings:  checkConnections,
    instruct:  loadInstructHistory,
  };
  if (loaders[name]) loaders[name]();
}

// ── API fetch helper ───────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: {'Content-Type':'application/json'} };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch('/api' + path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ── Stats ──────────────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await api('GET','/stats');
    document.getElementById('s-depts').textContent  = s.departments   || '9';
    document.getElementById('s-emp').textContent    = s.employees     || '—';
    document.getElementById('s-tasks').textContent  = s.tasks_total   || '0';
    document.getElementById('s-done').textContent   = s.tasks_done    || '0';
    document.getElementById('s-inprog').textContent = s.tasks_inprog  || '0';
    document.getElementById('s-pending').textContent= s.tasks_pending || '0';
    const dc = document.getElementById('deptCount');
    if (dc) dc.textContent = s.departments || '9';
  } catch(e) { console.error(e); }
}

// ── Home Depts ─────────────────────────────────────────────────
async function loadHomeDepts() {
  try {
    const depts = await api('GET','/departments');
    const grid  = document.getElementById('homeDepts');
    if (!grid) return;
    grid.innerHTML = depts.map(d => `
      <div class="dept-card" onclick="switchTab('chat',document.querySelectorAll('.tab-btn')[3]);selectAgent('${d.id}','${d.icon} ${d.name}',null)">
        <div class="dept-icon">${d.icon}</div>
        <div class="dept-name">${d.name}</div>
        <div class="dept-head">${d.head||''}</div>
      </div>`).join('');
  } catch(e) {}
}

async function loadHomeApprovals() {
  try {
    const items = await api('GET','/tasks?status=pending_approval');
    const el = document.getElementById('homeApprovals');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">אין תוצרים ממתינים</div>'; return; }
    el.innerHTML = items.slice(0,3).map(t => taskHTML(t)).join('');
  } catch(e) {}
}

async function loadHomeTasksInprog() {
  try {
    const items = await api('GET','/tasks?status=in_progress');
    const el = document.getElementById('homeTasksInprog');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">אין משימות פעילות</div>'; return; }
    el.innerHTML = items.slice(0,3).map(t => taskHTML(t)).join('');
  } catch(e) {}
}

// ── Instruction ────────────────────────────────────────────────
async function sendInstruction() {
  const txt = document.getElementById('homeInstruct').value.trim();
  if (!txt) return alert('נא לכתוב הוראה');
  setBusy('btnInstruct','loadInstruct',true);
  try {
    const r = await api('POST','/instruct',{instruction:txt});
    document.getElementById('instructResult').classList.add('show');
    document.getElementById('instructText').textContent = r.ceo_response;
  } catch(e) { alert('שגיאה: ' + e.message); }
  setBusy('btnInstruct','loadInstruct',false);
}

async function sendMainInstruction() {
  const txt = document.getElementById('mainInstruct').value.trim();
  if (!txt) return alert('נא לכתוב הוראה');
  setBusy('btnMainInstruct','loadMainInstruct',true);
  try {
    const r = await api('POST','/instruct',{instruction:txt});
    document.getElementById('mainInstructResult').classList.add('show');
    document.getElementById('mainInstructText').textContent = r.ceo_response;
    loadInstructHistory();
  } catch(e) { alert('שגיאה: ' + e.message); }
  setBusy('btnMainInstruct','loadMainInstruct',false);
}

async function loadInstructHistory() {
  try {
    const items = await api('GET','/tasks?dept=&status=');
    // Reuse tasks endpoint for now
  } catch(e) {}
}

// ── Tasks ──────────────────────────────────────────────────────
function taskHTML(t) {
  const dotMap  = {pending:'dot-pending',in_progress:'dot-inprog',done:'dot-done',pending_approval:'dot-approval'};
  const tagMap  = {pending:'tag-orange',in_progress:'',done:'tag-green',pending_approval:'tag-gold'};
  const lblMap  = {pending:'ממתין',in_progress:'בעבודה',done:'הושלם',pending_approval:'לאישור'};
  const dot = dotMap[t.status]||'dot-pending';
  const tag = tagMap[t.status]||'';
  const lbl = lblMap[t.status]||t.status;
  return `
    <div class="task-item">
      <div class="task-dot ${dot}"></div>
      <div class="task-info">
        <div class="task-title">${t.title||''}</div>
        <div class="task-meta">${t.department||''} • ${fmtDate(t.created_at)}</div>
      </div>
      <span class="tag ${tag}">${lbl}</span>
      ${t.status==='pending_approval'?`<button class="btn btn-sm btn-green" onclick="approveTask('${t.id}')">✓ אשר</button>`:''}
    </div>`;
}

async function loadTasks() {
  try {
    const items = await api('GET','/tasks');
    const el = document.getElementById('tasksList');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div class="card"><div style="color:var(--muted);font-size:13px">אין משימות עדיין</div></div>'; return; }
    el.innerHTML = '<div class="card">' + items.map(t => taskHTML(t)).join('') + '</div>';
  } catch(e) {}
}

async function createTask() {
  const title = document.getElementById('taskTitle').value.trim();
  if (!title) return alert('נא להזין כותרת');
  try {
    await api('POST','/tasks',{
      title,
      description: document.getElementById('taskDesc').value,
      department:  document.getElementById('taskDept').value,
      priority:    document.getElementById('taskPriority').value,
    });
    hideNewTaskForm();
    loadTasks();
  } catch(e) { alert('שגיאה: ' + e.message); }
}

async function approveTask(id) {
  try {
    await api('POST','/tasks/'+id+'/approve');
    loadTasks(); loadHomeApprovals();
  } catch(e) { alert('שגיאה: ' + e.message); }
}

function showNewTaskForm() { document.getElementById('newTaskForm').style.display='block'; }
function hideNewTaskForm() { document.getElementById('newTaskForm').style.display='none'; }

// ── Depts ──────────────────────────────────────────────────────
async function loadDepts() {
  try {
    const depts = await api('GET','/departments');
    const grid  = document.getElementById('deptsGrid');
    if (!grid) return;
    grid.innerHTML = depts.map(d => `
      <div class="dept-card" onclick="showDeptDetail('${d.id}','${d.icon} ${d.name}')">
        <div class="dept-icon">${d.icon}</div>
        <div class="dept-name">${d.name}</div>
        <div class="dept-head">${d.head||''}</div>
      </div>`).join('');
  } catch(e) {}
}

async function showDeptDetail(id, name) {
  document.getElementById('deptDetailTitle').textContent = name;
  document.getElementById('deptDetail').style.display = 'block';
  document.getElementById('deptDetailContent').innerHTML = '<div style="color:var(--muted);font-size:13px">טוען...</div>';
  try {
    const emps = await api('GET','/employees?dept='+id);
    const tasks= await api('GET','/tasks?dept='+id);
    document.getElementById('deptDetailContent').innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px">עובדים (${emps.length})</div>
          ${emps.map(e=>`<div class="task-item"><div class="task-dot dot-done"></div><div class="task-info"><div class="task-title">${e.name}</div><div class="task-meta">${e.role}</div></div></div>`).join('')}
        </div>
        <div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px">משימות אחרונות (${tasks.length})</div>
          ${tasks.slice(0,5).map(t=>taskHTML(t)).join('') || '<div style="color:var(--muted);font-size:13px">אין משימות</div>'}
        </div>
      </div>`;
  } catch(e) {}
}

// ── Chat ───────────────────────────────────────────────────────
function selectAgent(id, name, btn) {
  currentAgent     = id;
  currentAgentName = name;
  document.querySelectorAll('.chat-agent-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const h = document.getElementById('chatHeader');
  if (h) h.textContent = 'שיחה עם ' + name;
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.innerHTML = `<div class="msg msg-ai">שלום! אני ${name}. איך אוכל לעזור?</div>`;
  chatHistory = [];
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const msg   = input.value.trim();
  if (!msg) return;
  input.value = '';

  const msgs = document.getElementById('chatMessages');
  msgs.innerHTML += `<div class="msg msg-user">${msg}</div>`;
  msgs.innerHTML += `<div class="msg msg-ai" id="typingMsg"><span class="spinner"></span></div>`;
  msgs.scrollTop  = msgs.scrollHeight;

  chatHistory.push({role:'user', content: msg});
  document.getElementById('btnSendChat').disabled = true;

  try {
    const r = await api('POST','/chat/'+currentAgent,{message:msg, history:chatHistory});
    document.getElementById('typingMsg').remove();
    msgs.innerHTML += `<div class="msg msg-ai">${r.response}</div>`;
    chatHistory.push({role:'assistant', content: r.response});
    msgs.scrollTop = msgs.scrollHeight;
  } catch(e) {
    document.getElementById('typingMsg').textContent = 'שגיאה: ' + e.message;
  }
  document.getElementById('btnSendChat').disabled = false;
}

// ── Meetings ───────────────────────────────────────────────────
async function createMeeting() {
  const topic   = document.getElementById('meetingTopic').value.trim();
  const agenda  = document.getElementById('meetingAgenda').value.trim();
  if (!topic) return alert('נא להזין נושא');
  const depts = [...document.querySelectorAll('#meetingDepts input:checked')].map(i=>i.value);

  setBusy('btnMeeting','loadMeeting',true);
  try {
    const r = await api('POST','/meetings',{topic, agenda, departments:depts});
    const box = document.getElementById('meetingResult');
    box.classList.add('show');
    let html = `<div class="response-label">📅 סיכום ישיבה: ${topic}</div>`;
    for (const [dept, resp] of Object.entries(r.responses||{})) {
      html += `<div class="dept-response"><div class="dept-response-name">${dept}</div>${resp}</div>`;
    }
    box.innerHTML = html;
    loadMeetings();
  } catch(e) { alert('שגיאה: ' + e.message); }
  setBusy('btnMeeting','loadMeeting',false);
}

async function loadMeetings() {
  try {
    const items = await api('GET','/meetings');
    const el = document.getElementById('meetingsList');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">אין ישיבות עדיין</div>'; return; }
    el.innerHTML = items.map(m => {
      let resps = '';
      try {
        const obj = typeof m.responses==='string' ? JSON.parse(m.responses) : m.responses;
        for (const [dept,resp] of Object.entries(obj||{})) {
          resps += `<div class="dept-response"><div class="dept-response-name">${dept}</div>${resp.substring(0,200)}...</div>`;
        }
      } catch(e) {}
      return `
        <div class="meeting-card">
          <div class="meeting-topic">${m.topic||''}</div>
          <div style="font-size:11px;color:var(--muted)">${fmtDate(m.created_at)}</div>
          ${resps ? '<div class="meeting-responses">'+resps+'</div>' : ''}
        </div>`;
    }).join('');
  } catch(e) {}
}

// ── Reports ────────────────────────────────────────────────────
async function generateReport() {
  const dept = document.getElementById('reportDept').value;
  const type = document.getElementById('reportType').value;
  setBusy('btnReport','loadReport',true);
  try {
    const r = await api('POST','/reports/generate',{department:dept, type});
    document.getElementById('reportResult').classList.add('show');
    document.getElementById('reportLabel').textContent = r.report?.title || 'דוח';
    document.getElementById('reportText').textContent  = r.report?.content || '';
    loadReports();
  } catch(e) { alert('שגיאה: ' + e.message); }
  setBusy('btnReport','loadReport',false);
}

async function loadReports() {
  try {
    const items = await api('GET','/reports');
    const el = document.getElementById('reportsList');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">אין דוחות עדיין</div>'; return; }
    el.innerHTML = items.map(r => `
      <div class="task-item">
        <div class="task-dot dot-done"></div>
        <div class="task-info">
          <div class="task-title">${r.title||''}</div>
          <div class="task-meta">${r.department||''} • ${r.type||''} • ${fmtDate(r.created_at)}</div>
        </div>
      </div>`).join('');
  } catch(e) {}
}

// ── Strategy ───────────────────────────────────────────────────
async function setGoals() {
  const goals = document.getElementById('stratGoals').value.trim();
  if (!goals) return alert('נא להזין יעדים');
  setBusy('btnGoals','loadGoals',true);
  try {
    const r = await api('POST','/strategy/goals',{goals});
    document.getElementById('goalsResult').classList.add('show');
    document.getElementById('goalsText').textContent = r.plan;
    loadGoals();
  } catch(e) { alert('שגיאה: ' + e.message); }
  setBusy('btnGoals','loadGoals',false);
}

async function loadGoals() {
  try {
    const items = await api('GET','/strategy/goals');
    const el = document.getElementById('goalsList');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">אין יעדים עדיין</div>'; return; }
    el.innerHTML = items.map(g => `
      <div class="goal-item">
        <div class="goal-text">${g.goals||''}</div>
        ${g.plan ? `<div class="goal-plan">${g.plan.substring(0,400)}...</div>` : ''}
        <div style="font-size:11px;color:var(--muted);margin-top:8px">${fmtDate(g.created_at)}</div>
      </div>`).join('');
  } catch(e) {}
}

// ── Approvals ──────────────────────────────────────────────────
async function loadApprovals() {
  try {
    const items = await api('GET','/approvals');
    const el = document.getElementById('approvalsList');
    if (!el) return;
    if (!items.length) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">אין תוצרים ממתינים לאישור</div>'; return; }
    el.innerHTML = items.map(t => taskHTML(t)).join('');
  } catch(e) {}
}

// ── Settings ───────────────────────────────────────────────────
async function checkConnections() {
  try {
    const s = await api('GET','/stats');
    document.getElementById('anthropicStatus').textContent = '✅ מחובר';
    document.getElementById('anthropicStatus').style.color = 'var(--green)';
    document.getElementById('supabaseStatus').textContent  = s.departments > 0 ? '✅ מחובר' : '⚠ מחובר (טבלאות ריקות)';
    document.getElementById('supabaseStatus').style.color  = 'var(--green)';
  } catch(e) {
    document.getElementById('anthropicStatus').textContent = '❌ שגיאה';
    document.getElementById('anthropicStatus').style.color = 'var(--red)';
  }
}

// ── Helpers ────────────────────────────────────────────────────
function fmtDate(d) {
  if (!d) return '';
  try { return new Date(d).toLocaleDateString('he-IL',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'}); }
  catch(e) { return d; }
}

function setBusy(btnId, loadId, busy) {
  const btn  = document.getElementById(btnId);
  const load = document.getElementById(loadId);
  if (btn)  btn.disabled = busy;
  if (load) load.style.display = busy ? 'inline-flex' : 'none';
}

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadHomeDepts();
  loadHomeApprovals();
  loadHomeTasksInprog();
});
</script>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def dashboard(user=Depends(verify_auth)):
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Jabr Management System"}
