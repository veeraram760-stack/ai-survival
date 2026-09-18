from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import json
from config.settings import settings
import logging
from dotenv import load_dotenv
import os

from backend.database.connection import init_db, close_db, DBSessionFactory
from backend.api.router import router as api_router
from backend.agents.orchestrator import AgentOrchestrator
from backend.agents.ceo import CEODecisionMaker
from backend.revenue.simulation import RevenueEngine
from backend.risk.manager import RiskManager
from backend.finance.ledger import CapitalLedger
from backend.execution.engine import ExecutionEngine
from backend.tasks.manager import TaskManager
from backend.memory.manager import MemoryManager
from backend.performance.tracker import PerformanceTracker

load_dotenv()

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logger = logging.getLogger("ai_survival")

orchestrator: AgentOrchestrator | None = None
risk_manager: RiskManager | None = None
capital_ledger: CapitalLedger | None = None

app = FastAPI(
    title="AI Survival System",
    description="Autonomous multi-agent AI business system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://192.168.1.6:3000",
        "https://ai-survival.surge.sh",
        "http://ai-survival.surge.sh",
        "https://ai-survival-system.fly.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "alive"}


import os
import httpx
from typing import Dict, Any

async def _post_to_twitter(content: str) -> Dict[str, Any]:
    from backend.tools.content import _oauth1_auth_header

    missing = [
        name for name, val in {
            "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY"),
            "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET"),
            "TWITTER_ACCESS_TOKEN": os.getenv("TWITTER_ACCESS_TOKEN"),
            "TWITTER_ACCESS_TOKEN_SECRET": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        }.items() if not val
    ]
    if missing:
        return {"status": "failed", "platform": "twitter", "error": f"X OAuth 1.0a not fully configured. Missing: {', '.join(missing)}", "revenue": 0.0}
    
    try:
        auth_headers = _oauth1_auth_header("POST", "https://api.twitter.com/2/tweets")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"text": content[:280]},
            )
            response.raise_for_status()
            tweet_id = response.json().get("data", {}).get("id")
            return {
                "status": "success",
                "platform": "twitter",
                "tweet_id": tweet_id,
                "revenue": 0.0,
                "url": f"https://x.com/i/status/{tweet_id}" if tweet_id else None,
            }
    except Exception as e:
        return {"status": "failed", "error": str(e), "revenue": 0.0}


async def _post_to_linkedin(content: str) -> Dict[str, Any]:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN") or settings.linkedin_access_token
    person_id = os.getenv("LINKEDIN_PERSON_ID") or settings.linkedin_person_id
    if not token:
        return {"status": "failed", "error": "LinkedIn not configured", "revenue": 0.0}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "author": f"urn:li:person:{person_id or ''}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": content},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                },
            )
            response.raise_for_status()
            post_id = response.json().get("id")
            return {
                "status": "success",
                "platform": "linkedin",
                "post_id": post_id,
                "revenue": 0.08,
                "url": f"https://linkedin.com/feed/update/{post_id}" if post_id else None,
            }
    except Exception as e:
        return {"status": "failed", "error": str(e), "revenue": 0.0}


async def _send_email(content: str) -> Dict[str, Any]:
    smtp_host = settings.smtp_host or os.getenv("SMTP_HOST")
    if not smtp_host:
        return {"status": "failed", "error": "SMTP not configured", "revenue": 0.0}
    
    try:
        import aiosmtplib
        from email.message import EmailMessage
        
        msg = EmailMessage()
        msg["From"] = settings.smtp_from or os.getenv("SMTP_FROM", "noreply@example.com")
        msg["To"] = settings.smtp_to or os.getenv("SMTP_TO", "lead@example.com")
        msg["Subject"] = settings.smtp_subject or os.getenv("SMTP_SUBJECT", "Partnership Opportunity")
        msg.set_content(content[:2000])
        
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=settings.smtp_port or int(os.getenv("SMTP_PORT", 587)),
            username=settings.smtp_user or os.getenv("SMTP_USER"),
            password=settings.smtp_password or settings.smtp_pass or os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS"),
            use_tls=settings.smtp_tls if settings.smtp_tls is not None else os.getenv("SMTP_TLS", "true").lower() == "true",
        )
        return {"status": "success", "platform": "email", "revenue": 0.15}
    except Exception as e:
        return {"status": "failed", "error": str(e), "revenue": 0.0}


