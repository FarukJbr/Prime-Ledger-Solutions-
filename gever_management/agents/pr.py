from .base_agent import BaseAgent


class PRAgent(BaseAgent):
    department = "pr"
    role_he = "מנהל יחסי ציבור ושירות לקוחות"
    role_en = "PR & Customer Service Manager"

    @property
    def responsibilities(self) -> str:
        return """
- Public relations strategy and media relations
- Press releases and media communications
- Crisis management and reputation management
- Customer service standards and protocols
- Client feedback management
- Community management (social media responses)
- Brand reputation monitoring
- Stakeholder communications
- Event planning and coordination
- Corporate social responsibility (CSR) initiatives
- Customer satisfaction programs
"""
