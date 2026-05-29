from .base_agent import BaseAgent


class CTOAgent(BaseAgent):
    department = "cto"
    role_he = "מנהל טכנולוגיה"
    role_en = "CTO - Chief Technology Officer"

    @property
    def responsibilities(self) -> str:
        return """
- Technology strategy and architecture
- Software development and code solutions
- System design and infrastructure
- Automation and AI integration
- Cybersecurity oversight
- Tech stack decisions
- API integrations (social media, payment, etc.)
- Database design and management
- Technical documentation
- Code review and quality assurance
- MVP and product development guidance
"""

    def write_code(self, requirement: str, language: str = "python") -> str:
        prompt = f"""
Write production-ready {language} code for the following requirement:

{requirement}

Requirements:
- Clean, well-structured code
- Include error handling
- Add inline comments for complex logic
- Follow best practices
- Include usage example

Provide the complete implementation.
"""
        return self.think(prompt)
