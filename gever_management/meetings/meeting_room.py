import anthropic
from config import settings
from database import db
from agents import DEPARTMENT_AGENTS, CEOAgent
import json
import re


BOARD_MEMBERS = {
    "chairman": {"name_he": "יו\"ר", "name_en": "Chairman"},
    "ceo": {"name_he": "מנכ\"ל", "name_en": "CEO"},
    "cfo": {"name_he": "מנהל כספים", "name_en": "CFO"},
    "cto": {"name_he": "מנהל טכנולוגיה", "name_en": "CTO"},
    "legal": {"name_he": "יועץ משפטי", "name_en": "Legal Advisor"},
    "compliance": {"name_he": "קצין ציות", "name_en": "CCO"},
    "marketing": {"name_he": "מנהל שיווק", "name_en": "Marketing Manager"},
    "sales": {"name_he": "מנהל מכירות", "name_en": "Sales Manager"},
    "pr": {"name_he": "מנהל יח\"צ", "name_en": "PR Manager"},
    "content": {"name_he": "מנהל תוכן", "name_en": "Content Manager"},
}


class MeetingRoom:
    """
    Simulates management meetings where AI agents discuss topics,
    provide their department perspective, and reach decisions.
    """

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._agents = {}

    def _get_agent_opinion(self, department: str, topic: str,
                            context: str, previous_discussion: str) -> str:
        agent_class = DEPARTMENT_AGENTS.get(department)
        if not agent_class:
            return ""

        agent = agent_class()
        prompt = f"""
You are in a management meeting at {settings.company_name}.

Meeting Topic: {topic}
Context: {context}

Previous discussion:
{previous_discussion if previous_discussion else "You are the first to speak."}

Share your department's perspective on this topic:
- Key considerations from your department's view
- Your recommendation or position
- Any risks or concerns
- What resources/support you need

Be concise (3-5 sentences), professional, and direct.
"""
        return agent.think(prompt)

    def hold_meeting(self, title: str, topic: str,
                     participants: list, meeting_type: str = "management",
                     context: str = "") -> dict:
        """
        Runs a full AI management meeting with all participants.
        Returns transcript, decisions, and action items.
        """
        meeting = db.create_meeting(
            title=title,
            meeting_type=meeting_type,
            participants=participants,
            agenda=topic
        )
        meeting_id = meeting["id"]

        transcript = []
        discussion_so_far = ""

        for dept in participants:
            if dept == "chairman":
                continue

            member = BOARD_MEMBERS.get(dept, {})
            role_name = member.get("name_he", dept)

            opinion = self._get_agent_opinion(
                dept, topic, context, discussion_so_far
            )

            entry = {
                "speaker": dept,
                "role": role_name,
                "message": opinion
            }
            transcript.append(entry)
            discussion_so_far += f"\n{role_name}: {opinion}\n"

        decisions, action_items = self._synthesize_decisions(
            topic, discussion_so_far, participants
        )

        db.update_meeting(
            meeting_id=meeting_id,
            transcript=transcript,
            decisions=decisions,
            action_items=action_items
        )

        return {
            "meeting_id": meeting_id,
            "title": title,
            "transcript": transcript,
            "decisions": decisions,
            "action_items": action_items
        }

    def _synthesize_decisions(self, topic: str, discussion: str,
                               participants: list) -> tuple:
        ceo = CEOAgent()
        prompt = f"""
You facilitated a management meeting about: {topic}

Full discussion:
{discussion}

Now synthesize:
1. Key decisions reached (list each decision clearly)
2. Action items with responsible department (list each item)

Respond in JSON:
{{
  "decisions": ["decision 1", "decision 2"],
  "action_items": [
    {{"item": "description", "responsible": "department", "deadline": "timeframe"}},
  ]
}}
"""
        raw = ceo.think(prompt)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("decisions", []), result.get("action_items", [])
        return [], []

    def quick_consult(self, question: str, departments: list) -> dict:
        """Fast consultation - get quick opinions without a full meeting."""
        responses = {}
        for dept in departments:
            agent_class = DEPARTMENT_AGENTS.get(dept)
            if agent_class:
                agent = agent_class()
                responses[dept] = agent.think(
                    f"Quick consultation needed: {question}\n"
                    f"Give a brief 2-3 sentence expert opinion from your department."
                )
        return responses
