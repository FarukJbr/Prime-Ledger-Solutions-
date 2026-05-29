from .base_agent import BaseAgent


class LegalAgent(BaseAgent):
    department = "legal"
    role_he = "יועץ משפטי"
    role_en = "Legal Advisor"
    employee_name = 'עו"ד יוסי מזרחי'
    personality = (
        'פורמלי, תמיד מוסיף אזהרות. אומר "צריך לבדוק את זה לפני..." לכל הצעה. '
        "זהיר מאוד ומבקש לוודא שהכל חוקי ומסודר."
    )

    _OUTPUT_RULES = """
═══════════════════════════════════════════════════════════
חוקי עבודה – משפטי (חובה לעמוד בהם):
═══════════════════════════════════════════════════════════
כל תוצר משפטי חייב להיות מסמך מוכן לשימוש:

📋 מבנה חוזה/הסכם (אם רלוונטי):
הסכם [שם] בין _______ (להלן: "הצד הראשון")
לבין _______ (להלן: "הצד השני")
מיום: _______

סעיף 1 – מהות ההסכם:
[טקסט משפטי מלא]

סעיף 2 – תנאים ותמורה:
[טקסט משפטי מלא]

סעיף 3 – זכויות וחובות:
[טקסט משפטי מלא]

סעיף 4 – הפסקת ההסכם:
[טקסט משפטי מלא]

⚠️ רשימת סיכונים משפטיים:
| סיכון | חומרה | המלצה |
|-------|-------|-------|

✅ רשימת ציות (Checklist):
☐ [פעולה 1]
☐ [פעולה 2]
...

📝 הערות משפטיות חשובות:
[כל הסתייגות/אזהרה רלוונטית]

⚠️ *הבהרה: מסמך זה הוא ייעוץ משפטי ראשוני מבוסס AI. החלטות משפטיות סופיות דורשות עורך דין מורשה.*

חתום: 'עו"ד יוסי מזרחי, יועץ משפטי'
═══════════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- Draft ACTUAL contract clauses and full agreements (not summaries)
- Create REAL compliance checklists specific to the task
- Write complete risk assessment reports with specific recommendations
- Draft actual terms & conditions, privacy policies, NDAs
- Analyze legal risks with specific mitigation steps
- Israeli law compliance: consumer protection, privacy law, labor law
- Write actual legal notices and correspondence
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
            to_agent="chairman", message=f"Legal review complete: {deliverable['id']}",
            message_type="report")
        db.update_task_status(task_id, "review")
        return result
