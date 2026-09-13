"""
Blog Publisher Tool - Auto-generates and publishes product review pages
"""
import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.blog_publisher")

# Path to the docs directory for Surge deployment
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
REVIEWS_DIR = os.path.join(DOCS_DIR, "reviews")


class BlogPublisherTool(Tool):
    """Generate product review content and publish as HTML blog posts"""

    def __init__(self):
        super().__init__(
            name="blog_publisher",
            description="Generate SEO-optimized product review blog posts and publish to the website",
            cost=0.02,
        )
        self.llm = get_llm_provider()

    async def execute(
        self,
        topic: str,
        products: Optional[List[Dict[str, str]]] = None,
        affiliate_tag: str = "niryok-21",
        product_type: str = "general",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate and publish a product review blog post"""
        from config.settings import settings

        # Ensure directories exist
        os.makedirs(REVIEWS_DIR, exist_ok=True)

        # Generate slug from topic
        slug = self._topic_to_slug(topic)

        # Generate review content using LLM
        content_result = await self._generate_review_content(topic, products, product_type)

        if content_result["status"] != "success":
            return content_result

        review_data = content_result["review"]

        # Generate HTML page
        html_content = self._generate_html(
            title=review_data["title"],
            slug=slug,
            meta_description=review_data["meta_description"],
            sections=review_data["sections"],
            products=review_data["products"],
            affiliate_tag=affiliate_tag,
            product_type=product_type,
        )

        # Save HTML file
        filename = f"{slug}.html"
        filepath = os.path.join(REVIEWS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Update sitemap
        self._update_sitemap(slug, topic)

        # Generate the public URL
        site_url = getattr(settings, "site_url", "https://ai-survival.surge.sh")
        post_url = f"{site_url}/reviews/{filename}"

        # Generate tweet content for social sharing
        tweet_content = await self._generate_tweet(topic, review_data["title"], post_url)

        return {
            "status": "success",
            "blog_post": {
                "title": review_data["title"],
                "url": post_url,
                "filename": filename,
                "slug": slug,
                "meta_description": review_data["meta_description"],
                "product_count": len(review_data["products"]),
                "word_count": len(content_result.get("raw_content", "").split()),
            },
            "tweet_content": tweet_content,
            "social_sharing": {
                "twitter": tweet_content,
                "suggested_hashtags": [f"#{product_type}", "#TechReview", "#BestBuys", "#AITools"],
            },
            "affiliate_tag": affiliate_tag,
            "revenue": 0.0,
            "note": "Blog post published; revenue tracked via affiliate conversions",
        }

    def _topic_to_slug(self, topic: str) -> str:
        """Convert topic to URL-friendly slug"""
        slug = topic.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        # Add date prefix for uniqueness
        date_prefix = datetime.now().strftime("%Y%m%d")
        return f"{date_prefix}-{slug}"

    async def _generate_review_content(
        self, topic: str, products: Optional[List[Dict]], product_type: str
    ) -> Dict[str, Any]:
        """Generate review content using LLM"""

        products_context = ""
        if products:
            products_list = "\n".join([
                f"- {p.get('name', 'Product')} (${p.get('price', 'N/A')}): {p.get('description', 'No description')}"
                for p in products[:5]
            ])
            products_context = f"\n\nProducts to review:\n{products_list}"

        prompt = f"""Write a comprehensive product review article about "{topic}".

Requirements:
1. Title: Create a compelling, SEO-friendly title (e.g., "Best [Product] 2026: Top Picks for [Audience]")
2. Meta description: 150-160 character summary for search engines
3. Write 5 main sections with H2 headings
4. For each of 5 products, write: name, price range, key features (3-4 bullets), pros, cons, and a verdict
5. Include a comparison table at the end
6. Tone: Helpful, authoritative, like a knowledgeable friend recommending products
7. Include calls-to-action like "Check price on Amazon" naturally in the text
{products_context}

Return as JSON with this exact structure:
{{
    "title": "string",
    "meta_description": "string (150-160 chars)",
    "sections": [
        {{"heading": "string", "content": "string (200-300 words)"}}
    ],
    "products": [
        {{
            "name": "string",
            "price": "string (e.g., '$29.99')",
            "features": ["string", "string", "string"],
            "pros": ["string", "string"],
            "cons": ["string"],
            "verdict": "string (50-100 words)",
            "rating": 4.5,
            "amazon_search": "string (search query for Amazon)"
        }}
    ]
}}"""

        result = await self.llm.generate(prompt, max_tokens=4000, temperature=0.7)

        if result["status"] != "success":
            return {"status": "failed", "error": f"Content generation failed: {result.get('error', 'Unknown')}"}

        try:
            # Parse JSON from LLM response
            raw = result["output"]
            # Find JSON block in the response
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                review = json.loads(json_match.group())
            else:
                review = json.loads(raw)

            return {
                "status": "success",
                "review": review,
                "raw_content": raw,
                "model": result["model"],
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review JSON: {e}")
            return {"status": "failed", "error": f"Content parsing failed: {str(e)}"}

    def _generate_html(
        self,
        title: str,
        slug: str,
        meta_description: str,
        sections: List[Dict],
        products: List[Dict],
        affiliate_tag: str,
        product_type: str,
    ) -> str:
        """Generate complete HTML page for the review"""

        # Build sections HTML
        sections_html = ""
        for section in sections:
            sections_html += f"""
            <section class="review-section">
                <h2>{section.get('heading', '')}</h2>
                <div class="section-content">{section.get('content', '')}</div>
            </section>"""

        # Build products HTML
        products_html = ""
        for i, product in enumerate(products):
            features_list = "".join([
                f"<li>{feature}</li>" for feature in product.get("features", [])
            ])
            pros_list = "".join([
                f'<li class="pro">✓ {pro}</li>' for pro in product.get("pros", [])
            ])
            cons_list = "".join([
                f'<li class="con">✗ {con}</li>' for con in product.get("cons", [])
            ])

            # Generate Amazon affiliate link
            amazon_query = product.get("amazon_search", product.get("name", "")).replace(" ", "+")
            affiliate_url = f"https://www.amazon.com/s?k={amazon_query}&tag={affiliate_tag}"

            rating = product.get("rating", 4.5)
            stars = "★" * int(rating) + ("½" if rating % 1 else "") + "☆" * (5 - int(rating) - (1 if rating % 1 else 0))

            products_html += f"""
            <div class="product-card">
                <div class="product-header">
                    <h3 class="product-name">{product.get('name', 'Product')}</h3>
                    <div class="product-rating">
                        <span class="stars">{stars}</span>
                        <span class="rating-number">{rating}/5</span>
                    </div>
                    <div class="product-price">{product.get('price', 'Check price')}</div>
                </div>

                <div class="product-features">
                    <h4>Key Features:</h4>
                    <ul class="features">{features_list}</ul>
                </div>

                <div class="product-pros-cons">
                    <div class="pros">
                        <h4>Pros:</h4>
                        <ul>{pros_list}</ul>
                    </div>
                    <div class="cons">
                        <h4>Cons:</h4>
                        <ul>{cons_list}</ul>
                    </div>
                </div>

                <div class="product-verdict">
                    <h4>Verdict:</h4>
                    <p>{product.get('verdict', '')}</p>
                </div>

                <a href="{affiliate_url}" class="buy-button" target="_blank" rel="noopener">
                    Check Price on Amazon →
                </a>
            </div>"""

        # Build comparison table
        table_rows = ""
        for product in products:
            features = ", ".join(product.get("features", [])[:2])
            table_rows += f"""
                <tr>
                    <td>{product.get('name', '')}</td>
                    <td>{product.get('price', '')}</td>
                    <td>{product.get('rating', 4.5)}/5</td>
                    <td>{features}</td>
                </tr>"""

        current_date = datetime.now().strftime("%B %d, %Y")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{meta_description}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:type" content="article">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://ai-survival.surge.sh/reviews/{slug}.html">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #3b82f6;
            --accent-hover: #60a5fa;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --border: #334155;
        }}

        @media (prefers-color-scheme: light) {{
            :root {{
                --bg-primary: #f8fafc;
                --bg-secondary: #ffffff;
                --bg-card: #ffffff;
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --accent: #2563eb;
                --accent-hover: #3b82f6;
                --border: #e2e8f0;
            }}
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.7;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}

        header {{
            border-bottom: 1px solid var(--border);
            padding-bottom: 2rem;
            margin-bottom: 2rem;
        }}

        h1 {{
            font-size: 2.25rem;
            line-height: 1.2;
            margin-bottom: 1rem;
        }}

        .meta {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        .review-section {{
            margin-bottom: 2.5rem;
        }}

        .review-section h2 {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: var(--accent);
        }}

        .section-content {{
            color: var(--text-secondary);
        }}

        .product-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .product-header {{
            margin-bottom: 1rem;
        }}

        .product-name {{
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }}

        .product-rating {{
            margin-bottom: 0.5rem;
        }}

        .stars {{
            color: var(--warning);
            font-size: 1.1rem;
        }}

        .rating-number {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-left: 0.5rem;
        }}

        .product-price {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--success);
        }}

        .product-features {{
            margin: 1rem 0;
        }}

        .product-features h4, .pros h4, .cons h4, .product-verdict h4 {{
            font-size: 0.95rem;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }}

        .features {{
            list-style: disc;
            padding-left: 1.5rem;
            color: var(--text-secondary);
        }}

        .product-pros-cons {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin: 1rem 0;
        }}

        @media (max-width: 600px) {{
            .product-pros-cons {{
                grid-template-columns: 1fr;
            }}
        }}

        .pros ul, .cons ul {{
            list-style: none;
            padding: 0;
        }}

        .pro {{
            color: var(--success);
            margin-bottom: 0.25rem;
        }}

        .con {{
            color: var(--danger);
            margin-bottom: 0.25rem;
        }}

        .product-verdict {{
            margin: 1rem 0;
            padding: 1rem;
            background: var(--bg-primary);
            border-radius: 8px;
        }}

        .product-verdict p {{
            color: var(--text-secondary);
        }}

        .buy-button {{
            display: block;
            width: 100%;
            padding: 1rem;
            background: var(--accent);
            color: white;
            text-align: center;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: background 0.2s;
        }}

        .buy-button:hover {{
            background: var(--accent-hover);
        }}

        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2rem 0;
            overflow-x: auto;
        }}

        .comparison-table th, .comparison-table td {{
            padding: 0.75rem 1rem;
            border: 1px solid var(--border);
            text-align: left;
        }}

        .comparison-table th {{
            background: var(--bg-secondary);
            font-weight: 600;
        }}

        .comparison-table tr:hover {{
            background: var(--bg-secondary);
        }}

        footer {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-align: center;
        }}

        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <article class="container">
        <header>
            <h1>{title}</h1>
            <div class="meta">
                Last updated: {current_date} | Affiliate Disclosure: We earn from qualifying purchases
            </div>
        </header>

        <div class="review-content">
            {sections_html}
        </div>

        <div class="products-section">
            <h2>Our Top Picks</h2>
            {products_html}
        </div>

        <section class="comparison">
            <h2>Quick Comparison</h2>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Price</th>
                        <th>Rating</th>
                        <th>Key Features</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </section>

        <footer>
            <p>Affiliate Disclosure: As an Amazon Associate, we earn from qualifying purchases.
            Prices and availability are subject to change.</p>
            <p>Built by <a href="https://ai-survival.surge.sh">AI Survival System</a> —
            an autonomous AI business powered by multi-agent intelligence.</p>
        </footer>
    </article>
</body>
</html>"""

        return html

    def _update_sitemap(self, slug: str, topic: str):
        """Add the new post to sitemap.xml (idempotent — never duplicates a slug)"""
        sitemap_path = os.path.join(DOCS_DIR, "sitemap.xml")
        loc = f"https://ai-survival.surge.sh/reviews/{slug}.html"
        today = datetime.now().strftime('%Y-%m-%d')
        url_entry = f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>"""

        if os.path.exists(sitemap_path):
            with open(sitemap_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Skip if this post is already listed (republishing the same slug must not add a second entry)
            if f"<loc>{loc}</loc>" in content:
                return
            # Insert before </urlset>
            content = content.replace("</urlset>", url_entry + "\n</urlset>")
            with open(sitemap_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_entry}
</urlset>"""
            with open(sitemap_path, "w", encoding="utf-8") as f:
                f.write(sitemap)

    async def _generate_tweet(self, topic: str, title: str, url: str) -> str:
        """Generate a tweet-length summary for social sharing"""
        prompt = f"""Write a tweet (max 280 characters) about this product review article:
Title: {title}
URL: {url}

Include 2-3 relevant hashtags. Make it engaging and click-worthy. Include the URL."""

        result = await self.llm.generate(prompt, max_tokens=200, temperature=0.8)

        if result["status"] == "success":
            tweet = result["output"].strip()
            # Ensure it includes the URL
            if url not in tweet:
                tweet = f"{tweet[:250]}\n\n{url}"
            return tweet[:280]

        # Fallback tweet
        return f"🔍 {title}\n\nCheck out our latest review: {url}\n\n#TechReview #BestBuys"


# Register the tool
tool_registry.register(BlogPublisherTool())
