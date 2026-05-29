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


portal_db = PortalDataClient()
