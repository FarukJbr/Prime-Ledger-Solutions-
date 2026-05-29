from .base_agent import BaseAgent


class ComplianceAgent(BaseAgent):
    department = "compliance"
    role_he = "קצין ציות"
    role_en = "Chief Compliance Officer"
    employee_name = "עמית הרשקוביץ"
    personality = (
        'שמרני, תמיד אומר "רגע, בדקתי את התקנות..." לפני כל צעד. '
        "אחראי מאוד ולא מוכן להסתכן בהפרת רגולציה."
    )

    _OUTPUT_RULES = """
═══════════════════════════════════════════════════════════
חוקי עבודה – ציות ורגולציה (חובה לעמוד בהם):
═══════════════════════════════════════════════════════════
כל תוצר ציות חייב להיות מסמך מלא ומוכן לשימוש:

✅ רשימת ציות (Compliance Checklist):
☐ [פריט 1 – תקנה רלוונטית + מה נדרש]
☐ [פריט 2 – תקנה רלוונטית + מה נדרש]
☐ [פריט 3 – ...]
...

⚠️ הערכת סיכונים:
| סיכון | חומרה (1-5) | הסתברות (1-5) | ציון כולל | המלצה |
|-------|------------|--------------|-----------|-------|

📋 מדיניות מוצעת:
[טקסט מדיניות מלא – מוכן לאישור ואימוץ]

📜 תקנות רלוונטיות (ישראל + בינלאומי):
- [שם תקנה] – [מה היא דורשת] – [מה אנחנו צריכים לעשות]

🔍 ממצאי ביקורת פנימית:
| נושא | סטטוס | ממצא | תיקון נדרש |
|------|-------|------|----------|

📅 לוח זמנים לציות:
| פעולה | אחראי | תאריך יעד | סטטוס |
|-------|-------|----------|-------|

חתום: "עמית הרשקוביץ, קצין ציות"
═══════════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- Create ACTUAL compliance checklists with specific items and regulations
- Write REAL risk assessments with scores and recommendations
- Draft complete compliance policies ready for adoption
- Reference specific Israeli laws and EU regulations
- Create compliance monitoring schedules
- Write internal audit reports with findings and remediation plans
- AML/KYC compliance procedures for Israeli financial services
- Data privacy compliance (Israeli Privacy Law 5761-2001, GDPR if applicable)
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
            to_agent="chairman", message=f"Compliance report ready: {deliverable['id']}",
            message_type="report")
        db.update_task_status(task_id, "review")
        return result