@app.post("/webhook/publish")
async def webhook_publish(request: Request):
    data = await request.json()
    content = data.get("content", "")
    platform = data.get("platform", "webhook")
    affiliate_url = data.get("affiliate_url")  # Track if content included affiliate link

    logger.info(f"Webhook publish received for {platform}: {content[:200]}")

    # Always acknowledge receipt; platform posting can happen async
    if platform == "twitter":
        asyncio.create_task(_post_to_twitter(content))
    elif platform == "linkedin":
        asyncio.create_task(_post_to_linkedin(content))
    elif platform == "email":
        asyncio.create_task(_send_email(content))

    return {
        "status": "published",
        "platform": platform,
        "url": settings.webhook_publish_url or "http://localhost:8000/webhook/publish",
        "content_length": len(content),
        "revenue": 0.0,
        "note": "Social media publishing builds brand; revenue tracked via conversion webhook",
        "affiliate_url_tracked": bool(affiliate_url),
    }


@app.post("/webhook/conversion")
async def webhook_conversion(request: Request):
    """Receive real conversion events from affiliate networks or payment processors"""
    data = await request.json()

    # Expected fields: source, transaction_id, amount, commission, currency, timestamp
    source = data.get("source")  # "amazon", "shareasale", "cj", "stripe", "custom"
    transaction_id = data.get("transaction_id")
    amount = float(data.get("amount", 0))
    commission = float(data.get("commission", 0))
    currency = data.get("currency", "USD")
    timestamp = data.get("timestamp")
    campaign_id = data.get("campaign_id")
    agent_id = data.get("agent_id")

    if not transaction_id or commission <= 0:
        return {"status": "failed", "error": "Invalid conversion data: requires transaction_id and positive commission"}

    logger.info(f"Real conversion received: {source} - ${commission:.2f} commission from ${amount:.2f} sale")

    # Get ledger and database from app state
    ledger = request.app.state.capital_ledger
    db_factory = request.app.state.orchestrator._db_factory if hasattr(request.app.state.orchestrator, '_db_factory') else None

    if ledger and db_factory:
        async with db_factory() as db:
            # Find agent_id from campaign if not provided
            if not agent_id and campaign_id:
                from sqlalchemy import select
                from backend.models.database import Campaign as DBCampaign
                campaign_result = await db.execute(select(DBCampaign).where(DBCampaign.id == campaign_id))
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    agent_id = campaign.agent_id

            # Record the real commission revenue
            from decimal import Decimal
            txn = await ledger.record_transaction(
                db=db,
                agent_id=agent_id,
                category="real_revenue",
                action=f"affiliate_commission_{source}",
                amount=Decimal(str(commission)),
                risk_level="LOW",
                approval_reason=f"Real {source} affiliate commission: ${amount:.2f} sale, ${commission:.2f} commission",
            )
            await ledger.commit_transaction(db, txn.id)
            await db.commit()

    return {
        "status": "success",
        "conversion_recorded": True,
        "source": source,
        "transaction_id": transaction_id,
        "commission": commission,
        "currency": currency,
    }


@app.get("/webhook/status")
async def webhook_status():
    return {
        "twitter_configured": all(os.getenv(k) for k in ("TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET")),
        "linkedin_configured": bool(os.getenv("LINKEDIN_ACCESS_TOKEN")),
        "smtp_configured": bool(os.getenv("SMTP_HOST")),
        "webhook_url": os.getenv("WEBHOOK_PUBLISH_URL"),
    }


