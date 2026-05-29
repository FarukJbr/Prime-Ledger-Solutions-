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


@app.get("/api/board")
async def list_board():
    return db.get_board_members()


@app.get("/api/discussions")
async def list_discussions():
    return db.get_discussions()


@app.post("/api/discussions/new")
async def create_discussion(req: DiscussionRequest,
                             user: str = Depends(require_auth)):
    result = db.create_discussion(
        title=req.title,
        discussion_type=req.discussion_type,
        task_id=req.task_id,
        participants=req.participants
    )
    return {"success": True, "discussion": result}


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
    <div class="chairman-badge">👑 פארוק ג'אבר — יו"ר</div>
  </div>
</div>

<!-- Tabs -->
<div class="tabs-bar">
  <div class="tab active" onclick="switchTab('home')" id="tab-home">🏠 ראשי</div>
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
    <div class="section-title">🏢 כל המחלקות</div>

    <!-- Board Section -->
    <div class="section-title" style="margin-top:0">👑 דירקטוריון החברה</div>
    <div class="board-grid" id="board-grid">
      <div class="loading"><div class="spinner"></div></div>
    </div>

    <div class="section-title">🏢 מחלקות ועובדים</div>
    <div class="departments-grid" id="departments-grid">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

  <!-- MEETINGS TAB -->
  <div class="tab-panel" id="panel-meetings">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="section-title" style="margin-bottom:0; border:none;">🎙️ ישיבות ופגישות</div>
      <div class="filter-bar" id="meetings-filter">
        <button class="filter-btn active" onclick="filterMeetings('all', this)">הכל</button>
        <button class="filter-btn" onclick="filterMeetings('board', this)">דירקטוריון</button>
        <button class="filter-btn" onclick="filterMeetings('management', this)">הנהלה</button>
        <button class="filter-btn" onclick="filterMeetings('department', this)">מחלקה</button>
        <button class="filter-btn" onclick="filterMeetings('emergency', this)">חירום</button>
      </div>
    </div>
    <div class="meetings-list" id="meetings-list">
      <div class="loading"><div class="spinner"></div></div>
    </div>
  </div>

  <!-- DISCUSSIONS TAB -->
  <div class="tab-panel" id="panel-discussions">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="section-title" style="margin-bottom:0; border:none;">💬 דיונים צוותיים</div>
      <button class="btn btn-sm" onclick="showNewDiscussionForm()">+ דיון חדש</button>
    </div>
    <div id="new-discussion-form" style="display:none; margin-bottom:16px;">
      <div class="card">
        <h4 style="margin-bottom:12px; font-size:0.9rem;">דיון חדש</h4>
        <input type="text" id="disc-title" placeholder="כותרת הדיון" style="width:100%; background:var(--bg); border:1px solid var(--border); color:var(--text); border-radius:8px; padding:10px 12px; font-size:0.9rem; direction:rtl; margin-bottom:10px; font-family:inherit;">
        <select id="disc-type" style="width:100%; background:var(--bg); border:1px solid var(--border); color:var(--text); border-radius:8px; padding:10px 12px; font-size:0.9rem; direction:rtl; margin-bottom:10px; font-family:inherit;">
          <option value="team">צוות</option>
          <option value="management">הנהלה</option>
          <option value="board">דירקטוריון</option>
          <option value="committee">ועדה</option>
          <option value="employee">עובד</option>
        </select>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-sm" onclick="createDiscussion()">צור דיון</button>
          <button class="filter-btn" onclick="hideNewDiscussionForm()">ביטול</button>
        </div>
      </div>
    </div>
    <div class="discussions-list" id="discussions-list">
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

