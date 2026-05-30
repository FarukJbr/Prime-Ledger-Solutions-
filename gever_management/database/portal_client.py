"""
Portal Supabase client – reads cash flow data from the client portal.
Tables used: accounts_ledger, ledger_records, bank_rows
"""
import logging
from config import settings

logger = logging.getLogger(__name__)


class PortalDataClient:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            url = settings.portal_supabase_url
            key = settings.portal_supabase_key
            if not url or not key:
                return None
            from supabase import create_client
            self._client = create_client(url, key)
        return self._client

    @property
    def available(self) -> bool:
        return bool(settings.portal_supabase_url and settings.portal_supabase_key)

    # ── Accounts ──────────────────────────────────────────────────────────────

    def get_accounts(self) -> list:
        """Return all bank/cash accounts from the portal."""
        c = self._get_client()
        if not c:
            return []
        try:
            return c.table("accounts_ledger").select("*").order("name").execute().data
        except Exception as e:
            logger.error("Portal get_accounts: %s", e)
            return []

    # ── Transactions ──────────────────────────────────────────────────────────

    def get_transactions(self, months: int = 12) -> list:
        """Return ledger records for the last N months."""
        c = self._get_client()
        if not c:
            return []
        try:
            from datetime import datetime, timedelta
            since = (datetime.utcnow() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
            return (
                c.table("ledger_records")
                .select("*")
                .gte("record_date", since)
                .order("record_date", desc=True)
                .execute()
                .data
            )
        except Exception as e:
            logger.error("Portal get_transactions: %s", e)
            return []

    def get_bank_rows(self, months: int = 12) -> list:
        """Return imported bank statement rows for the last N months."""
        c = self._get_client()
        if not c:
            return []
        try:
            from datetime import datetime, timedelta
            since = (datetime.utcnow() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
            return (
                c.table("bank_rows")
                .select("*")
                .gte("row_date", since)
                .order("row_date", desc=True)
                .execute()
                .data
            )
        except Exception as e:
            logger.error("Portal get_bank_rows: %s", e)
            return []

    # ── Aggregated Summary ────────────────────────────────────────────────────

    def get_financial_summary(self) -> dict:
        """
        Returns a structured summary ready for CFO analysis:
        - accounts with balances
        - monthly income/expense breakdown
        - top categories
        - cash flow trend
        """
        accounts   = self.get_accounts()
        records    = self.get_transactions(months=12)
        bank_rows  = self.get_bank_rows(months=12)

        if not accounts and not records:
            return {"available": False}

        # Total balances
        total_balance = sum(float(a.get("opening_balance") or 0) for a in accounts)

        # Income vs expenses from ledger_records
        income   = [r for r in records if r.get("type") == "income"]
        expenses = [r for r in records if r.get("type") == "expense"]

        total_income   = sum(float(r.get("amount") or 0) for r in income)
        total_expenses = sum(float(r.get("amount") or 0) for r in expenses)
        net_cashflow   = total_income - total_expenses

        # Monthly breakdown
        monthly: dict = {}
        for r in records:
            date = (r.get("record_date") or "")[:7]  # YYYY-MM
            if date not in monthly:
                monthly[date] = {"income": 0.0, "expenses": 0.0}
            amount = float(r.get("amount") or 0)
            if r.get("type") == "income":
                monthly[date]["income"] += amount
            else:
                monthly[date]["expenses"] += amount

        # Top expense categories
        cat_totals: dict = {}
        for r in expenses:
            cat = r.get("category") or "כללי"
            cat_totals[cat] = cat_totals.get(cat, 0.0) + float(r.get("amount") or 0)
        top_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:8]

        # Bank rows summary
        bank_credits = sum(float(r.get("credit") or 0) for r in bank_rows)
        bank_debits  = sum(float(r.get("debit")  or 0) for r in bank_rows)

        return {
            "available": True,
            "accounts": [
                {
                    "name":    a.get("name"),
                    "type":    a.get("type"),
                    "balance": float(a.get("opening_balance") or 0),
                    "color":   a.get("color"),
                }
                for a in accounts
            ],
            "total_accounts_balance_ils": round(total_balance, 2),
            "period_months": 12,
            "total_income_ils":   round(total_income, 2),
            "total_expenses_ils": round(total_expenses, 2),
            "net_cashflow_ils":   round(net_cashflow, 2),
            "monthly_breakdown":  monthly,
            "top_expense_categories": [
                {"category": c, "amount_ils": round(v, 2)}
                for c, v in top_categories
            ],
            "bank_statement": {
                "total_credits": round(bank_credits, 2),
                "total_debits":  round(bank_debits, 2),
                "rows_count":    len(bank_rows),
            },
            "transaction_count": len(records),
        }


    # ── Tracking Report ───────────────────────────────────────────────────────

    def get_tracking_report(self) -> dict:
        """
        Weekly / Monthly / Annual profitability tracking.
        Single DB query, all calculations done in Python.
        """
        c = self._get_client()
        if not c:
            return {"available": False}

        from datetime import datetime, timedelta, date as dt_date

        today = datetime.utcnow().date()
        two_years_ago = dt_date(today.year - 2, 1, 1).isoformat()

        try:
            records = (
                c.table("ledger_records")
                .select("record_date,type,amount,category")
                .gte("record_date", two_years_ago)
                .execute()
                .data
            )
        except Exception as e:
            logger.error("get_tracking_report: %s", e)
            return {"available": False}

        # Helper: sum income/expenses for a date range (inclusive)
        def period(from_d: str, to_d: str) -> dict:
            inc = exp = 0.0
            for r in records:
                d = (r.get("record_date") or "")[:10]
                if from_d <= d <= to_d:
                    amt = float(r.get("amount") or 0)
                    if r.get("type") == "income":
                        inc += amt
                    else:
                        exp += amt
            net = inc - exp
            return {
                "income":   round(inc, 2),
                "expenses": round(exp, 2),
                "net":      round(net, 2),
                "profitable": net > 0,
            }

        def pct(cur, prev):
            if prev == 0:
                return None
            return round((cur - prev) / abs(prev) * 100, 1)

        # ── Week ──────────────────────────────────────────────
        week_start   = today - timedelta(days=today.weekday())   # Monday
        pw_start     = week_start - timedelta(weeks=1)
        pw_end       = week_start - timedelta(days=1)

        tw = period(week_start.isoformat(), today.isoformat())
        lw = period(pw_start.isoformat(),   pw_end.isoformat())

        # ── Month ─────────────────────────────────────────────
        m_start = today.replace(day=1)
        if m_start.month == 1:
            pm_start = dt_date(m_start.year - 1, 12, 1)
        else:
            pm_start = dt_date(m_start.year, m_start.month - 1, 1)
        pm_end = m_start - timedelta(days=1)

        tm = period(m_start.isoformat(), today.isoformat())
        lm = period(pm_start.isoformat(), pm_end.isoformat())

        # ── Year ──────────────────────────────────────────────
        y_start  = dt_date(today.year, 1, 1)
        py_start = dt_date(today.year - 1, 1, 1)
        py_end   = dt_date(today.year - 1, 12, 31)

        ty = period(y_start.isoformat(), today.isoformat())
        ly = period(py_start.isoformat(), py_end.isoformat())

        # ── 13-month rolling trend ────────────────────────────
        monthly_trend = []
        for i in range(12, -1, -1):
            # Go back i months from current month
            year  = today.year  - ((today.month - 1 - i) // 12 + 1 if (today.month - 1 - i) < 0 else 0)
            month = ((today.month - 1 - i) % 12) + 1
            year  = today.year + (today.month - 1 - i) // 12 if (today.month - 1 - i) >= 0 else today.year - 1
            month = ((today.month - 1 - i) % 12) + 1
            ms = dt_date(year, month, 1)
            if month == 12:
                me = dt_date(year, 12, 31)
            else:
                me = dt_date(year, month + 1, 1) - timedelta(days=1)
            p = period(ms.isoformat(), me.isoformat())
            he_months = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                         "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
            monthly_trend.append({
                "key":   ms.strftime("%Y-%m"),
                "label": f"{he_months[month-1]} {year}",
                **p,
            })

        # ── Weekly breakdown for current month ────────────────
        weeks_this_month = []
        cursor = m_start
        while cursor <= today:
            wend = min(cursor + timedelta(days=6), today)
            p = period(cursor.isoformat(), wend.isoformat())
            weeks_this_month.append({
                "label": f"{cursor.strftime('%d/%m')}–{wend.strftime('%d/%m')}",
                **p,
            })
            cursor = wend + timedelta(days=1)

        # ── Category breakdown this year ──────────────────────
        cat_inc: dict = {}
        cat_exp: dict = {}
        y_start_str = y_start.isoformat()
        today_str   = today.isoformat()
        for r in records:
            d = (r.get("record_date") or "")[:10]
            if y_start_str <= d <= today_str:
                cat = r.get("category") or "כללי"
                amt = float(r.get("amount") or 0)
                if r.get("type") == "income":
                    cat_inc[cat] = cat_inc.get(cat, 0.0) + amt
                else:
                    cat_exp[cat] = cat_exp.get(cat, 0.0) + amt

        top_inc = sorted(cat_inc.items(), key=lambda x: x[1], reverse=True)[:6]
        top_exp = sorted(cat_exp.items(), key=lambda x: x[1], reverse=True)[:8]

        he_months_map = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                         "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]

        return {
            "available": True,
            "as_of": today.isoformat(),
            "weekly": {
                "this_week":         tw,
                "last_week":         lw,
                "income_change_pct": pct(tw["income"],   lw["income"]),
                "expense_change_pct":pct(tw["expenses"], lw["expenses"]),
                "net_change_pct":    pct(tw["net"],      lw["net"]) if lw["net"] != 0 else None,
                "label": f"{week_start.strftime('%d/%m')} – {today.strftime('%d/%m/%Y')}",
            },
            "monthly": {
                "this_month":        tm,
                "last_month":        lm,
                "income_change_pct": pct(tm["income"],   lm["income"]),
                "expense_change_pct":pct(tm["expenses"], lm["expenses"]),
                "net_change_pct":    pct(tm["net"],      lm["net"]) if lm["net"] != 0 else None,
                "label": f"{he_months_map[today.month-1]} {today.year}",
            },
            "annual": {
                "this_year":         ty,
                "last_year":         ly,
                "income_change_pct": pct(ty["income"],   ly["income"]),
                "expense_change_pct":pct(ty["expenses"], ly["expenses"]),
                "net_change_pct":    pct(ty["net"],      ly["net"]) if ly["net"] != 0 else None,
                "label": str(today.year),
                "ytd_days": (today - y_start).days + 1,
            },
            "overall_profitable": tm["profitable"] and ty["profitable"],
            "monthly_trend":      monthly_trend,
            "weeks_this_month":   weeks_this_month,
            "top_income_categories":  [{"category": k, "amount": round(v, 2)} for k, v in top_inc],
            "top_expense_categories": [{"category": k, "amount": round(v, 2)} for k, v in top_exp],
        }


portal_db = PortalDataClient()
