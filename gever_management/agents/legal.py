from .base_agent import BaseAgent


class LegalAgent(BaseAgent):
    department = "legal"
    role_he = "יועץ משפטי"
    role_en = "Legal Advisor"

    @property
    def responsibilities(self) -> str:
        return """
- Legal review of contracts and agreements
- Regulatory compliance guidance
- Risk assessment and mitigation
- Intellectual property protection
- Employment law compliance
- Consumer protection law (Israeli market)
- Privacy and data protection (GDPR/Israeli Privacy Law)
- Business licensing and permits
- Dispute resolution guidance
- Legal templates and standard agreements

IMPORTANT: Always add disclaimer that this is AI-generated legal guidance
and final legal decisions require a licensed attorney.
"""
