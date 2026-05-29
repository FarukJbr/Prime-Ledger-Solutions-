import asyncio
from agents import CEOAgent, DEPARTMENT_AGENTS
from database import db
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Central task orchestration engine.
    Receives chairman instructions → delegates → collects results.
    """

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
        """
        Main entry point: takes a chairman instruction and runs the full workflow.
        Returns task summary when all departments complete.
        """
        if on_progress:
            on_progress("🧠 CEO analyzing instruction...")

        delegation = self.ceo.analyze_and_delegate(instruction, instruction_id)
        task = delegation["task"]
        plan = delegation["plan"]
        task_id = task["id"]

        if on_progress:
            depts = ", ".join(plan["departments_needed"])
            on_progress(f"📋 Delegating to: {depts}")

        results = {}
        for department in plan["departments_needed"]:
            agent = self._get_agent(department)
            if not agent:
                logger.warning(f"No agent found for department: {department}")
                continue

            dept_task = plan["department_tasks"].get(department, instruction)

            if on_progress:
                on_progress(f"⚙️ {department.upper()} working...")

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
            except Exception as e:
                logger.error(f"Error in {department}: {e}")
                results[department] = f"Error: {str(e)}"

        if on_progress:
            on_progress("📊 CEO compiling final report...")

        final_report = self.ceo.compile_final_report(task_id)

        db.save_deliverable(
            task_id=task_id,
            department="ceo",
            agent_role="CEO Summary",
            content=final_report,
            content_type="markdown"
        )

        db.update_task_status(task_id, "review")

        return {
            "task_id": task_id,
            "task_title": task["title"],
            "departments_involved": plan["departments_needed"],
            "final_report": final_report,
            "department_results": results
        }

    def approve_deliverable(self, deliverable_id: str,
                             feedback: str = None) -> dict:
        return db.update_deliverable_status(
            deliverable_id, "approved", feedback
        )

    def reject_deliverable(self, deliverable_id: str,
                            feedback: str) -> dict:
        return db.update_deliverable_status(
            deliverable_id, "rejected", feedback
        )

    def request_revision(self, deliverable_id: str,
                          feedback: str) -> str:
        db.update_deliverable_status(
            deliverable_id, "revision_requested", feedback
        )
        deliverable = (
            db.get_deliverables_for_task(
                db._client.table("deliverables")
                .select("task_id")
                .eq("id", deliverable_id)
                .single()
                .execute()
                .data["task_id"]
            )
        )
        return "Revision requested"

    def get_pending_reviews(self) -> list:
        return db.get_pending_review()

    def get_task_summary(self, task_id: str) -> dict:
        task = db.get_task(task_id)
        deliverables = db.get_deliverables_for_task(task_id)
        return {"task": task, "deliverables": deliverables}
