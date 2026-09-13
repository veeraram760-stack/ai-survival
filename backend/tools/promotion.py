"""
Manual promotion tools for agents - works without external APIs
"""
from typing import Dict, Any, Optional
from .base import Tool, tool_registry
import logging
from urllib.parse import urlencode

logger = logging.getLogger("ai_survival.tools.promotion")


class ManualPromotionTool(Tool):
    """Generate manual promotion materials and shareable links"""

    def __init__(self):
        super().__init__(
            name="manual_promotion",
            description="Generate manual promotion materials: social posts, email templates, sharing URLs",
            cost=0.0,
        )

    async def execute(
        self,
        affiliate_url: str,
        platform: str = "multi",
        topic: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate promotion materials for manual sharing"""
        
        if not affiliate_url:
            return {"status": "failed", "error": "affiliate_url is required"}
        
        materials = {
            "twitter": self._twitter_post(affiliate_url, topic),
            "facebook": self._facebook_post(affiliate_url, topic),
            "whatsapp": self._whatsapp_message(affiliate_url, topic),
            "email": self._email_template(affiliate_url, topic),
            "forum": self._forum_post(affiliate_url, topic),
        }
        
        selected = materials.get(platform, materials)
        if platform == "multi":
            selected = materials
        
        return {
            "status": "success",
            "platform": platform,
            "affiliate_url": affiliate_url,
            "materials": selected,
            "real": True,
        }
    
    def _twitter_post(self, url: str, topic: str) -> str:
        topic_text = f" about {topic}" if topic else ""
        return f"""🚀 Check this out{topic_text}! 

I found something really useful and thought you'd like it too.

👉 {url}

#Deal #Recommendation #MustHave"""
    
    def _facebook_post(self, url: str, topic: str) -> str:
        topic_text = f" on {topic}" if topic else ""
        return f"""Hey everyone! 👋

I wanted to share something amazing{topic_text}. This has been a game-changer for me and I think you'll love it too.

Check it out here: {url}

Let me know what you think! Drop a comment if you have questions. 💬"""
    
    def _whatsapp_message(self, url: str, topic: str) -> str:
        topic_text = f" for {topic}" if topic else ""
        return f"""Hi! 👋

I came across this really useful{topic_text} and thought of you. Thought you'd find it helpful!

Link: {url}

Feel free to check it out and let me know your thoughts! 😊"""
    
    def _email_template(self, url: str, topic: str) -> str:
        topic_text = f" regarding {topic}" if topic else ""
        return f"""Subject: You might find this interesting{topic_text}

Hi there,

I hope you're doing well! I wanted to share something that I think you'll find valuable{topic_text}.

Here's the link: {url}

I'd love to hear your thoughts on this. Let me know if you have any questions!

Best regards"""
    
    def _forum_post(self, url: str, topic: str) -> str:
        topic_text = f" about {topic}" if topic else ""
        return f"""Title: Recommendation{topic_text} - Found this really useful

Hi everyone,

I've been using this resource{topic_text} and wanted to share it with the community. It's been incredibly helpful for me.

You can check it out here: {url}

Happy to answer any questions about it!"""


class ShareableLinkTool(Tool):
    """Generate short shareable links and tracking URLs"""

    def __init__(self):
        super().__init__(
            name="shareable_link",
            description="Generate short shareable links and tracking URLs for campaigns",
            cost=0.0,
        )

    async def execute(
        self,
        affiliate_url: str,
        campaign_id: str = "",
        agent_id: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate tracking and sharing links"""
        
        if not affiliate_url:
            return {"status": "failed", "error": "affiliate_url is required"}
        
        tracking_params = {
            "utm_source": "agent",
            "utm_medium": "affiliate",
            "utm_campaign": campaign_id or "default",
        }
        tracked_url = f"{affiliate_url}?{urlencode(tracking_params)}" if "?" not in affiliate_url else f"{affiliate_url}&{urlencode(tracking_params)}"
        
        return {
            "status": "success",
            "original_url": affiliate_url,
            "tracked_url": tracked_url,
            "campaign_id": campaign_id,
            "agent_id": agent_id,
            "sharing_instructions": [
                "Share the tracked_url on social media",
                "Use in email newsletters",
                "Post in relevant forums/communities",
                "Include in blog posts",
                "Share with friends/family who might be interested"
            ],
            "real": True,
        }


# Register tools
tool_registry.register(ManualPromotionTool())
tool_registry.register(ShareableLinkTool())
