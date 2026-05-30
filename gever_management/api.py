"""FastAPI dashboard for Gever Management System."""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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
    version="2.0.0"
)

security = HTTPBasic()
_task_manager = None
_meeting_room = None


def get_task_manager():
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def get_meeting_room():
    global _meeting_room
    if _meeting_room is None:
        _meeting_room = MeetingRoom()
    return _meeting_room


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


class DiscussionRequest(BaseModel):
    title: str
    discussion_type: str = "team"
    task_id: Optional[str] = None
    participants: Optional[List[str]] = None


class ActivityLogRequest(BaseModel):
    activity_type: str
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    employee_name: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Optional[dict] = None


class PublishRequest(BaseModel):
    platform: str = "facebook"   # facebook | instagram | tiktok | all
    task_title: Optional[str] = None


class EmployeeCreateRequest(BaseModel):
    name: str
    title_he: str
    title_en: str
    department_code: str
    is_manager: bool = False
    personality: Optional[str] = ""
    expertise: Optional[str] = ""


class EmployeeUpdateRequest(BaseModel):
    name: Optional[str] = None
    title_he: Optional[str] = None
    title_en: Optional[str] = None
    department_code: Optional[str] = None
    is_manager: Optional[bool] = None
    personality: Optional[str] = None
    expertise: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str


class GoalCreateRequest(BaseModel):
    title: str
    description: str
    kpis: Optional[List[str]] = None
    departments: Optional[List[str]] = None
    deadline: Optional[str] = None


class DiscussionCreateRequest(BaseModel):
    title: str
    discussion_type: str = "team"
    task_id: Optional[str] = None
    participants: Optional[List[dict]] = None


# ─── TASK ENDPOINTS ──────────────────────────────────────────────────────────

@app.post("/api/tasks/new")
async def create_task(req: InstructionRequest, user: str = Depends(require_auth)):
    saved = db.save_instruction(req.instruction, req.language)
    result = get_task_manager().process_chairman_instruction(
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
    return get_task_manager().get_task_summary(task_id)


@app.get("/api/review/pending")
async def pending_review():
    return get_task_manager().get_pending_reviews()


@app.post("/api/deliverables/{deliverable_id}/approve")
async def approve(deliverable_id: str, req: Optional[FeedbackRequest] = None,
                  user: str = Depends(require_auth)):
    return get_task_manager().approve_deliverable(
        deliverable_id, req.feedback if req else None
    )


@app.post("/api/deliverables/{deliverable_id}/reject")
async def reject(deliverable_id: str, req: FeedbackRequest,
                 user: str = Depends(require_auth)):
    return get_task_manager().reject_deliverable(deliverable_id, req.feedback)


@app.post("/api/deliverables/{deliverable_id}/publish")
async def publish_deliverable(deliverable_id: str, req: PublishRequest,
                               user: str = Depends(require_auth)):
    result = get_task_manager().publish_deliverable(
        deliverable_id, req.platform, req.task_title or ""
    )
    return {"success": True, **result}


# ─── MEETING ENDPOINTS ───────────────────────────────────────────────────────

@app.post("/api/meetings/new")
async def create_meeting(req: MeetingRequest, user: str = Depends(require_auth)):
    result = get_meeting_room().hold_meeting(
        title=req.title,
        topic=req.topic,
        participants=req.participants,
        meeting_type=req.meeting_type
    )
    return {"success": True, "result": result}


@app.post("/api/consult")
async def consult(req: ConsultRequest, user: str = Depends(require_auth)):
    return get_meeting_room().quick_consult(req.question, req.departments)


# ─── NEW ENDPOINTS ───────────────────────────────────────────────────────────

@app.get("/api/departments")
async def list_departments():
    departments = db.get_departments()
    employees = db.get_employees()
    emp_by_dept = {}
    for emp in employees:
        code = emp.get("department_code", "")
        if code not in emp_by_dept:
            emp_by_dept[code] = []
        emp_by_dept[code].append(emp)
    for dept in departments:
        dept["employees"] = emp_by_dept.get(dept["code"], [])
        dept["employee_count"] = len(dept["employees"])
    return departments


@app.get("/api/employees")
async def list_employees(department: Optional[str] = None):
    return db.get_employees(department=department)


@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str):
    return db.get_employee(employee_id)


@app.post("/api/employees/new")
async def create_employee(req: EmployeeCreateRequest,
                           user: str = Depends(require_auth)):
    emp = db.create_employee(
        name=req.name, title_he=req.title_he, title_en=req.title_en,
        department_code=req.department_code, is_manager=req.is_manager,
        personality=req.personality or "", expertise=req.expertise or ""
    )
    db.log_activity(activity_type="task_created", title=f"עובד חדש גויס: {req.name}",
                    description=f"מחלקה: {req.department_code}", department=req.department_code,
                    employee_name=req.name)
    try:
        from services.email_service import notify_employee_change
        notify_employee_change("גיוס עובד חדש", req.name, f"{req.title_he} | {req.department_code}")
    except Exception:
        pass
    return {"success": True, "employee": emp}


@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: str, req: EmployeeUpdateRequest,
                           user: str = Depends(require_auth)):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    emp = db.update_employee(employee_id, **fields)
    db.log_activity(activity_type="task_created", title=f"פרטי עובד עודכנו: {emp.get('name','')}",
                    department=emp.get("department_code", ""), employee_name=emp.get("name", ""))
    return {"success": True, "employee": emp}


@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: str, user: str = Depends(require_auth)):
    try:
        emp = db.get_employee(employee_id)
        db.delete_employee(employee_id)
        db.log_activity(activity_type="task_created", title=f"עובד הופסק: {emp.get('name','')}",
                        department=emp.get("department_code", ""), employee_name=emp.get("name", ""))
        try:
            from services.email_service import notify_employee_change
            notify_employee_change("סיום העסקה", emp.get("name", ""), emp.get("title_he", ""))
        except Exception:
            pass
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/board")
async def list_board():
    return db.get_board_members()


@app.get("/api/discussions")
async def list_discussions():
    return db.get_discussions()


@app.post("/api/discussions/new")
async def create_discussion(req: DiscussionCreateRequest,
                             user: str = Depends(require_auth)):
    result = db.create_discussion(
        title=req.title,
        discussion_type=req.discussion_type,
        task_id=req.task_id,
        participants=req.participants or []
    )
    db.log_activity(activity_type="discussion",
                    title=f"דיון חדש נפתח: {req.title}",
                    description=f"סוג: {req.discussion_type} • משתתפים: {len(req.participants or [])}")
    return {"success": True, "discussion": result}


@app.get("/api/discussions/{disc_id}")
async def get_discussion(disc_id: str):
    return db.get_discussion(disc_id)


@app.post("/api/discussions/{disc_id}/send")
async def send_discussion_message(disc_id: str, req: SendMessageRequest,
                                   user: str = Depends(require_auth)):
    from agents import DEPARTMENT_AGENTS
    disc = db.get_discussion(disc_id)
    if not disc:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if disc.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Discussion is closed")

    db.add_discussion_message(disc_id, "פארוק ג'בר", req.message, 'יו"ר')

    disc = db.get_discussion(disc_id)
    messages = disc.get("messages", [])
    participants = disc.get("participants", [])

    context = (
        f"דיון פנימי בחברה: {disc['title']}\n"
        f"סוג: {disc.get('discussion_type','')}\n\n"
        "שיחה אחרונה:\n" +
        "\n".join(
            f"{m['sender']} ({m.get('role','')}): {m['message']}"
            for m in messages[-12:]
        )
    )

    ai_responses = []
    for p in participants:
        if not isinstance(p, dict):
            continue
        dept_code = p.get("department_code")
        if not dept_code or dept_code not in DEPARTMENT_AGENTS:
            continue
        agent = DEPARTMENT_AGENTS[dept_code]()
        prompt = (
            f"אתה {p.get('name','')} – {p.get('title_he', dept_code)} – בדיון פנימי.\n\n"
            f"{context}\n\n"
            f"היו\"ר פארוק ג'בר שאל/כתב:\n{req.message}\n\n"
            f"השב מנקודת מבט מקצועית שלך בלבד (2-4 משפטים). תשובה ישירה ותכליתית."
        )
        response = agent.think(prompt)
        db.add_discussion_message(disc_id, p["name"], response, p.get("title_he", ""))
        ai_responses.append({"name": p["name"], "response": response})

    updated = db.get_discussion(disc_id)
    return {"success": True, "messages": updated.get("messages", []), "ai_responses": ai_responses}


@app.post("/api/discussions/{disc_id}/close")
async def close_discussion(disc_id: str, user: str = Depends(require_auth)):
    disc = db.get_discussion(disc_id)
    db.close_discussion(disc_id)
    db.log_activity(activity_type="discussion",
                    title=f"דיון נסגר: {disc.get('title','')}",
                    description="הדיון הסתיים ונסגר")
    return {"success": True}


@app.get("/api/activities")
async def list_activities(limit: int = 50, department: Optional[str] = None):
    return db.get_activities(limit=limit, department=department)


@app.post("/api/activities/log")
async def log_activity(req: ActivityLogRequest,
                       user: str = Depends(require_auth)):
    result = db.log_activity(
        activity_type=req.activity_type,
        title=req.title,
        description=req.description,
        department=req.department,
        employee_name=req.employee_name,
        task_id=req.task_id,
        metadata=req.metadata
    )
    return {"success": True, "activity": result}


@app.get("/api/meetings")
async def list_meetings(limit: int = 20):
    return db.get_meetings(limit=limit)


@app.get("/api/deliverables")
async def list_deliverables(status: Optional[str] = None, limit: int = 50):
    return db.get_all_deliverables(status=status, limit=limit)


# ─── STRATEGIC GOALS ─────────────────────────────────────────────────────────

@app.get("/api/goals")
async def list_goals():
    return db.get_goals()


@app.post("/api/goals/new")
async def create_goal(req: GoalCreateRequest, user: str = Depends(require_auth)):
    goal = db.create_goal(
        title=req.title, description=req.description,
        kpis=req.kpis or [], departments=req.departments or [],
        deadline=req.deadline
    )
    db.log_activity(activity_type="task_created",
                    title=f"יעד אסטרטגי חדש: {req.title}",
                    description=req.description, department="ceo")
    return {"success": True, "goal": goal}


@app.delete("/api/goals/{goal_id}")
async def archive_goal(goal_id: str, user: str = Depends(require_auth)):
    db.archive_goal(goal_id)
    db.log_activity(activity_type="task_completed",
                    title="יעד אסטרטגי הושלם/הוסר", department="ceo")
    return {"success": True}


@app.post("/api/goals/execute")
async def execute_goals(user: str = Depends(require_auth)):
    result = get_task_manager().execute_strategic_goals()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "task_id": result.get("task_id"), "departments": result.get("departments_involved")}


