from .base_agent import BaseAgent


class CFOAgent(BaseAgent):
    department = "cfo"
    role_he = "מנהל כספים"
    role_en = "CFO - Chief Financial Officer"

    @property
    def responsibilities(self) -> str:
        return """
- Financial planning and analysis
- Budget management and cost control
- Investment evaluation and ROI analysis
- Financial reporting to the board
- Cash flow management
- Financial risk assessment
- Pricing strategy support
- Vendor payment and contract financials
"""