<script>
// ── State ──────────────────────────────────────────────────────────────────
let allMeetings = [];
let allActivities = [];
let allDeliverables = [];

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
      pendingEl.innerHTML = pending.slice(0, 5).map(p => `
        <div class="task-card review">
          <div class="task-title">${p.agent_role || ''} — ${(p.tasks && p.tasks.title) || ''}</div>
          <div class="task-meta">
            <span>${deptIcon(p.department)} ${p.department || ''}</span>
            ${statusBadge(p.status)}
            <span>${timeAgo(p.created_at)}</span>
          </div>
          <div style="margin-top:10px; font-size:0.83rem; color:var(--muted); background:var(--bg); padding:10px; border-radius:8px; white-space:pre-wrap; max-height:80px; overflow:hidden;">${(p.content || '').slice(0, 200)}${p.content && p.content.length > 200 ? '...' : ''}</div>
          <div class="deliverable-actions" style="margin-top:8px;">
            <button class="btn btn-success btn-sm" onclick="quickApprove('${p.id}')">✅ אשר</button>
            <button class="btn btn-danger btn-sm" onclick="quickReject('${p.id}')">❌ דחה</button>
          </div>
        </div>
      `).join('');
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
    const deptsEl = document.getElementById('departments-grid');
    if (!departments || departments.length === 0) {
      deptsEl.innerHTML = '<p style="color:var(--muted)">אין מחלקות</p>';
    } else {
      deptsEl.innerHTML = departments.map(d => {
        const emps = d.employees || [];
        const manager = emps.find(e => e.is_manager);
        const others = emps.filter(e => !e.is_manager);
        return `
          <div class="dept-card">
            <div class="dept-header">
              <div class="dept-icon">${deptIcon(d.code)}</div>
              <div>
                <div class="dept-name">${d.name_he}</div>
                <div class="dept-manager">👤 ${d.manager_name} • ${d.manager_title}</div>
              </div>
            </div>
            ${d.description ? `<div style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;">${d.description}</div>` : ''}
            <div class="dept-employees">
              <div style="font-size:0.75rem;color:var(--muted);margin-bottom:6px;">${emps.length} עובדים</div>
              ${manager ? `<div class="employee-chip manager">⭐ ${manager.name}</div>` : ''}
              ${others.map(e => `<div class="employee-chip"><div class="dot"></div>${e.name}</div>`).join('')}
            </div>
          </div>
        `;
      }).join('');
    }
  } catch(e) {
    console.error(e);
    document.getElementById('departments-grid').innerHTML = '<p style="color:var(--danger)">שגיאה בטעינת מחלקות</p>';
  }
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

// ── Discussions Tab ────────────────────────────────────────────────────────
async function loadDiscussions() {
  try {
    const discussions = await fetch('/api/discussions').then(r => r.json());
    renderDiscussions(discussions);
  } catch(e) {
    document.getElementById('discussions-list').innerHTML = '<div class="empty-state"><p>שגיאה בטעינת דיונים</p></div>';
  }
}

function renderDiscussions(discussions) {
  const el = document.getElementById('discussions-list');
  if (!discussions || discussions.length === 0) {
    el.innerHTML = '<div class="empty-state"><div class="icon">💬</div><p>אין דיונים עדיין. צור דיון חדש.</p></div>';
    return;
  }
  const typeLabels = { team: 'צוות', management: 'הנהלה', board: 'דירקטוריון', committee: 'ועדה', employee: 'עובד' };
  el.innerHTML = discussions.map((d, i) => {
    const messages = Array.isArray(d.messages) ? d.messages : [];
    const participants = Array.isArray(d.participants) ? d.participants : [];
    return `
      <div class="discussion-card">
        <div class="discussion-header" onclick="toggleDiscussion('d${i}')">
          <div>
            <div style="font-weight:600;font-size:0.9rem;">${d.title}</div>
            <div style="font-size:0.75rem;color:var(--muted);margin-top:3px;">
              <span class="badge badge-blue">${typeLabels[d.discussion_type] || d.discussion_type}</span>
              ${participants.length > 0 ? '• ' + participants.slice(0,3).join(', ') : ''}
              • ${messages.length} הודעות • ${timeAgo(d.updated_at)}
            </div>
          </div>
          <span style="color:var(--muted);" id="arr-d${i}">▾</span>
        </div>
        <div class="discussion-msgs" id="d${i}">
          ${messages.length === 0 ? '<p style="color:var(--muted);font-size:0.85rem;">אין הודעות עדיין</p>' :
            messages.map(m => `
              <div class="msg-row">
                <div class="msg-avatar">${initials(m.sender || '?')}</div>
                <div class="msg-bubble">
                  <div class="msg-sender">${m.sender || '?'} ${m.role ? '— ' + m.role : ''}</div>
                  <div class="msg-text">${m.message || ''}</div>
                  ${m.timestamp ? `<div class="msg-time">${timeAgo(m.timestamp)}</div>` : ''}
                </div>
              </div>
            `).join('')
          }
        </div>
      </div>
    `;
  }).join('');
}

function toggleDiscussion(id) {
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

function showNewDiscussionForm() {
  document.getElementById('new-discussion-form').style.display = 'block';
}

function hideNewDiscussionForm() {
  document.getElementById('new-discussion-form').style.display = 'none';
}

async function createDiscussion() {
  const title = document.getElementById('disc-title').value.trim();
  const type = document.getElementById('disc-type').value;
  if (!title) { toast('אנא הכנס כותרת לדיון', 'error'); return; }
  try {
    await fetch('/api/discussions/new', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ title, discussion_type: type })
    });
    hideNewDiscussionForm();
    document.getElementById('disc-title').value = '';
    toast('דיון נוצר בהצלחה!', 'success');
    loadDiscussions();
  } catch(e) {
    toast('שגיאה ביצירת דיון: ' + e.message, 'error');
  }
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
    const taskTitle = d.tasks ? d.tasks.title : '';
    return `
      <div class="deliverable-card">
        <div class="deliverable-header">
          <div>
            <div style="font-weight:600;font-size:0.95rem;">${d.agent_role || d.department || ''}</div>
            <div style="font-size:0.78rem;color:var(--muted);margin-top:3px;">
              ${deptIcon(d.department)} ${d.department || ''} • ${taskTitle ? '📋 ' + taskTitle + ' •' : ''} ${timeAgo(d.created_at)}
            </div>
          </div>
          ${statusBadge(d.status)}
        </div>
        <div class="deliverable-body">
          <div class="deliverable-content">${d.content || ''}</div>
          ${d.chairman_feedback ? `<div style="margin-top:10px;padding:10px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;font-size:0.83rem;"><strong>משוב יו"ר:</strong> ${d.chairman_feedback}</div>` : ''}
          ${d.status === 'pending_review' ? `
            <div class="deliverable-actions">
              <button class="btn btn-success btn-sm" onclick="quickApprove('${d.id}')">✅ אשר</button>
              <button class="btn btn-danger btn-sm" onclick="quickReject('${d.id}')">❌ דחה</button>
            </div>
          ` : ''}
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

async function quickReject(id) {
  const feedback = prompt('סיבת הדחייה:');
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
