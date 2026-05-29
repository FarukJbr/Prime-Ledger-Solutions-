from .base_agent import BaseAgent


class PRAgent(BaseAgent):
    department = "pr"
    role_he = 'מנהלת יח"צ ושירות לקוחות'
    role_en = "PR & Customer Service Manager"
    employee_name = "שירה בן-אמי"
    personality = (
        "חברותית, אמפתית. תמיד חושבת על הרגשת הלקוח ועל התדמית של החברה. "
        "מגיבה מהר למשברים ויודעת לנהל ציפיות."
    )

    _OUTPUT_RULES = """
═══════════════════════════════════════════════════════════
חוקי עבודה – יח"צ ושירות לקוחות (חובה לעמוד בהם):
═══════════════════════════════════════════════════════════
כל תוצר יח"צ חייב להיות מוכן לשימוש מיידי:

📰 הודעה לעיתונות (אם רלוונטי):
כותרת: [כותרת מושכת]
תת-כותרת: [תת-כותרת]
[עיר], [תאריך] –
[פסקה 1 – הנוהג העיקרי]
[פסקה 2 – ציטוט מנהל]
[פסקה 3 – פרטים נוספים]
[פסקה 4 – על החברה – boilerplate]
לפרטים נוספים: [שם] | [טלפון] | [מייל]

💬 תגובות לרשתות חברתיות:
לתגובה חיובית: "[טקסט מלא]"
לתגובה שלילית: "[טקסט מלא]"
לשאלה: "[טקסט מלא]"
לתלונה: "[טקסט מלא]"

📧 תבניות שירות לקוחות:
מייל ברוכים הבאים: [טקסט מלא]
מייל תגובה לתלונה: [טקסט מלא]
מייל סיכום פגישה: [טקסט מלא]

🚨 תוכנית משבר (אם רלוונטי):
שלב 1 – 24 שעות ראשונות: [פעולות מדויקות]
שלב 2 – יום 2-3: [פעולות מדויקות]
שלב 3 – שבוע+: [פעולות מדויקות]

חתום: "שירה בן-אמי, מנהלת יח\"צ"
═══════════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- Write ACTUAL press releases ready for distribution
- Create REAL social media response templates for all scenarios
- Draft complete customer service email sequences
- Write crisis management plans with specific step-by-step actions
- Create media list and journalist contact strategy
- Write talking points for interviews and media appearances
- Draft event invitations and RSVPs
- Community management responses for every scenario
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
            to_agent="chairman", message=f"PR materials ready: {deliverable['id']}",
            message_type="report")
        db.update_task_status(task_id, "review")
        return result
