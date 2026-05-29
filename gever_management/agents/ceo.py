from .base_agent import BaseAgent
from database import db
from config import settings
import json
import re


class CEOAgent(BaseAgent):
    """
    מנכ"ל - CEO / Orchestrator
    Receives chairman instructions, analyzes them, and delegates to departments.
    """

    department = "ceo"
    role_he = "מנכ\"ל"
    role_en = "CEO"
    employee_name = "דוד אזולאי"
    personality = "ישיר, מקצועי, לא מבזבז מילים. מקבל החלטות מהיר. מצפה לתוצאות מהצוות ולא מקבל תירוצים."

    @property
    def responsibilities(self) -> str:
        return """
- Receive and analyze instructions from the Chairman (יו"ר)
- Break down complex tasks into department-specific subtasks
- Delegate work to the right departments
- Oversee all company operations
- Ensure company goals are met
- Report back to the Chairman with consolidated results
- Facilitate management meetings and board discussions
"""

    DELEGATION_PROMPT = """
Analyze the following chairman instruction and create a delegation plan.

Chairman Instruction: {instruction}

Available Departments:
- cfo: Financial analysis, budgets, cost planning
- marketing: Marketing campaigns, social media content, brand strategy
- sales: Sales strategy, client acquisition, proposals
- legal: Legal review, compliance, contracts
- cto: Technical solutions, code, systems, automation
- content: Content creation, design briefs, multimedia
- pr: Public relations, press releases, customer service
- compliance: Regulatory compliance, risk assessment

Respond in JSON format ONLY:
{{
  "task_title": "Short task title",
  "task_description": "Full description of what needs to be done",
  "departments_needed": ["dept1", "dept2"],
  "department_tasks": {{
    "dept1": "Specific instruction for this department",
    "dept2": "Specific instruction for this department"
  }},
  "priority": "normal|high|urgent",
  "language": "he|en|tr",
  "requires_meeting": false,
  "ceo_notes": "Any strategic notes"
}}
"""

    def analyze_and_delegate(self, instruction: str,
                               instruction_id: str) -> dict:
        prompt = self.DELEGATION_PROMPT.format(instruction=instruction)

        raw = self.think(prompt)

        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            plan = json.loads(json_match.group())
        else:
            plan = {
                "task_title": "Task from Chairman",
                "task_description": instruction,
                "departments_needed": ["marketing"],
                "department_tasks": {"marketing": instruction},
                "priority": "normal",
                "language": "he",
                "requires_meeting": False,
                "ceo_notes": ""
            }

        task = db.create_task(
            title=plan["task_title"],
            description=plan["task_description"],
            assigned_to=",".join(plan["departments_needed"]),
            priority=plan.get("priority", "normal"),
            language=plan.get("language", "he"),
            metadata={"delegation_plan": plan, "instruction_id": instruction_id}
        )

        db.mark_instruction_processed(instruction_id, task["id"])

        db.log_agent_message(
            task_id=task["id"],
            from_agent="ceo",
            to_agent="system",
            message=f"Delegation plan created for: {plan['task_title']}",
            message_type="decision"
        )

        return {"task": task, "plan": plan}

    def compile_final_report(self, task_id: str) -> str:
        task = db.get_task(task_id)
        deliverables = db.get_deliverables_for_task(task_id)

        dept_results = "\n\n".join([
            f"### {d['department'].upper()} ({d['agent_role']})\n{d['content']}"
            for d in deliverables
        ])

        prompt = f"""
You are preparing the final consolidated report for the Chairman.

Original Task: {task['title']}
Description: {task['description']}

Department Submissions:
{dept_results}

Create a professional executive summary that:
1. Summarizes all department contributions
2. Highlights key decisions and outputs
3. Lists items requiring chairman approval
4. Suggests next steps

Be concise and professional.
"""
        return self.think(prompt)
