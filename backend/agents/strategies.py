"""
Revenue Strategies - Pre-built agent strategies that wire tools together for specific revenue models
"""
from typing import Dict, Any, List
from backend.tools import tool_registry


class RevenueStrategy:
    """Base class for revenue-generating agent strategies"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.required_tools: List[str] = []
        self.required_env: List[str] = []

    async def execute(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the strategy - override in subclasses"""
        raise NotImplementedError


class AffiliateContentStrategy(RevenueStrategy):
    """Generate affiliate content, publish to blog + social, track conversions"""

    def __init__(self):
        super().__init__(
            name="affiliate_content",
            description="Create SEO product reviews, publish to blog + social media, track affiliate commissions"
        )
        self.required_tools = ["web_search", "blog_publisher", "social_publisher", "affiliate_link", "track_conversions"]
        self.required_env = ["AMAZON_ASSOCIATE_TAG", "META_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]

    async def execute(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        niche = context.get("niche", "tech gadgets")
        budget = context.get("budget", 0.50)  # Max spend per cycle

        results = {"actions": [], "revenue": 0.0, "expenses": 0.0}

        # 1. Research trending products in niche
        search_result = await tool_registry.execute("web_search", query=f"best {niche} 2024 reviews", count=10)
        results["actions"].append({"step": "research", "result": search_result})

        if search_result.get("status") != "success":
            return {"status": "failed", "error": "Research failed", **results}

        # 2. Generate blog review post
        topic = f"Best {niche.title()} 2024"
        blog_result = await tool_registry.execute("blog_publisher", topic=topic, product_type=niche)
        results["actions"].append({"step": "blog_publish", "result": blog_result})

        # 3. Create affiliate links for mentioned products
        # (blog_publisher already embeds Amazon links with associate tag)

        # 4. Publish to social media (Instagram + Facebook)
        if blog_result.get("status") == "success":
            blog_url = blog_result.get("blog_post", {}).get("url")
            tweet = blog_result.get("tweet_content", "")

            social_result = await tool_registry.execute("social_publisher", platform="instagram", action="publish_post", content_data={
                "caption": tweet,
                "hashtags": [f"#{niche}", "#review", "#bestbuys", "#affiliate"],
            })
            results["actions"].append({"step": "social_publish", "result": social_result})

            # Also post to Facebook
            fb_result = await tool_registry.execute("social_publisher", platform="facebook", action="publish_post", content_data={
                "caption": tweet,
            })
            results["actions"].append({"step": "facebook_publish", "result": fb_result})

        # 5. Track conversions from affiliate networks
        track_result = await tool_registry.execute("track_conversions", network="all")
        results["actions"].append({"step": "track_conversions", "result": track_result})

        # Calculate revenue from tracked commissions
        if track_result.get("status") == "success":
            networks = track_result.get("networks", {})
            for net_data in networks.values():
                if isinstance(net_data, dict):
                    commissions = net_data.get("commissions", [])
                    for c in commissions:
                        results["revenue"] += float(c.get("commission", 0))

        return {"status": "success", **results}


class DigitalProductStrategy(RevenueStrategy):
    """Create and sell digital products (guides, courses, templates) via Stripe/Gumroad"""

    def __init__(self):
        super().__init__(
            name="digital_products",
            description="Create digital products, list on Stripe/Gumroad, drive traffic via content + email"
        )
        self.required_tools = ["stripe_products", "gumroad", "blog_publisher", "social_publisher", "email_send", "template_content"]
        self.required_env = ["STRIPE_SECRET_KEY", "GUMROAD_ACCESS_TOKEN", "SMTP_HOST"]

    async def execute(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        topic = context.get("topic", "AI productivity")
        product_type = context.get("product_type", "guide")  # guide, course, template
        price_cents = context.get("price_cents", 2900)

        results = {"actions": [], "revenue": 0.0, "expenses": 0.0}

        # 1. Create product on Stripe with AI-generated content
        stripe_result = await tool_registry.execute("stripe_products", action="create_product", product_data={
            "name": f"{topic.title()} {product_type.title()}",
            "topic": topic,
            "price_cents": price_cents,
            "type": product_type,
            "generate_content": True,
        })
        results["actions"].append({"step": "create_stripe_product", "result": stripe_result})

        # 2. Also create on Gumroad for additional reach
        gumroad_result = await tool_registry.execute("gumroad", action="create_product", platform="gumroad", product_data={
            "name": f"{topic.title()} {product_type.title()}",
            "description": f"Complete {product_type} on {topic}",
            "price_cents": price_cents,
            "type": product_type,
            "generate_content": True,
        })
        results["actions"].append({"step": "create_gumroad_product", "result": gumroad_result})

        # 3. Create blog post as lead magnet / SEO content
        blog_result = await tool_registry.execute("blog_publisher", topic=f"How to {topic}", product_type="guide")
        results["actions"].append({"step": "blog_lead_magnet", "result": blog_result})

        # 4. Social media promotion
        if stripe_result.get("status") == "success":
            checkout = await tool_registry.execute("stripe_products", action="create_checkout_session",
                product_id=stripe_result["product"]["id"])
            checkout_url = checkout.get("checkout_session", {}).get("url", "")

            social_result = await tool_registry.execute("social_publisher", platform="instagram", action="publish_reel", content_data={
                "caption": f"Just launched my new {product_type} on {topic}! 🚀\n\nLink in bio to get it.",
                "hashtags": [f"#{topic.replace(' ', '')}", "#digitalproducts", "#passiveincome"],
                "affiliate_url": checkout_url,
            })
            results["actions"].append({"step": "social_promo", "result": social_result})

        # 5. Email outreach to leads
        email_result = await tool_registry.execute("email_send", subject=f"New {product_type}: {topic.title()}",
            body=f"Hey! I just created a new {product_type} on {topic}. Check it out: {checkout_url}")
        results["actions"].append({"step": "email_promo", "result": email_result})

        return {"status": "success", **results}


class PrintOnDemandStrategy(RevenueStrategy):
    """Design and sell print-on-demand merchandise via Printful/Printify"""

    def __init__(self):
        super().__init__(
            name="print_on_demand",
            description="Generate AI designs, create POD products, list on Printful/Printify, promote via social"
        )
        self.required_tools = ["print_on_demand", "social_publisher", "web_search"]
        self.required_env = ["PRINTFUL_API_KEY", "PRINTIFY_API_KEY", "PRINTIFY_SHOP_ID", "META_ACCESS_TOKEN"]

    async def execute(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        niche = context.get("niche", "motivation")
        product_types = context.get("product_types", ["t-shirt", "mug", "poster"])
        style = context.get("style", "minimalist")

        results = {"actions": [], "revenue": 0.0, "expenses": 0.0}

        for product_type in product_types:
            # 1. Generate design concept
            design_result = await tool_registry.execute("print_on_demand", action="create_design", design_data={
                "niche": niche,
                "product_type": product_type,
                "style": style,
                "topic": f"{niche} quotes",
            })
            results["actions"].append({"step": f"design_{product_type}", "result": design_result})

            if design_result.get("status") != "success":
                continue

            # 2. Create product on Printful
            printful_result = await tool_registry.execute("print_on_demand", action="create_product",
                platform="printful", design_data=design_result, listing_data={
                    "name": f"{niche.title()} {product_type.title()}",
                    "price": 29.99 if product_type == "t-shirt" else 19.99,
                })
            results["actions"].append({"step": f"printful_{product_type}", "result": printful_result})

            # 3. Create product on Printify
            printify_result = await tool_registry.execute("print_on_demand", action="create_product",
                platform="printify", design_data=design_result, listing_data={
                    "name": f"{niche.title()} {product_type.title()}",
                    "price": 29.99 if product_type == "t-shirt" else 19.99,
                })
            results["actions"].append({"step": f"printify_{product_type}", "result": printify_result})

            # 4. Generate mockups for social media
            if printful_result.get("status") == "success":
                mockup_result = await tool_registry.execute("print_on_demand", action="generate_mockup",
                    platform="printful", product_id=printful_result.get("product_id"))
                results["actions"].append({"step": f"mockup_{product_type}", "result": mockup_result})

                # 5. Promote on social media
                social_result = await tool_registry.execute("social_publisher", platform="instagram", action="publish_post",
                    content_data={
                        "caption": f"New {product_type} design! {niche.title()} vibes 🎨",
                        "hashtags": [f"#{niche}", f"#{product_type}", "#printondemand", "#merch"],
                    })
                results["actions"].append({"step": f"social_{product_type}", "result": social_result})

        return {"status": "success", **results}


class ShopifyStoreStrategy(RevenueStrategy):
    """Build complete Shopify store with products, collections, pages"""

    def __init__(self):
        super().__init__(
            name="shopify_store",
            description="Build full Shopify store: niche research, products, collections, pages, navigation, apps"
        )
        self.required_tools = ["shopify_builder", "print_on_demand", "stripe_products", "social_publisher", "blog_publisher"]
        self.required_env = ["SHOPIFY_ACCESS_TOKEN", "SHOPIFY_STORE_DOMAIN", "PRINTFUL_API_KEY"]

    async def execute(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        niche = context.get("niche", "pet accessories")
        target_audience = context.get("target_audience", "dog owners")
        budget = context.get("budget", "medium")
        product_count = context.get("product_count", 15)

        results = {"actions": [], "revenue": 0.0, "expenses": 0.0}

        # 1. Generate complete store plan
        plan_result = await tool_registry.execute("shopify_builder", action="generate_store_plan", store_config={
            "niche": niche,
            "target_audience": target_audience,
            "budget": budget,
            "products_count": product_count,
        })
        results["actions"].append({"step": "store_plan", "result": plan_result})

        if plan_result.get("status") != "success":
            return {"status": "failed", "error": "Store planning failed", **results}

        plan = plan_result.get("store_plan", {})

        # 2. Create collections
        collections = plan.get("collections", [])
        for coll in collections[:5]:  # Limit to 5 collections
            coll_result = await tool_registry.execute("shopify_builder", action="create_collection", collection_data={
                "title": coll.get("name", "Collection"),
                "description": coll.get("description", ""),
                "handle": coll.get("handle", coll.get("name", "").lower().replace(" ", "-")),
                "type": "manual",
            })
            results["actions"].append({"step": f"collection_{coll.get('handle')}", "result": coll_result})

        # 3. Create products (mix of POD and digital)
        products = plan.get("products", [])
        for product in products[:product_count]:
            # Decide product type
            if product.get("type") == "pod" or "physical" in product.get("type", ""):
                # Create via POD
                pod_result = await tool_registry.execute("print_on_demand", action="create_design", design_data={
                    "niche": niche,
                    "product_type": product.get("product_type", "t-shirt"),
                    "topic": product.get("name", ""),
                })
                if pod_result.get("status") == "success":
                    # Create on Printful and sync to Shopify (would need Printful-Shopify connection)
                    results["actions"].append({"step": f"pod_product_{product.get('name')}", "result": "Design created - connect Printful to Shopify"})
            else:
                # Create digital product on Stripe
                stripe_result = await tool_registry.execute("stripe_products", action="create_product", product_data={
                    "name": product.get("name", "Digital Product"),
                    "topic": product.get("description", ""),
                    "price_cents": int(float(product.get("price", "29")) * 100),
                    "type": "digital_download",
                })
                results["actions"].append({"step": f"digital_product_{product.get('name')}", "result": stripe_result})

        # 4. Create essential pages
        pages = ["About Us", "Contact", "Shipping Info", "Returns", "FAQ"]
        for page_title in pages:
            page_result = await tool_registry.execute("shopify_builder", action="create_page", page_data={
                "title": page_title,
                "handle": page_title.lower().replace(" ", "-"),
                "content": f"<h2>{page_title}</h2><p>Content for {page_title} page. Customize in Shopify admin.</p>",
            })
            results["actions"].append({"step": f"page_{page_title.lower().replace(' ', '_')}", "result": page_result})

        # 5. Create navigation
        nav_result = await tool_registry.execute("shopify_builder", action="create_navigation", store_config={})
        results["actions"].append({"step": "navigation", "result": nav_result})

        # 6. Install recommended apps
        apps_result = await tool_registry.execute("shopify_builder", action="install_apps", store_config={})
        results["actions"].append({"step": "apps", "result": apps_result})

        return {"status": "success", **results}


class MultiChannelStrategy(RevenueStrategy):
    """Orchestrate multiple revenue channels simultaneously"""

    def __init__(self):
        super().__init__(
            name="multi_channel",
            description="Run affiliate + digital products + POD + Shopify in parallel"
        )
        self.required_tools = ["affiliate_content", "digital_products", "print_on_demand", "shopify_store"]
        self.required_env = ["ALL"]  # Requires most API keys

        # Sub-strategies
        self.affiliate = AffiliateContentStrategy()
        self.digital = DigitalProductStrategy()
        self.pod = PrintOnDemandStrategy()
        self.shopify = ShopifyStoreStrategy()

    async def execute(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        # Run all sub-strategies in parallel
        import asyncio

        niche = context.get("niche", "tech")
        results = {"channels": {}, "total_revenue": 0.0, "total_expenses": 0.0}

        # Execute each channel
        tasks = [
            self.affiliate.execute(agent, {"niche": niche, "budget": 0.30}),
            self.digital.execute(agent, {"topic": f"{niche} mastery", "product_type": "guide", "price_cents": 4900}),
            self.pod.execute(agent, {"niche": niche, "product_types": ["t-shirt", "mug"], "style": "minimalist"}),
            self.shopify.execute(agent, {"niche": niche, "target_audience": f"{niche} enthusiasts", "budget": "medium"}),
        ]

        channel_results = await asyncio.gather(*tasks, return_exceptions=True)

        channel_names = ["affiliate", "digital_products", "print_on_demand", "shopify_store"]
        for name, result in zip(channel_names, channel_results):
            if isinstance(result, Exception):
                results["channels"][name] = {"status": "error", "error": str(result)}
            else:
                results["channels"][name] = result
                results["total_revenue"] += result.get("revenue", 0)
                results["total_expenses"] += result.get("expenses", 0)

        return {"status": "success", **results}


# Registry of all strategies
STRATEGY_REGISTRY = {
    "affiliate_content": AffiliateContentStrategy(),
    "digital_products": DigitalProductStrategy(),
    "print_on_demand": PrintOnDemandStrategy(),
    "shopify_store": ShopifyStoreStrategy(),
    "multi_channel": MultiChannelStrategy(),
}


def get_strategy(name: str) -> RevenueStrategy:
    """Get a strategy by name"""
    return STRATEGY_REGISTRY.get(name)


def list_strategies() -> Dict[str, Dict[str, Any]]:
    """List all available strategies"""
    return {
        name: {
            "name": s.name,
            "description": s.description,
            "required_tools": s.required_tools,
            "required_env": s.required_env,
        }
        for name, s in STRATEGY_REGISTRY.items()
    }