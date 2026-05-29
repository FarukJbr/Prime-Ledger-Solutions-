from .base_agent import BaseAgent
from database import db
from database.portal_client import portal_db


def _format_portal_data(summary: dict) -> str:
    if not summary.get("available"):
        return "⚠️ נתוני תזרים מזומנים מהפורטל אינם זמינים – השתמש בהנחות סבירות לשוק הישראלי."

    accounts_lines = "\n".join(
        f"  • {a['name']} ({a.get('type','—')}): ₪{a['balance']:,.0f}"
        for a in summary.get("accounts", [])
    )

    monthly = summary.get("monthly_breakdown", {})
    monthly_lines = "\n".join(
        f"  | {month} | ₪{v['income']:>12,.0f} | ₪{v['expenses']:>12,.0f} | ₪{v['income']-v['expenses']:>12,.0f} |"
        for month, v in sorted(monthly.items())
    )

    cats = summary.get("top_expense_categories", [])
    cats_lines = "\n".join(
        f"  • {c['category']}: ₪{c['amount_ils']:,.0f}"
        for c in cats
    )

    bank = summary.get("bank_statement", {})

    return f"""
═══════════════════════════════════════════════════════
נתוני תזרים מזומנים אמיתיים מהפורטל (12 חודשים אחרונים):
═══════════════════════════════════════════════════════
חשבונות בנק ויתרות:
{accounts_lines}
יתרה כוללת: ₪{summary['total_accounts_balance_ils']:,.2f}

סיכום תקופה ({summary['period_months']} חודשים):
  הכנסות סה"כ:  ₪{summary['total_income_ils']:,.2f}
  הוצאות סה"כ:  ₪{summary['total_expenses_ils']:,.2f}
  תזרים נטו:    ₪{summary['net_cashflow_ils']:,.2f}
  מספר עסקאות:  {summary['transaction_count']}

פירוט חודשי:
  | חודש       | הכנסות          | הוצאות          | נטו             |
  |------------|-----------------|-----------------|-----------------|
{monthly_lines}

קטגוריות הוצאה מובילות:
{cats_lines}

תנועות בנק (ייבוא):
  זיכויים: ₪{bank.get('total_credits',0):,.2f}
  חיובים:  ₪{bank.get('total_debits',0):,.2f}
  שורות:   {bank.get('rows_count',0)}
═══════════════════════════════════════════════════════
השתמש בנתונים אלו כבסיס לניתוח שלך. אלו מספרים אמיתיים מהפורטל.
"""


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

        portal_section = _format_portal_data(portal_db.get_financial_summary())

        full_task = (
            f"{task_description}\n\n"
            f"{portal_section}\n\n"
            f"{self._CALC_RULES}\n\n"
            "חשוב: בסס את הניתוח שלך על נתוני הפורטל האמיתיים שסופקו למעלה. "
            "אם ישנם נתונים חסרים – השלם עם הנחות סבירות ורשום אותן בבירור. "
            "אל תכתוב 'נדון בתקציב' – כתוב את התקציב עצמו עם המספרים האמיתיים."
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
