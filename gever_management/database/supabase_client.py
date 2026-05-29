from supabase import create_client, Client
from config import settings
import uuid
from datetime import datetime


class DatabaseClient:
    def __init__(self):
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

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
        result = self._client.table("tasks").insert(data).execute()
        return result.data[0]

    def update_task_status(self, task_id: str, status: str) -> dict:
        result = (
            self._client.table("tasks")
            .update({"status": status})
            .eq("id", task_id)
            .execute()
        )
        return result.data[0]

    def get_task(self, task_id: str) -> dict:
        result = (
            self._client.table("tasks")
            .select("*")
            .eq("id", task_id)
            .single()
            .execute()
        )
        return result.data

    def get_tasks_by_status(self, status: str) -> list:
        result = (
            self._client.table("tasks")
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
        result = self._client.table("deliverables").insert(data).execute()
        return result.data[0]

    def update_deliverable_status(self, deliverable_id: str, status: str,
                                  feedback: str = None) -> dict:
        update_data = {"status": status}
        if feedback:
            update_data["chairman_feedback"] = feedback
        result = (
            self._client.table("deliverables")
            .update(update_data)
            .eq("id", deliverable_id)
            .execute()
        )
        return result.data[0]

    def get_deliverables_for_task(self, task_id: str) -> list:
        result = (
            self._client.table("deliverables")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    def get_pending_review(self) -> list:
        result = (
            self._client.table("deliverables")
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
        result = self._client.table("meetings").insert(data).execute()
        return result.data[0]

    def update_meeting(self, meeting_id: str, transcript: list,
                       decisions: list, action_items: list) -> dict:
        result = (
            self._client.table("meetings")
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
        result = self._client.table("agent_messages").insert(data).execute()
        return result.data[0]

    # ─── CHAIRMAN INSTRUCTIONS ───────────────────────────────────────────────

    def save_instruction(self, instruction: str, language: str = "he") -> dict:
        data = {"instruction": instruction, "language": language}
        result = (
            self._client.table("chairman_instructions")
            .insert(data)
            .execute()
        )
        return result.data[0]

    def mark_instruction_processed(self, instruction_id: str,
                                    task_id: str) -> dict:
        result = (
            self._client.table("chairman_instructions")
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
        result = self._client.table("publications").insert(data).execute()
        return result.data[0]

    def mark_published(self, publication_id: str,
                       platform_post_id: str = None) -> dict:
        result = (
            self._client.table("publications")
            .update({
                "status": "published",
                "published_at": datetime.utcnow().isoformat(),
                "platform_post_id": platform_post_id
            })
            .eq("id", publication_id)
            .execute()
        )
        return result.data[0]


db = DatabaseClient()
