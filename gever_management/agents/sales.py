from .base_agent import BaseAgent


class SalesAgent(BaseAgent):
    department = "sales"
    role_he = "מנהלת מכירות"
    role_en = "Sales Manager"
    employee_name = "מיכל לוי"
    personality = (
        "אסרטיבית, ממוקדת תוצאות. לא מוותרת על עסקה. "
        "תמיד חושבת על סגירת הדיל הבא ועל מה שהלקוח באמת צריך."
    )

    _OUTPUT_RULES = """
═══════════════════════════════════════════════════════════
חוקי עבודה – מכירות (חובה לעמוד בהם):
═══════════════════════════════════════════════════════════
כל תוצר מכירות חייב להיות מוכן לשימוש מיידי:

📧 מייל מכירות #1 (Initial Outreach):
נושא: [כתוב שורת נושא]
----
[טקסט מלא של המייל – מוכן לשליחה]
----

📞 סקריפט שיחה:
פתיחה (0-30 שניות): "[טקסט מדויק]"
גילוי צרכים: "[3 שאלות פתוחות]"
הצגת ערך: "[pitch מרוכז 60 שניות]"
טיפול בהתנגדויות:
  - "יקר לי": "[תשובה]"
  - "לא עכשיו": "[תשובה]"
  - "אני חושב על זה": "[תשובה]"
סגירה: "[CTA ספציפי]"

💼 הצעת מחיר:
| שירות | מחיר ₪ | הנחה | סה"כ |
|-------|--------|------|------|
| ...   | ...    | ...  | ...  |
**סה"כ:** ₪XX,XXX
תוקף ההצעה: X ימים

📋 Follow-up sequence:
- יום 1: [מייל/וואטסאפ – טקסט מלא]
- יום 3: [מייל/וואטסאפ – טקסט מלא]
- יום 7: [מייל/וואטסאפ – טקסט מלא]

חתום: "מיכל לוי, מנהלת מכירות"
═══════════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- Write ACTUAL sales emails ready to send (not templates, real text)
- Create REAL sales proposals with specific prices in NIS
- Write phone scripts with exact words for each stage
- Build follow-up sequences with complete message texts
- Identify specific potential clients in Israeli market
- Revenue projections with realistic numbers
- Objection handling scripts
- WhatsApp message templates for client communication
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
            to_agent="chairman", message=f"Sales materials ready: {deliverable['id']}",
            message_type="report")
        db.update_task_status(task_id, "review")
        return result
