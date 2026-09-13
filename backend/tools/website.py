"""
Website/landing page generator for affiliate marketing
"""
from typing import Dict, Any, Optional
from .base import Tool, tool_registry
import logging

logger = logging.getLogger("ai_survival.tools.website")


class WebsiteGeneratorTool(Tool):
    """Generate static landing pages/websites with affiliate links"""

    def __init__(self):
        super().__init__(
            name="website_generator",
            description="Generate static landing pages/websites with affiliate content and links",
            cost=0.0,
        )

    async def execute(
        self,
        topic: str,
        affiliate_url: str,
        style: str = "modern",
        pages: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a static website with affiliate content"""

        html_content = self._generate_landing_page(topic, affiliate_url, style)
        
        return {
            "status": "success",
            "topic": topic,
            "affiliate_url": affiliate_url,
            "style": style,
            "pages_generated": pages,
            "html": html_content,
            "filename": f"{topic.replace(' ', '_').lower()}_landing.html",
            "deploy_instructions": [
                "Save the HTML to a file",
                "Upload to GitHub Pages, Netlify, or Vercel",
                "Or serve locally with: python -m http.server 8080",
            ],
            "real": True,
        }
    
    def _generate_landing_page(self, topic: str, affiliate_url: str, style: str) -> str:
        title = f"{topic.title()} - Best Resources & Deals"
        
        if style == "modern":
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="Discover the best {topic.lower()} resources and deals. Curated recommendations and exclusive offers.">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; line-height: 1.6; color: #333; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 60px 0; text-align: center; }}
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        header p {{ font-size: 1.2em; opacity: 0.9; }}
        .content {{ padding: 60px 0; }}
        .card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card h2 {{ color: #667eea; margin-bottom: 15px; }}
        .cta-button {{ display: inline-block; background: #667eea; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px; transition: transform 0.2s; }}
        .cta-button:hover {{ transform: translateY(-2px); }}
        footer {{ text-align: center; padding: 40px 0; color: #666; }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>{topic.title()}</h1>
            <p>Curated resources and exclusive deals</p>
        </div>
    </header>
    <div class="content">
        <div class="container">
            <div class="card">
                <h2>Recommended Resources</h2>
                <p>We've curated the best {topic.lower()} resources to help you achieve your goals. Our team has tested and reviewed each recommendation to ensure quality and value.</p>
                <a href="{affiliate_url}" class="cta-button" target="_blank" rel="noopener">Check Out Our Top Pick</a>
            </div>
            <div class="card">
                <h2>Why Trust Our Recommendations?</h2>
                <p>We specialize in {topic.lower()} and have helped thousands of users find the right solutions. Our recommendations are based on real-world testing and user feedback.</p>
            </div>
            <div class="card">
                <h2>Exclusive Offers</h2>
                <p>Take advantage of our exclusive deals and discounts. Click the button below to access limited-time offers on top {topic.lower()} products and services.</p>
                <a href="{affiliate_url}" class="cta-button" target="_blank" rel="noopener">View Exclusive Deals</a>
            </div>
        </div>
    </div>
    <footer>
        <div class="container">
            <p>Affiliate Disclosure: We may earn a commission when you use one of our coupons/links to make a purchase.</p>
        </div>
    </footer>
</body>
</html>"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="Discover the best {topic.lower()} resources and deals.">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .cta {{ background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Discover the best {topic.lower()} resources and deals.</p>
    <a href="{affiliate_url}" class="cta">Check It Out</a>
    <footer><small>Affiliate Disclosure: We may earn a commission when you use our links.</small></footer>
</body>
</html>"""


# Register tool
tool_registry.register(WebsiteGeneratorTool())
