"""
Stripe Digital Products Tool - Create and sell digital products via Stripe
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.stripe_products")

# Digital product storage directory
PRODUCTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "digital_products")
DOWNLOADS_DIR = os.path.join(PRODUCTS_DIR, "downloads")


class StripeProductsTool(Tool):
    """Create digital products, Stripe Checkout sessions, and handle fulfillment"""

    def __init__(self):
        super().__init__(
            name="stripe_products",
            description="Create digital products (PDFs, templates, courses), generate Stripe Checkout links, and manage fulfillment",
            cost=0.05,
        )
        self.llm = get_llm_provider()
        self._stripe = None
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    def _get_stripe(self):
        """Lazy-load Stripe client"""
        if self._stripe is None:
            import stripe
            from config.settings import settings
            if not settings.stripe_secret_key:
                raise ValueError("STRIPE_SECRET_KEY not configured in .env")
            stripe.api_key = settings.stripe_secret_key
            self._stripe = stripe
        return self._stripe

    async def execute(
        self,
        action: str = "create_product",
        product_data: Optional[Dict[str, Any]] = None,
        product_id: Optional[str] = None,
        session_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Main entry point for Stripe product operations"""
        from config.settings import settings

        if not settings.stripe_secret_key:
            return {"status": "failed", "error": "STRIPE_SECRET_KEY not configured"}

        stripe = self._get_stripe()

        try:
            if action == "create_product":
                return await self._create_product(stripe, product_data or {})
            elif action == "create_checkout_session":
                return await self._create_checkout_session(stripe, product_id, customer_email)
            elif action == "get_product":
                return await self._get_product(stripe, product_id)
            elif action == "list_products":
                return await self._list_products(stripe)
            elif action == "create_digital_content":
                return await self._create_digital_content(product_data or {})
            elif action == "fulfill_order":
                return await self._fulfill_order(stripe, session_id)
            elif action == "setup_webhook":
                return await self._setup_webhook(stripe)
            else:
                return {"status": "failed", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"StripeProductsTool error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _create_product(self, stripe, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a digital product with Stripe Product + Price"""
        name = product_data.get("name", "Digital Product")
        description = product_data.get("description", "")
        price_amount = product_data.get("price_cents", 2900)  # in cents
        currency = product_data.get("currency", "usd")
        product_type = product_data.get("type", "digital_download")  # digital_download, course, template
        metadata = product_data.get("metadata", {})

        # Create Stripe Product
        product = stripe.Product.create(
            name=name,
            description=description,
            type="service",
            metadata={
                "product_type": product_type,
                "created_by": "ai_survival_agent",
                **metadata
            }
        )

        # Create Price (one-time payment)
        price = stripe.Price.create(
            product=product.id,
            unit_amount=price_amount,
            currency=currency,
            metadata={"product_type": product_type}
        )

        # Generate digital content if needed
        content_result = None
        if product_data.get("generate_content", True):
            content_result = await self._create_digital_content({
                "product_id": product.id,
                "name": name,
                "topic": product_data.get("topic", name),
                "product_type": product_type,
                "outline": product_data.get("outline"),
            })

        return {
            "status": "success",
            "product": {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price_cents": price_amount,
                "currency": currency,
                "price_id": price.id,
                "product_type": product_type,
                "content_generated": content_result is not None and content_result.get("status") == "success",
                "download_path": content_result.get("download_path") if content_result else None,
            },
            "revenue": 0.0,
            "note": "Product created. Use create_checkout_session to generate payment link."
        }

    async def _create_checkout_session(self, stripe, product_id: str, customer_email: Optional[str] = None) -> Dict[str, Any]:
        """Create a Stripe Checkout Session for a product"""
        if not product_id:
            return {"status": "failed", "error": "product_id required"}

        from config.settings import settings
        success_url = settings.webhook_publish_url or "https://ai-survival.surge.sh/success"
        cancel_url = settings.webhook_publish_url or "https://ai-survival.surge.sh/cancel"

        # Get the product's default price
        product = stripe.Product.retrieve(product_id)
        prices = stripe.Price.list(product=product_id, limit=1, active=True)
        if not prices.data:
            return {"status": "failed", "error": "No active price found for product"}

        price_id = prices.data[0].id

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            customer_email=customer_email,
            metadata={
                "product_id": product_id,
                "source": "ai_survival_agent",
            },
            allow_promotion_codes=True,
        )

        return {
            "status": "success",
            "checkout_session": {
                "id": session.id,
                "url": session.url,
                "product_id": product_id,
                "amount_cents": session.amount_total,
                "currency": session.currency,
                "expires_at": session.expires_at,
            },
            "revenue": 0.0,
            "note": f"Checkout session created. Share URL: {session.url}"
        }

    async def _get_product(self, stripe, product_id: str) -> Dict[str, Any]:
        """Retrieve a product with its prices"""
        product = stripe.Product.retrieve(product_id)
        prices = stripe.Price.list(product=product_id, active=True)

        return {
            "status": "success",
            "product": {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "active": product.active,
                "prices": [{
                    "id": p.id,
                    "amount_cents": p.unit_amount,
                    "currency": p.currency,
                    "type": p.type,
                } for p in prices.data]
            }
        }

    async def _list_products(self, stripe) -> Dict[str, Any]:
        """List all products created by agents"""
        products = stripe.Product.list(limit=50, active=True)

        return {
            "status": "success",
            "products": [{
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "metadata": p.metadata,
                "created": p.created,
            } for p in products.data if p.metadata.get("created_by") == "ai_survival_agent"]
        }

    async def _create_digital_content(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate digital product content (PDF, template, course materials)"""
        product_id = product_data.get("product_id", str(uuid.uuid4()))
        name = product_data.get("name", "Digital Product")
        topic = product_data.get("topic", name)
        product_type = product_data.get("product_type", "digital_download")
        outline = product_data.get("outline")

        # Generate content based on product type
        if product_type == "course":
            content = await self._generate_course_content(topic, outline)
            file_ext = "md"
        elif product_type == "template":
            content = await self._generate_template_content(topic, outline)
            file_ext = "json"
        else:  # digital_download, guide, ebook
            content = await self._generate_guide_content(topic, outline)
            file_ext = "md"

        # Save to file
        filename = f"{product_id}.{file_ext}"
        filepath = os.path.join(DOWNLOADS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Also create a delivery info file
        delivery_info = {
            "product_id": product_id,
            "filename": filename,
            "download_path": filepath,
            "content_type": product_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(content.encode('utf-8')),
        }

        info_path = os.path.join(DOWNLOADS_DIR, f"{product_id}_delivery.json")
        with open(info_path, "w") as f:
            json.dump(delivery_info, f, indent=2)

        return {
            "status": "success",
            "download_path": filepath,
            "filename": filename,
            "delivery_info_path": info_path,
            "content_preview": content[:500] + "..." if len(content) > 500 else content,
        }

    async def _generate_guide_content(self, topic: str, outline: Optional[str] = None) -> str:
        """Generate a comprehensive guide/ebook content"""
        outline_section = f"\nOutline to follow:\n{outline}" if outline else ""

        prompt = f"""Write a comprehensive, high-value digital guide about "{topic}".
{outline_section}

Requirements:
- Professional, authoritative tone
- 3000-5000 words
- Actionable advice with specific steps
- Include table of contents
- 5-8 chapters with subsections
- Practical examples and templates where relevant
- Conclusion with next steps

Format as Markdown with proper headings (#, ##, ###).
Include a compelling title page and introduction."""

        result = await self.llm.generate(prompt, max_tokens=6000, temperature=0.7)

        if result["status"] != "success":
            return f"# {topic}\n\nError generating content: {result.get('error', 'Unknown error')}"

        return f"# {topic}\n\n*Generated by AI Survival System on {datetime.now().strftime('%B %d, %Y')}*\n\n---\n\n{result['output']}"

    async def _generate_course_content(self, topic: str, outline: Optional[str] = None) -> str:
        """Generate a course structure with modules and lessons"""
        outline_section = f"\nOutline to follow:\n{outline}" if outline else ""

        prompt = f"""Create a complete online course structure for "{topic}".
{outline_section}

Requirements:
- 6-10 modules
- 3-5 lessons per module
- Learning objectives for each module
- Lesson descriptions with key concepts
- Practical exercises/assignments per lesson
- Estimated time per lesson
- Prerequisites and target audience
- Course completion certificate criteria

Format as detailed Markdown with:
# Course Title
## Module 1: Name
### Learning Objectives
### Lesson 1.1: Title - Description (X min)
### Exercise: ...
## Module 2: ..."""

        result = await self.llm.generate(prompt, max_tokens=6000, temperature=0.7)

        if result["status"] != "success":
            return f"# Course: {topic}\n\nError: {result.get('error', 'Unknown')}"

        return f"# Course: {topic}\n\n*Generated by AI Survival System on {datetime.now().strftime('%B %d, %Y')}*\n\n---\n\n{result['output']}"

    async def _generate_template_content(self, topic: str, outline: Optional[str] = None) -> str:
        """Generate a JSON template (Notion, Airtable, spreadsheet structure, etc.)"""
        outline_section = f"\nRequirements:\n{outline}" if outline else ""

        prompt = f"""Create a comprehensive JSON template for "{topic}".
{outline_section}

Output ONLY valid JSON. No markdown, no explanations.
The template should be immediately usable - include example data.
Structure should be appropriate for the topic (e.g., content calendar, budget tracker, project plan, CRM, etc.)"""

        result = await self.llm.generate(prompt, max_tokens=4000, temperature=0.5)

        if result["status"] != "success":
            return json.dumps({"error": result.get('error', 'Unknown')}, indent=2)

        # Try to extract JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result["output"])
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return json.dumps(parsed, indent=2)
            except:
                pass
        return json.dumps({"content": result["output"]}, indent=2)

    async def _fulfill_order(self, stripe, session_id: str) -> Dict[str, Any]:
        """Fulfill a digital order after successful payment"""
        session = stripe.checkout.Session.retrieve(session_id, expand=["line_items", "customer"])

        if session.payment_status != "paid":
            return {"status": "failed", "error": "Payment not completed"}

        product_id = session.metadata.get("product_id")
        if not product_id:
            return {"status": "failed", "error": "No product_id in session metadata"}

        # Find the delivery file
        delivery_path = os.path.join(DOWNLOADS_DIR, f"{product_id}_delivery.json")
        if not os.path.exists(delivery_path):
            return {"status": "failed", "error": "Delivery content not found"}

        with open(delivery_path, "r") as f:
            delivery_info = json.load(f)

        # In production: send email with download link, or generate signed URL
        download_url = f"/api/v1/download/{product_id}"  # Would need backend endpoint

        return {
            "status": "success",
            "fulfillment": {
                "session_id": session_id,
                "product_id": product_id,
                "customer_email": session.customer_details.email if session.customer_details else None,
                "amount_paid_cents": session.amount_total,
                "currency": session.currency,
                "download_url": download_url,
                "filename": delivery_info["filename"],
                "fulfilled_at": datetime.now(timezone.utc).isoformat(),
            },
            "revenue": float(session.amount_total) / 100,
        }

    async def _setup_webhook(self, stripe) -> Dict[str, Any]:
        """Instructions for setting up Stripe webhook"""
        from config.settings import settings
        webhook_url = f"{settings.webhook_publish_url or 'https://your-domain.com'}/api/v1/webhook/stripe"

        return {
            "status": "success",
            "webhook_setup": {
                "url": webhook_url,
                "events": [
                    "checkout.session.completed",
                    "checkout.session.expired",
                    "payment_intent.succeeded",
                    "payment_intent.payment_failed",
                ],
                "instructions": [
                    "1. Go to Stripe Dashboard > Developers > Webhooks",
                    f"2. Add endpoint: {webhook_url}",
                    "3. Select events: checkout.session.completed (required)",
                    "4. Copy signing secret to STRIPE_WEBHOOK_SECRET in .env",
                    "5. Backend will auto-fulfill digital orders on payment"
                ]
            }
        }


# Register the tool
tool_registry.register(StripeProductsTool())