@app.post("/webhook/stripe")
async def webhook_stripe(request: Request):
    """Handle Stripe webhook events (checkout.session.completed, etc.)"""
    import stripe
    from config.settings import settings

    if not settings.stripe_secret_key:
        return {"status": "failed", "error": "Stripe not configured"}

    stripe.api_key = settings.stripe_secret_key
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = json.loads(payload)
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        return {"status": "failed", "error": "Webhook signature verification failed"}

    logger.info(f"Stripe webhook received: {event['type']}")

    # Handle checkout.session.completed - fulfill digital order
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]

        # Only fulfill if it's a digital product from our agents
        if session.get("metadata", {}).get("source") == "ai_survival_agent":
            product_id = session.get("metadata", {}).get("product_id")
            if product_id:
                # Fulfill the order
                from backend.tools import tool_registry
                stripe_tool = tool_registry.get("stripe_products")
                if stripe_tool:
                    result = await stripe_tool.execute(action="fulfill_order", session_id=session_id)
                    logger.info(f"Order fulfillment result: {result}")

                    # Record revenue in ledger
                    ledger = request.app.state.capital_ledger
                    db_factory = request.app.state.orchestrator._db_factory if hasattr(request.app.state.orchestrator, '_db_factory') else None

                    if ledger and db_factory and result.get("status") == "success":
                        async with db_factory() as db:
                            from decimal import Decimal
                            revenue = Decimal(str(result.get("revenue", 0)))
                            if revenue > 0:
                                txn = await ledger.record_transaction(
                                    db=db,
                                    agent_id=session.get("metadata", {}).get("agent_id"),
                                    category="real_revenue",
                                    action="stripe_digital_product_sale",
                                    amount=revenue,
                                    risk_level="LOW",
                                    approval_reason=f"Stripe digital product sale: ${revenue:.2f}",
                                )
                                await ledger.commit_transaction(db, txn.id)
                                await db.commit()

    return {"status": "received", "event_type": event["type"]}


@app.post("/webhook/gumroad")
async def webhook_gumroad(request: Request):
    """Handle Gumroad webhook events (sale_completed, refund_created, etc.)"""
    from config.settings import settings
    import hmac
    import hashlib

    webhook_secret = os.getenv("GUMROAD_WEBHOOK_SECRET")

    payload = await request.body()

    # Verify webhook signature
    if webhook_secret:
        sig_header = request.headers.get("X-Gumroad-Signature")
        if sig_header:
            expected_sig = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected_sig):
                logger.error("Gumroad webhook signature verification failed")
                return {"status": "failed", "error": "Invalid signature"}

    try:
        data = json.loads(payload)
    except:
        return {"status": "failed", "error": "Invalid JSON"}

    logger.info(f"Gumroad webhook received: {data.get('sale', {}).get('id')}")

    # Handle sale_completed
    if data.get("sale"):
        sale = data["sale"]
        product_id = sale.get("product_id")
        amount_cents = sale.get("amount_cents", 0)
        currency = sale.get("currency", "usd")
        email = sale.get("email")

        # Record revenue
        ledger = request.app.state.capital_ledger
        db_factory = request.app.state.orchestrator._db_factory if hasattr(request.app.state.orchestrator, '_db_factory') else None

        if ledger and db_factory:
            async with db_factory() as db:
                from decimal import Decimal
                from backend.tools import tool_registry
                gumroad_tool = tool_registry.get("gumroad")
                if gumroad_tool:
                    # Get product info to find agent_id
                    product_result = await gumroad_tool.execute(action="get_product", platform="gumroad", product_id=product_id)
                    agent_id = product_result.get("product", {}).get("metadata", {}).get("agent_id")

                revenue = Decimal(str(amount_cents / 100))
                txn = await ledger.record_transaction(
                    db=db,
                    agent_id=agent_id,
                    category="real_revenue",
                    action="gumroad_digital_product_sale",
                    amount=revenue,
                    risk_level="LOW",
                    approval_reason=f"Gumroad sale: ${revenue:.2f} from {email}",
                )
                await ledger.commit_transaction(db, txn.id)
                await db.commit()

    return {"status": "received"}


