from .base_agent import BaseAgent


class SalesAgent(BaseAgent):
    department = "sales"
    role_he = "מנהל מכירות"
    role_en = "Sales Manager"

    @property
    def responsibilities(self) -> str:
        return """
- Sales strategy development and execution
- Client acquisition and lead management
- Sales proposals and presentations
- Client relationship management (CRM)
- Revenue targets and forecasting
- Sales team performance management
- Negotiation strategies
- Partnership development
- Customer retention strategies
- Sales pipeline management
"""
