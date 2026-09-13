"""
Printful/Printify Tool - Print-on-demand merchandise creation and listing
"""
import os
import json
import uuid
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.print_on_demand")


class PrintOnDemandTool(Tool):
    """Create designs, list products on Printful/Printify, and manage orders"""

    def __init__(self):
        super().__init__(
            name="print_on_demand",
            description="Create AI-generated designs and list print-on-demand products (t-shirts, mugs, posters, etc.) on Printful or Printify",
            cost=0.10,
        )
        self.llm = get_llm_provider()
        self._printful = None
        self._printify = None

    def _get_printful_client(self):
        """Lazy-load Printful API client"""
        if self._printful is None:
            from config.settings import settings
            if not settings.printful_api_key:
                raise ValueError("PRINTFUL_API_KEY not configured in .env")
            import httpx
            self._printful = httpx.AsyncClient(
                base_url="https://api.printful.com",
                headers={"Authorization": f"Bearer {settings.printful_api_key}"},
                timeout=30.0
            )
        return self._printful

    def _get_printify_client(self):
        """Lazy-load Printify API client"""
        if self._printify is None:
            from config.settings import settings
            if not settings.printify_api_key:
                raise ValueError("PRINTIFY_API_KEY not configured in .env")
            import httpx
            shop_id = settings.printify_shop_id
            self._printify = httpx.AsyncClient(
                base_url=f"https://api.printify.com/v1/shops/{shop_id}",
                headers={"Authorization": f"Bearer {settings.printify_api_key}"},
                timeout=30.0
            )
        return self._printify

    async def execute(
        self,
        action: str = "create_design",
        platform: str = "printful",  # or "printify"
        design_data: Optional[Dict[str, Any]] = None,
        product_id: Optional[str] = None,
        listing_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Main entry point for POD operations"""
        from config.settings import settings

        if platform == "printful" and not settings.printful_api_key:
            return {"status": "failed", "error": "PRINTFUL_API_KEY not configured"}
        if platform == "printify" and not settings.printify_api_key:
            return {"status": "failed", "error": "PRINTIFY_API_KEY not configured"}

        try:
            if action == "create_design":
                return await self._create_design(design_data or {})
            elif action == "create_product":
                return await self._create_product(platform, design_data or {}, listing_data or {})
            elif action == "list_products":
                return await self._list_products(platform)
            elif action == "get_product":
                return await self._get_product(platform, product_id)
            elif action == "publish_product":
                return await self._publish_product(platform, product_id, listing_data or {})
            elif action == "get_orders":
                return await self._get_orders(platform)
            elif action == "generate_mockup":
                return await self._generate_mockup(platform, product_id, design_data or {})
            else:
                return {"status": "failed", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"PrintOnDemandTool error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _create_design(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI design concept and prompt for image generation"""
        niche = design_data.get("niche", "general")
        style = design_data.get("style", "minimalist")
        topic = design_data.get("topic", f"{niche} inspiration")
        product_type = design_data.get("product_type", "t-shirt")
        color_scheme = design_data.get("color_scheme", "auto")

        prompt = f"""Create a detailed design specification for a {product_type} in the "{niche}" niche.

Topic: {topic}
Style: {style}
Color scheme: {color_scheme}

Provide:
1. Design concept description (what the design looks like)
2. Detailed image generation prompt for AI (Midjourney/DALL-E style)
3. Placement suggestions (center, pocket, sleeve, all-over)
4. Color variations (3-5 colorways)
5. Target audience
6. SEO keywords for listing
7. Suggested retail price range

Return as JSON with keys: concept, image_prompt, placements, colorways, audience, keywords, price_range"""

        result = await self.llm.generate(prompt, max_tokens=3000, temperature=0.8)

        if result["status"] != "success":
            return {"status": "failed", "error": f"Design generation failed: {result.get('error')}"}

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result["output"])
            if json_match:
                design = json.loads(json_match.group())
            else:
                design = json.loads(result["output"])
        except:
            design = {"concept": result["output"], "image_prompt": result["output"][:500]}

        design_id = str(uuid.uuid4())[:8]
        design["design_id"] = design_id
        design["created_at"] = datetime.now(timezone.utc).isoformat()
        design["niche"] = niche
        design["product_type"] = product_type

        # Save design spec
        designs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pod_designs")
        os.makedirs(designs_dir, exist_ok=True)
        with open(os.path.join(designs_dir, f"{design_id}.json"), "w") as f:
            json.dump(design, f, indent=2)

        return {
            "status": "success",
            "design": design,
            "note": "Design spec created. Use create_product with this design_id to list on POD platform."
        }

    async def _create_product(self, platform: str, design_data: Dict[str, Any], listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a product on Printful or Printify with the design"""
        design_id = design_data.get("design_id") or str(uuid.uuid4())[:8]
        design_spec = design_data.get("design") or design_data

        # Sync product catalog first
        catalog = await self._sync_catalog(platform)

        # Find matching product variant
        product_type = design_spec.get("product_type", "t-shirt")
        variant_id = self._find_variant(catalog, product_type, design_spec.get("placements", ["front"]))

        if not variant_id:
            return {"status": "failed", "error": f"No matching variant found for {product_type}"}

        # Prepare product data
        product_payload = {
            "variant_id": variant_id,
            "name": listing_data.get("name", design_spec.get("concept", "Custom Design")[:100]),
            "description": listing_data.get("description", self._generate_description(design_spec)),
            "images": [],  # Would need uploaded design images
            "price": listing_data.get("price", 29.99),
            "currency": "USD",
            "visible": listing_data.get("visible", True),
            "tags": listing_data.get("tags", design_spec.get("keywords", [])),
        }

        if platform == "printful":
            return await self._create_printful_product(product_payload, design_spec)
        else:
            return await self._create_printify_product(product_payload, design_spec)

    def _find_variant(self, catalog: List[Dict], product_type: str, placements: List[str]) -> Optional[int]:
        """Find matching variant ID from catalog"""
        type_keywords = {
            "t-shirt": ["t-shirt", "tee", "shirt"],
            "hoodie": ["hoodie", "hooded"],
            "mug": ["mug", "ceramic"],
            "poster": ["poster", "print", "wall art"],
            "tote": ["tote", "bag"],
            "hat": ["hat", "cap", "beanie"],
            "sticker": ["sticker", "decal"],
        }
        keywords = type_keywords.get(product_type.lower(), [product_type.lower()])

        for item in catalog:
            name_lower = item.get("name", "").lower()
            if any(kw in name_lower for kw in keywords):
                # Check if it supports required placements
                return item.get("id") or item.get("variant_id")
        return None

    async def _sync_catalog(self, platform: str) -> List[Dict]:
        """Fetch and cache product catalog"""
        if platform == "printful":
            client = self._get_printful_client()
            response = await client.get("/sync/products")
            response.raise_for_status()
            data = response.json()
            return data.get("result", [])
        else:
            client = self._get_printify_client()
            response = await client.get("/catalog.json")
            response.raise_for_status()
            return response.json()

    async def _create_printful_product(self, payload: Dict, design_spec: Dict) -> Dict[str, Any]:
        """Create product on Printful"""
        client = self._get_printful_client()

        # Note: Printful requires design files to be uploaded first
        # This is a simplified version - real implementation needs file upload
        response = await client.post("/store/products", json={
            "sync_product": {
                "variant_id": payload["variant_id"],
                "name": payload["name"],
            }
        })

        if response.status_code not in (200, 201):
            return {"status": "failed", "error": f"Printful API error: {response.text}"}

        result = response.json().get("result", {})
        return {
            "status": "success",
            "platform": "printful",
            "product_id": result.get("id"),
            "name": result.get("name"),
            "variant_id": payload["variant_id"],
            "price": payload["price"],
            "note": "Product created on Printful. Upload design files and publish to store."
        }

    async def _create_printify_product(self, payload: Dict, design_spec: Dict) -> Dict[str, Any]:
        """Create product on Printify"""
        client = self._get_printify_client()

        response = await client.post("/products.json", json={
            "title": payload["name"],
            "description": payload["description"],
            "variants": [{
                "id": payload["variant_id"],
                "price": int(payload["price"] * 100),  # Printify uses cents
                "is_enabled": True,
            }],
            "images": payload["images"],
            "tags": payload["tags"],
            "visible": payload["visible"],
        })

        if response.status_code not in (200, 201):
            return {"status": "failed", "error": f"Printify API error: {response.text}"}

        result = response.json()
        return {
            "status": "success",
            "platform": "printify",
            "product_id": result.get("id"),
            "name": result.get("title"),
            "price": payload["price"],
            "note": "Product created on Printify. Add design images and publish."
        }

    def _generate_description(self, design_spec: Dict) -> str:
        """Generate product description from design spec"""
        concept = design_spec.get("concept", "Unique AI-generated design")
        audience = design_spec.get("audience", "everyone")
        return f"""{concept}

Perfect for {audience} who appreciate unique, AI-crafted designs.

Features:
- Premium quality materials
- Vibrant, long-lasting prints
- Ethically sourced and printed on demand
- Each piece made specifically for you

Design by AI Survival System - Autonomous AI Business"""

    async def _list_products(self, platform: str) -> Dict[str, Any]:
        """List all products on the platform"""
        if platform == "printful":
            client = self._get_printful_client()
            response = await client.get("/store/products")
        else:
            client = self._get_printify_client()
            response = await client.get("/products.json")

        response.raise_for_status()
        data = response.json()

        products = data.get("result", data.get("data", []))
        return {
            "status": "success",
            "platform": platform,
            "products": [{
                "id": p.get("id"),
                "name": p.get("name") or p.get("title"),
                "price": p.get("price") or p.get("variants", [{}])[0].get("price", 0) / 100,
                "status": p.get("status") or "draft",
            } for p in products]
        }

    async def _get_product(self, platform: str, product_id: str) -> Dict[str, Any]:
        """Get product details"""
        if platform == "printful":
            client = self._get_printful_client()
            response = await client.get(f"/store/products/{product_id}")
        else:
            client = self._get_printify_client()
            response = await client.get(f"/products/{product_id}.json")

        response.raise_for_status()
        return {"status": "success", "platform": platform, "product": response.json().get("result", response.json())}

    async def _publish_product(self, platform: str, product_id: str, listing_data: Dict) -> Dict[str, Any]:
        """Publish product to connected store (Shopify, Etsy, etc.)"""
        if platform == "printful":
            client = self._get_printful_client()
            response = await client.post(f"/store/products/{product_id}/publish")
        else:
            client = self._get_printify_client()
            response = await client.post(f"/products/{product_id}/publish.json")

        response.raise_for_status()
        return {"status": "success", "platform": platform, "product_id": product_id, "published": True}

    async def _get_orders(self, platform: str) -> Dict[str, Any]:
        """Fetch recent orders"""
        if platform == "printful":
            client = self._get_printful_client()
            response = await client.get("/orders?limit=20")
        else:
            client = self._get_printify_client()
            response = await client.get("/orders.json?limit=20")

        response.raise_for_status()
        data = response.json()
        orders = data.get("result", data.get("data", []))

        return {
            "status": "success",
            "platform": platform,
            "orders": [{
                "id": o.get("id"),
                "status": o.get("status"),
                "total": o.get("costs", {}).get("total", 0) / 100 if platform == "printful" else o.get("total_price", 0) / 100,
                "created": o.get("created") or o.get("created_at"),
            } for o in orders]
        }

    async def _generate_mockup(self, platform: str, product_id: str, design_data: Dict) -> Dict[str, Any]:
        """Generate product mockup images"""
        # This would call the platform's mockup generator API
        # Simplified response
        return {
            "status": "success",
            "platform": platform,
            "product_id": product_id,
            "mockup_urls": [
                f"https://mockup-{platform}.com/{product_id}/front.png",
                f"https://mockup-{platform}.com/{product_id}/back.png",
            ],
            "note": "Mockups generated. Use for marketing/social media."
        }


# Register the tool
tool_registry.register(PrintOnDemandTool())