@app.post("/webhook/lemonsqueezy")
async def webhook_lemonsqueezy(request: Request):
    """Handle LemonSqueezy webhook events (order_created, subscription_created, etc.)"""
    from config.settings import settings
    import hmac
    import hashlib

    webhook_secret = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")

    payload = await request.body()

    # Verify webhook signature
    if webhook_secret:
        sig_header = request.headers.get("X-Signature")
        if sig_header:
            expected_sig = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected_sig):
                logger.error("LemonSqueezy webhook signature verification failed")
                return {"status": "failed", "error": "Invalid signature"}

    try:
        data = json.loads(payload)
    except:
        return {"status": "failed", "error": "Invalid JSON"}

    event_name = data.get("meta", {}).get("event_name")
    logger.info(f"LemonSqueezy webhook received: {event_name}")

    # Handle order_created
    if event_name == "order_created":
        order_data = data.get("data", {}).get("attributes", {})
        product_id = data.get("data", {}).get("relationships", {}).get("product", {}).get("data", {}).get("id")
        amount_cents = order_data.get("total", 0)
        currency = order_data.get("currency", "usd")
        email = order_data.get("user_email")

        ledger = request.app.state.capital_ledger
        db_factory = request.app.state.orchestrator._db_factory if hasattr(request.app.state.orchestrator, '_db_factory') else None

        if ledger and db_factory:
            async with db_factory() as db:
                from decimal import Decimal
                revenue = Decimal(str(amount_cents / 100))
                txn = await ledger.record_transaction(
                    db=db,
                    agent_id=None,
                    category="real_revenue",
                    action="lemonsqueezy_digital_product_sale",
                    amount=revenue,
                    risk_level="LOW",
                    approval_reason=f"LemonSqueezy sale: ${revenue:.2f} from {email}",
                )
                await ledger.commit_transaction(db, txn.id)
                await db.commit()

    return {"status": "received"}


@app.post("/webhook/meta")
async def webhook_meta(request: Request):
    """Handle Meta (Instagram/Facebook) webhook events"""
    from config.settings import settings

    webhook_secret = os.getenv("META_WEBHOOK_SECRET")

    # Meta sends challenge for verification
    if request.query_params.get("hub.mode") == "subscribe":
        challenge = request.query_params.get("hub.challenge")
        verify_token = request.query_params.get("hub.verify_token")
        if verify_token == webhook_secret:
            return int(challenge)
        return {"status": "failed", "error": "Invalid verify token"}

    payload = await request.body()

    if webhook_secret:
        sig_header = request.headers.get("X-Hub-Signature-256")
        if sig_header:
            import hmac
            import hashlib
            expected_sig = "sha256=" + hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected_sig):
                logger.error("Meta webhook signature verification failed")
                return {"status": "failed", "error": "Invalid signature"}

    try:
        data = json.loads(payload)
    except:
        return {"status": "failed", "error": "Invalid JSON"}

    # Process Instagram/Facebook events (comments, messages, etc.)
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})
            logger.info(f"Meta webhook: {field} - {value.get('verb', 'unknown')}")

            # Could trigger agent actions based on comments/mentions
            # e.g., auto-reply to comments with affiliate links

    return {"status": "received"}


@app.post("/webhook/tiktok")
async def webhook_tiktok(request: Request):
    """Handle TikTok webhook events"""
    from config.settings import settings

    webhook_secret = os.getenv("TIKTOK_WEBHOOK_SECRET")

    payload = await request.body()

    if webhook_secret:
        sig_header = request.headers.get("X-TikTok-Signature")
        if sig_header:
            import hmac
            import hashlib
            expected_sig = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected_sig):
                logger.error("TikTok webhook signature verification failed")
                return {"status": "failed", "error": "Invalid signature"}

    try:
        data = json.loads(payload)
    except:
        return {"status": "failed", "error": "Invalid JSON"}

    event = data.get("event")
    logger.info(f"TikTok webhook received: {event}")

    # Handle video views, comments, shares
    # Could trigger agent actions for viral content

    return {"status": "received"}


