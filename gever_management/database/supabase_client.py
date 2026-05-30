from supabase import create_client, Client
from config import settings
import uuid
from datetime import datetime


class DatabaseClient:
    def __init__(self):
        self._client: Client = None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
        return self._client

    @property
    def client(self) -> Client:
        return self._get_client()

    # ─── TASKS ───────────────────────────────────────────────────────────────

    def create_task(self, title: str, description: str, assigned_to: str,
                    priority: str = "normal", language: str = "he",
                    metadata: dict = None) -> dict:
        data = {
            "title": title,
            "description": description,
            "assigned_to": assigned_to,
            "priority": priority,
            "language": language,
            "metadata": metadata or {},
            "status": "pending"
        }
        result = self.client.table("tasks").insert(data).execute()
        return result.data[0]

    def update_task_status(self, task_id: str, status: str) -> dict:
        result = (
            self.client.table("tasks")
            .update({"status": status})
            .eq("id", task_id)
            .execute()
        )
        return result.data[0]

    def get_task(self, task_id: str) -> dict:
        result = (
            self.client.table("tasks")
            .select("*")
            .eq("id", task_id)
            .single()
            .execute()
        )
        return result.data

    def get_tasks_by_status(self, status: str) -> list:
        result = (
            self.client.table("tasks")
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    # ─── DELIVERABLES ────────────────────────────────────────────────────────

    def save_deliverable(self, task_id: str, department: str, agent_role: str,
                         content: str, content_type: str = "text") -> dict:
        data = {
            "task_id": task_id,
            "department": department,
            "agent_role": agent_role,
            "content": content,
            "content_type": content_type,
            "status": "pending_review"
        }
        result = self.client.table("deliverables").insert(data).execute()
        return result.data[0]

    def update_deliverable_status(self, deliverable_id: str, status: str,
                                  feedback: str = None) -> dict:
        update_data = {"status": status}
        if feedback:
            update_data["chairman_feedback"] = feedback
        result = (
            self.client.table("deliverables")
            .update(update_data)
            .eq("id", deliverable_id)
            .execute()
        )
        return result.data[0]

    def get_deliverables_for_task(self, task_id: str) -> list:
        result = (
            self.client.table("deliverables")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    def get_pending_review(self) -> list:
        result = (
            self.client.table("deliverables")
            .select("*, tasks(title, assigned_to)")
            .eq("status", "pending_review")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    # ─── MEETINGS ────────────────────────────────────────────────────────────

    def create_meeting(self, title: str, meeting_type: str,
                       participants: list, agenda: str = None) -> dict:
        data = {
            "title": title,
            "meeting_type": meeting_type,
            "participants": participants,
            "agenda": agenda,
            "status": "in_progress"
        }
        result = self.client.table("meetings").insert(data).execute()
        return result.data[0]

    def update_meeting(self, meeting_id: str, transcript: list,
                       decisions: list, action_items: list) -> dict:
        result = (
            self.client.table("meetings")
            .update({
                "transcript": transcript,
                "decisions": decisions,
                "action_items": action_items,
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            })
            .eq("id", meeting_id)
            .execute()
        )
        return result.data[0]

    # ─── AGENT MESSAGES ──────────────────────────────────────────────────────

    def log_agent_message(self, task_id: str, from_agent: str,
                          to_agent: str, message: str,
                          message_type: str = "task") -> dict:
        data = {
            "task_id": task_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "message_type": message_type
        }
        result = self.client.table("agent_messages").insert(data).execute()
        return result.data[0]

    # ─── STRATEGIC GOALS ─────────────────────────────────────────────────────

    def get_goals(self) -> list:
        """Return active strategic goals (stored as special chairman_instructions)."""
        try:
            import json as _json
            result = (
                self.client.table("chairman_instructions")
                .select("*")
                .eq("language", "strategic_goal")
                .eq("processed", False)
                .order("created_at")
                .execute()
            )
            goals = []
            for row in result.data:
                try:
                    data = _json.loads(row["instruction"])
                    data["id"] = row["id"]
                    data["created_at"] = row.get("created_at", "")
                    goals.append(data)
                except Exception:
                    pass
            return goals
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("get_goals: %s", e)
            return []

    def create_goal(self, title: str, description: str,
                    kpis: list = None, departments: list = None,
                    deadline: str = None) -> dict:
        import json as _json
        payload = {
            "title": title,
            "description": description,
            "kpis": kpis or [],
            "departments": departments or [],
            "deadline": deadline,
        }
        result = self.client.table("chairman_instructions").insert({
            "instruction": _json.dumps(payload, ensure_ascii=False),
            "language": "strategic_goal",
            "processed": False
        }).execute()
        return result.data[0]

    def archive_goal(self, goal_id: str) -> bool:
        self.client.table("chairman_instructions") \
            .update({"processed": True}) \
            .eq("id", goal_id) \
            .execute()
        return True

    # ─── CHAIRMAN INSTRUCTIONS ───────────────────────────────────────────────

    def save_instruction(self, instruction: str, language: str = "he") -> dict:
        data = {"instruction": instruction, "language": language}
        result = (
            self.client.table("chairman_instructions")
            .insert(data)
            .execute()
        )
        return result.data[0]

    def mark_instruction_processed(self, instruction_id: str,
                                    task_id: str) -> dict:
        result = (
            self.client.table("chairman_instructions")
            .update({"processed": True, "task_id": task_id})
            .eq("id", instruction_id)
            .execute()
        )
        return result.data[0]

    # ─── PUBLICATIONS ────────────────────────────────────────────────────────

    def schedule_publication(self, deliverable_id: str, task_id: str,
                              platform: str, content: str,
                              scheduled_at: str = None) -> dict:
        data = {
            "deliverable_id": deliverable_id,
            "task_id": task_id,
            "platform": platform,
            "content": content,
            "scheduled_at": scheduled_at,
            "status": "scheduled"
        }
        result = self.client.table("publications").insert(data).execute()
        return result.data[0]

    def mark_published(self, publication_id: str,
                       platform_post_id: str = None) -> dict:
        result = (
            self.client.table("publications")
            .update({
                "status": "published",
                "published_at": datetime.utcnow().isoformat(),
                "platform_post_id": platform_post_id
            })
            .eq("id", publication_id)
            .execute()
        )
        return result.data[0]

    # ─── BOARD MEMBERS ───────────────────────────────────────────────────────

    def get_board_members(self) -> list:
        try:
            result = (
                self.client.table("board_members")
                .select("*")
                .order("created_at")
                .execute()
            )
            return result.data
        except Exception:
            return []

    # ─── DEPARTMENTS ─────────────────────────────────────────────────────────

    def get_departments(self) -> list:
        try:
            result = (
                self.client.table("departments")
                .select("*")
                .order("code")
                .execute()
            )
            return result.data
        except Exception:
            return []

    # ─── EMPLOYEES ───────────────────────────────────────────────────────────

    def get_employees(self, department: str = None) -> list:
        try:
            query = self.client.table("employees").select("*")
            if department:
                query = query.eq("department_code", department)
            result = query.order("is_manager", desc=True).order("name").execute()
            return result.data
        except Exception:
            return []

    def create_employee(self, name: str, title_he: str, title_en: str,
                        department_code: str, is_manager: bool = False,
                        personality: str = "", expertise: str = "") -> dict:
        data = {
            "name": name, "title_he": title_he, "title_en": title_en,
            "department_code": department_code, "is_manager": is_manager,
            "is_ai": True, "personality": personality, "expertise": expertise,
        }
        result = self.client.table("employees").insert(data).execute()
        return result.data[0]

    def update_employee(self, employee_id: str, **fields) -> dict:
        allowed = {"name", "title_he", "title_en", "department_code",
                   "is_manager", "personality", "expertise"}
        update_data = {k: v for k, v in fields.items() if k in allowed}
        result = (
            self.client.table("employees")
            .update(update_data)
            .eq("id", employee_id)
            .execute()
        )
        return result.data[0]

    def delete_employee(self, employee_id: str) -> bool:
        self.client.table("employees").delete().eq("id", employee_id).execute()
        return True

    def get_employee(self, employee_id: str) -> dict:
        result = (
            self.client.table("employees")
            .select("*")
            .eq("id", employee_id)
            .single()
            .execute()
        )
        return result.data

    # ─── DISCUSSIONS ─────────────────────────────────────────────────────────

    def get_discussion(self, discussion_id: str) -> dict:
        result = (
            self.client.table("discussions")
            .select("*")
            .eq("id", discussion_id)
            .single()
            .execute()
        )
        return result.data

    def close_discussion(self, discussion_id: str) -> dict:
        result = (
            self.client.table("discussions")
            .update({"status": "closed"})
            .eq("id", discussion_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_discussions(self, limit: int = 50) -> list:
        try:
            result = (
                self.client.table("discussions")
                .select("*")
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception:
            return []

    def create_discussion(self, title: str, discussion_type: str = "team",
                          task_id: str = None, participants: list = None) -> dict:
        data = {
            "title": title,
            "discussion_type": discussion_type,
            "participants": participants or [],
            "messages": [],
            "status": "active"
        }
        if task_id:
            data["task_id"] = task_id
        result = self.client.table("discussions").insert(data).execute()
        return result.data[0]

    def add_discussion_message(self, discussion_id: str, sender: str,
                                message: str, role: str = "") -> dict:
        discussion = (
            self.client.table("discussions")
            .select("messages")
            .eq("id", discussion_id)
            .single()
            .execute()
        )
        messages = discussion.data.get("messages", []) or []
        messages.append({
            "sender": sender,
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        result = (
            self.client.table("discussions")
            .update({"messages": messages})
            .eq("id", discussion_id)
            .execute()
        )
        return result.data[0]

    # ─── ACTIVITIES ──────────────────────────────────────────────────────────

    def get_activities(self, limit: int = 50, department: str = None) -> list:
        try:
            query = (
                self.client.table("activities")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
            )
            if department:
                query = query.eq("department", department)
            result = query.execute()
            return result.data
        except Exception:
            return []

    def log_activity(self, activity_type: str, title: str,
                     description: str = None, department: str = None,
                     employee_name: str = None, task_id: str = None,
                     deliverable_id: str = None, meeting_id: str = None,
                     metadata: dict = None) -> dict:
        try:
            data = {
                "activity_type": activity_type,
                "title": title,
                "description": description,
                "department": department,
                "employee_name": employee_name,
                "metadata": metadata or {}
            }
            if task_id:
                data["task_id"] = task_id
            if deliverable_id:
                data["deliverable_id"] = deliverable_id
            if meeting_id:
                data["meeting_id"] = meeting_id
            result = self.client.table("activities").insert(data).execute()
            return result.data[0]
        except Exception as e:
            return {}

    def get_meetings(self, limit: int = 20) -> list:
        try:
            result = (
                self.client.table("meetings")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception:
            return []

    def get_all_deliverables(self, status: str = None, limit: int = 50) -> list:
        try:
            query = (
                self.client.table("deliverables")
                .select("*, tasks(title, assigned_to, priority)")
                .order("created_at", desc=True)
                .limit(limit)
            )
            if status:
                query = query.eq("status", status)
            result = query.execute()
            return result.data
        except Exception:
            return []


db = DatabaseClient()
