import asyncio
from agents import CEOAgent, DEPARTMENT_AGENTS
from database import db
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def _email_safe(fn, *args, **kwargs):
    """Fire email notification without crashing if email not configured."""
    try:
        from services import notify_task_completed, notify_deliverable_ready, notify_published
        fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Email notification skipped: %s", e)


class TaskManager:
    """Central task orchestration engine."""

    def __init__(self):
        self.ceo = CEOAgent()
        self._agents = {}

    def _get_agent(self, department: str):
        if department not in self._agents:
            agent_class = DEPARTMENT_AGENTS.get(department)
            if agent_class:
                self._agents[department] = agent_class()
        return self._agents.get(department)

    def process_chairman_instruction(self, instruction: str,
                                      instruction_id: str,
                                      on_progress=None) -> dict:
        if on_progress:
            on_progress("🧠 CEO מנתח את ההוראה...")

        delegation = self.ceo.analyze_and_delegate(instruction, instruction_id)
        task = delegation["task"]
        plan = delegation["plan"]
        task_id = task["id"]

        if on_progress:
            depts = ", ".join(plan["departments_needed"])
            on_progress(f"📋 מעביר ל: {depts}")

        db.log_activity(
            activity_type="task_created",
            title=f"משימה חדשה: {plan['task_title']}",
            description=plan.get("task_description", ""),
            department="ceo",
            employee_name="דוד אזולאי",
            task_id=task_id,
            metadata={"departments": plan["departments_needed"]}
        )

        results = {}
        for department in plan["departments_needed"]:
            agent = self._get_agent(department)
            if not agent:
                logger.warning("No agent for department: %s", department)
                continue

            dept_task = plan["department_tasks"].get(department, instruction)

            if on_progress:
                on_progress(f"⚙️ {department.upper()} עובד...")

            try:
                result = agent.process_task(task_id, dept_task)
                results[department] = result
                db.log_agent_message(
                    task_id=task_id,
                    from_agent=department,
                    to_agent="ceo",
                    message="Task completed successfully",
                    message_type="report"
                )
                employee_name = getattr(agent, "employee_name", department)
                db.log_activity(
                    activity_type="deliverable_submitted",
                    title=f"תוצר הוגש: {plan['task_title']}",
                    description=f"מחלקת {department} השלימה את העבודה",
                    department=department,
                    employee_name=employee_name,
                    task_id=task_id
                )
                # Email per-department notification
                _email_safe(
                    lambda: __import__('services').notify_deliverable_ready(
                        plan['task_title'], department, employee_name
                    )
                )
            except Exception as e:
                logger.error("Error in %s: %s", department, e)
                results[department] = f"Error: {str(e)}"

        if on_progress:
            on_progress("📊 CEO מכין דוח סופי...")

        final_report = self.ceo.compile_final_report(task_id)

        db.save_deliverable(
            task_id=task_id,
            department="ceo",
            agent_role="CEO Summary",
            content=final_report,
            content_type="markdown"
        )

        db.update_task_status(task_id, "review")

        db.log_activity(
            activity_type="task_completed",
            title=f"משימה הושלמה: {plan['task_title']}",
            description='כל המחלקות סיימו. ממתין לאישור יו"ר.',
            department="ceo",
            employee_name="דוד אזולאי",
            task_id=task_id,
            metadata={"departments": plan["departments_needed"]}
        )

        # Final summary email
        try:
            from services import notify_task_completed
            notify_task_completed(plan['task_title'], plan["departments_needed"], task_id)
        except Exception as e:
            logger.debug("Summary email skipped: %s", e)

        return {
            "task_id": task_id,
            "task_title": task["title"],
            "departments_involved": plan["departments_needed"],
            "final_report": final_report,
            "department_results": results
        }

    def approve_deliverable(self, deliverable_id: str,
                             feedback: str = None) -> dict:
        result = db.update_deliverable_status(deliverable_id, "approved", feedback)
        db.log_activity(
            activity_type="deliverable_approved",
            title='תוצר אושר על ידי יו"ר',
            description=feedback or 'היו"ר אישר את התוצר',
            employee_name="פארוק ג'בר",
            deliverable_id=deliverable_id,
            metadata={"feedback": feedback}
        )
        return result

    def publish_deliverable(self, deliverable_id: str, platform: str,
                             task_title: str = "") -> dict:
        """Approve + publish to social media (or return download package)."""
        from services.publish_service import publish_content

        deliverable = db.client.table("deliverables") \
            .select("*, tasks(title)") \
            .eq("id", deliverable_id).single().execute().data

        content = deliverable.get("content", "")
        title = task_title or (deliverable.get("tasks") or {}).get("title", "")

        publish_results = publish_content(content, platform, title)

        # Mark as published if any platform succeeded
        any_published = any(v.get("success") for v in publish_results.values())
        if any_published:
            db.update_task_status(deliverable.get("task_id", ""), "published")
            db.log_activity(
                activity_type="published",
                title=f"פורסם ב-{platform}",
                description=title,
                employee_name="פארוק ג'בר",
                deliverable_id=deliverable_id,
            )
            try:
                from services import notify_published
                for p, r in publish_results.items():
                    if r.get("success"):
                        notify_published(title, p, r.get("post_id", ""))
            except Exception:
                pass
        else:
            # Content ready for manual publishing
            try:
                from services.email_service import notify_publish_ready
                notify_publish_ready(title, platform)
            except Exception:
                pass

        return {
            "published": any_published,
            "results": publish_results,
            "task_title": title,
        }

    def reject_deliverable(self, deliverable_id: str, feedback: str) -> dict:
        result = db.update_deliverable_status(deliverable_id, "rejected", feedback)
        db.log_activity(
            activity_type="deliverable_submitted",
            title='תוצר נדחה על ידי יו"ר',
            description=feedback,
            employee_name="פארוק ג'בר",
            deliverable_id=deliverable_id,
            metadata={"feedback": feedback, "action": "rejected"}
        )
        return result

    def execute_strategic_goals(self) -> dict:
        """Run all departments autonomously based on the board's active strategic goals."""
        goals = db.get_goals()
        if not goals:
            return {"error": "אין יעדים אסטרטגיים פעילים. הוסף יעדים בלשונית האסטרטגיה."}

        goals_text = ""
        for g in goals:
            kpis = ", ".join(g.get("kpis") or [])
            deadline = g.get("deadline") or "ללא תאריך יעד"
            goals_text += (
                f"■ {g.get('title','')}\n"
                f"  תיאור: {g.get('description','')}\n"
                f"  KPIs: {kpis or '—'}\n"
                f"  דד-ליין: {deadline}\n\n"
            )

        instruction = (
            f"דירקטוריון החברה קבע את היעדים האסטרטגיים הבאים שכל הצוות צריך לעבוד להשגתם:\n\n"
            f"{goals_text}"
            f"כל מחלקה תייצר עכשיו תוצרים אמיתיים ומוכנים לביצוע. "
            f"תוצרים נדרשים: תוכן מוכן לפרסום, סקריפטים מכירה, תוכניות עם תאריכים ומספרים, "
            f"אימיילים, קמפיינים, הצעות מחיר — הכל ממש מוכן לשימוש מיידי. "
            f"כל מחלקה: מה תעשה השבוע, מה תעשה בחודש, ובאילו מדדים תמדוד הצלחה."
        )

        saved = db.save_instruction(instruction, "he")
        result = self.process_chairman_instruction(instruction, saved["id"])
        return {"success": True, **result}

    def get_pending_reviews(self) -> list:
        return db.get_pending_review()

    def get_task_summary(self, task_id: str) -> dict:
        task = db.get_task(task_id)
        deliverables = db.get_deliverables_for_task(task_id)
        return {"task": task, "deliverables": deliverables}
