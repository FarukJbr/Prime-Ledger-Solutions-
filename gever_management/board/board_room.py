"""
Board of Directors room.
Chairman + 3 Directors vote on strategic decisions.
"""

import anthropic
from config import settings
import json
import re

DIRECTORS = {
    "director_1": {
        "name": "דירקטור - מומחה פיננסי",
        "expertise": "Financial strategy, investments, risk management, M&A"
    },
    "director_2": {
        "name": "דירקטור - מומחה שיווק",
        "expertise": "Brand strategy, market expansion, digital transformation, growth"
    },
    "director_3": {
        "name": "דירקטור - מומחה משפטי/אסטרטגי",
        "expertise": "Legal governance, strategic partnerships, regulatory affairs, corporate law"
    },
}


class BoardRoom:
    """Simulates board-level discussions and voting on strategic matters."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _director_opinion(self, director_id: str, director_info: dict,
                           topic: str, context: str) -> str:
        prompt = f"""
You are {director_info['name']} on the Board of Directors at {settings.company_name}.
Your expertise: {director_info['expertise']}

Strategic Topic for Board Vote: {topic}
Context: {context}

Provide your board-level perspective:
1. Your position (FOR / AGAINST / ABSTAIN)
2. Key reasoning (2-3 points)
3. Conditions or recommendations if you vote FOR
4. Risks if you vote AGAINST

Be concise and decisive as a board member.
"""
        response = self._client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def board_vote(self, topic: str, context: str = "") -> dict:
        """
        Conduct a board vote on a strategic topic.
        Returns voting results and board decision.
        """
        votes = {}
        opinions = {}

        for director_id, director_info in DIRECTORS.items():
            opinion = self._director_opinion(director_id, director_info, topic, context)
            opinions[director_id] = {
                "name": director_info["name"],
                "opinion": opinion
            }

            if "FOR" in opinion.upper() or "בעד" in opinion:
                votes[director_id] = "for"
            elif "AGAINST" in opinion.upper() or "נגד" in opinion:
                votes[director_id] = "against"
            else:
                votes[director_id] = "abstain"

        vote_counts = {
            "for": sum(1 for v in votes.values() if v == "for"),
            "against": sum(1 for v in votes.values() if v == "against"),
            "abstain": sum(1 for v in votes.values() if v == "abstain"),
        }

        board_decision = "approved" if vote_counts["for"] > vote_counts["against"] else "rejected"

        return {
            "topic": topic,
            "opinions": opinions,
            "vote_counts": vote_counts,
            "board_decision": board_decision,
            "note": "Chairman (יו\"ר) has final veto power"
        }