# ─── DASHBOARD HTML ──────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>גבר יזמות - מרכז ניהול AI</title>
<style>
  :root {
    --bg: #0a0f1e;
    --surface: #111827;
    --surface2: #1a2236;
    --border: #1e2d45;
    --text: #e2e8f0;
    --muted: #64748b;
    --accent: #3b82f6;
    --accent2: #7c3aed;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --gold: #f59e0b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; background: var(--bg); color: var(--text); direction: rtl; min-height: 100vh; }

  /* Header */
  .header {
    background: linear-gradient(135deg, #1e3a8a 0%, #5b21b6 50%, #1e3a8a 100%);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }
  .header-left { display: flex; align-items: center; gap: 12px; }
  .header-logo { font-size: 2rem; }
  .header-title { font-size: 1.3rem; font-weight: 700; letter-spacing: -0.02em; }
  .header-subtitle { font-size: 0.78rem; opacity: 0.75; margin-top: 2px; }
  .header-right { display: flex; align-items: center; gap: 10px; }
  .chairman-badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.8rem;
    backdrop-filter: blur(4px);
  }

  /* Tabs */
  .tabs-bar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    display: flex;
    gap: 4px;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .tabs-bar::-webkit-scrollbar { display: none; }
  .tab {
    padding: 14px 18px;
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--muted);
    border-bottom: 3px solid transparent;
    white-space: nowrap;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tab:hover { color: var(--text); background: rgba(255,255,255,0.04); border-radius: 6px 6px 0 0; }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }

  /* Main Content */
  .content { padding: 24px; max-width: 1400px; margin: 0 auto; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* Stats Row */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
  }
  .stat-card:hover { transform: translateY(-2px); border-color: var(--accent); }
  .stat-number { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .stat-label { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }

  /* Section Titles */
  .section-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* Instruction Box */
  .instruction-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 24px;
  }
  .instruction-box h3 { font-size: 1rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
  .instruction-textarea {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 1rem;
    resize: vertical;
    min-height: 80px;
    direction: rtl;
    font-family: inherit;
    transition: border-color 0.2s;
  }
  .instruction-textarea:focus { outline: none; border-color: var(--accent); }
  .btn {
    background: linear-gradient(135deg, #1e40af, #6d28d9);
    color: white;
    border: none;
    padding: 10px 22px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.95rem;
    margin-top: 10px;
    transition: opacity 0.2s, transform 0.1s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .btn:hover { opacity: 0.9; transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }
  .btn-success { background: linear-gradient(135deg, #059669, #10b981); }
  .btn-danger { background: linear-gradient(135deg, #dc2626, #ef4444); }
  .btn-sm { padding: 6px 14px; font-size: 0.82rem; margin-top: 0; }
  .result-msg { margin-top: 12px; font-size: 0.9rem; color: var(--accent); min-height: 20px; }

  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    transition: border-color 0.2s;
  }
  .card:hover { border-color: rgba(59,130,246,0.4); }

  /* Task Cards */
  .task-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-right: 4px solid var(--accent);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
  }
  .task-card.review { border-right-color: var(--warning); }
  .task-card.approved { border-right-color: var(--success); }
  .task-card.urgent { border-right-color: var(--danger); }
  .task-title { font-weight: 600; font-size: 0.95rem; }
  .task-meta { font-size: 0.78rem; color: var(--muted); margin-top: 5px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

  /* Badge */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.73rem;
    font-weight: 600;
  }
  .badge-blue { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
  .badge-yellow { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
  .badge-green { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
  .badge-red { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
  .badge-purple { background: rgba(124,58,237,0.15); color: #a78bfa; border: 1px solid rgba(124,58,237,0.3); }
  .badge-gray { background: rgba(100,116,139,0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }

  /* ── Content Modal ───────────────────────────────────────── */
  .modal-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.88);
    z-index: 2000;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 16px;
  }
  .modal-overlay.open { display: flex; }
  .modal-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    width: 100%; max-width: 840px;
    max-height: 90vh;
    display: flex; flex-direction: column;
    animation: modalIn 0.2s ease;
  }
  @keyframes modalIn {
    from { opacity:0; transform: translateY(18px) scale(0.98); }
    to   { opacity:1; transform: translateY(0)    scale(1); }
  }
  .modal-header {
    padding: 16px 20px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
    border-radius: 16px 16px 0 0;
    display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
  }
  .modal-title  { font-size: 1.05rem; font-weight: 700; }
  .modal-subtitle { font-size: 0.78rem; color: var(--muted); margin-top: 3px; }
  .modal-close {
    background: rgba(255,255,255,0.06); border: 1px solid var(--border);
    color: var(--muted); cursor: pointer; font-size: 1rem;
    width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; transition: background 0.15s;
  }
  .modal-close:hover { background: rgba(255,255,255,0.14); color: var(--text); }
  .modal-body {
    flex: 1; overflow-y: auto; padding: 20px;
    font-size: 0.9rem; line-height: 1.8;
    white-space: pre-wrap; word-break: break-word; direction: rtl;
  }
  .modal-footer {
    padding: 12px 20px;
    background: var(--surface2);
    border-top: 1px solid var(--border);
    border-radius: 0 0 16px 16px;
    display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
  }
  .modal-footer .spacer { flex: 1; }
  .btn-copy     { background: linear-gradient(135deg,#0f766e,#0d9488); }
  .btn-download { background: linear-gradient(135deg,#1d4ed8,#2563eb); }
  .btn-publish  { background: linear-gradient(135deg,#9333ea,#c026d3); }
  .read-more-btn {
    background: none; border: 1px solid var(--border); color: var(--accent);
    font-size: 0.78rem; border-radius: 6px; padding: 4px 10px;
    cursor: pointer; margin-top: 6px; transition: background 0.15s;
  }
  .read-more-btn:hover { background: rgba(59,130,246,0.1); }

  /* Departments Grid */
  .departments-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }
  .dept-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .dept-card:hover { transform: translateY(-2px); border-color: var(--accent); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .dept-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .dept-icon { font-size: 2rem; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; background: rgba(59,130,246,0.1); border-radius: 12px; }
  .dept-name { font-weight: 700; font-size: 1rem; }
  .dept-manager { font-size: 0.8rem; color: var(--muted); margin-top: 2px; }
  .dept-employees { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
  .employee-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 10px;
    font-size: 0.77rem;
    margin: 3px;
  }
  .employee-chip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success); }
  .employee-chip.manager { border-color: rgba(245,158,11,0.5); color: #fbbf24; }
  .employee-chip.manager .dot { background: var(--gold); }

  /* Meeting Transcript */
  .meetings-list { display: flex; flex-direction: column; gap: 16px; }
  .meeting-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
  }
  .meeting-header {
    padding: 14px 18px;
    background: var(--surface2);
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: background 0.2s;
  }
  .meeting-header:hover { background: rgba(59,130,246,0.08); }
  .meeting-title { font-weight: 600; font-size: 0.95rem; }
  .meeting-meta { font-size: 0.78rem; color: var(--muted); margin-top: 3px; }
  .meeting-body { padding: 16px 18px; display: none; }
  .meeting-body.open { display: block; }
  .transcript { display: flex; flex-direction: column; gap: 10px; }
  .transcript-msg {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }
  .speaker-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
  }
  .speaker-bubble {
    background: var(--surface2);
    border-radius: 10px;
    padding: 10px 14px;
    flex: 1;
  }
  .speaker-name { font-size: 0.78rem; font-weight: 700; color: var(--accent); margin-bottom: 4px; }
  .speaker-text { font-size: 0.88rem; line-height: 1.5; }
  .decisions-box { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); border-radius: 10px; padding: 12px; margin-top: 12px; }
  .decisions-box h4 { color: var(--success); font-size: 0.85rem; margin-bottom: 8px; }
  .decisions-box li { font-size: 0.85rem; margin-right: 16px; margin-bottom: 4px; }

  /* Discussions */
  .discussions-list { display: flex; flex-direction: column; gap: 12px; }
  .discussion-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }
  .discussion-header {
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    background: var(--surface2);
  }
  .discussion-msgs { padding: 12px 16px; display: none; }
  .discussion-msgs.open { display: block; }
  .msg-row { display: flex; gap: 10px; margin-bottom: 10px; }
  .msg-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: linear-gradient(135deg, #1d4ed8, #7c3aed);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; font-weight: 700; flex-shrink: 0;
  }
  .msg-bubble { background: var(--surface2); border-radius: 8px; padding: 8px 12px; flex: 1; }
  .msg-sender { font-size: 0.75rem; font-weight: 700; color: var(--accent); }
  .msg-text { font-size: 0.85rem; margin-top: 2px; }
  .msg-time { font-size: 0.7rem; color: var(--muted); margin-top: 3px; }

  /* Activity Feed */
  .activity-feed { display: flex; flex-direction: column; gap: 0; }
  .activity-item {
    display: flex;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--border);
    align-items: flex-start;
  }
  .activity-item:last-child { border-bottom: none; }
  .activity-icon {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
  }
  .activity-icon.task_created { background: rgba(59,130,246,0.15); }
  .activity-icon.task_completed { background: rgba(16,185,129,0.15); }
  .activity-icon.deliverable_submitted { background: rgba(245,158,11,0.15); }
  .activity-icon.deliverable_approved { background: rgba(16,185,129,0.15); }
  .activity-icon.meeting_held { background: rgba(124,58,237,0.15); }
  .activity-icon.published { background: rgba(236,72,153,0.15); }
  .activity-icon.discussion { background: rgba(6,182,212,0.15); }
  .activity-content { flex: 1; }
  .activity-title { font-size: 0.9rem; font-weight: 600; }
  .activity-desc { font-size: 0.8rem; color: var(--muted); margin-top: 3px; }
  .activity-time { font-size: 0.72rem; color: var(--muted); margin-top: 4px; }
  .activity-meta { display: flex; gap: 8px; margin-top: 5px; flex-wrap: wrap; }

  /* Deliverables */
  .deliverables-list { display: flex; flex-direction: column; gap: 14px; }
  .deliverable-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
  }
  .deliverable-header {
    padding: 14px 18px;
    background: var(--surface2);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .deliverable-body { padding: 16px 18px; }
  .deliverable-content {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    font-size: 0.85rem;
    line-height: 1.6;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    direction: auto;
  }
  .deliverable-actions { display: flex; gap: 8px; margin-top: 12px; }

  /* Board Members */
  .board-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
  }
  .board-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    transition: all 0.2s;
  }
  .board-card:hover { transform: translateY(-2px); border-color: var(--gold); }
  .board-avatar {
    width: 60px; height: 60px; border-radius: 50%;
    background: linear-gradient(135deg, #1e40af, #7c3aed);
    margin: 0 auto 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; font-weight: 700;
  }
  .board-avatar.chairman { background: linear-gradient(135deg, #92400e, #f59e0b); }
  .board-name { font-weight: 700; font-size: 1rem; }
  .board-title { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }
  .board-expertise { font-size: 0.75rem; color: var(--muted); margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); }

  /* Filter Bar */
  .filter-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .filter-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 6px 14px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 0.82rem;
    transition: all 0.2s;
  }
  .filter-btn:hover, .filter-btn.active { background: var(--accent); border-color: var(--accent); color: white; }

  /* Loading */
  .loading { text-align: center; padding: 40px; color: var(--muted); }
  .spinner { display: inline-block; width: 28px; height: 28px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Empty State */
  .empty-state { text-align: center; padding: 50px 20px; color: var(--muted); }
  .empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
  .empty-state p { font-size: 0.9rem; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }

  /* Responsive */
  @media (max-width: 768px) {
    .content { padding: 14px; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .departments-grid { grid-template-columns: 1fr; }
    .board-grid { grid-template-columns: repeat(2, 1fr); }
    .header { padding: 12px 16px; }
  }

  /* Tooltip */
  [title] { cursor: help; }

  /* Notification toast */
  .toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 0.9rem;
    z-index: 9999;
    transition: transform 0.3s;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    max-width: 90vw;
    text-align: center;
  }
  .toast.show { transform: translateX(-50%) translateY(0); }
  .toast.success { border-color: var(--success); color: var(--success); }
  .toast.error { border-color: var(--danger); color: var(--danger); }

  /* ── Participant Picker ───────────────────────────────────── */
  .picker-search {
    width: 100%; background: var(--bg); border: 1px solid var(--border);
    color: var(--text); border-radius: 8px; padding: 8px 12px; font-size: 0.85rem;
    direction: rtl; margin-bottom: 10px; font-family: inherit;
  }
  .picker-search:focus { outline: none; border-color: var(--accent); }
  .picker-scroll {
    max-height: 260px; overflow-y: auto; border: 1px solid var(--border);
    border-radius: 10px; background: var(--bg);
  }
  .picker-dept-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; background: var(--surface2);
    font-size: 0.78rem; font-weight: 700; color: var(--muted);
    border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1;
  }
  .picker-dept-head .pick-all { font-size: 0.72rem; color: var(--accent); cursor: pointer; }
  .picker-item {
    display: flex; align-items: center; gap: 10px; padding: 8px 14px;
    cursor: pointer; font-size: 0.85rem; border-bottom: 1px solid rgba(30,45,69,0.5);
    transition: background 0.15s;
  }
  .picker-item:hover { background: rgba(59,130,246,0.07); }
  .picker-item:last-child { border-bottom: none; }
  .picker-item input[type=checkbox] { width: 15px; height: 15px; cursor: pointer; accent-color: var(--accent); }
  .picker-item .pi-name { font-weight: 600; }
  .picker-item .pi-title { font-size: 0.75rem; color: var(--muted); }
  .selected-chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; min-height: 28px; }
  .sel-chip {
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.35);
    border-radius: 20px; padding: 3px 10px; font-size: 0.75rem; color: #60a5fa;
  }
  .sel-chip button { background: none; border: none; color: #60a5fa; cursor: pointer; font-size: 0.8rem; padding: 0; }

  /* ── Discussion Cards (new) ───────────────────────────────── */
  .disc-card {
    background: var(--surface); border: 1px solid var(--border);
    border-right: 4px solid var(--accent2); border-radius: 12px;
    padding: 14px 16px; margin-bottom: 10px; transition: border-color 0.2s;
    cursor: pointer;
  }
  .disc-card:hover { border-color: var(--accent2); box-shadow: 0 4px 14px rgba(0,0,0,0.25); }
  .disc-card.closed { border-right-color: var(--muted); opacity: 0.7; }
  .disc-card.committee { border-right-color: var(--gold); }
  .disc-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
  .disc-title { font-weight: 700; font-size: 0.95rem; }
  .disc-meta { font-size: 0.77rem; color: var(--muted); margin-top: 5px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .disc-participants { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .disc-participant {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 20px; padding: 2px 9px; font-size: 0.72rem; color: var(--muted);
    display: inline-flex; align-items: center; gap: 4px;
  }
  .disc-last-msg {
    margin-top: 8px; padding: 8px 10px; background: var(--bg);
    border-radius: 7px; font-size: 0.8rem; color: var(--muted);
    border: 1px solid var(--border); overflow: hidden;
    white-space: nowrap; text-overflow: ellipsis;
  }

  /* ── Discussion Chat Modal ────────────────────────────────── */
  .disc-chat-box {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; width: 100%; max-width: 900px; max-height: 92vh;
    display: flex; flex-direction: column; animation: modalIn 0.2s ease;
  }
  .chat-participants-bar {
    padding: 10px 18px; background: var(--bg);
    border-bottom: 1px solid var(--border);
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  }
  .chat-participants-bar .label { font-size: 0.75rem; color: var(--muted); margin-left: 4px; }
  .chat-thread {
    flex: 1; overflow-y: auto; padding: 16px 18px;
    display: flex; flex-direction: column; gap: 10px;
  }
  .chat-msg {
    display: flex; gap: 10px; align-items: flex-start;
    animation: fadeInUp 0.2s ease;
  }
  @keyframes fadeInUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
  .chat-msg.chairman { flex-direction: row-reverse; }
  .chat-avatar {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700;
    background: linear-gradient(135deg, #1e40af, #7c3aed);
  }
  .chat-msg.chairman .chat-avatar { background: linear-gradient(135deg, #92400e, #f59e0b); }
  .chat-bubble {
    background: var(--surface2); border-radius: 12px 12px 12px 2px;
    padding: 10px 14px; max-width: 72%;
  }
  .chat-msg.chairman .chat-bubble { background: rgba(30,64,175,0.25); border-radius: 12px 12px 2px 12px; }
  .chat-bubble-name { font-size: 0.73rem; font-weight: 700; color: var(--accent); margin-bottom: 4px; }
  .chat-msg.chairman .chat-bubble-name { color: var(--gold); }
  .chat-bubble-text { font-size: 0.87rem; line-height: 1.55; }
  .chat-bubble-time { font-size: 0.68rem; color: var(--muted); margin-top: 4px; }
  .chat-input-row {
    display: flex; gap: 8px; padding: 12px 16px;
    background: var(--surface2); border-top: 1px solid var(--border);
    border-radius: 0 0 16px 16px;
  }
  .chat-input {
    flex: 1; background: var(--bg); border: 1px solid var(--border);
    color: var(--text); border-radius: 10px; padding: 9px 13px;
    font-size: 0.9rem; direction: rtl; font-family: inherit;
    resize: none; min-height: 40px; max-height: 100px;
  }
  .chat-input:focus { outline: none; border-color: var(--accent); }
  .chat-typing {
    display: none; padding: 8px 18px; font-size: 0.78rem; color: var(--muted);
    font-style: italic;
  }
  .chat-typing.show { display: block; }

  /* ── Meeting Creation Form ────────────────────────────────── */
  .meeting-dept-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 8px; margin-top: 6px;
  }
  .meeting-dept-item {
    display: flex; align-items: center; gap: 8px;
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 10px; cursor: pointer;
    transition: all 0.15s; font-size: 0.83rem;
  }
  .meeting-dept-item:hover { border-color: var(--accent); }
  .meeting-dept-item.selected { border-color: var(--accent); background: rgba(59,130,246,0.12); color: white; }
  .meeting-dept-item input { accent-color: var(--accent); }
  .meeting-type-btns { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
  .type-btn {
    padding: 7px 14px; border-radius: 20px; border: 1px solid var(--border);
    background: var(--bg); color: var(--muted); cursor: pointer;
    font-size: 0.82rem; transition: all 0.15s;
  }
  .type-btn.selected { border-color: var(--accent); background: rgba(59,130,246,0.15); color: white; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-left">
    <div class="header-logo">🏢</div>
    <div>
      <div class="header-title">גבר יזמות ייעוץ עסקי והשקעות</div>
      <div class="header-subtitle">מרכז ניהול AI • Gever Entrepreneurship Management</div>
    </div>
  </div>
  <div class="header-right">
    <div class="chairman-badge">👑 פארוק ג'בר — יו"ר</div>
  </div>
</div>

<!-- Tabs -->
<div class="tabs-bar">
  <div class="tab active" onclick="switchTab('home')" id="tab-home">🏠 ראשי</div>
  <div class="tab" onclick="switchTab('strategy')" id="tab-strategy">🎯 אסטרטגיה</div>
  <div class="tab" onclick="switchTab('departments')" id="tab-departments">🏢 מחלקות</div>
  <div class="tab" onclick="switchTab('meetings')" id="tab-meetings">🎙️ ישיבות</div>
  <div class="tab" onclick="switchTab('discussions')" id="tab-discussions">💬 דיונים</div>
  <div class="tab" onclick="switchTab('activity')" id="tab-activity">📊 פעילות</div>
  <div class="tab" onclick="switchTab('deliverables')" id="tab-deliverables">📋 תוצרים</div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<!-- Content -->
<div class="content">

  <!-- STRATEGY TAB -->
  <div class="tab-panel" id="panel-strategy">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,rgba(30,58,138,0.3),rgba(91,33,182,0.3));border:1px solid rgba(59,130,246,0.2);border-radius:14px;padding:20px;margin-bottom:20px;">
      <div style="font-size:1.1rem;font-weight:700;margin-bottom:6px;">🎯 תוכנית אסטרטגית — יעדי הדירקטוריון</div>
      <div style="font-size:0.85rem;color:var(--muted);">הגדר יעדים ברורים והצוות כולו יעבוד אוטומטית להשגתם — ללא צורך בהוראות ידניות לכל מחלקה</div>
    </div>

    <!-- Add Goal Form -->
    <div class="card" style="margin-bottom:20px;" id="goal-form-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div style="font-weight:700;font-size:0.95rem;">➕ הוסף יעד אסטרטגי חדש</div>
        <button class="filter-btn" onclick="toggleGoalForm()">סגור ▲</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;" id="goal-form-inner">
        <div>
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:4px;">שם היעד *</div>
          <input id="goal-title" type="text" placeholder='לדוגמה: הגעה ל-5 לידים בשבוע' class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
        </div>
        <div>
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:4px;">תיאור מפורט</div>
          <textarea id="goal-desc" class="instruction-textarea" placeholder="פרט את היעד, הרקע, והציפיות..." style="min-height:70px;"></textarea>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div>
            <div style="font-size:0.78rem;color:var(--muted);margin-bottom:4px;">KPIs (אחד בשורה)</div>
            <textarea id="goal-kpis" class="instruction-textarea" placeholder="5 לידים/שבוע&#10;3 לקוחות/חודש&#10;20% גידול הכנסות" style="min-height:80px;font-size:0.82rem;"></textarea>
          </div>
          <div>
            <div style="font-size:0.78rem;color:var(--muted);margin-bottom:4px;">תאריך יעד</div>
            <input id="goal-deadline" type="date" class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
            <div style="font-size:0.78rem;color:var(--muted);margin-top:10px;margin-bottom:4px;">מחלקות אחראיות</div>
            <div id="goal-dept-checks" style="display:flex;flex-wrap:wrap;gap:5px;">
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="marketing" checked> 📣 שיווק</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="sales" checked> 📈 מכירות</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="content"> 🎨 תוכן</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="pr"> 🤝 יח"צ</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="cfo"> 💰 כספים</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="cto"> 💻 טכנולוגיה</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="legal"> ⚖️ משפטי</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;"><input type="checkbox" value="compliance"> 🛡️ ציות</label>
            </div>
          </div>
        </div>
        <div>
          <button class="btn btn-success btn-sm" onclick="addGoal()">✅ הוסף יעד</button>
          <span id="goal-form-msg" style="font-size:0.83rem;color:var(--accent);margin-right:10px;"></span>
        </div>
      </div>
    </div>

    <!-- Active Goals -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <div class="section-title" style="margin-bottom:0;border:none;">📊 יעדים פעילים</div>
      <button class="filter-btn" onclick="loadGoals()">↻ רענן</button>
    </div>
    <div id="goals-list" style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px;">
      <div class="loading"><div class="spinner"></div></div>
    </div>

    <!-- Execute Panel -->
    <div style="background:linear-gradient(135deg,rgba(5,150,105,0.1),rgba(16,185,129,0.05));border:1px solid rgba(16,185,129,0.25);border-radius:14px;padding:24px;text-align:center;">
      <div style="font-size:1.2rem;font-weight:700;margin-bottom:8px;">🚀 הפעלת עבודה אוטומטית</div>
      <div style="font-size:0.85rem;color:var(--muted);margin-bottom:16px;max-width:480px;margin-left:auto;margin-right:auto;">
        כל המחלקות יעבדו בו-זמנית על היעדים הפעילים וייצרו תוצרים מוכנים לשימוש — פוסטים, תוכניות, סקריפטים, מספרים — ללא הוראות ידניות.
      </div>
      <button class="btn btn-success" onclick="executeGoals()" id="execute-btn" style="font-size:1rem;padding:12px 30px;">
        ⚡ הפעל את כל הצוות עכשיו
      </button>
      <div id="execute-status" style="margin-top:14px;font-size:0.88rem;color:var(--accent);min-height:24px;"></div>
    </div>

  </div>

  <!-- HOME TAB -->
  <div class="tab-panel active" id="panel-home">
    <div class="stats-grid" id="stats-row">
      <div class="stat-card"><div class="stat-number" id="stat-pending">—</div><div class="stat-label">ממתין לאישור</div></div>
      <div class="stat-card"><div class="stat-number" id="stat-inprogress">—</div><div class="stat-label">בעבודה</div></div>
      <div class="stat-card"><div class="stat-number" id="stat-completed">—</div><div class="stat-label">הושלמו</div></div>
      <div class="stat-card"><div class="stat-number">9</div><div class="stat-label">מחלקות</div></div>
      <div class="stat-card"><div class="stat-number" id="stat-employees">—</div><div class="stat-label">עובדים</div></div>
      <div class="stat-card"><div class="stat-number" id="stat-activities">—</div><div class="stat-label">פעולות היום</div></div>
    </div>

    <div class="instruction-box">
      <h3>📝 הוראה חדשה ליו"ר</h3>
      <textarea class="instruction-textarea" id="instruction" placeholder="כתוב כאן את ההוראה שלך... לדוגמה: צור קמפיין שיווקי לרגל חג הפסח, כלול יצירתיות ותוכן מרתק."></textarea>
      <button class="btn" onclick="sendInstruction()">🚀 שלח לצוות</button>
      <div class="result-msg" id="result"></div>
    </div>

    <div class="section-title">👁️ ממתינים לאישורך</div>
    <div id="home-pending">
      <div class="loading"><div class="spinner"></div></div>
    </div>

    <div class="section-title" style="margin-top:24px">⚙️ משימות בעבודה</div>
    <div id="home-inprogress">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

  <!-- DEPARTMENTS TAB -->
  <div class="tab-panel" id="panel-departments">

    <!-- Board Section -->
    <div class="section-title">👑 דירקטוריון החברה</div>
    <div class="board-grid" id="board-grid">
      <div class="loading"><div class="spinner"></div></div>
    </div>

    <!-- Departments + drill-down -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px;">
      <div class="section-title" style="margin-bottom:0;border:none;">🏢 מחלקות ועובדים</div>
      <button class="btn btn-sm btn-success" onclick="showHireModal()">➕ גייס עובד חדש</button>
    </div>

    <!-- Dept filter tabs -->
    <div class="filter-bar" id="dept-filter" style="margin-bottom:16px;">
      <button class="filter-btn active" onclick="filterDept('all',this)">הכל</button>
    </div>

    <div class="departments-grid" id="departments-grid">
      <div class="loading"><div class="spinner"></div></div>
    </div>

    <!-- Selected dept employees -->
    <div id="dept-employees-section" style="display:none;margin-top:24px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div class="section-title" style="margin-bottom:0;border:none;" id="dept-employees-title">עובדי המחלקה</div>
        <button class="filter-btn" onclick="closeDeptDetail()">✕ סגור</button>
      </div>
      <div id="dept-employees-grid" class="departments-grid"></div>
    </div>
  </div>

  <!-- MEETINGS TAB -->
  <div class="tab-panel" id="panel-meetings">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="section-title" style="margin-bottom:0; border:none;">🎙️ ישיבות ופגישות</div>
      <button class="btn btn-sm" onclick="showMeetingModal()">+ ישיבה חדשה</button>
    </div>
    <div class="filter-bar" id="meetings-filter" style="margin-bottom:16px;">
      <button class="filter-btn active" onclick="filterMeetings('all', this)">הכל</button>
      <button class="filter-btn" onclick="filterMeetings('board', this)">דירקטוריון</button>
      <button class="filter-btn" onclick="filterMeetings('management', this)">הנהלה</button>
      <button class="filter-btn" onclick="filterMeetings('department', this)">מחלקה</button>
      <button class="filter-btn" onclick="filterMeetings('emergency', this)">חירום</button>
    </div>
    <div class="meetings-list" id="meetings-list">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

  <!-- DISCUSSIONS TAB -->
  <div class="tab-panel" id="panel-discussions">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="section-title" style="margin-bottom:0; border:none;">💬 דיונים וועדות</div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-sm" onclick="openDiscModal('discussion')">+ דיון חדש</button>
        <button class="btn btn-sm btn-success" onclick="openDiscModal('committee')">🏛️ ועדה חדשה</button>
      </div>
    </div>
    <div class="filter-bar" id="disc-filter-bar" style="margin-bottom:16px;">
      <button class="filter-btn active" onclick="filterDiscs('all',this)">הכל</button>
      <button class="filter-btn" onclick="filterDiscs('active',this)">פעילים</button>
      <button class="filter-btn" onclick="filterDiscs('closed',this)">סגורים</button>
      <button class="filter-btn" onclick="filterDiscs('committee',this)">ועדות</button>
      <button class="filter-btn" onclick="filterDiscs('management',this)">הנהלה</button>
      <button class="filter-btn" onclick="filterDiscs('team',this)">צוות</button>
      <button class="filter-btn" onclick="filterDiscs('board',this)">דירקטוריון</button>
    </div>
    <div id="discussions-list">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

  <!-- ACTIVITY TAB -->
  <div class="tab-panel" id="panel-activity">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="section-title" style="margin-bottom:0; border:none;">📊 יומן פעילות</div>
      <div class="filter-bar">
        <button class="filter-btn active" onclick="filterActivity('all', this)">הכל</button>
        <button class="filter-btn" onclick="filterActivity('task_created', this)">משימות</button>
        <button class="filter-btn" onclick="filterActivity('task_completed', this)">הושלמו</button>
        <button class="filter-btn" onclick="filterActivity('deliverable_approved', this)">אושרו</button>
        <button class="filter-btn" onclick="filterActivity('meeting_held', this)">ישיבות</button>
        <button class="filter-btn" onclick="filterActivity('published', this)">פרסומים</button>
      </div>
    </div>
    <div id="activity-feed" class="activity-feed">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

  <!-- DELIVERABLES TAB -->
  <div class="tab-panel" id="panel-deliverables">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="section-title" style="margin-bottom:0; border:none;">📋 תוצרים</div>
      <div class="filter-bar">
        <button class="filter-btn active" onclick="filterDeliverables('all', this)">הכל</button>
        <button class="filter-btn" onclick="filterDeliverables('pending_review', this)">ממתין לאישור</button>
        <button class="filter-btn" onclick="filterDeliverables('approved', this)">אושר</button>
        <button class="filter-btn" onclick="filterDeliverables('rejected', this)">נדחה</button>
      </div>
    </div>
    <div class="deliverables-list" id="deliverables-list">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

</div><!-- /content -->

<!-- ── Hire Employee Modal ────────────────────────────────────────────────── -->
<div id="hire-modal" class="modal-overlay" onclick="if(event.target===this)closeHireModal()">
  <div class="modal-box" style="max-width:520px;">
    <div class="modal-header">
      <div><div class="modal-title">➕ גייס עובד חדש</div></div>
      <button class="modal-close" onclick="closeHireModal()">✕</button>
    </div>
    <div class="modal-body" style="white-space:normal;">
      <div style="display:flex;flex-direction:column;gap:12px;">
        <input id="hire-name"     type="text" placeholder="שם מלא *"              class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
        <input id="hire-title-he" type="text" placeholder="תפקיד בעברית *"         class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
        <input id="hire-title-en" type="text" placeholder="Title in English *"     class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
        <select id="hire-dept" class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
          <option value="">בחר מחלקה *</option>
          <option value="ceo">הנהלה</option><option value="cfo">כספים</option>
          <option value="marketing">שיווק</option><option value="sales">מכירות</option>
          <option value="legal">משפטי</option><option value="cto">טכנולוגיה</option>
          <option value="content">תוכן ועיצוב</option><option value="pr">יח"צ</option>
          <option value="compliance">ציות</option>
        </select>
        <label style="display:flex;align-items:center;gap:8px;font-size:0.85rem;cursor:pointer;">
          <input type="checkbox" id="hire-manager" style="width:16px;height:16px;"> מנהל/ת מחלקה
        </label>
        <textarea id="hire-expertise"   class="instruction-textarea" placeholder="תחומי מומחיות"           style="min-height:60px;"></textarea>
        <textarea id="hire-personality" class="instruction-textarea" placeholder="אופי ואישיות (לסוכן AI)" style="min-height:60px;"></textarea>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-success btn-sm" onclick="submitHire()">✅ גייס</button>
      <button class="filter-btn" onclick="closeHireModal()">ביטול</button>
    </div>
  </div>
</div>

<!-- ── Employee Detail Modal ──────────────────────────────────────────────── -->
<div id="emp-modal" class="modal-overlay" onclick="if(event.target===this)closeEmpModal()">
  <div class="modal-box" style="max-width:520px;">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="emp-modal-name">עובד</div>
        <div class="modal-subtitle" id="emp-modal-dept"></div>
      </div>
      <button class="modal-close" onclick="closeEmpModal()">✕</button>
    </div>
    <div class="modal-body" style="white-space:normal;" id="emp-modal-body"></div>
    <div class="modal-footer">
      <button class="btn btn-sm" onclick="promoteEmployee()">⬆️ קדם</button>
      <button class="btn btn-sm" onclick="editEmployee()">✏️ ערוך</button>
      <div class="spacer"></div>
      <button class="btn btn-danger btn-sm" onclick="fireEmployee()">🔴 פטר</button>
    </div>
  </div>
</div>

<!-- ── New Meeting Modal ───────────────────────────────────────────────── -->
<div id="meeting-modal" class="modal-overlay" onclick="if(event.target===this)closeMeetingModal()">
  <div class="modal-box" style="max-width:580px;">
    <div class="modal-header">
      <div><div class="modal-title">🎙️ ישיבה חדשה</div><div class="modal-subtitle">הסוכנים ינהלו את הישיבה ויפיקו פרוטוקול</div></div>
      <button class="modal-close" onclick="closeMeetingModal()">✕</button>
    </div>
    <div class="modal-body" style="white-space:normal;">
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:5px;">כותרת הישיבה *</div>
          <input id="mtg-title" type="text" placeholder='לדוגמה: ישיבת הנהלה - אסטרטגיה 2025' class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
        </div>
        <div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:5px;">נושא / סדר יום *</div>
          <textarea id="mtg-topic" class="instruction-textarea" placeholder="מה נדון בישיבה? פרט את הנושאים..." style="min-height:80px;"></textarea>
        </div>
        <div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:6px;">סוג ישיבה</div>
          <div class="meeting-type-btns">
            <button class="type-btn selected" onclick="selectMtgType('management',this)">🏢 הנהלה</button>
            <button class="type-btn" onclick="selectMtgType('board',this)">👑 דירקטוריון</button>
            <button class="type-btn" onclick="selectMtgType('department',this)">🏗️ מחלקה</button>
            <button class="type-btn" onclick="selectMtgType('emergency',this)">🚨 חירום</button>
          </div>
        </div>
        <div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:6px;">משתתפים — בחר מחלקות</div>
          <div class="meeting-dept-grid" id="mtg-dept-grid">
            <label class="meeting-dept-item selected"><input type="checkbox" value="ceo" checked> 🎯 מנכ"ל</label>
            <label class="meeting-dept-item selected"><input type="checkbox" value="cfo" checked> 💰 כספים</label>
            <label class="meeting-dept-item"><input type="checkbox" value="marketing"> 📣 שיווק</label>
            <label class="meeting-dept-item"><input type="checkbox" value="sales"> 📈 מכירות</label>
            <label class="meeting-dept-item"><input type="checkbox" value="legal"> ⚖️ משפטי</label>
            <label class="meeting-dept-item"><input type="checkbox" value="cto"> 💻 טכנולוגיה</label>
            <label class="meeting-dept-item"><input type="checkbox" value="content"> 🎨 תוכן</label>
            <label class="meeting-dept-item"><input type="checkbox" value="pr"> 🤝 יח"צ</label>
            <label class="meeting-dept-item"><input type="checkbox" value="compliance"> 🛡️ ציות</label>
          </div>
        </div>
        <div id="mtg-status" style="font-size:0.85rem;color:var(--accent);min-height:20px;"></div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-sm btn-success" onclick="submitMeeting()" id="mtg-submit-btn">🎙️ התחל ישיבה</button>
      <button class="filter-btn" onclick="closeMeetingModal()">ביטול</button>
    </div>
  </div>
</div>

<!-- ── Create Discussion / Committee Modal ─────────────────────────────── -->
<div id="disc-create-modal" class="modal-overlay" onclick="if(event.target===this)closeDiscModal()">
  <div class="modal-box" style="max-width:600px;">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="disc-modal-title">+ דיון חדש</div>
        <div class="modal-subtitle" id="disc-modal-sub">בחר משתתפים — הם יוכלו לדון ולהשיב</div>
      </div>
      <button class="modal-close" onclick="closeDiscModal()">✕</button>
    </div>
    <div class="modal-body" style="white-space:normal;">
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:5px;" id="disc-title-label">כותרת הדיון *</div>
          <input id="new-disc-title" type="text" placeholder="נושא הדיון..." class="instruction-textarea" style="min-height:auto;height:42px;padding:8px 12px;">
        </div>
        <div id="disc-type-row">
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:6px;">סוג</div>
          <div class="meeting-type-btns">
            <button class="type-btn selected" onclick="selectDiscType('team',this)">👥 צוות</button>
            <button class="type-btn" onclick="selectDiscType('management',this)">🏢 הנהלה</button>
            <button class="type-btn" onclick="selectDiscType('board',this)">👑 דירקטוריון</button>
            <button class="type-btn" onclick="selectDiscType('direct',this)">👤 ישיר</button>
          </div>
        </div>
        <div>
          <div style="font-size:0.82rem;color:var(--muted);margin-bottom:5px;">משתתפים</div>
          <input class="picker-search" id="disc-picker-search" type="text" placeholder="חפש שם עובד..." oninput="filterPicker(this.value)">
          <div class="picker-scroll" id="disc-picker-list">
            <div style="padding:20px;text-align:center;color:var(--muted);font-size:0.85rem;">טוען עובדים...</div>
          </div>
          <div style="font-size:0.77rem;color:var(--muted);margin-top:6px;">נבחרו:</div>
          <div class="selected-chips" id="disc-selected-chips"></div>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-sm btn-success" onclick="submitDiscussion()" id="disc-submit-btn">✅ צור</button>
      <button class="filter-btn" onclick="closeDiscModal()">ביטול</button>
    </div>
  </div>
</div>

<!-- ── Discussion Chat Modal ──────────────────────────────────────────────── -->
<div id="disc-chat-modal" class="modal-overlay" onclick="if(event.target===this)closeDiscChat()">
  <div class="disc-chat-box">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="chat-disc-title">דיון</div>
        <div class="modal-subtitle" id="chat-disc-meta"></div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <button id="chat-close-disc-btn" class="btn btn-danger btn-sm" onclick="closeChatDiscussion()" style="display:none;">🔒 סגור דיון</button>
        <button class="modal-close" onclick="closeDiscChat()">✕</button>
      </div>
    </div>
    <div class="chat-participants-bar" id="chat-participants-bar">
      <span class="label">משתתפים:</span>
    </div>
    <div class="chat-thread" id="chat-thread"></div>
    <div class="chat-typing" id="chat-typing">⏳ הסוכנים מגיבים...</div>
    <div class="chat-input-row" id="chat-input-area">
      <textarea class="chat-input" id="chat-msg-input" placeholder="כתוב הודעה לצוות..." rows="1"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChatMsg();}"></textarea>
      <button class="btn btn-sm" onclick="sendChatMsg()" id="chat-send-btn">שלח ▶</button>
    </div>
  </div>
</div>

<!-- ── Content Modal ─────────────────────────────────────────────────── -->
<div id="content-modal" class="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal-box">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="modal-title">תוצר</div>
        <div class="modal-subtitle" id="modal-subtitle"></div>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
    <div class="modal-footer">
      <button class="btn btn-sm btn-copy"     onclick="copyModal()">📋 העתק</button>
      <button class="btn btn-sm btn-download" onclick="downloadModal()">⬇️ הורד קובץ</button>
      <div class="spacer"></div>
      <button class="btn btn-sm btn-publish"  id="modal-publish-btn"  style="display:none" onclick="publishModal()">🚀 פרסם</button>
      <button class="btn btn-success btn-sm"  id="modal-approve-btn"  style="display:none" onclick="approveModal()">✅ אשר</button>
      <button class="btn btn-danger  btn-sm"  id="modal-reject-btn"   style="display:none" onclick="rejectModal()">❌ דחה</button>
    </div>
  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────────────────
let allMeetings = [];
let allActivities = [];
let allDeliverables = [];

// ── Modal ──────────────────────────────────────────────────────────────────
let _modalId     = null;
let _modalStatus = null;
let _modalTitle  = '';

function openModal(title, subtitle, content, deliverableId, status) {
  _modalId     = deliverableId || null;
  _modalStatus = status || null;
  _modalTitle  = title || 'תוצר';
  document.getElementById('modal-title').textContent    = _modalTitle;
  document.getElementById('modal-subtitle').textContent = subtitle || '';
  document.getElementById('modal-body').textContent     = content  || '';

  document.getElementById('modal-approve-btn').style.display  = status === 'pending_review' ? 'inline-flex' : 'none';
  document.getElementById('modal-reject-btn').style.display   = status === 'pending_review' ? 'inline-flex' : 'none';
  document.getElementById('modal-publish-btn').style.display  = status === 'approved'       ? 'inline-flex' : 'none';

  document.getElementById('content-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('content-modal').classList.remove('open');
  document.body.style.overflow = '';
  _modalId = null;
}

function copyModal() {
  const text = document.getElementById('modal-body').textContent;
  navigator.clipboard.writeText(text).then(() => toast('הועתק ✓', 'success'));
}

function downloadModal() {
  const text  = document.getElementById('modal-body').textContent;
  const fname = _modalTitle.replace(/[^א-תa-zA-Z0-9 ]/g, '_') + '.txt';
  const blob  = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url   = URL.createObjectURL(blob);
  const a     = Object.assign(document.createElement('a'), { href: url, download: fname });
  a.click();
  URL.revokeObjectURL(url);
  toast('מוריד קובץ ✓', 'success');
}

async function approveModal() {
  if (!_modalId) return;
  await quickApprove(_modalId);
  closeModal();
}

async function rejectModal() {
  if (!_modalId) return;
  const feedback = prompt('סיבת הדחייה:');
  if (!feedback) return;
  await quickReject(_modalId, feedback);
  closeModal();
}

async function publishModal() {
  if (!_modalId) return;
  const platform = prompt('פרסם ב:\n  facebook\n  instagram\n  tiktok\n  all', 'facebook');
  if (!platform) return;
  toast('שולח לפרסום...', '');
  try {
    const r = await fetch(`/api/deliverables/${_modalId}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform })
    }).then(x => x.json());

    if (r.published) {
      toast('פורסם בהצלחה! 🚀', 'success');
    } else {
      // Show download option – content is ready
      const pkg = Object.values(r.results || {})[0]?.package;
      if (pkg) {
        toast('אין חיבור API – מוריד קובץ תוכן מוכן ✓', 'success');
        const blob = new Blob([pkg.content], { type: 'text/plain;charset=utf-8' });
        const url  = URL.createObjectURL(blob);
        const a    = Object.assign(document.createElement('a'), { href: url, download: `post_${platform}.txt` });
        a.click();
        URL.revokeObjectURL(url);
      } else {
        toast('בעיה בפרסום', 'error');
      }
    }
    closeModal();
    loadDeliverables();
  } catch(e) {
    toast('שגיאה: ' + e.message, 'error');
  }
}

// ── Tab Switching ──────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  loadTab(name);
}

function loadTab(name) {
  switch(name) {
    case 'home': loadHome(); break;
    case 'strategy': loadGoals(); break;
    case 'departments': loadDepartments(); break;
    case 'meetings': loadMeetings(); break;
    case 'discussions': loadDiscussions(); break;
    case 'activity': loadActivity(); break;
    case 'deliverables': loadDeliverables(); break;
  }
}

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + type;
  setTimeout(() => el.classList.remove('show'), 3500);
}

// ── Helpers ────────────────────────────────────────────────────────────────
function deptIcon(code) {
  const icons = {
    ceo: '🎯', cfo: '💰', marketing: '📣', sales: '📈',
    legal: '⚖️', cto: '💻', content: '🎨', pr: '🤝', compliance: '🛡️'
  };
  return icons[code] || '🏢';
}

function statusBadge(status) {
  const map = {
    pending: '<span class="badge badge-gray">ממתין</span>',
    in_progress: '<span class="badge badge-blue">בעבודה</span>',
    review: '<span class="badge badge-yellow">לאישור</span>',
    approved: '<span class="badge badge-green">אושר</span>',
    rejected: '<span class="badge badge-red">נדחה</span>',
    published: '<span class="badge badge-purple">פורסם</span>',
    pending_review: '<span class="badge badge-yellow">ממתין לאישור</span>',
    revision_requested: '<span class="badge badge-red">בתיקון</span>',
  };
  return map[status] || `<span class="badge badge-gray">${status}</span>`;
}

function meetingTypeBadge(type) {
  const map = {
    board: '<span class="badge badge-purple">דירקטוריון</span>',
    management: '<span class="badge badge-blue">הנהלה</span>',
    department: '<span class="badge badge-green">מחלקה</span>',
    emergency: '<span class="badge badge-red">חירום</span>',
  };
  return map[type] || `<span class="badge badge-gray">${type}</span>`;
}

function activityIcon(type) {
  const map = {
    task_created: '📝',
    task_completed: '✅',
    deliverable_submitted: '📤',
    deliverable_approved: '👍',
    meeting_held: '🎙️',
    discussion: '💬',
    published: '📢',
  };
  return map[type] || '📌';
}

function timeAgo(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60) return 'לפני ' + diff + ' שניות';
  if (diff < 3600) return 'לפני ' + Math.floor(diff / 60) + ' דקות';
  if (diff < 86400) return 'לפני ' + Math.floor(diff / 3600) + ' שעות';
  if (diff < 604800) return 'לפני ' + Math.floor(diff / 86400) + ' ימים';
  return d.toLocaleDateString('he-IL');
}

function initials(name) {
  if (!name) return '?';
  const parts = name.split(' ');
  if (parts.length >= 2) return parts[0][0] + parts[1][0];
  return name[0];
}

// ── Strategy Tab ───────────────────────────────────────────────────────────
let _goalFormVisible = true;

function toggleGoalForm() {
  _goalFormVisible = !_goalFormVisible;
  document.getElementById('goal-form-inner').style.display = _goalFormVisible ? 'flex' : 'none';
}

async function loadGoals() {
  const el = document.getElementById('goals-list');
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  try {
    const goals = await fetch('/api/goals').then(r => r.json()) || [];
    if (goals.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="icon">🎯</div><p>אין יעדים פעילים. הוסף יעד כדי להתחיל.</p></div>';
      return;
    }
    el.innerHTML = goals.map(g => {
      const kpis = (g.kpis || []);
      const depts = (g.departments || []);
      const deptIcons = { marketing:'📣', sales:'📈', content:'🎨', pr:'🤝', cfo:'💰', cto:'💻', legal:'⚖️', compliance:'🛡️', ceo:'🎯' };
      return `
        <div class="card" style="border-right:4px solid var(--success);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
            <div style="flex:1;">
              <div style="font-weight:700;font-size:1rem;margin-bottom:4px;">📌 ${g.title}</div>
              <div style="font-size:0.83rem;color:var(--muted);margin-bottom:10px;">${g.description}</div>
              ${kpis.length > 0 ? `
                <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px;">
                  ${kpis.map(k => `<span class="badge badge-green">📊 ${k}</span>`).join('')}
                </div>` : ''}
              ${g.deadline ? `<div style="font-size:0.77rem;color:var(--warning);">📅 דד-ליין: ${g.deadline}</div>` : ''}
              ${depts.length > 0 ? `
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;">
                  ${depts.map(d => `<span class="badge badge-blue">${deptIcons[d]||'🏢'} ${d}</span>`).join('')}
                </div>` : ''}
            </div>
            <button class="btn btn-danger btn-sm" onclick="archiveGoal('${g.id}')" style="flex-shrink:0;">✓ הושלם</button>
          </div>
        </div>`;
    }).join('');
  } catch(e) {
    el.innerHTML = '<div class="empty-state"><p>שגיאה בטעינת יעדים</p></div>';
  }
}

async function addGoal() {
  const title = document.getElementById('goal-title').value.trim();
  const desc  = document.getElementById('goal-desc').value.trim();
  if (!title || !desc) { toast('מלא שם ותיאור', 'error'); return; }

  const kpisRaw = document.getElementById('goal-kpis').value.trim();
  const kpis = kpisRaw ? kpisRaw.split('\n').map(k => k.trim()).filter(Boolean) : [];
  const deadline = document.getElementById('goal-deadline').value || null;
  const departments = Array.from(
    document.querySelectorAll('#goal-dept-checks input:checked')
  ).map(cb => cb.value);

  const msgEl = document.getElementById('goal-form-msg');
  msgEl.textContent = 'שומר...';
  try {
    const r = await fetch('/api/goals/new', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ title, description: desc, kpis, departments, deadline })
    }).then(x => x.json());

    if (r.success) {
      toast('✅ יעד נוסף!', 'success');
      msgEl.textContent = '';
      document.getElementById('goal-title').value = '';
      document.getElementById('goal-desc').value = '';
      document.getElementById('goal-kpis').value = '';
      document.getElementById('goal-deadline').value = '';
      loadGoals();
    } else { msgEl.textContent = 'שגיאה'; }
  } catch(e) { msgEl.textContent = 'שגיאה: ' + e.message; }
}

async function archiveGoal(id) {
  if (!confirm('סמן יעד זה כהושלם ולהסיר אותו מהרשימה?')) return;
  await fetch('/api/goals/' + id, { method: 'DELETE' });
  toast('יעד הוסר ✓', 'success');
  loadGoals();
}

async function executeGoals() {
  const goals = await fetch('/api/goals').then(r => r.json());
  if (!goals || goals.length === 0) {
    toast('הוסף יעדים פעילים תחילה', 'error');
    return;
  }
  const btn = document.getElementById('execute-btn');
  const statusEl = document.getElementById('execute-status');
  btn.disabled = true;
  btn.textContent = '⏳ כל המחלקות עובדות...';
  statusEl.innerHTML = '⏳ המנכ"ל מנתח את היעדים ומחלק משימות לכל המחלקות... זה יכול לקחת 2-5 דקות.';

  try {
    const r = await fetch('/api/goals/execute', { method: 'POST' }).then(x => x.json());
    if (r.success) {
      const depts = (r.departments || []).join(', ');
      statusEl.innerHTML = `✅ הצוות סיים לעבוד! מחלקות שעבדו: <strong>${depts}</strong><br>עבור ללשונית "תוצרים" לאישור התוצרים.`;
      toast('🚀 כל המחלקות סיימו!', 'success');
    } else {
      statusEl.innerHTML = '❌ ' + (r.detail || 'שגיאה');
    }
  } catch(e) {
    statusEl.innerHTML = '❌ שגיאה: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ הפעל את כל הצוות עכשיו';
  }
}

// ── Home Tab ───────────────────────────────────────────────────────────────
async function loadHome() {
  try {
    const [pending, inprog, activities, employees] = await Promise.all([
      fetch('/api/review/pending').then(r => r.json()),
      fetch('/api/tasks?status=in_progress').then(r => r.json()),
      fetch('/api/activities?limit=100').then(r => r.json()),
      fetch('/api/employees').then(r => r.json()),
    ]);

    document.getElementById('stat-pending').textContent = pending.length;
    document.getElementById('stat-inprogress').textContent = inprog.length;
    document.getElementById('stat-completed').textContent =
      (await fetch('/api/tasks?status=review').then(r => r.json())).length;
    document.getElementById('stat-employees').textContent = employees.length;

    const today = new Date().toISOString().slice(0, 10);
    const todayActs = (activities || []).filter(a => a.created_at && a.created_at.startsWith(today));
    document.getElementById('stat-activities').textContent = todayActs.length;

    // Pending
    const pendingEl = document.getElementById('home-pending');
    if (!pending || pending.length === 0) {
      pendingEl.innerHTML = '<div class="empty-state"><div class="icon">✅</div><p>אין תוצרים ממתינים לאישור</p></div>';
    } else {
      pendingEl.innerHTML = pending.slice(0, 5).map(p => {
        const preview = (p.content || '').slice(0, 220);
        const hasMore = (p.content || '').length > 220;
        const subtitle = `${deptIcon(p.department)} ${p.department || ''} • ${timeAgo(p.created_at)}`;
        return `
        <div class="task-card review">
          <div class="task-title">${p.agent_role || ''} — ${(p.tasks && p.tasks.title) || ''}</div>
          <div class="task-meta">
            <span>${deptIcon(p.department)} ${p.department || ''}</span>
            ${statusBadge(p.status)}
            <span>${timeAgo(p.created_at)}</span>
          </div>
          <div style="margin-top:10px;font-size:0.83rem;color:var(--muted);background:var(--bg);padding:10px;border-radius:8px;white-space:pre-wrap;max-height:80px;overflow:hidden;">${preview}${hasMore ? '...' : ''}</div>
          ${hasMore ? `<button class="read-more-btn" onclick="openModal('${(p.agent_role||'').replace(/'/g,"\\'")} — ${((p.tasks&&p.tasks.title)||'').replace(/'/g,"\\'")}','${subtitle.replace(/'/g,"\\'")}',${JSON.stringify(p.content||'')},'${p.id}','${p.status}')">📖 קרא הכל</button>` : ''}
          <div class="deliverable-actions" style="margin-top:8px;">
            <button class="btn btn-success btn-sm" onclick="quickApprove('${p.id}')">✅ אשר</button>
            <button class="btn btn-danger btn-sm" onclick="quickReject('${p.id}')">❌ דחה</button>
          </div>
        </div>`;
      }).join('');
    }

    // In Progress
    const ipEl = document.getElementById('home-inprogress');
    if (!inprog || inprog.length === 0) {
      ipEl.innerHTML = '<div class="empty-state"><div class="icon">🔍</div><p>אין משימות פעילות כרגע</p></div>';
    } else {
      ipEl.innerHTML = inprog.slice(0, 5).map(t => `
        <div class="task-card">
          <div class="task-title">${t.title || ''}</div>
          <div class="task-meta">
            <span>${t.assigned_to || ''}</span>
            ${statusBadge(t.status)}
            <span>${timeAgo(t.created_at)}</span>
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    console.error(e);
    document.getElementById('home-pending').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת נתונים</p></div>';
  }
}

// ── Employee Management ────────────────────────────────────────────────────
let _currentEmpId = null;
let _currentEmpData = null;

function showHireModal() {
  document.getElementById('hire-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeHireModal() {
  document.getElementById('hire-modal').classList.remove('open');
  document.body.style.overflow = '';
}

async function submitHire() {
  const name    = document.getElementById('hire-name').value.trim();
  const titleHe = document.getElementById('hire-title-he').value.trim();
  const titleEn = document.getElementById('hire-title-en').value.trim();
  const dept    = document.getElementById('hire-dept').value;
  if (!name || !titleHe || !titleEn || !dept) { toast('מלא את כל השדות החובה', 'error'); return; }
  try {
    const r = await fetch('/api/employees/new', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        name, title_he: titleHe, title_en: titleEn, department_code: dept,
        is_manager: document.getElementById('hire-manager').checked,
        expertise: document.getElementById('hire-expertise').value.trim(),
        personality: document.getElementById('hire-personality').value.trim(),
      })
    }).then(x => x.json());
    if (r.success) {
      toast(`✅ ${name} גויס/ה בהצלחה!`, 'success');
      closeHireModal();
      loadDepartments();
    } else { toast('שגיאה בגיוס', 'error'); }
  } catch(e) { toast('שגיאה: ' + e.message, 'error'); }
}

function openEmpModal(emp) {
  _currentEmpId = emp.id;
  _currentEmpData = emp;
  document.getElementById('emp-modal-name').textContent = emp.name;
  document.getElementById('emp-modal-dept').textContent =
    `${emp.title_he} • ${emp.department_code}${emp.is_manager ? ' • מנהל/ת' : ''}`;
  document.getElementById('emp-modal-body').innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div style="display:flex;justify-content:space-between;">
        <span style="color:var(--muted);font-size:0.85rem;">תפקיד</span>
        <span style="font-size:0.85rem;">${emp.title_he}</span>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <span style="color:var(--muted);font-size:0.85rem;">מחלקה</span>
        <span style="font-size:0.85rem;">${deptIcon(emp.department_code)} ${emp.department_code}</span>
      </div>
      ${emp.expertise ? `<div style="margin-top:4px;"><div style="color:var(--muted);font-size:0.82rem;margin-bottom:4px;">מומחיות</div><div style="font-size:0.85rem;">${emp.expertise}</div></div>` : ''}
      ${emp.personality ? `<div style="margin-top:4px;"><div style="color:var(--muted);font-size:0.82rem;margin-bottom:4px;">אופי</div><div style="font-size:0.85rem;color:var(--muted);">${emp.personality}</div></div>` : ''}
      ${emp.is_ai ? '<span class="badge badge-blue" style="width:fit-content;">🤖 AI Agent</span>' : '<span class="badge badge-yellow" style="width:fit-content;">👤 Human</span>'}
    </div>
  `;
  document.getElementById('emp-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeEmpModal() {
  document.getElementById('emp-modal').classList.remove('open');
  document.body.style.overflow = '';
  _currentEmpId = null;
}

async function promoteEmployee() {
  if (!_currentEmpId || !_currentEmpData) return;
  const newTitle = prompt('תפקיד חדש (עברית):', _currentEmpData.title_he);
  if (!newTitle) return;
  const newTitleEn = prompt('New Title (English):', _currentEmpData.title_en);
  const isManager = confirm('למנות כמנהל/ת מחלקה?');
  try {
    await fetch(`/api/employees/${_currentEmpId}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ title_he: newTitle, title_en: newTitleEn || _currentEmpData.title_en, is_manager: isManager })
    });
    toast(`${_currentEmpData.name} קודם/ה בהצלחה! ✓`, 'success');
    closeEmpModal();
    loadDepartments();
  } catch(e) { toast('שגיאה', 'error'); }
}

async function editEmployee() {
  if (!_currentEmpId || !_currentEmpData) return;
  const dept = prompt('מחלקה (ceo/cfo/marketing/sales/legal/cto/content/pr/compliance):', _currentEmpData.department_code);
  if (!dept) return;
  const expertise = prompt('מומחיות:', _currentEmpData.expertise || '');
  try {
    await fetch(`/api/employees/${_currentEmpId}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ department_code: dept, expertise: expertise || '' })
    });
    toast('עודכן בהצלחה ✓', 'success');
    closeEmpModal();
    loadDepartments();
  } catch(e) { toast('שגיאה', 'error'); }
}

async function fireEmployee() {
  if (!_currentEmpId || !_currentEmpData) return;
  if (!confirm(`האם לפטר את ${_currentEmpData.name}?\nפעולה זו אינה ניתנת לביטול.`)) return;
  try {
    await fetch(`/api/employees/${_currentEmpId}`, { method: 'DELETE' });
    toast(`${_currentEmpData.name} הוסר/ה מהמערכת`, 'error');
    closeEmpModal();
    loadDepartments();
  } catch(e) { toast('שגיאה', 'error'); }
}

let _allDepartments = [];

function filterDept(code, btn) {
  document.querySelectorAll('#dept-filter .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (code === 'all') {
    renderDepartmentsGrid(_allDepartments);
    document.getElementById('dept-employees-section').style.display = 'none';
  } else {
    const dept = _allDepartments.find(d => d.code === code);
    if (dept) showDeptDetail(dept);
  }
}

function showDeptDetail(dept) {
  document.getElementById('dept-employees-section').style.display = 'block';
  document.getElementById('dept-employees-title').textContent =
    `${deptIcon(dept.code)} עובדי ${dept.name_he}`;
  const emps = dept.employees || [];
  if (emps.length === 0) {
    document.getElementById('dept-employees-grid').innerHTML =
      '<div class="empty-state"><p>אין עובדים במחלקה זו</p></div>';
    return;
  }
  document.getElementById('dept-employees-grid').innerHTML = emps.map(e => `
    <div class="dept-card" onclick="openEmpModal(${JSON.stringify(e).replace(/"/g,'&quot;')})">
      <div class="dept-header">
        <div class="dept-icon">${e.is_manager ? '⭐' : '👤'}</div>
        <div>
          <div class="dept-name">${e.name}</div>
          <div class="dept-manager">${e.title_he}</div>
        </div>
      </div>
      ${e.expertise ? `<div style="font-size:0.78rem;color:var(--muted);margin-top:6px;">${e.expertise}</div>` : ''}
      <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">
        ${e.is_manager ? '<span class="badge badge-yellow">מנהל/ת</span>' : ''}
        ${e.is_ai ? '<span class="badge badge-blue">🤖 AI</span>' : '<span class="badge badge-gray">👤 Human</span>'}
      </div>
    </div>
  `).join('');
  document.getElementById('dept-employees-section').scrollIntoView({ behavior: 'smooth' });
}

function closeDeptDetail() {
  document.getElementById('dept-employees-section').style.display = 'none';
}

// ── Departments Tab ────────────────────────────────────────────────────────
async function loadDepartments() {
  try {
    const [departments, board] = await Promise.all([
      fetch('/api/departments').then(r => r.json()),
      fetch('/api/board').then(r => r.json()),
    ]);

    // Board
    const boardEl = document.getElementById('board-grid');
    if (!board || board.length === 0) {
      boardEl.innerHTML = '<p style="color:var(--muted)">אין נתוני דירקטוריון</p>';
    } else {
      boardEl.innerHTML = board.map(m => `
        <div class="board-card">
          <div class="board-avatar ${m.role === 'chairman' ? 'chairman' : ''}">
            ${m.role === 'chairman' ? '👑' : initials(m.name)}
          </div>
          <div class="board-name">${m.name}</div>
          <div class="board-title">${m.title_he}</div>
          ${m.is_ai === false ? '<span class="badge badge-yellow" style="margin-top:6px;">אנושי</span>' : '<span class="badge badge-blue" style="margin-top:6px;">AI</span>'}
          ${m.expertise ? `<div class="board-expertise">${m.expertise}</div>` : ''}
        </div>
      `).join('');
    }

    // Departments
    _allDepartments = departments || [];
    // Build filter tabs
    const filterEl = document.getElementById('dept-filter');
    filterEl.innerHTML = '<button class="filter-btn active" onclick="filterDept(\'all\',this)">הכל</button>' +
      (_allDepartments.map(d =>
        `<button class="filter-btn" onclick="filterDept('${d.code}',this)">${deptIcon(d.code)} ${d.name_he}</button>`
      ).join(''));
    renderDepartmentsGrid(_allDepartments);
  } catch(e) {
    console.error(e);
    document.getElementById('departments-grid').innerHTML = '<p style="color:var(--danger)">שגיאה בטעינת מחלקות</p>';
  }
}

function renderDepartmentsGrid(departments) {
  const deptsEl = document.getElementById('departments-grid');
  if (!departments || departments.length === 0) {
    deptsEl.innerHTML = '<p style="color:var(--muted)">אין מחלקות</p>';
    return;
  }
  deptsEl.innerHTML = departments.map(d => {
    const emps = d.employees || [];
    const manager = emps.find(e => e.is_manager);
    const others = emps.filter(e => !e.is_manager);
    return `
      <div class="dept-card" onclick="showDeptDetail(${JSON.stringify(d).replace(/"/g,'&quot;')})">
        <div class="dept-header">
          <div class="dept-icon">${deptIcon(d.code)}</div>
          <div>
            <div class="dept-name">${d.name_he}</div>
            <div class="dept-manager">👤 ${d.manager_name} • ${d.manager_title}</div>
          </div>
        </div>
        ${d.description ? `<div style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;">${d.description}</div>` : ''}
        <div class="dept-employees">
          <div style="font-size:0.75rem;color:var(--muted);margin-bottom:6px;">${emps.length} עובדים • לחץ לפרטים</div>
          ${manager ? `<div class="employee-chip manager">⭐ ${manager.name}</div>` : ''}
          ${others.slice(0,3).map(e => `<div class="employee-chip"><div class="dot"></div>${e.name}</div>`).join('')}
          ${others.length > 3 ? `<div class="employee-chip">+${others.length - 3}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ── Meetings Tab ───────────────────────────────────────────────────────────
async function loadMeetings() {
  try {
    allMeetings = await fetch('/api/meetings').then(r => r.json());
    renderMeetings(allMeetings);
  } catch(e) {
    document.getElementById('meetings-list').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת ישיבות</p></div>';
  }
}

function filterMeetings(type, btn) {
  document.querySelectorAll('#meetings-filter .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const filtered = type === 'all' ? allMeetings : allMeetings.filter(m => m.meeting_type === type);
  renderMeetings(filtered);
}

function renderMeetings(meetings) {
  const el = document.getElementById('meetings-list');
  if (!meetings || meetings.length === 0) {
    el.innerHTML = '<div class="empty-state"><div class="icon">🎙️</div><p>אין ישיבות רשומות</p></div>';
    return;
  }
  el.innerHTML = meetings.map((m, i) => {
    const transcript = Array.isArray(m.transcript) ? m.transcript : [];
    const decisions = Array.isArray(m.decisions) ? m.decisions : [];
    const participants = Array.isArray(m.participants) ? m.participants : [];
    return `
      <div class="meeting-card">
        <div class="meeting-header" onclick="toggleMeeting('m${i}')">
          <div>
            <div class="meeting-title">${m.title || 'ישיבה'}</div>
            <div class="meeting-meta">${meetingTypeBadge(m.meeting_type)} • ${participants.join(', ')} • ${timeAgo(m.created_at)}</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            ${statusBadge(m.status)}
            <span style="color:var(--muted);font-size:1.2rem;" id="arr-m${i}">▾</span>
          </div>
        </div>
        <div class="meeting-body" id="m${i}">
          ${m.agenda ? `<div style="font-size:0.85rem;color:var(--muted);margin-bottom:12px;padding:10px;background:var(--bg);border-radius:8px;"><strong>סדר יום:</strong> ${m.agenda}</div>` : ''}
          ${transcript.length > 0 ? `
            <div class="transcript">
              ${transcript.map(t => `
                <div class="transcript-msg">
                  <div class="speaker-avatar">${initials(t.speaker || t.role || '?')}</div>
                  <div class="speaker-bubble">
                    <div class="speaker-name">${t.speaker || t.role || 'משתתף'}</div>
                    <div class="speaker-text">${t.message || t.content || ''}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          ` : '<p style="color:var(--muted);font-size:0.85rem;">אין תמליל זמין</p>'}
          ${decisions.length > 0 ? `
            <div class="decisions-box">
              <h4>✅ החלטות שהתקבלו</h4>
              <ul>${decisions.map(d => `<li>${typeof d === 'string' ? d : (d.decision || JSON.stringify(d))}</li>`).join('')}</ul>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function toggleMeeting(id) {
  const el = document.getElementById(id);
  const arr = document.getElementById('arr-' + id);
  if (el.classList.contains('open')) {
    el.classList.remove('open');
    if (arr) arr.textContent = '▾';
  } else {
    el.classList.add('open');
    if (arr) arr.textContent = '▴';
  }
}

// ── Meeting Modal ──────────────────────────────────────────────────────────
let _mtgType = 'management';

function showMeetingModal() {
  document.getElementById('meeting-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
  document.getElementById('mtg-status').textContent = '';
  document.getElementById('mtg-submit-btn').disabled = false;
  // visual sync checkboxes with label styles
  document.querySelectorAll('#mtg-dept-grid label').forEach(lbl => {
    const cb = lbl.querySelector('input');
    if (cb.checked) lbl.classList.add('selected'); else lbl.classList.remove('selected');
    cb.onchange = () => {
      if (cb.checked) lbl.classList.add('selected'); else lbl.classList.remove('selected');
    };
  });
}

function closeMeetingModal() {
  document.getElementById('meeting-modal').classList.remove('open');
  document.body.style.overflow = '';
}

function selectMtgType(type, btn) {
  _mtgType = type;
  document.querySelectorAll('.meeting-type-btns .type-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
}

async function submitMeeting() {
  const title = document.getElementById('mtg-title').value.trim();
  const topic = document.getElementById('mtg-topic').value.trim();
  if (!title || !topic) { toast('מלא כותרת ונושא', 'error'); return; }

  const participants = Array.from(
    document.querySelectorAll('#mtg-dept-grid input[type=checkbox]:checked')
  ).map(cb => cb.value);

  if (participants.length === 0) { toast('בחר לפחות משתתף אחד', 'error'); return; }

  const statusEl = document.getElementById('mtg-status');
  const submitBtn = document.getElementById('mtg-submit-btn');
  statusEl.innerHTML = '⏳ הישיבה מתנהלת... הסוכנים דנים בנושא. זה יכול לקחת כמה דקות.';
  submitBtn.disabled = true;

  try {
    const r = await fetch('/api/meetings/new', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ title, topic, participants, meeting_type: _mtgType })
    }).then(x => x.json());

    if (r.success) {
      toast('✅ הישיבה הסתיימה! הפרוטוקול נשמר.', 'success');
      closeMeetingModal();
      document.getElementById('mtg-title').value = '';
      document.getElementById('mtg-topic').value = '';
      loadMeetings();
    } else {
      statusEl.textContent = 'שגיאה בקיום הישיבה';
      submitBtn.disabled = false;
    }
  } catch(e) {
    statusEl.textContent = 'שגיאה: ' + e.message;
    submitBtn.disabled = false;
  }
}

// ── Discussions ────────────────────────────────────────────────────────────
let _allDiscs = [];
let _discType = 'discussion';
let _discSelectedType = 'team';
let _discPickerEmployees = [];
let _discSelectedParticipants = [];
let _chatDiscId = null;

async function loadDiscussions() {
  try {
    _allDiscs = await fetch('/api/discussions').then(r => r.json()) || [];
    renderDiscussions(_allDiscs);
  } catch(e) {
    document.getElementById('discussions-list').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת דיונים</p></div>';
  }
}

function filterDiscs(filter, btn) {
  document.querySelectorAll('#disc-filter-bar .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  let filtered = _allDiscs;
  if (filter === 'active')     filtered = _allDiscs.filter(d => d.status !== 'closed');
  else if (filter === 'closed') filtered = _allDiscs.filter(d => d.status === 'closed');
  else if (filter !== 'all')   filtered = _allDiscs.filter(d => d.discussion_type === filter);
  renderDiscussions(filtered);
}

const _discTypeLabel = { team: 'צוות', management: 'הנהלה', board: 'דירקטוריון', committee: 'ועדה', direct: 'ישיר', employee: 'עובד' };
const _discTypeBadge = { team: 'badge-blue', management: 'badge-purple', board: 'badge-yellow', committee: 'badge-green', direct: 'badge-gray' };

function renderDiscussions(discussions) {
  const el = document.getElementById('discussions-list');
  if (!discussions || discussions.length === 0) {
    el.innerHTML = '<div class="empty-state"><div class="icon">💬</div><p>אין דיונים עדיין. לחץ "+ דיון חדש" כדי להתחיל.</p></div>';
    return;
  }
  el.innerHTML = discussions.map(d => {
    const msgs = Array.isArray(d.messages) ? d.messages : [];
    const parts = Array.isArray(d.participants) ? d.participants : [];
    const isClosed = d.status === 'closed';
    const isCommittee = d.discussion_type === 'committee';
    const lastMsg = msgs[msgs.length - 1];
    const badgeClass = _discTypeBadge[d.discussion_type] || 'badge-gray';
    const typeLabel = _discTypeLabel[d.discussion_type] || d.discussion_type;

    const partsHtml = parts.slice(0, 5).map(p => {
      const n = typeof p === 'string' ? p : (p.name || '');
      return `<span class="disc-participant">${initials(n)} ${n}</span>`;
    }).join('') + (parts.length > 5 ? `<span class="disc-participant">+${parts.length-5}</span>` : '');

    return `
      <div class="disc-card ${isClosed ? 'closed' : ''} ${isCommittee ? 'committee' : ''}"
           onclick="openDiscChat(${JSON.stringify(d.id)})">
        <div class="disc-card-header">
          <div class="disc-title">${isCommittee ? '🏛️ ' : '💬 '}${d.title}</div>
          <div style="display:flex;gap:5px;flex-shrink:0;">
            <span class="badge ${badgeClass}">${typeLabel}</span>
            ${isClosed ? '<span class="badge badge-gray">סגור</span>' : '<span class="badge badge-green">פעיל</span>'}
          </div>
        </div>
        <div class="disc-meta">
          <span>💬 ${msgs.length} הודעות</span>
          <span>•</span>
          <span>${timeAgo(d.updated_at || d.created_at)}</span>
        </div>
        ${parts.length > 0 ? `<div class="disc-participants">${partsHtml}</div>` : ''}
        ${lastMsg ? `<div class="disc-last-msg"><strong>${lastMsg.sender}:</strong> ${(lastMsg.message||'').slice(0,100)}${(lastMsg.message||'').length > 100 ? '...' : ''}</div>` : ''}
      </div>
    `;
  }).join('');
}

// ── Discussion Chat Modal ──────────────────────────────────────────────────
async function openDiscChat(discId) {
  _chatDiscId = discId;
  document.getElementById('disc-chat-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
  document.getElementById('chat-thread').innerHTML = '<div style="text-align:center;padding:30px;color:var(--muted);">⏳ טוען...</div>';

  try {
    const disc = await fetch('/api/discussions/' + discId).then(r => r.json());
    renderChatModal(disc);
  } catch(e) {
    document.getElementById('chat-thread').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת הדיון</p></div>';
  }
}

function renderChatModal(disc) {
  const parts = Array.isArray(disc.participants) ? disc.participants : [];
  const msgs  = Array.isArray(disc.messages)     ? disc.messages     : [];
  const isClosed = disc.status === 'closed';

  document.getElementById('chat-disc-title').textContent = (_discTypeLabel[disc.discussion_type] === 'ועדה' ? '🏛️ ' : '💬 ') + disc.title;
  document.getElementById('chat-disc-meta').textContent =
    `${_discTypeLabel[disc.discussion_type] || disc.discussion_type} • ${msgs.length} הודעות • ${isClosed ? 'סגור' : 'פעיל'}`;

  // Participants bar
  const partsBar = document.getElementById('chat-participants-bar');
  partsBar.innerHTML = '<span class="label">משתתפים:</span>';
  if (parts.length === 0) {
    partsBar.innerHTML += '<span style="font-size:0.78rem;color:var(--muted);">אין משתתפים</span>';
  } else {
    parts.forEach(p => {
      const n = typeof p === 'string' ? p : (p.name || '');
      const t = typeof p === 'object' ? (p.title_he || '') : '';
      partsBar.innerHTML += `<span class="disc-participant" title="${t}">${deptIcon(typeof p === 'object' ? p.department_code : '')} ${n}</span>`;
    });
  }

  // Messages
  const thread = document.getElementById('chat-thread');
  if (msgs.length === 0) {
    thread.innerHTML = '<div class="empty-state" style="padding:30px;"><div class="icon">💬</div><p>אין הודעות עדיין. שלח הודעה ראשונה!</p></div>';
  } else {
    thread.innerHTML = msgs.map(m => {
      const isChairman = (m.sender || '').includes('פארוק') || (m.role || '').includes('יו"ר');
      return `
        <div class="chat-msg ${isChairman ? 'chairman' : ''}">
          <div class="chat-avatar">${initials(m.sender || '?')}</div>
          <div class="chat-bubble">
            <div class="chat-bubble-name">${m.sender || ''} ${m.role ? '— ' + m.role : ''}</div>
            <div class="chat-bubble-text">${(m.message || '').replace(/\n/g,'<br>')}</div>
            <div class="chat-bubble-time">${m.timestamp ? timeAgo(m.timestamp) : ''}</div>
          </div>
        </div>`;
    }).join('');
    thread.scrollTop = thread.scrollHeight;
  }

  // Close discussion button
  const closeBtn = document.getElementById('chat-close-disc-btn');
  closeBtn.style.display = isClosed ? 'none' : 'inline-flex';

  // Input area
  const inputArea = document.getElementById('chat-input-area');
  inputArea.style.display = isClosed ? 'none' : 'flex';
  if (isClosed) {
    thread.innerHTML += '<div style="text-align:center;padding:10px;font-size:0.8rem;color:var(--muted);">🔒 הדיון נסגר</div>';
  }
}

function closeDiscChat() {
  document.getElementById('disc-chat-modal').classList.remove('open');
  document.body.style.overflow = '';
  _chatDiscId = null;
}

async function sendChatMsg() {
  if (!_chatDiscId) return;
  const input = document.getElementById('chat-msg-input');
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  input.disabled = true;
  document.getElementById('chat-send-btn').disabled = true;
  document.getElementById('chat-typing').classList.add('show');

  // Optimistically add chairman's message
  const thread = document.getElementById('chat-thread');
  thread.innerHTML += `
    <div class="chat-msg chairman">
      <div class="chat-avatar">👑</div>
      <div class="chat-bubble">
        <div class="chat-bubble-name">פארוק ג'בר — יו"ר</div>
        <div class="chat-bubble-text">${msg.replace(/\n/g,'<br>')}</div>
        <div class="chat-bubble-time">עכשיו</div>
      </div>
    </div>`;
  thread.scrollTop = thread.scrollHeight;

  try {
    const r = await fetch('/api/discussions/' + _chatDiscId + '/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ message: msg })
    }).then(x => x.json());

    if (r.success) {
      // Re-render with full updated messages
      const disc = await fetch('/api/discussions/' + _chatDiscId).then(x => x.json());
      renderChatModal(disc);
      // Refresh list
      _allDiscs = await fetch('/api/discussions').then(x => x.json()) || [];
      renderDiscussions(_allDiscs);
    } else {
      toast('שגיאה בשליחת הודעה', 'error');
    }
  } catch(e) {
    toast('שגיאה: ' + e.message, 'error');
  } finally {
    input.disabled = false;
    document.getElementById('chat-send-btn').disabled = false;
    document.getElementById('chat-typing').classList.remove('show');
    input.focus();
  }
}

async function closeChatDiscussion() {
  if (!_chatDiscId) return;
  if (!confirm('לסגור את הדיון? לא ניתן יהיה לשלוח הודעות חדשות.')) return;
  try {
    await fetch('/api/discussions/' + _chatDiscId + '/close', { method: 'POST' });
    toast('הדיון נסגר', 'success');
    const disc = await fetch('/api/discussions/' + _chatDiscId).then(r => r.json());
    renderChatModal(disc);
    _allDiscs = await fetch('/api/discussions').then(r => r.json()) || [];
    renderDiscussions(_allDiscs);
  } catch(e) { toast('שגיאה', 'error'); }
}

// ── Create Discussion Modal ────────────────────────────────────────────────
async function openDiscModal(mode) {
  _discType = mode;
  _discSelectedParticipants = [];
  _discSelectedType = mode === 'committee' ? 'committee' : 'team';

  document.getElementById('disc-modal-title').textContent = mode === 'committee' ? '🏛️ ועדה חדשה' : '+ דיון חדש';
  document.getElementById('disc-modal-sub').textContent   = mode === 'committee' ? 'הגדר ועדה ובחר חברים' : 'בחר משתתפים — הם יגיבו על הודעותיך';
  document.getElementById('disc-title-label').textContent = mode === 'committee' ? 'שם הוועדה *' : 'כותרת הדיון *';
  document.getElementById('new-disc-title').value = '';

  // Hide type selector for committee (always "committee")
  document.getElementById('disc-type-row').style.display = mode === 'committee' ? 'none' : 'block';

  document.getElementById('disc-create-modal').classList.add('open');
  document.body.style.overflow = 'hidden';

  renderSelectedChips();
  await loadPickerEmployees();
}

function closeDiscModal() {
  document.getElementById('disc-create-modal').classList.remove('open');
  document.body.style.overflow = '';
}

function selectDiscType(type, btn) {
  _discSelectedType = type;
  document.querySelectorAll('#disc-type-row .type-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
}

async function loadPickerEmployees() {
  const listEl = document.getElementById('disc-picker-list');
  listEl.innerHTML = '<div style="padding:16px;text-align:center;color:var(--muted);font-size:0.85rem;">טוען...</div>';
  try {
    const [employees, board] = await Promise.all([
      fetch('/api/employees').then(r => r.json()),
      fetch('/api/board').then(r => r.json()),
    ]);

    // Board members with synthetic dept codes
    const boardEmps = (board || []).filter(b => b.role !== 'chairman').map(b => ({
      id: 'board-' + b.id, name: b.name, title_he: b.title_he,
      department_code: b.role || 'ceo', is_ai: b.is_ai !== false,
      _dept_label: '👑 דירקטוריון'
    }));

    // Group employees by department
    const deptGroups = {};
    const deptNames = { ceo:'🎯 הנהלה', cfo:'💰 כספים', marketing:'📣 שיווק', sales:'📈 מכירות',
                        legal:'⚖️ משפטי', cto:'💻 טכנולוגיה', content:'🎨 תוכן', pr:'🤝 יח"צ', compliance:'🛡️ ציות' };
    (employees || []).forEach(e => {
      const dk = e.department_code || 'other';
      if (!deptGroups[dk]) deptGroups[dk] = [];
      deptGroups[dk].push({ id: e.id, name: e.name, title_he: e.title_he,
                            department_code: e.department_code, is_ai: e.is_ai !== false });
    });

    _discPickerEmployees = [...boardEmps, ...(employees || []).map(e => ({
      id: e.id, name: e.name, title_he: e.title_he,
      department_code: e.department_code, is_ai: e.is_ai !== false
    }))];

    let html = '';
    if (boardEmps.length > 0) {
      html += `<div class="picker-dept-head">👑 דירקטוריון <span class="pick-all" onclick="pickAllDept('board')">בחר הכל</span></div>`;
      boardEmps.forEach(e => {
        html += pickerItemHtml(e);
      });
    }
    Object.entries(deptGroups).forEach(([code, emps]) => {
      html += `<div class="picker-dept-head">${deptNames[code]||code} <span class="pick-all" onclick="pickAllDept('${code}')">בחר הכל</span></div>`;
      emps.forEach(e => { html += pickerItemHtml(e); });
    });
    listEl.innerHTML = html;
  } catch(e) {
    listEl.innerHTML = '<div style="padding:16px;color:var(--danger);font-size:0.85rem;">שגיאה בטעינת עובדים</div>';
  }
}

function pickerItemHtml(e) {
  const isSelected = _discSelectedParticipants.some(p => p.id === e.id);
  return `<label class="picker-item" id="pi-${e.id}">
    <input type="checkbox" ${isSelected ? 'checked' : ''} onchange="toggleParticipant('${e.id}')">
    <div>
      <div class="pi-name">${e.name} ${e.is_ai ? '🤖' : '👤'}</div>
      <div class="pi-title">${e.title_he || ''} ${e.department_code ? '• ' + e.department_code : ''}</div>
    </div>
  </label>`;
}

function toggleParticipant(empId) {
  const emp = _discPickerEmployees.find(e => e.id === empId || e.id === empId);
  if (!emp) return;
  const idx = _discSelectedParticipants.findIndex(p => p.id === empId);
  if (idx >= 0) {
    _discSelectedParticipants.splice(idx, 1);
  } else {
    _discSelectedParticipants.push(emp);
  }
  renderSelectedChips();
}

function pickAllDept(code) {
  const deptEmps = _discPickerEmployees.filter(e =>
    code === 'board' ? (e._dept_label || '').includes('דירקטוריון') : e.department_code === code
  );
  deptEmps.forEach(e => {
    if (!_discSelectedParticipants.find(p => p.id === e.id)) {
      _discSelectedParticipants.push(e);
    }
    const cb = document.querySelector(`#pi-${e.id} input`);
    if (cb) cb.checked = true;
  });
  renderSelectedChips();
}

function renderSelectedChips() {
  const el = document.getElementById('disc-selected-chips');
  el.innerHTML = _discSelectedParticipants.length === 0
    ? '<span style="font-size:0.78rem;color:var(--muted);">טרם נבחרו משתתפים</span>'
    : _discSelectedParticipants.map(p => `
        <span class="sel-chip">${p.name}
          <button onclick="removeParticipant('${p.id}')">✕</button>
        </span>`).join('');
}

function removeParticipant(id) {
  _discSelectedParticipants = _discSelectedParticipants.filter(p => p.id !== id);
  const cb = document.querySelector(`#pi-${id} input`);
  if (cb) cb.checked = false;
  renderSelectedChips();
}

function filterPicker(query) {
  document.querySelectorAll('.picker-item').forEach(el => {
    const text = el.textContent.toLowerCase();
    el.style.display = (!query || text.includes(query.toLowerCase())) ? '' : 'none';
  });
}

async function submitDiscussion() {
  const title = document.getElementById('new-disc-title').value.trim();
  if (!title) { toast('אנא הכנס כותרת', 'error'); return; }

  const type = _discType === 'committee' ? 'committee' : _discSelectedType;

  try {
    document.getElementById('disc-submit-btn').disabled = true;
    const r = await fetch('/api/discussions/new', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        title, discussion_type: type,
        participants: _discSelectedParticipants
      })
    }).then(x => x.json());

    if (r.success) {
      toast(`✅ ${_discType === 'committee' ? 'ועדה' : 'דיון'} נוצר/ה בהצלחה!`, 'success');
      closeDiscModal();
      loadDiscussions();
      // Auto-open the chat
      if (r.discussion) setTimeout(() => openDiscChat(r.discussion.id), 400);
    } else { toast('שגיאה', 'error'); }
  } catch(e) { toast('שגיאה: ' + e.message, 'error'); }
  finally { document.getElementById('disc-submit-btn').disabled = false; }
}

// ── Activity Tab ───────────────────────────────────────────────────────────
async function loadActivity() {
  try {
    allActivities = await fetch('/api/activities?limit=100').then(r => r.json());
    renderActivity(allActivities);
  } catch(e) {
    document.getElementById('activity-feed').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת פעילות</p></div>';
  }
}

function filterActivity(type, btn) {
  document.querySelectorAll('#panel-activity .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const filtered = type === 'all' ? allActivities : allActivities.filter(a => a.activity_type === type);
  renderActivity(filtered);
}

function renderActivity(activities) {
  const el = document.getElementById('activity-feed');
  if (!activities || activities.length === 0) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📊</div><p>אין פעילות עדיין</p></div>';
    return;
  }
  el.innerHTML = activities.map(a => `
    <div class="activity-item">
      <div class="activity-icon ${a.activity_type}">${activityIcon(a.activity_type)}</div>
      <div class="activity-content">
        <div class="activity-title">${a.title || ''}</div>
        ${a.description ? `<div class="activity-desc">${a.description}</div>` : ''}
        <div class="activity-meta">
          ${a.department ? `<span class="badge badge-blue">${deptIcon(a.department)} ${a.department}</span>` : ''}
          ${a.employee_name ? `<span class="badge badge-gray">👤 ${a.employee_name}</span>` : ''}
        </div>
        <div class="activity-time">${timeAgo(a.created_at)}</div>
      </div>
    </div>
  `).join('');
}

// ── Deliverables Tab ───────────────────────────────────────────────────────
async function loadDeliverables() {
  try {
    allDeliverables = await fetch('/api/deliverables?limit=50').then(r => r.json());
    renderDeliverables(allDeliverables);
  } catch(e) {
    document.getElementById('deliverables-list').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת תוצרים</p></div>';
  }
}

function filterDeliverables(status, btn) {
  document.querySelectorAll('#panel-deliverables .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const filtered = status === 'all' ? allDeliverables : allDeliverables.filter(d => d.status === status);
  renderDeliverables(filtered);
}

function renderDeliverables(deliverables) {
  const el = document.getElementById('deliverables-list');
  if (!deliverables || deliverables.length === 0) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📋</div><p>אין תוצרים</p></div>';
    return;
  }
  el.innerHTML = deliverables.map(d => {
    const taskTitle  = d.tasks ? d.tasks.title : '';
    const subtitle   = `${deptIcon(d.department)} ${d.department||''} • ${taskTitle ? '📋 '+taskTitle+' • ' : ''}${timeAgo(d.created_at)}`;
    const preview    = (d.content || '').slice(0, 300);
    const hasMore    = (d.content || '').length > 300;
    const titleText  = d.agent_role || d.department || 'תוצר';
    return `
      <div class="deliverable-card">
        <div class="deliverable-header">
          <div>
            <div style="font-weight:600;font-size:0.95rem;">${titleText}</div>
            <div style="font-size:0.78rem;color:var(--muted);margin-top:3px;">${subtitle}</div>
          </div>
          ${statusBadge(d.status)}
        </div>
        <div class="deliverable-body">
          <div class="deliverable-content" style="cursor:pointer" onclick="openModal(${JSON.stringify(titleText)},${JSON.stringify(subtitle)},${JSON.stringify(d.content||'')},${JSON.stringify(d.id)},${JSON.stringify(d.status)})">${preview}${hasMore ? '...' : ''}</div>
          <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;align-items:center;">
            <button class="read-more-btn" onclick="openModal(${JSON.stringify(titleText)},${JSON.stringify(subtitle)},${JSON.stringify(d.content||'')},${JSON.stringify(d.id)},${JSON.stringify(d.status)})">📖 קרא הכל</button>
            <button class="btn btn-sm btn-copy"     onclick="navigator.clipboard.writeText(${JSON.stringify(d.content||'')}).then(()=>toast('הועתק ✓','success'))">📋 העתק</button>
            <button class="btn btn-sm btn-download" onclick="dlContent(${JSON.stringify(titleText)},${JSON.stringify(d.content||'')})">⬇️ הורד</button>
            ${d.status === 'pending_review' ? `
              <button class="btn btn-success btn-sm" onclick="quickApprove('${d.id}')">✅ אשר</button>
              <button class="btn btn-danger  btn-sm" onclick="quickReject('${d.id}')">❌ דחה</button>
            ` : ''}
            ${d.status === 'approved' ? `
              <button class="btn btn-sm btn-publish" onclick="publishDirect('${d.id}','${taskTitle.replace(/'/g,"\\'")}')">🚀 פרסם</button>
            ` : ''}
          </div>
          ${d.chairman_feedback ? `<div style="margin-top:10px;padding:10px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;font-size:0.83rem;"><strong>משוב יו"ר:</strong> ${d.chairman_feedback}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ── Actions ────────────────────────────────────────────────────────────────
async function quickApprove(id) {
  try {
    await fetch('/api/deliverables/' + id + '/approve', { method: 'POST' });
    toast('התוצר אושר בהצלחה!', 'success');
    loadHome();
    if (document.getElementById('panel-deliverables').classList.contains('active')) loadDeliverables();
  } catch(e) {
    toast('שגיאה: ' + e.message, 'error');
  }
}

async function quickReject(id, feedbackText) {
  const feedback = feedbackText || prompt('סיבת הדחייה:');
  if (!feedback) return;
  try {
    await fetch('/api/deliverables/' + id + '/reject', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ feedback })
    });
    toast('התוצר נדחה', 'error');
    loadHome();
    if (document.getElementById('panel-deliverables').classList.contains('active')) loadDeliverables();
  } catch(e) {
    toast('שגיאה: ' + e.message, 'error');
  }
}

// ── Send Instruction ───────────────────────────────────────────────────────
async function sendInstruction() {
  const text = document.getElementById('instruction').value.trim();
  if (!text) { toast('אנא כתוב הוראה', 'error'); return; }
  const resultEl = document.getElementById('result');
  resultEl.innerHTML = '<span>⏳ שולח לצוות... הצוות מתחיל לעבוד</span>';
  document.querySelector('.instruction-box .btn').disabled = true;
  try {
    const resp = await fetch('/api/tasks/new', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ instruction: text })
    });
    if (!resp.ok) throw new Error('Server error ' + resp.status);
    const data = await resp.json();
    resultEl.innerHTML = '<span style="color:var(--success)">✅ ההוראה נשלחה! הצוות עובד עליה.</span>';
    document.getElementById('instruction').value = '';
    toast('ההוראה נשלחה לצוות!', 'success');
    setTimeout(() => { loadHome(); }, 2000);
  } catch(e) {
    resultEl.innerHTML = '<span style="color:var(--danger)">❌ שגיאה: ' + e.message + '</span>';
    toast('שגיאה בשליחת הוראה', 'error');
  } finally {
    document.querySelector('.instruction-box .btn').disabled = false;
  }
}

