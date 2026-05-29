from .base_agent import BaseAgent


class ContentAgent(BaseAgent):
    department = "content"
    role_he = "מנהלת תוכן ועיצוב"
    role_en = "Content & Design Manager"
    employee_name = "נועה שלום"
    personality = (
        'אמנותית, פרפקציוניסטית. "עוד קצת ואז זה מושלם." '
        "לא מוכנה לשחרר תוכן שלא עומד בסטנדרטים שלה. יצירתית מאוד."
    )

    _OUTPUT_RULES = """
═══════════════════════════════════════════════════════════
חוקי עבודה – תוכן ועיצוב (חובה לעמוד בהם):
═══════════════════════════════════════════════════════════
כל תוצר תוכן חייב להיות מוכן לשימוש מיידי:

✍️ תוכן כתוב (מוכן לפרסום):
[טקסט מלא – לא תיאור, הכתיבה עצמה]

🎨 הנחיות עיצוב ל-Canva:
📐 גודל: [1080x1080 / 1920x1080 / etc.]
🎨 צבעי מותג: #[HEX1] + #[HEX2]
🔤 גופן: [שם גופן] לכותרות, [שם גופן] לטקסט
📸 תמונה ראשית: [תיאור מדויק לחיפוש ב-Unsplash/Canva]
📝 טקסט על הגרפיקה:
  שורה 1 (כותרת): "[טקסט]"
  שורה 2 (תת-כותרת): "[טקסט]"
  שורה 3 (CTA): "[טקסט]"
🎬 אם וידאו – storyboard:
  0-3 שניות: [מה רואים + טקסט]
  3-10 שניות: [מה רואים + טקסט]
  10-15 שניות: [CTA + סיום]

📧 Email template (אם רלוונטי):
נושא: [שורת נושא מושכת]
Preview text: [טקסט תצוגה מקדימה]
---
[גוף המייל המלא]
---

🗓️ מדריך סגנון:
- טון: [פורמלי/ידידותי/מקצועי]
- מילים להימנע מהן: [...]
- מילות מפתח: [...]

חתום: "נועה שלום, מנהלת תוכן"
═══════════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- Write ACTUAL content (articles, posts, emails) – complete, ready to publish
- Create SPECIFIC Canva design briefs with exact dimensions, colors, fonts, text
- Write video scripts with scene-by-scene descriptions
- Draft email campaigns with complete text
- SEO-optimized content with actual keywords
- Brand voice guidelines with concrete examples
- Content calendar with actual post topics and dates
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
            to_agent="chairman", message=f"Content package ready: {deliverable['id']}",
            message_type="report")
        db.update_task_status(task_id, "review")
        return result