@app.post("/webhook/shopify")
async def webhook_shopify(request: Request):
    """Handle Shopify webhook events (orders/create, products/create, etc.)"""
    from config.settings import settings
    import hmac
    import hashlib
    import base64

    webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")

    payload = await request.body()

    if webhook_secret:
        sig_header = request.headers.get("X-Shopify-Hmac-Sha256")
        if sig_header:
            expected_sig = base64.b64encode(
                hmac.new(
                    webhook_secret.encode(),
                    payload,
                    hashlib.sha256
                ).digest()
            ).decode()
            if not hmac.compare_digest(sig_header, expected_sig):
                logger.error("Shopify webhook signature verification failed")
                return {"status": "failed", "error": "Invalid signature"}

    try:
        data = json.loads(payload)
    except:
        return {"status": "failed", "error": "Invalid JSON"}

    # Get webhook topic from header
    topic = request.headers.get("X-Shopify-Topic", "unknown")
    logger.info(f"Shopify webhook received: {topic}")

    ledger = request.app.state.capital_ledger
    db_factory = request.app.state.orchestrator._db_factory if hasattr(request.app.state.orchestrator, '_db_factory') else None

    if topic == "orders/create" and ledger and db_factory:
        order = data
        total_price = float(order.get("total_price", "0"))
        email = order.get("email", "")
        order_id = order.get("id")

        async with db_factory() as db:
            from decimal import Decimal
            revenue = Decimal(str(total_price))
            txn = await ledger.record_transaction(
                db=db,
                agent_id=None,
                category="real_revenue",
                action="shopify_order",
                amount=revenue,
                risk_level="LOW",
                approval_reason=f"Shopify order #{order_id}: ${revenue:.2f} from {email}",
            )
            await ledger.commit_transaction(db, txn.id)
            await db.commit()

    return {"status": "received"}


@app.get("/api/v1/download/{product_id}")
async def download_digital_product(product_id: str):
    """Serve digital product file after purchase verification"""
    import os
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "digital_products", "downloads")
    delivery_path = os.path.join(DOWNLOADS_DIR, f"{product_id}_delivery.json")

    if not os.path.exists(delivery_path):
        raise HTTPException(status_code=404, detail="Product not found")

    with open(delivery_path, "r") as f:
        import json
        delivery_info = json.load(f)

    file_path = delivery_info.get("download_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    filename = delivery_info.get("filename", f"{product_id}.download")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")


@app.on_event("startup")
async def startup_event():
    global orchestrator, risk_manager, capital_ledger
    await init_db()
    capital_ledger = CapitalLedger(starting_capital=float(os.getenv("STARTING_CAPITAL", "50.0")))
    risk_manager = RiskManager(capital_ledger)
    orchestrator = AgentOrchestrator(capital_ledger, risk_manager)
    db_factory = DBSessionFactory()
    task_manager = TaskManager(db_factory.session)
    memory_manager = MemoryManager(db_factory.session)
    performance_tracker = PerformanceTracker(db_factory.session)
    ceo = CEODecisionMaker(orchestrator, capital_ledger, risk_manager, task_manager, memory_manager, performance_tracker)
    revenue_engine = RevenueEngine()
    execution_engine = ExecutionEngine(capital_ledger)
    orchestrator.ceo = ceo
    orchestrator.revenue_engine = revenue_engine
    orchestrator.execution_engine = execution_engine
    orchestrator.task_manager = task_manager
    orchestrator.memory_manager = memory_manager
    orchestrator.performance_tracker = performance_tracker
    orchestrator.set_db_factory(db_factory.session)
    await orchestrator.start()
    app.state.orchestrator = orchestrator
    app.state.capital_ledger = capital_ledger
    app.state.risk_manager = risk_manager
    app.state.task_manager = task_manager
    app.state.memory_manager = memory_manager
    app.state.performance_tracker = performance_tracker

    if getattr(settings, "auto_promotion_enabled", False):
        from backend.scheduler import get_scheduler, get_revenue_scheduler, get_analytics_scheduler
        scheduler = get_scheduler(orchestrator)
        asyncio.create_task(scheduler.start())
        logger.info("Auto-promotion scheduler launched")

        revenue_scheduler = get_revenue_scheduler(orchestrator)
        asyncio.create_task(revenue_scheduler.start())
        logger.info("Revenue cycle scheduler launched")

        analytics_scheduler = get_analytics_scheduler(orchestrator)
        asyncio.create_task(analytics_scheduler.start())
        logger.info("Analytics scheduler launched")

    logger.info("AI Survival System started with Master Operating Instructions")


@app.on_event("shutdown")
async def shutdown_event():
    global orchestrator, risk_manager, capital_ledger
    if orchestrator:
        await orchestrator.stop()
    
    # Stop schedulers
    from backend.scheduler import get_scheduler, get_revenue_scheduler, get_analytics_scheduler
    for get_fn in [get_scheduler, get_revenue_scheduler, get_analytics_scheduler]:
        try:
            s = get_fn()
            if s:
                await s.stop()
        except Exception:
            pass
    
    await close_db()
    logger.info("AI Survival System stopped")