// ── Download helper ────────────────────────────────────────────────────────
function dlContent(title, content) {
  const fname = (title||'content').replace(/[^א-תa-zA-Z0-9 ]/g,'_') + '.txt';
  const blob  = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url   = URL.createObjectURL(blob);
  const a     = Object.assign(document.createElement('a'), { href: url, download: fname });
  a.click();
  URL.revokeObjectURL(url);
  toast('מוריד קובץ ✓', 'success');
}

// ── Publish direct ─────────────────────────────────────────────────────────
async function publishDirect(deliverableId, taskTitle) {
  const platform = prompt('פרסם ב:\n  facebook\n  instagram\n  tiktok\n  all', 'facebook');
  if (!platform) return;
  toast('שולח לפרסום...', '');
  try {
    const r = await fetch(`/api/deliverables/${deliverableId}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, task_title: taskTitle })
    }).then(x => x.json());

    if (r.published) {
      toast('פורסם בהצלחה! 🚀', 'success');
      loadDeliverables();
    } else {
      // No API key → download the ready content
      const results = r.results || {};
      let downloaded = false;
      for (const [p, v] of Object.entries(results)) {
        const pkg = v.package;
        if (pkg) {
          const blob = new Blob([pkg.content], { type: 'text/plain;charset=utf-8' });
          const url  = URL.createObjectURL(blob);
          const a    = Object.assign(document.createElement('a'), { href: url, download: `פרסום_${p}.txt` });
          a.click();
          URL.revokeObjectURL(url);
          downloaded = true;
        }
      }
      toast(downloaded ? 'קובץ תוכן מוכן הורד ✓' : 'לא הצלחנו לפרסם', downloaded ? 'success' : 'error');
    }
  } catch(e) {
    toast('שגיאה: ' + e.message, 'error');
  }
}

// ── Init ───────────────────────────────────────────────────────────────────
loadHome();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard(user: str = Depends(require_auth)):
    return DASHBOARD_HTML


@app.get("/health")
async def health():
    return {"status": "ok", "company": settings.company_name, "version": "2.0.0"}
