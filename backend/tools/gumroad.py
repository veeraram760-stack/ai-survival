"""
Gumroad/LemonSqueezy Tool - Alternative digital product platforms
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.gumroad")


class GumroadTool(Tool):
    """Create and sell digital products on Gumroad and LemonSqueezy"""

    def __init__(self):
        super().__init__(
            name="gumroad",
            description="Create digital products on Gumroad and LemonSqueezy, manage licenses, and track sales",
            cost=0.05,
        )
        self.llm = get_llm_provider()
        self._gumroad = None
        self._lemonsqueezy = None

    def _get_gumroad_client(self):
        """Lazy-load Gumroad client"""
        if self._gumroad is None:
            from config.settings import settings
            if not settings.gumroad_access_token:
                raise ValueError("GUMROAD_ACCESS_TOKEN not configured in .env")
            import httpx
            self._gumroad = httpx.AsyncClient(
                base_url="https://api.gumroad.com/v2",
                headers={"Authorization": f"Bearer {settings.gumroad_access_token}"},
                timeout=30.0
            )
        return self._gumroad

    def _get_lemonsqueezy_client(self):
        """Lazy-load LemonSqueezy client"""
        if self._lemonsqueezy is None:
            from config.settings import settings
            if not settings.lemonsqueezy_api_key:
                raise ValueError("LEMONSQUEEZY_API_KEY not configured in .env")
            import httpx
            self._lemonsqueezy = httpx.AsyncClient(
                base_url="https://api.lemonsqueezy.com/v1",
                headers={
                    "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
                    "Accept": "application/vnd.api+json",
                    "Content-Type": "application/vnd.api+json",
                },
                timeout=30.0
            )
        return self._lemonsqueezy

    async def execute(
        self,
        action: str = "create_product",
        platform: str = "gumroad",  # or "lemonsqueezy"
        product_data: Optional[Dict[str, Any]] = None,
        product_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Main entry point"""
        from config.settings import settings

        if platform == "gumroad" and not settings.gumroad_access_token:
            return {"status": "failed", "error": "GUMROAD_ACCESS_TOKEN not configured"}
        if platform == "lemonsqueezy" and not settings.lemonsqueezy_api_key:
            return {"status": "failed", "error": "LEMONSQUEEZY_API_KEY not configured"}

        try:
            if action == "create_product":
                return await self._create_product(platform, product_data or {})
            elif action == "update_product":
                return await self._update_product(platform, product_id, product_data or {})
            elif action == "create_license":
                return await self._create_license(platform, product_id, product_data or {})
            elif action == "list_products":
                return await self._list_products(platform)
            elif action == "get_sales":
                return await self._get_sales(platform, product_id)
            elif action == "create_coupon":
                return await self._create_coupon(platform, product_id, product_data or {})
            elif action == "setup_webhook":
                return await self._setup_webhook(platform)
            else:
                return {"status": "failed", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"GumroadTool error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _create_product(self, platform: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a digital product on Gumroad or LemonSqueezy"""
        name = product_data.get("name", "Digital Product")
        description = product_data.get("description", "")
        price_cents = product_data.get("price_cents", 2900)
        currency = product_data.get("currency", "usd")
        product_type = product_data.get("type", "digital")  # digital, course, membership
        files = product_data.get("files", [])  # List of file URLs or paths
        tags = product_data.get("tags", [])
        custom_fields = product_data.get("custom_fields", [])
        generate_content = product_data.get("generate_content", True)

        # Generate digital content if requested
        if generate_content and not files:
            content_result = await self._generate_digital_content(product_data)
            if content_result.get("status") == "success":
                files = [content_result["download_path"]]

        if platform == "gumroad":
            return await self._create_gumroad_product(name, description, price_cents, currency, files, tags, custom_fields, product_type)
        else:
            return await self._create_lemonsqueezy_product(name, description, price_cents, currency, files, tags, product_type)

    async def _create_gumroad_product(self, name: str, description: str, price_cents: int, currency: str,
                                       files: List[str], tags: List[str], custom_fields: List[Dict], product_type: str) -> Dict[str, Any]:
        """Create product on Gumroad"""
        client = self._get_gumroad_client()

        # Gumroad requires at least one file for digital products
        # For now, we'll create and note that files need to be uploaded
        payload = {
            "name": name,
            "description": description,
            "price": price_cents,
            "currency": currency,
            "tags": ",".join(tags) if tags else "",
            "custom_permalinks": [name.lower().replace(" ", "-")],
        }

        if product_type == "course":
            payload["course"] = "true"

        response = await client.post("/products", data=payload)

        if response.status_code not in (200, 201):
            return {"status": "failed", "error": f"Gumroad API error: {response.text}"}

        result = response.json().get("product", {})
        return {
            "status": "success",
            "platform": "gumroad",
            "product_id": result.get("id"),
            "name": result.get("name"),
            "price_cents": result.get("price"),
            "currency": result.get("currency"),
            "short_url": result.get("short_url"),
            "files_uploaded": False,
            "note": "Product created. Upload files via Gumroad dashboard or API.",
        }

    async def _create_lemonsqueezy_product(self, name: str, description: str, price_cents: int, currency: str,
                                            files: List[str], tags: List[str], product_type: str) -> Dict[str, Any]:
        """Create product on LemonSqueezy"""
        client = self._get_lemonsqueezy_client()
        from config.settings import settings
        store_id = settings.lemonsqueezy_store_id

        payload = {
            "data": {
                "type": "products",
                "attributes": {
                    "name": name,
                    "description": description,
                    "price": price_cents,
                    "price_currency": currency,
                    "tags": tags,
                    "status": "published",
                },
                "relationships": {
                    "store": {
                        "data": {"type": "stores", "id": store_id}
                    }
                }
            }
        }

        response = await client.post("/products", json=payload)

        if response.status_code not in (200, 201):
            return {"status": "failed", "error": f"LemonSqueezy API error: {response.text}"}

        result = response.json().get("data", {})
        attrs = result.get("attributes", {})
        return {
            "status": "success",
            "platform": "lemonsqueezy",
            "product_id": result.get("id"),
            "name": attrs.get("name"),
            "price_cents": attrs.get("price"),
            "currency": attrs.get("price_currency"),
            "buy_url": attrs.get("buy_now_url"),
            "note": "Product created on LemonSqueezy. Attach files via dashboard.",
        }

    async def _generate_digital_content(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate digital product content"""
        topic = product_data.get("topic", product_data.get("name", "Digital Product"))
        product_type = product_data.get("type", "guide")
        outline = product_data.get("outline")

        if product_type == "course":
            content = await self._generate_course(topic, outline)
        elif product_type == "template":
            content = await self._generate_template(topic, outline)
        else:
            content = await self._generate_guide(topic, outline)

        # Save file
        product_id = str(uuid.uuid4())[:8]
        ext = "md" if product_type != "template" else "json"
        filename = f"{product_id}.{ext}"
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "digital_products", "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        filepath = os.path.join(downloads_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "download_path": filepath,
            "filename": filename,
            "content_preview": content[:500],
        }

    async def _generate_guide(self, topic: str, outline: Optional[str] = None) -> str:
        outline_section = f"\nOutline:\n{outline}" if outline else ""
        prompt = f"""Write a comprehensive guide about "{topic}".
{outline_section}

Requirements:
- 3000-5000 words
- Professional formatting with headers
- Actionable steps and examples
- Table of contents
- 5-8 chapters
- Conclusion with next steps

Format as Markdown."""
        result = await self.llm.generate(prompt, max_tokens=6000, temperature=0.7)
        return f"# {topic}\n\n*Generated by AI Survival System*\n\n---\n\n{result.get('output', 'Error generating content')}"

    async def _generate_course(self, topic: str, outline: Optional[str] = None) -> str:
        outline_section = f"\nOutline:\n{outline}" if outline else ""
        prompt = f"""Create a complete course structure for "{topic}".
{outline_section}

Include:
- 6-10 modules
- 3-5 lessons per module
- Learning objectives
- Exercises per lesson
- Time estimates
- Prerequisites

Format as detailed Markdown."""
        result = await self.llm.generate(prompt, max_tokens=6000, temperature=0.7)
        return f"# Course: {topic}\n\n*Generated by AI Survival System*\n\n---\n\n{result.get('output', 'Error')}"

    async def _generate_template(self, topic: str, outline: Optional[str] = None) -> str:
        outline_section = f"\nRequirements:\n{outline}" if outline else ""
        prompt = f"""Create a comprehensive JSON template for "{topic}".
{outline_section}

Output ONLY valid JSON. Include example data."""
        result = await self.llm.generate(prompt, max_tokens=4000, temperature=0.5)
        import re, json
        json_match = re.search(r'\{[\s\S]*\}', result.get("output", "{}"))
        try:
            return json.dumps(json.loads(json_match.group()) if json_match else {"content": result.get("output")}, indent=2)
        except:
            return json.dumps({"content": result.get("output")}, indent=2)

    async def _update_product(self, platform: str, product_id: str, product_data: Dict) -> Dict[str, Any]:
        """Update an existing product"""
        if platform == "gumroad":
            client = self._get_gumroad_client()
            response = await client.put(f"/products/{product_id}", data=product_data)
        else:
            client = self._get_lemonsqueezy_client()
            response = await client.patch(f"/products/{product_id}", json={"data": {"type": "products", "id": product_id, "attributes": product_data}})

        response.raise_for_status()
        return {"status": "success", "platform": platform, "product_id": product_id}

    async def _create_license(self, platform: str, product_id: str, license_data: Dict) -> Dict[str, Any]:
        """Create a license key for a product (software/SAAS)"""
        if platform == "gumroad":
            client = self._get_gumroad_client()
            response = await client.post(f"/products/{product_id}/license_keys", data={
                "license_key": license_data.get("license_key", str(uuid.uuid4())),
                "uses": license_data.get("uses", 1),
                "expires_at": license_data.get("expires_at"),
            })
        else:
            client = self._get_lemonsqueezy_client()
            response = await client.post("/licenses", json={
                "data": {
                    "type": "licenses",
                    "attributes": {
                        "key": license_data.get("license_key", str(uuid.uuid4())),
                        "uses": license_data.get("uses", 1),
                        "expires_at": license_data.get("expires_at"),
                    },
                    "relationships": {
                        "product": {"data": {"type": "products", "id": product_id}}
                    }
                }
            })

        response.raise_for_status()
        return {"status": "success", "platform": platform, "license": response.json()}

    async def _list_products(self, platform: str) -> Dict[str, Any]:
        """List all products"""
        if platform == "gumroad":
            client = self._get_gumroad_client()
            response = await client.get("/products")
            products = response.json().get("products", [])
            return {"status": "success", "platform": "gumroad", "products": [{
                "id": p.get("id"), "name": p.get("name"), "price_cents": p.get("price"),
                "sales": p.get("sales_count"), "revenue": p.get("sales_usd_cents", 0) / 100
            } for p in products]}
        else:
            client = self._get_lemonsqueezy_client()
            response = await client.get("/products")
            products = response.json().get("data", [])
            return {"status": "success", "platform": "lemonsqueezy", "products": [{
                "id": p.get("id"), "name": p.get("attributes", {}).get("name"),
                "price_cents": p.get("attributes", {}).get("price"),
            } for p in products]}

    async def _get_sales(self, platform: str, product_id: Optional[str] = None) -> Dict[str, Any]:
        """Get sales data"""
        if platform == "gumroad":
            client = self._get_gumroad_client()
            url = f"/products/{product_id}/sales" if product_id else "/sales"
            response = await client.get(url)
            sales = response.json().get("sales", [])
        else:
            client = self._get_lemonsqueezy_client()
            params = {"filter[product_id]": product_id} if product_id else {}
            response = await client.get("/orders", params=params)
            sales = response.json().get("data", [])

        return {"status": "success", "platform": platform, "sales_count": len(sales), "sales": sales[:50]}

    async def _create_coupon(self, platform: str, product_id: str, coupon_data: Dict) -> Dict[str, Any]:
        """Create a discount coupon"""
        code = coupon_data.get("code", "SAVE20")
        discount = coupon_data.get("discount_percent", 20)
        max_uses = coupon_data.get("max_uses", 100)

        if platform == "gumroad":
            client = self._get_gumroad_client()
            response = await client.post("/coupons", data={
                "product_id": product_id,
                "code": code,
                "discount_type": "percentage",
                "discount_amount": discount,
                "max_uses": max_uses,
            })
        else:
            client = self._get_lemonsqueezy_client()
            response = await client.post("/discounts", json={
                "data": {
                    "type": "discounts",
                    "attributes": {
                        "code": code,
                        "discount_type": "percentage",
                        "discount_amount": discount,
                        "usage_limit": max_uses,
                    },
                    "relationships": {
                        "product": {"data": {"type": "products", "id": product_id}}
                    }
                }
            })

        response.raise_for_status()
        return {"status": "success", "platform": platform, "coupon": response.json()}

    async def _setup_webhook(self, platform: str) -> Dict[str, Any]:
        """Webhook setup instructions"""
        from config.settings import settings
        base_url = settings.webhook_publish_url or "https://your-domain.com"

        return {
            "status": "success",
            "platform": platform,
            "webhook_url": f"{base_url}/api/v1/webhook/{platform}",
            "events": ["sale_completed", "refund_created", "subscription_created"] if platform == "gumroad" 
                     else ["order_created", "subscription_created", "license_key_created"],
            "instructions": [
                f"1. Go to {platform.capitalize()} Dashboard > Settings > Webhooks",
                f"2. Add endpoint: {base_url}/api/v1/webhook/{platform}",
                f"3. Select events: {', '.join(['sale_completed', 'refund_created'] if platform == 'gumroad' else ['order_created'])}",
                f"4. Copy signing secret to {platform.upper()}_WEBHOOK_SECRET in .env",
            ]
        }


# Register the tool
tool_registry.register(GumroadTool())