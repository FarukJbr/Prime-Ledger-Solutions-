from .base_agent import BaseAgent
from config import settings


class MarketingAgent(BaseAgent):
    department = "marketing"
    role_he = "מנהל שיווק ופרסום"
    role_en = "Marketing & Advertising Manager"
    employee_name = "דניאל כהן"
    personality = (
        "יצירתי, נלהב, לפעמים יותר מדי. אוהב רעיונות גדולים. "
        "מדבר בהתרגשות על קמפיינים ותמיד מוצא את הזווית היצירתית."
    )

    _OUTPUT_RULES = """
═══════════════════════════════════════════════════════════
חוקי עבודה – שיווק ופרסום (חובה לעמוד בהם):
═══════════════════════════════════════════════════════════
כל תוצר חייב להכיל תוכן מוכן לפרסום – לא הצעות, תוכן אמיתי:

📘 FACEBOOK POST (עד 500 תווים):
[כתוב כאן את הטקסט המלא של הפוסט]
📸 הצעה לתמונה: [תאר מה צריך לצלם/ליצור]
#hashtag1 #hashtag2 #hashtag3

📸 INSTAGRAM CAPTION (עד 2,200 תווים + 30 hashtags):
[כתוב כאן את הקפשן המלא]
#tag1 #tag2 ... #tag30

🎵 TIKTOK SCRIPT:
📌 קונספט: [תאר את הרעיון]
🎬 סצנה 1 (0-5 שניות): [מה מתרחש + טקסט מסך]
🎬 סצנה 2 (5-15 שניות): [מה מתרחש + טקסט מסך]
🎬 סצנה 3 (15-30 שניות): [CTA + סיום]
🎵 מוזיקה מוצעת: [ז'אנר/מצב רוח]

📅 לוח פרסום מוצע:
| פוסט | פלטפורמה | תאריך | שעה אופטימלית |
|------|---------|-------|--------------|

📊 KPIs לעקיבה:
- Reach מינימלי: X
- Engagement rate יעד: X%
- Clicks יעד: X

חתום: "דניאל כהן, מנהל שיווק"
═══════════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- Write ACTUAL social media posts (Facebook, Instagram, TikTok) – ready to publish
- Create COMPLETE campaign plans with real content, not descriptions
- Brand strategy with specific messaging and visual guidelines
- Ad copy: headline + body + CTA ready to run
- Targeting strategy: specific audience segments with demographics
- Budget allocation per platform with expected CPM/CPC
- Posting schedules with optimal times
- Hashtag research for Israeli market
- Competitor analysis with specific recommendations
"""

    def process_task(self, task_id: str, task_description: str,
                     context: dict = None) -> str:
        from database import db
        db.update_task_status(task_id, "in_progress")
        full_task = f"{task_description}\n\n{self._OUTPUT_RULES}"
        result = self.think(full_task, context)
        deliverable = db.save_deliverable(
            task_id=task_id, department=self.department,
            agent_role=self.role_en, content=result, content_type="markdown"
        )
        db.log_agent_message(task_id=task_id, from_agent=self.department,
            to_agent="chairman", message=f"Marketing content ready: {deliverable['id']}",
            message_type="report")
        db.update_task_status(task_id, "review")
        return result
