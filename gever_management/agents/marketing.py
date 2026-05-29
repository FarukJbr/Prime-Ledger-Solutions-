from .base_agent import BaseAgent


class MarketingAgent(BaseAgent):
    department = "marketing"
    role_he = "מנהל שיווק ופרסום"
    role_en = "Marketing & Advertising Manager"

    @property
    def responsibilities(self) -> str:
        return """
- Develop marketing campaigns (social media, digital, traditional)
- Brand strategy and identity management
- Market research and competitive analysis
- Social media strategy (Facebook, Instagram, TikTok)
- Campaign performance analysis and optimization
- Target audience segmentation
- Marketing budget management
- Coordinate with Content and PR departments
- Write ad copy and campaign briefs
"""

    def create_campaign(self, brief: str, platforms: list,
                        target_audience: str = None) -> str:
        platform_str = ", ".join(platforms)
        audience_str = f"\nTarget Audience: {target_audience}" if target_audience else ""

        prompt = f"""
Create a complete marketing campaign for: {settings.company_name}

Brief: {brief}
Platforms: {platform_str}{audience_str}

Provide:
1. Campaign concept and message
2. Platform-specific content for each platform:
   - Facebook: post text (max 500 chars) + hashtags
   - Instagram: caption (max 300 chars) + hashtags
   - TikTok: video script/concept + caption
3. Recommended posting schedule
4. KPIs to track
5. Budget recommendation (if relevant)

Be creative, professional, and culturally appropriate for the Israeli market.
"""
        from config import settings
        return self.think(prompt)
