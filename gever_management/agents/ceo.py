from .base_agent import BaseAgent
from database import db
from config import settings
import json
import re


class CEOAgent(BaseAgent):
    """
    דוד אזולאי – מנכ"ל
    מקבל הוראות מהיו"ר, מנתח, מאציל למחלקות, ומסכם עם פרספקטיבות.
    """

    department = "ceo"
    role_he = 'מנכ"ל'
    role_en = "CEO"
    employee_name = "דוד אזולאי"
    personality = (
        "ישיר, מקצועי, לא מבזבז מילים. מקבל החלטות מהיר. "
        "מצפה לתוצאות מהצוות ולא מקבל תירוצים."
    )

    @property
    def responsibilities(self) -> str:
        return """
- Receive and analyze instructions from the Chairman (יו"ר)
- Break down complex tasks into department-specific subtasks
- Delegate work to the right departments
- Oversee all company operations
- Ensure company goals are met
- Compile multi-perspective synthesis reports for the Chairman
- Facilitate management meetings and board discussions
"""

    DELEGATION_PROMPT = """
Analyze the following chairman instruction and create a delegation plan.

Chairman Instruction: {instruction}

Available Departments:
- cfo: Financial analysis, budgets, cost planning, cash flow
- marketing: Marketing campaigns, social media content, brand strategy
- sales: Sales strategy, client acquisition, proposals, scripts
- legal: Legal review, compliance, contracts, risk
- cto: Technical solutions, code, systems, automation
- content: Content creation, design briefs, Canva visuals, multimedia
- pr: Public relations, press releases, customer service, crisis
- compliance: Regulatory compliance, risk assessment, checklists

IMPORTANT: Select only the departments that are ACTUALLY needed for this task.
Do not involve all departments unless genuinely necessary.

Respond in JSON format ONLY:
{{
  "task_title": "Short task title in Hebrew",
  "task_description": "Full description of what needs to be done",
  "departments_needed": ["dept1", "dept2"],
  "department_tasks": {{
    "dept1": "Specific instruction in Hebrew for this department",
    "dept2": "Specific instruction in Hebrew for this department"
  }},
  "priority": "normal|high|urgent",
  "language": "he|en|tr",
  "ceo_notes": "Strategic notes"
}}
"""

    PERSPECTIVE_PROMPT = """
You are {name}, {role} at {company}.

The Chairman asked: "{original_instruction}"

Here is what all departments produced:
{all_results}

Give YOUR professional perspective on this work:
1. What do you think is the strongest recommendation?
2. What concerns you or what's missing from your professional angle?
3. What would you prioritize if you were the Chairman?
4. One specific action you recommend the Chairman take today.

Be direct, opinionated, and speak as {name}. Sign your name at the end.
"""

    SYNTHESIS_PROMPT = """
You are דוד אזולאי, CEO. You've reviewed all department outputs and their individual perspectives.

Original Chairman Instruction: {instruction}
Task: {task_title}

Department Outputs Summary:
{dept_summaries}

Individual Perspectives from Each Manager:
{perspectives}

Create a FINAL SYNTHESIS REPORT for the Chairman:

## סיכום מנכ"ל – {task_title}

### 1. מה הושלם
[Concise summary of what each department produced]

### 2. נקודות הסכמה
[Where all departments align]

### 3. מחלוקות ומתחים
[Where departments disagree – present both sides]

### 4. המלצת המנכ"ל
[YOUR clear recommendation as CEO]

### 5. החלטות שהיו"ר צריך לקבל
[Numbered list of specific decisions needed from the Chairman]

### 6. צעדים הבאים
[Concrete next steps with owner and timeline]

Be direct and opinionated. The Chairman trusts your judgment.
Sign: דוד אזולאי, מנכ"ל
"""

    def analyze_and_delegate(self, instruction: str,
                               instruction_id: str) -> dict:
        prompt = self.DELEGATION_PROMPT.format(instruction=instruction)
        raw = self.think(prompt)

        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            try:
                plan = json.loads(json_match.group())
            except json.JSONDecodeError:
                plan = self._default_plan(instruction)
        else:
            plan = self._default_plan(instruction)

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
            task_id=task["id"], from_agent="ceo", to_agent="system",
            message=f"Delegation created: {plan['task_title']}",
            message_type="decision"
        )

        return {"task": task, "plan": plan}

    def compile_final_report(self, task_id: str) -> str:
        task = db.get_task(task_id)
        deliverables = db.get_deliverables_for_task(task_id)

        # Filter out previous CEO summaries (avoid recursion)
        dept_deliverables = [d for d in deliverables if d["department"] != "ceo"]

        if not dept_deliverables:
            return f"משימה: {task['title']}\n\nאין תוצרים ממחלקות עדיין."

        # Build combined summary for perspective requests
        dept_summaries = "\n\n".join([
            f"### {d['department'].upper()} ({d['agent_role']})\n{d['content'][:800]}..."
            for d in dept_deliverables
        ])

        # Collect perspective from each department manager
        perspectives = self._collect_perspectives(
            task["description"], task["title"], dept_deliverables
        )

        perspectives_text = "\n\n---\n\n".join([
            f"**{name}** ({role}):\n{perspective}"
            for name, role, perspective in perspectives
        ])

        # Build synthesis
        synthesis_prompt = self.SYNTHESIS_PROMPT.format(
            instruction=task["description"],
            task_title=task["title"],
            dept_summaries=dept_summaries,
            perspectives=perspectives_text
        )

        return self.think(synthesis_prompt)

    def _collect_perspectives(self, instruction: str, task_title: str,
                               deliverables: list) -> list:
        """Ask each department manager for their professional perspective."""
        from . import DEPARTMENT_AGENTS
        perspectives = []

        all_results = "\n\n".join([
            f"**{d['department']}**: {d['content'][:500]}..."
            for d in deliverables
        ])

        for d in deliverables:
            dept = d["department"]
            agent_class = DEPARTMENT_AGENTS.get(dept)
            if not agent_class:
                continue
            try:
                agent = agent_class()
                prompt = self.PERSPECTIVE_PROMPT.format(
                    name=agent.employee_name,
                    role=agent.role_he,
                    company=settings.company_name,
                    original_instruction=instruction,
                    all_results=all_results
                )
                perspective = agent.think(prompt)
                perspectives.append((agent.employee_name, agent.role_he, perspective))
            except Exception:
                pass

        return perspectives

    def _default_plan(self, instruction: str) -> dict:
        return {
            "task_title": "משימה מהיו\"ר",
            "task_description": instruction,
            "departments_needed": ["marketing"],
            "department_tasks": {"marketing": instruction},
            "priority": "normal",
            "language": "he",
            "ceo_notes": ""
        }
