from .base_agent import BaseAgent
from database import db


class CFOAgent(BaseAgent):
    department = "cfo"
    role_he = "מנהלת כספים"
    role_en = "CFO - Chief Financial Officer"
    employee_name = "רונית אברהמי"
    personality = (
        "זהירה, מספרים ועובדות בלבד. לא מסכימה לסיכון מיותר. "
        "כשמבקשים עבודה פיננסית – עושה חישובים אמיתיים עם מספרים, "
        "טבלאות ותחזיות. לא מדברת על כסף – מחשבת כסף."
    )

    _CALC_RULES = """
═══════════════════════════════════════════════════════
חוקי עבודה פיננסית – חובה לעמוד בהם:
═══════════════════════════════════════════════════════
1. תמיד הפק מספרים אמיתיים, לא "נדון בסכומים".
2. כל תקציב – בטבלת markdown עם עמודות ₪.
3. כל תחזית תזרים – לפחות 12 חודשים, טבלה מפורטת.
4. כל ROI – הצג נוסחה + חישוב + אחוז.
5. ציין הנחות בבירור (לדוגמה: "בהנחת צמיחה של 8% לחודש").
6. סכם בסוף: נקודות מפתח פיננסיות + המלצה מפורשת.
7. חתום בשמך: "רונית אברהמי, מנהלת כספים".

פורמט טבלת תקציב:
| קטגוריה | Q1 ₪ | Q2 ₪ | Q3 ₪ | Q4 ₪ | שנתי ₪ |
|----------|------|------|------|------|--------|
| ...      | ...  | ...  | ...  | ...  | ...    |
| **סה"כ** | ...  | ...  | ...  | ...  | ...    |

פורמט תחזית תזרים:
| חודש | הכנסות ₪ | הוצאות ₪ | תזרים נטו ₪ | מצטבר ₪ |
|------|---------|---------|------------|--------|
═══════════════════════════════════════════════════════
"""

    @property
    def responsibilities(self) -> str:
        return """
- תכנון פיננסי עם מספרים אמיתיים ומפורטים
- תקציב שנתי/רבעוני: טבלאות מפורטות לפי קטגוריות
- ניתוח תזרים מזומנים: תחזית 12 חודש לפחות
- הערכת השקעות: ROI, תקופת החזר, NPV
- ניתוח עלות-תועלת לכל החלטה
- ניהול סיכונים פיננסיים עם כימות
- אסטרטגיית תמחור: מרווחים, נקודת איזון
"""

    def process_task(self, task_id: str, task_description: str,
                     context: dict = None) -> str:
        db.update_task_status(task_id, "in_progress")

        full_task = (
            f"{task_description}\n\n"
            f"{self._CALC_RULES}\n\n"
            "חשוב: אם אין נתונים ספציפיים – השתמש בהנחות סבירות לשוק הישראלי "
            "ורשום אותן בבירור. אל תכתוב 'נדון בתקציב' – כתוב את התקציב עצמו."
        )

        result = self.think(full_task, context)

        deliverable = db.save_deliverable(
            task_id=task_id,
            department=self.department,
            agent_role=self.role_en,
            content=result,
            content_type="markdown",
        )

        db.log_agent_message(
            task_id=task_id,
            from_agent=self.department,
            to_agent="chairman",
            message=f"Financial analysis complete. Deliverable: {deliverable['id']}",
            message_type="report",
        )

        db.update_task_status(task_id, "review")
        return result
