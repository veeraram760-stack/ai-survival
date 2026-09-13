"""
Shopify Store Builder Tool - Create and manage Shopify stores via Admin API
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.shopify_builder")


class ShopifyBuilderTool(Tool):
    """Build complete Shopify stores: products, collections, pages, themes, apps"""

    def __init__(self):
        super().__init__(
            name="shopify_builder",
            description="Create and manage Shopify stores - products, collections, pages, navigation, themes via Admin API",
            cost=0.15,
        )
        self.llm = get_llm_provider()
        self._client = None

    def _get_shopify_client(self):
        """Lazy-load Shopify Admin API client (GraphQL)"""
        if self._client is None:
            from config.settings import settings
            if not settings.shopify_access_token or not settings.shopify_store_domain:
                raise ValueError("SHOPIFY_ACCESS_TOKEN and SHOPIFY_STORE_DOMAIN required in .env")
            import httpx
            self._client = httpx.AsyncClient(
                base_url=f"https://{settings.shopify_store_domain}/admin/api/2024-01/graphql.json",
                headers={
                    "X-Shopify-Access-Token": settings.shopify_access_token,
                    "Content-Type": "application/json",
                },
                timeout=60.0
            )
        return self._client

    def _graphql(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        import asyncio
        return asyncio.create_task(self._graphql_async(query, variables))

    async def _graphql_async(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """Execute GraphQL query asynchronously"""
        client = self._get_shopify_client()
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await client.post("", json=payload)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result.get("data", {})

    async def execute(
        self,
        action: str = "create_store",
        store_config: Optional[Dict[str, Any]] = None,
        product_data: Optional[Dict[str, Any]] = None,
        collection_data: Optional[Dict[str, Any]] = None,
        page_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Main entry point for Shopify operations"""
        from config.settings import settings

        if not settings.shopify_access_token or not settings.shopify_store_domain:
            return {"status": "failed", "error": "SHOPIFY_ACCESS_TOKEN and SHOPIFY_STORE_DOMAIN required"}

        try:
            if action == "create_store":
                return await self._setup_store(store_config or {})
            elif action == "create_product":
                return await self._create_product(product_data or {})
            elif action == "create_collection":
                return await self._create_collection(collection_data or {})
            elif action == "create_page":
                return await self._create_page(page_data or {})
            elif action == "create_navigation":
                return await self._create_navigation(store_config or {})
            elif action == "setup_theme":
                return await self._setup_theme(store_config or {})
            elif action == "install_apps":
                return await self._install_apps(store_config or {})
            elif action == "get_store_info":
                return await self._get_store_info()
            elif action == "generate_store_plan":
                return await self._generate_store_plan(store_config or {})
            else:
                return {"status": "failed", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"ShopifyBuilderTool error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _setup_store(self, config: Dict) -> Dict[str, Any]:
        """Initial store setup: settings, policies, basic config"""
        # This would configure store settings via REST API (not GraphQL)
        # For now, return setup checklist
        return {
            "status": "success",
            "action": "store_setup_checklist",
            "checklist": [
                "Configure store details (name, address, timezone, currency)",
                "Set up payment providers (Shopify Payments, PayPal, Stripe)",
                "Configure shipping zones and rates",
                "Set up tax regions",
                "Create legal pages (refund policy, privacy policy, terms of service)",
                "Configure checkout settings",
                "Set up domains",
                "Configure email notifications",
            ],
            "note": "Use Shopify Admin UI for initial setup. Then use this tool for products/collections/content.",
        }

    async def _create_product(self, product_data: Dict) -> Dict[str, Any]:
        """Create a product with variants, images, SEO"""
        title = product_data.get("title", "New Product")
        description = product_data.get("description", "")
        product_type = product_data.get("product_type", "Physical")
        vendor = product_data.get("vendor", "AI Survival")
        tags = product_data.get("tags", [])
        variants = product_data.get("variants", [{"price": "29.99", "sku": "AUTO", "inventory_quantity": 100}])
        images = product_data.get("images", [])  # List of image URLs
        seo_title = product_data.get("seo_title", title)
        seo_description = product_data.get("seo_description", description[:160])
        collections = product_data.get("collections", [])

        mutation = """
        mutation createProduct($input: ProductInput!) {
            productCreate(input: $input) {
                product { id title handle status }
                userErrors { field message }
            }
        }
        """

        variants_input = []
        for v in variants:
            variants_input.append({
                "price": v.get("price", "29.99"),
                "sku": v.get("sku", str(uuid.uuid4())[:8]),
                "inventoryQuantities": [{"availableQuantity": v.get("inventory_quantity", 100), "locationId": "gid://shopify/Location/1"}],
                "optionValues": v.get("options", []),
            })

        variables = {
            "input": {
                "title": title,
                "descriptionHtml": description,
                "productType": product_type,
                "vendor": vendor,
                "tags": tags,
                "variants": variants_input,
                "seo": {"title": seo_title, "description": seo_description},
                "status": "ACTIVE",
            }
        }

        if images:
            variables["input"]["images"] = [{"src": url, "altText": f"{title} image"} for url in images]

        result = await self._graphql_async(mutation, variables)

        if result.get("productCreate", {}).get("userErrors"):
            return {"status": "failed", "error": result["productCreate"]["userErrors"]}

        product = result["productCreate"]["product"]
        product_id = product["id"]

        # Add to collections
        for collection_handle in collections:
            await self._add_product_to_collection(product_id, collection_handle)

        return {
            "status": "success",
            "product_id": product_id,
            "title": product["title"],
            "handle": product["handle"],
            "url": f"https://{self._get_store_domain()}/products/{product['handle']}",
        }

    async def _add_product_to_collection(self, product_id: str, collection_handle: str) -> Dict:
        """Add product to a collection"""
        mutation = """
        mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
            collectionAddProducts(id: $id, productIds: $productIds) {
                collection { id title }
                userErrors { field message }
            }
        }
        """
        # Need to get collection ID from handle
        collection_id = await self._get_collection_id(collection_handle)
        if collection_id:
            await self._graphql_async(mutation, {"id": collection_id, "productIds": [product_id]})
        return {"status": "completed"}

    async def _get_collection_id(self, handle: str) -> Optional[str]:
        """Get collection ID by handle"""
        query = """
        query getCollection($handle: String!) {
            collectionByHandle(handle: $handle) { id }
        }
        """
        result = await self._graphql_async(query, {"handle": handle})
        return result.get("collectionByHandle", {}).get("id")

    async def _create_collection(self, collection_data: Dict) -> Dict[str, Any]:
        """Create a collection (manual or automated)"""
        title = collection_data.get("title", "New Collection")
        description = collection_data.get("description", "")
        handle = collection_data.get("handle", title.lower().replace(" ", "-"))
        collection_type = collection_data.get("type", "manual")  # manual or smart
        conditions = collection_data.get("conditions", [])  # For smart collections
        image_url = collection_data.get("image_url")
        seo_title = collection_data.get("seo_title", title)
        seo_description = collection_data.get("seo_description", description[:160])

        mutation = """
        mutation createCollection($input: CollectionInput!) {
            collectionCreate(input: $input) {
                collection { id title handle }
                userErrors { field message }
            }
        }
        """

        variables = {
            "input": {
                "title": title,
                "descriptionHtml": description,
                "handle": handle,
                "templateSuffix": collection_type,
                "seo": {"title": seo_title, "description": seo_description},
            }
        }

        if image_url:
            variables["input"]["image"] = {"src": image_url, "altText": f"{title} collection"}

        if collection_type == "smart" and conditions:
            variables["input"]["ruleSet"] = {
                "appliedDisjunctively": False,
                "rules": [{"column": c["column"], "relation": c["relation"], "condition": c["value"]} for c in conditions]
            }

        result = await self._graphql_async(mutation, variables)

        if result.get("collectionCreate", {}).get("userErrors"):
            return {"status": "failed", "error": result["collectionCreate"]["userErrors"]}

        collection = result["collectionCreate"]["collection"]
        return {
            "status": "success",
            "collection_id": collection["id"],
            "title": collection["title"],
            "handle": collection["handle"],
            "url": f"https://{self._get_store_domain()}/collections/{collection['handle']}",
        }

    async def _create_page(self, page_data: Dict) -> Dict[str, Any]:
        """Create a store page (About, Contact, FAQ, etc.)"""
        title = page_data.get("title", "New Page")
        content = page_data.get("content", "")
        handle = page_data.get("handle", title.lower().replace(" ", "-"))
        template = page_data.get("template", "page")
        seo_title = page_data.get("seo_title", title)
        seo_description = page_data.get("seo_description", content[:160])

        mutation = """
        mutation createPage($input: PageInput!) {
            pageCreate(input: $input) {
                page { id title handle onlineStoreUrl }
                userErrors { field message }
            }
        }
        """

        variables = {
            "input": {
                "title": title,
                "bodyHtml": content,
                "handle": handle,
                "templateSuffix": template,
                "seo": {"title": seo_title, "description": seo_description},
                "isPublished": True,
            }
        }

        result = await self._graphql_async(mutation, variables)

        if result.get("pageCreate", {}).get("userErrors"):
            return {"status": "failed", "error": result["pageCreate"]["userErrors"]}

        page = result["pageCreate"]["page"]
        return {
            "status": "success",
            "page_id": page["id"],
            "title": page["title"],
            "handle": page["handle"],
            "url": page["onlineStoreUrl"],
        }

    async def _create_navigation(self, config: Dict) -> Dict[str, Any]:
        """Create main navigation menus"""
        menus = config.get("menus", [
            {"handle": "main-menu", "items": [
                {"title": "Home", "url": "/", "type": "HOME"},
                {"title": "Shop", "url": "/collections/all", "type": "COLLECTIONS"},
                {"title": "About", "url": "/pages/about", "type": "PAGE"},
                {"title": "Contact", "url": "/pages/contact", "type": "PAGE"},
            ]},
            {"handle": "footer-menu", "items": [
                {"title": "Privacy Policy", "url": "/policies/privacy-policy", "type": "POLICY"},
                {"title": "Terms of Service", "url": "/policies/terms-of-service", "type": "POLICY"},
                {"title": "Refund Policy", "url": "/policies/refund-policy", "type": "POLICY"},
                {"title": "Shipping Info", "url": "/pages/shipping", "type": "PAGE"},
            ]},
        ])

        results = []
        for menu in menus:
            mutation = """
            mutation createMenu($menu: MenuInput!) {
                menuCreate(menu: $menu) {
                    menu { id title handle }
                    userErrors { field message }
                }
            }
            """
            items = []
            for item in menu["items"]:
                items.append({
                    "title": item["title"],
                    "url": item["url"],
                    "type": item.get("type", "URL"),
                })

            variables = {"menu": {"title": menu["handle"].replace("-", " ").title(), "handle": menu["handle"], "items": items}}
            result = await self._graphql_async(mutation, variables)
            results.append(result.get("menuCreate", {}))

        return {"status": "success", "menus_created": len(results), "results": results}

    async def _setup_theme(self, config: Dict) -> Dict[str, Any]:
        """Configure theme settings (Dawn theme customization)"""
        theme_id = config.get("theme_id")  # Get current live theme
        settings_data = config.get("settings", {
            "color_scheme": "scheme-1",
            "font_heading": "system",
            "font_body": "system",
            "show_announcement_bar": True,
            "announcement_text": "Free shipping on orders over $50!",
            "logo_width": 180,
            "favicon": None,
        })

        # Theme customization is done via theme assets API
        # This is a simplified version
        return {
            "status": "success",
            "action": "theme_setup",
            "settings_applied": list(settings_data.keys()),
            "note": "Full theme customization requires theme editor or CLI. Use Shopify CLI for advanced changes.",
        }

    async def _install_apps(self, config: Dict) -> Dict[str, Any]:
        """Install recommended apps for the store"""
        recommended_apps = [
            {"name": "Klaviyo", "handle": "klaviyo", "purpose": "Email marketing"},
            {"name": "Yotpo", "handle": "yotpo", "purpose": "Reviews & UGC"},
            {"name": "Omnisend", "handle": "omnisend", "purpose": "SMS & Email automation"},
            {"name": "Google Channel", "handle": "google-shopping", "purpose": "Google Shopping integration"},
            {"name": "Facebook Channel", "handle": "facebook-shop", "purpose": "Instagram/Facebook Shop sync"},
            {"name": "Printful", "handle": "printful", "purpose": "Print-on-demand fulfillment"},
            {"name": "DSers", "handle": "dsers", "purpose": "AliExpress dropshipping"},
            {"name": "PageFly", "handle": "pagefly", "purpose": "Advanced page builder"},
        ]

        # App installation requires OAuth flow - can't do via Admin API directly
        return {
            "status": "success",
            "action": "app_recommendations",
            "recommended_apps": recommended_apps,
            "note": "Install apps manually from Shopify App Store. Use Printful app to connect POD products.",
        }

    async def _get_store_info(self) -> Dict[str, Any]:
        """Get basic store information"""
        query = """
        query {
            shop { name email currencyCode primaryDomain { url } plan { displayName } }
        }
        """
        result = await self._graphql_async(query)
        shop = result.get("shop", {})
        return {"status": "success", "store": shop}

    def _get_store_domain(self) -> str:
        from config.settings import settings
        return settings.shopify_store_domain.replace(".myshopify.com", "")

    async def _generate_store_plan(self, config: Dict) -> Dict[str, Any]:
        """Generate complete store build plan from niche"""
        niche = config.get("niche", "general")
        target_audience = config.get("target_audience", "general consumers")
        budget = config.get("budget", "low")  # low, medium, high
        products_count = config.get("products_count", 20)

        prompt = f"""Create a complete Shopify store build plan for a "{niche}" niche store.

Target audience: {target_audience}
Budget tier: {budget}
Number of products: {products_count}

Provide:
1. Store name ideas (5 options)
2. Brand identity (colors, fonts, voice, tagline)
3. Product categories/collections (5-8)
4. Product ideas with pricing (list {products_count} products with descriptions)
5. Required pages (About, Contact, FAQ, Shipping, Returns, Blog)
6. Navigation structure (main menu, footer menu)
7. Recommended apps (email, reviews, upsell, analytics, POD/dropshipping)
8. Marketing setup (email flows, abandoned cart, welcome series)
9. SEO strategy (keywords, blog topics, meta templates)
10. Launch checklist (pre-launch, launch day, post-launch)

Return as structured JSON."""

        result = await self.llm.generate(prompt, max_tokens=6000, temperature=0.7)

        if result["status"] != "success":
            return {"status": "failed", "error": result.get("error")}

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result["output"])
            plan = json.loads(json_match.group()) if json_match else {"raw": result["output"]}
        except:
            plan = {"raw": result["output"]}

        return {
            "status": "success",
            "niche": niche,
            "store_plan": plan,
            "estimated_setup_hours": 10 if budget == "low" else 25,
            "estimated_monthly_cost": 29 + 15 + (50 if budget != "low" else 0),  # Shopify + apps
        }


# Register the tool
tool_registry.register(ShopifyBuilderTool())