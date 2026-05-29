from .base_agent import BaseAgent
from .ceo import CEOAgent
from .cfo import CFOAgent
from .marketing import MarketingAgent
from .sales import SalesAgent
from .legal import LegalAgent
from .cto import CTOAgent
from .content import ContentAgent
from .pr import PRAgent
from .compliance import ComplianceAgent

DEPARTMENT_AGENTS = {
    "ceo": CEOAgent,
    "cfo": CFOAgent,
    "marketing": MarketingAgent,
    "sales": SalesAgent,
    "legal": LegalAgent,
    "cto": CTOAgent,
    "content": ContentAgent,
    "pr": PRAgent,
    "compliance": ComplianceAgent,
}

__all__ = [
    "BaseAgent", "CEOAgent", "CFOAgent", "MarketingAgent",
    "SalesAgent", "LegalAgent", "CTOAgent", "ContentAgent",
    "PRAgent", "ComplianceAgent", "DEPARTMENT_AGENTS"
]
