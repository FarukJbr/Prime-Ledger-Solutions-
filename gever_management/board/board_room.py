"""
Board of Directors room.
Chairman + 3 Directors vote on strategic decisions.
Each director is powered by a different AI model.
"""

import anthropic
import openai
import google.generativeai as genai
from config import settings

DIRECTORS = {
    "claude": {
        "name": "דירקטור קלוד - מומחה אסטרטגי",
        "model": "claude",
        "expertise": "Legal governance, strategic partnerships, regulatory affairs, corporate law",
        "ai_label": "Claude (Anthropic)",
    },
    "gpt": {
        "name": "דירקטור GPT - מומחה פיננסי",
        "model": "gpt",
        "expertise": "Financial strategy, investments, risk management, M&A",
        "ai_label": "GPT-4o (OpenAI)",
    },
    "gemini": {
        "name": "דירקטור ג'מיני - מומחה שיווק",
        "model": "gemini",
        "expertise": "Brand strategy, market expansion, digital transformation, growth",
        "ai_label": "Gemini (Google)",
    },
}


def _build_prompt(director_info: dict, topic: str, context: str) -> str:
    return f"""You are {director_info['name']} on the Board of Directors at {settings.company_name}.
Your expertise: {director_info['expertise']}

Strategic Topic for Board Vote: {topic}
Context: {context}

Provide your board-level perspective in Hebrew:
1. Your position (בעד / נגד / נמנע)
2. Key reasoning (2-3 points)
3. Conditions or recommendations
4. Main risks

Be concise and decisive as a board member. Respond in Hebrew."""


def _ask_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def _ask_gpt(prompt: str) -> str:
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def _ask_gemini(prompt: str) -> str:
    genai.configure(api_key=settings.google_gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text


def _get_director_opinion(director_info: dict, topic: str, context: str) -> str:
    prompt = _build_prompt(director_info, topic, context)
    model = director_info["model"]
    if model == "claude":
        return _ask_claude(prompt)
    elif model == "gpt":
        return _ask_gpt(prompt)
    elif model == "gemini":
        return _ask_gemini(prompt)
    return ""


class BoardRoom:
    """Conducts board-level discussions and voting on strategic matters."""

    def board_vote(self, topic: str, context: str = "") -> dict:
        votes = {}
        opinions = {}

        for director_id, director_info in DIRECTORS.items():
            try:
                opinion = _get_director_opinion(director_info, topic, context)
            except Exception as e:
                opinion = f"שגיאה בקבלת דעת הדירקטור: {e}"

            opinions[director_id] = {
                "name": director_info["name"],
                "ai_label": director_info["ai_label"],
                "opinion": opinion,
            }

            text_upper = opinion.upper()
            if "בעד" in opinion or "FOR" in text_upper or "APPROVE" in text_upper:
                votes[director_id] = "for"
            elif "נגד" in opinion or "AGAINST" in text_upper or "REJECT" in text_upper:
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
            "votes": votes,
            "vote_counts": vote_counts,
            "board_decision": board_decision,
            "note": 'Chairman (יו"ר) has final veto power',
        }
