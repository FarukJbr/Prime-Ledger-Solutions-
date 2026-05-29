from .base_agent import BaseAgent


class ContentAgent(BaseAgent):
    department = "content"
    role_he = "מנהל יצור תוכן ועיצוב"
    role_en = "Content Creation & Design Manager"

    @property
    def responsibilities(self) -> str:
        return """
- Content strategy and editorial calendar
- Copywriting (website, social media, email, ads)
- Design briefs and visual identity guidelines
- Video scripts and storyboards
- Blog posts and articles
- Email marketing campaigns
- Infographic concepts
- Brand storytelling
- SEO content optimization
- Content performance analysis
- Coordinate with Marketing and PR departments
"""

    def create_content_package(self, brief: str,
                                content_types: list) -> str:
        types_str = "\n".join([f"- {t}" for t in content_types])
        prompt = f"""
Create a complete content package for: {brief}

Required content types:
{types_str}

For each content type provide:
- Full content text (ready to publish)
- Design notes / visual suggestions
- Tone and style guidelines used

Make it engaging, professional, and relevant to the Israeli business audience.
Company: {settings.company_name}
"""
        from config import settings
        return self.think(prompt)
