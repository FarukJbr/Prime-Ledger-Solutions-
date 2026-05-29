"""FastAPI dashboard for Gever Management System."""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from database import db
from tasks import TaskManager
from meetings import MeetingRoom
from config import settings
import secrets
import os

app = FastAPI(
    title="Gever Management System",
    description="גבר יזמות ייעוץ עסקי והשקעות - AI Management Platform",
    version="1.0.0"
)

security = HTTPBasic()
task_manager = TaskManager()
meeting_room = MeetingRoom()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(
        credentials.username.encode("utf8"),
        os.getenv("DASHBOARD_USER", "chairman").encode("utf8")
    )
    correct_pass = secrets.compare_digest(
        credentials.password.encode("utf8"),
        os.getenv("DASHBOARD_PASSWORD", "gever2024").encode("utf8")
    )
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            detail="גישה נדחתה",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ─── PYDANTIC MODELS ─────────────────────────────────────────────────────────

class InstructionRequest(BaseModel):
    instruction: str
    language: str = "he"


class FeedbackRequest(BaseModel):
    feedback: str


class MeetingRequest(BaseModel):
    title: str
    topic: str
    participants: List[str]
    meeting_type: str = "management"


class ConsultRequest(BaseModel):
    question: str
    departments: List[str]


# ─── TASK ENDPOINTS ──────────────────────────────────────────────────────────

@app.post("/api/tasks/new")
async def create_task(req: InstructionRequest, user: str = Depends(require_auth)):
    saved = db.save_instruction(req.instruction, req.language)
    result = task_manager.process_chairman_instruction(
        req.instruction, saved["id"]
    )
    return {"success": True, "result": result}


@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None):
    if status:
        return db.get_tasks_by_status(status)
    all_tasks = []
    for s in ["pending", "in_progress", "review", "approved", "published"]:
        all_tasks.extend(db.get_tasks_by_status(s))
    return all_tasks


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    return task_manager.get_task_summary(task_id)


@app.get("/api/review/pending")
async def pending_review():
    return task_manager.get_pending_reviews()


@app.post("/api/deliverables/{deliverable_id}/approve")
async def approve(deliverable_id: str, req: Optional[FeedbackRequest] = None):
    return task_manager.approve_deliverable(
        deliverable_id, req.feedback if req else None
    )


@app.post("/api/deliverables/{deliverable_id}/reject")
async def reject(deliverable_id: str, req: FeedbackRequest):
    return task_manager.reject_deliverable(deliverable_id, req.feedback)


# ─── MEETING ENDPOINTS ───────────────────────────────────────────────────────

@app.post("/api/meetings/new")
async def create_meeting(req: MeetingRequest):
    result = meeting_room.hold_meeting(
        title=req.title,
        topic=req.topic,
        participants=req.participants,
        meeting_type=req.meeting_type
    )
    return {"success": True, "result": result}


@app.post("/api/consult")
async def consult(req: ConsultRequest):
    return meeting_room.quick_consult(req.question, req.departments)


