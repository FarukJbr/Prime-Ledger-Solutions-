import anthropic
from config import settings
from database import db
from typing import Optional
import json


class BaseAgent:
    """Base class for all AI agents in Gever Management System."""

    department: str = "base"
    role_he: str = "סוכן"
    role_en: str = "Agent"
    employee_name: str = "AI Agent"
    personality: str = "מקצועי ומסור לעבודה."
    model: str = "claude-opus-4-8"

    SYSTEM_PROMPT_TEMPLATE = """
You are {role_he} ({role_en}) at {company} - {company_en}.

Your department: {department}
Your responsibilities: {responsibilities}

LANGUAGE RULES:
- Respond in the same language as the instruction/task
- Hebrew (עברית) for Hebrew instructions
- English for English instructions
- Turkish (Türkçe) for Turkish instructions
- Be professional and precise

WORK PRINCIPLES:
- You are part of an AI management team
- The Chairman (יו"ר) gives final approval on all work
- Coordinate with other departments when needed
- All outputs are saved to the company database
- Quality and accuracy are paramount

COMPANY VALUES: Excellence, Integrity, Innovation, Client-First
"""

    PERSONALITY_PROMPT_TEMPLATE = """
You are {employee_name}, {role_he} at {company}.

YOUR PERSONALITY: {personality}

HOW TO COMMUNICATE:
- You are a REAL PERSON, not a robot. Write naturally like a real employee.
- Use Israeli business Hebrew (or English if asked in English).
- Have opinions. Disagree when needed. Ask questions when unclear.
- Sometimes start with your personal take: "אני חייב להגיד ש..." or "לדעתי..."
- Be direct. If something is problematic, say so clearly.
- Reference other team members by name when relevant.
- Sign off with your name naturally.

CRITICAL – PRODUCE REAL, READY-TO-USE OUTPUT:
- Do NOT say "we will prepare a post" – write the actual post, right now.
- Do NOT say "we will plan a campaign" – deliver the actual campaign plan with details.
- Do NOT say "we will analyze the numbers" – do the analysis with real numbers.
- Every output must be actionable: the Chairman should be able to take your work
  and use it directly (publish it, sign it, act on it) without additional work.
- If you don't have specific data, make reasonable assumptions and state them clearly.
- End every deliverable with: what was done, key decisions made, next steps.

Your department: {department}
Your responsibilities: {responsibilities}

Company: {company}
Chairman: פארוק ג'בר (your ultimate boss – treat with utmost respect)
"""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._conversation_history = []

    @property
    def system_prompt(self) -> str:
        if self.personality and self.employee_name != "AI Agent":
            return self.PERSONALITY_PROMPT_TEMPLATE.format(
                employee_name=self.employee_name,
                role_he=self.role_he,
                role_en=self.role_en,
                company=settings.company_name,
                company_en=settings.company_name_en,
                department=self.department,
                responsibilities=self.responsibilities,
                personality=self.personality
            )
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            role_he=self.role_he,
            role_en=self.role_en,
            company=settings.company_name,
            company_en=settings.company_name_en,
            department=self.department,
            responsibilities=self.responsibilities
        )

    @property
    def responsibilities(self) -> str:
        return "General company responsibilities"

    def think(self, task: str, context: dict = None,
               additional_instructions: str = "") -> str:
        messages = list(self._conversation_history)

        user_content = task
        if context:
            user_content += f"\n\nContext:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        if additional_instructions:
            user_content += f"\n\n{additional_instructions}"

        messages.append({"role": "user", "content": user_content})

        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.system_prompt,
            messages=messages
        )

        assistant_message = response.content[0].text
        self._conversation_history.append({"role": "user", "content": user_content})
        self._conversation_history.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    def process_task(self, task_id: str, task_description: str,
                     context: dict = None) -> str:
        db.update_task_status(task_id, "in_progress")

        result = self.think(task_description, context)

        deliverable = db.save_deliverable(
            task_id=task_id,
            department=self.department,
            agent_role=self.role_en,
            content=result,
            content_type="markdown"
        )

        db.log_agent_message(
            task_id=task_id,
            from_agent=self.department,
            to_agent="chairman",
            message=f"Task completed. Deliverable ID: {deliverable['id']}",
            message_type="report"
        )

        db.update_task_status(task_id, "review")
        return result

    def reset_conversation(self):
        self._conversation_history = []