# ─── DASHBOARD HTML ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(user: str = Depends(require_auth)):
    pending = task_manager.get_pending_reviews()
    in_progress = db.get_tasks_by_status("in_progress")
    completed = db.get_tasks_by_status("review")

    return f"""
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>גבר יזמות - מרכז ניהול</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; direction: rtl; }}
  .header {{ background: linear-gradient(135deg, #1e40af, #7c3aed); padding: 20px 30px; display: flex; align-items: center; gap: 15px; }}
  .header h1 {{ font-size: 1.5rem; }}
  .header p {{ font-size: 0.85rem; opacity: 0.8; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; padding: 20px 30px; }}
  .stat-card {{ background: #1e293b; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #334155; }}
  .stat-card .number {{ font-size: 2.5rem; font-weight: bold; color: #60a5fa; }}
  .stat-card .label {{ font-size: 0.85rem; color: #94a3b8; margin-top: 5px; }}
  .section {{ padding: 0 30px 20px; }}
  .section h2 {{ font-size: 1.1rem; color: #94a3b8; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 10px; }}
  .task-list {{ display: grid; gap: 10px; }}
  .task-card {{ background: #1e293b; border-radius: 10px; padding: 15px; border-right: 4px solid #3b82f6; }}
  .task-card.urgent {{ border-right-color: #ef4444; }}
  .task-card.review {{ border-right-color: #f59e0b; }}
  .task-title {{ font-weight: 600; }}
  .task-meta {{ font-size: 0.8rem; color: #64748b; margin-top: 5px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.75rem; }}
  .badge-blue {{ background: #1d4ed8; color: #bfdbfe; }}
  .badge-yellow {{ background: #92400e; color: #fde68a; }}
  .departments {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 0 30px 30px; }}
  .dept-card {{ background: #1e293b; border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #334155; }}
  .dept-icon {{ font-size: 1.8rem; }}
  .dept-name {{ font-size: 0.8rem; margin-top: 8px; color: #94a3b8; }}
  .instruction-box {{ margin: 0 30px 20px; background: #1e293b; border-radius: 12px; padding: 20px; }}
  .instruction-box textarea {{ width: 100%; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; border-radius: 8px; padding: 12px; font-size: 1rem; resize: vertical; min-height: 80px; direction: rtl; }}
  .btn {{ background: linear-gradient(135deg, #1e40af, #7c3aed); color: white; border: none; padding: 10px 25px; border-radius: 8px; cursor: pointer; font-size: 1rem; margin-top: 10px; }}
  .btn:hover {{ opacity: 0.9; }}
</style>
</head>
<body>
<div class="header">
  <div style="font-size:2rem">🏢</div>
  <div>
    <h1>{settings.company_name}</h1>
    <p>מרכז ניהול AI - {settings.company_name_en}</p>
  </div>
</div>

<div class="stats">
  <div class="stat-card"><div class="number">{len(pending)}</div><div class="label">ממתין לאישור</div></div>
  <div class="stat-card"><div class="number">{len(in_progress)}</div><div class="label">בעבודה כעת</div></div>
  <div class="stat-card"><div class="number">{len(completed)}</div><div class="label">הושלמו היום</div></div>
  <div class="stat-card"><div class="number">9</div><div class="label">מחלקות פעילות</div></div>
</div>

<div class="instruction-box">
  <h2 style="margin-bottom:10px">📝 הוראה חדשה ליו"ר</h2>
  <textarea id="instruction" placeholder="כתוב כאן את ההוראה שלך... לדוגמה: צור קמפיין שיווקי לרגל חג הפסח"></textarea>
  <button class="btn" onclick="sendInstruction()">🚀 שלח לצוות</button>
  <div id="result" style="margin-top:15px;font-size:0.9rem;color:#60a5fa;"></div>
</div>

<div class="section">
  <h2>👁 ממתינים לאישור ({len(pending)})</h2>
  <div class="task-list">
    {''.join([f'<div class="task-card review"><div class="task-title">{p.get("agent_role","")}</div><div class="task-meta">{p["department"]} • {p["created_at"][:10]}</div><div style="margin-top:8px;font-size:0.85rem;color:#94a3b8;">{p["content"][:150]}...</div></div>' for p in pending[:4]]) or '<p style="color:#64748b">אין תוצרים ממתינים</p>'}
  </div>
</div>

<div class="section">
  <h2>⚙️ משימות בעבודה ({len(in_progress)})</h2>
  <div class="task-list">
    {''.join([f'<div class="task-card"><div class="task-title">{t["title"]}</div><div class="task-meta">{t["assigned_to"]} • <span class="badge badge-blue">{t["status"]}</span></div></div>' for t in in_progress[:4]]) or '<p style="color:#64748b">אין משימות פעילות</p>'}
  </div>
</div>

<div class="section" style="margin-bottom:10px"><h2>🏢 מחלקות הניהול</h2></div>
<div class="departments">
  <div class="dept-card"><div class="dept-icon">👑</div><div class="dept-name">יו"ר דירקטוריון</div></div>
  <div class="dept-card"><div class="dept-icon">🎯</div><div class="dept-name">מנכ"ל (CEO)</div></div>
  <div class="dept-card"><div class="dept-icon">💰</div><div class="dept-name">מנהל כספים (CFO)</div></div>
  <div class="dept-card"><div class="dept-icon">📣</div><div class="dept-name">מנהל שיווק</div></div>
  <div class="dept-card"><div class="dept-icon">📈</div><div class="dept-name">מנהל מכירות</div></div>
  <div class="dept-card"><div class="dept-icon">⚖️</div><div class="dept-name">יועץ משפטי</div></div>
  <div class="dept-card"><div class="dept-icon">💻</div><div class="dept-name">מנהל טכנולוגיה (CTO)</div></div>
  <div class="dept-card"><div class="dept-icon">🎨</div><div class="dept-name">מנהל תוכן ועיצוב</div></div>
  <div class="dept-card"><div class="dept-icon">🤝</div><div class="dept-name">מנהל יח"צ</div></div>
  <div class="dept-card"><div class="dept-icon">🛡️</div><div class="dept-name">קצין ציות</div></div>
</div>

<script>
async function sendInstruction() {{
  const text = document.getElementById('instruction').value.trim();
  if (!text) return alert('אנא כתוב הוראה');
  document.getElementById('result').textContent = '⏳ שולח לצוות...';
  try {{
    const resp = await fetch('/api/tasks/new', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{instruction: text}})
    }});
    const data = await resp.json();
    document.getElementById('result').textContent = '✅ ההוראה נשלחה! הצוות עובד עליה.';
    document.getElementById('instruction').value = '';
    setTimeout(() => location.reload(), 3000);
  }} catch(e) {{
    document.getElementById('result').textContent = '❌ שגיאה: ' + e.message;
  }}
}}
</script>
</body>
</html>
"""


@app.get("/health")
async def health():
    return {"status": "ok", "company": settings.company_name}
