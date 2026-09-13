"""
API call and integration tools for agents
"""
import os
from datetime import datetime, timedelta, timezone
import httpx
from typing import Dict, Any, Optional
from .base import Tool, tool_registry
import logging
from urllib.parse import quote, urlencode

logger = logging.getLogger("ai_survival.tools.api")


class APICallTool(Tool):
    """Make HTTP API calls"""

    def __init__(self):
        super().__init__(
            name="api_call",
            description="Make HTTP requests to external APIs",
            cost=0.0001,
        )

    async def execute(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute API call"""

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )

                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                }
        except httpx.HTTPStatusError as e:
            return {
                "status": "failed",
                "error": f"HTTP {e.response.status_code}",
                "status_code": e.response.status_code,
                "response": e.response.text,
            }
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {"status": "failed", "error": str(e)}


class AffiliateLinkTool(Tool):
    """Generate and track affiliate links"""

    def __init__(self):
        super().__init__(
            name="affiliate_link",
            description="Generate and track affiliate links",
            cost=0.0001,
        )
        from config.settings import settings
        self.settings = settings
        self.networks = {
            "amazon": settings.amazon_associate_tag or os.getenv("AMAZON_ASSOCIATE_TAG"),
            "shareasale": settings.shareasale_id or os.getenv("SHAREASALE_ID"),
            "cj": settings.cj_affiliate_id or os.getenv("CJ_AFFILIATE_ID"),
            "impact": settings.impact_partner_id or os.getenv("IMPACT_PARTNER_ID"),
            "custom": None,
        }
        self.cj_api_key = settings.cj_api_key or os.getenv("CJ_API_KEY")

    async def execute(
        self,
        network: str,
        product_url: str,
        campaign_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate affiliate link with tracking parameters for conversion attribution"""

        if network not in self.networks:
            return {"status": "failed", "error": f"Network '{network}' not configured"}

        # Build tracking parameters with campaign_id and agent_id for attribution
        tracking_params = {}
        if campaign_id:
            tracking_params["ref"] = campaign_id
        if agent_id:
            tracking_params["agent"] = agent_id

        try:
            if network == "amazon" and self.networks["amazon"]:
                tag = self.networks["amazon"]
                base_url = product_url
                separator = "&" if "?" in base_url else "?"
                base_url += f"{separator}tag={tag}"
                # Add tracking params
                if tracking_params:
                    base_url += f"&{urlencode(tracking_params)}"
                return {
                    "status": "success",
                    "network": network,
                    "original_url": product_url,
                    "affiliate_url": base_url,
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                    "tracking_params": tracking_params,
                }

            if network == "shareasale" and self.networks["shareasale"]:
                affiliate_id = self.networks["shareasale"]
                base_url = f"https://shareasale.com/r.cfm?u={affiliate_id}&urllink={quote(product_url, safe='')}"
                # Add tracking params
                if tracking_params:
                    base_url += f"&{urlencode(tracking_params)}"
                return {
                    "status": "success",
                    "network": network,
                    "original_url": product_url,
                    "affiliate_url": base_url,
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                    "tracking_params": tracking_params,
                }

            if network == "cj" and self.networks["cj"]:
                affiliate_id = self.networks["cj"]
                if self.cj_api_key:
                    try:
                        affiliate_url = await self._cj_create_link(affiliate_id, product_url)
                        if affiliate_url:
                            # Add tracking params to CJ link
                            if tracking_params:
                                separator = "&" if "?" in affiliate_url else "?"
                                affiliate_url += f"{separator}{urlencode(tracking_params)}"
                            return {
                                "status": "success",
                                "network": network,
                                "original_url": product_url,
                                "affiliate_url": affiliate_url,
                                "campaign_id": campaign_id,
                                "agent_id": agent_id,
                                "tracking_params": tracking_params,
                            }
                    except Exception as e:
                        logger.warning(f"CJ API link creation failed: {e}")
                # Fallback: return original URL with tracking params
                base_url = product_url
                if tracking_params:
                    separator = "&" if "?" in base_url else "?"
                    base_url += f"{separator}{urlencode(tracking_params)}"
                return {
                    "status": "success",
                    "network": network,
                    "original_url": product_url,
                    "affiliate_url": base_url,
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                    "tracking_params": tracking_params,
                    "note": "CJ API unavailable; tracking params added to original URL",
                }

            if network == "impact" and self.networks["impact"]:
                partner_id = self.networks["impact"]
                base_url = product_url
                if tracking_params:
                    separator = "&" if "?" in base_url else "?"
                    base_url += f"{separator}{urlencode(tracking_params)}"
                return {
                    "status": "success",
                    "network": network,
                    "original_url": product_url,
                    "affiliate_url": base_url,
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                    "tracking_params": tracking_params,
                    "note": "Use Impact dashboard to convert links with partner ID; tracking params added",
                }

            # Custom/other networks
            base_url = product_url
            if tracking_params:
                separator = "&" if "?" in base_url else "?"
                base_url += f"{separator}{urlencode(tracking_params)}"

            return {
                "status": "success",
                "network": network,
                "original_url": product_url,
                "affiliate_url": base_url,
                "campaign_id": campaign_id,
                "agent_id": agent_id,
                "tracking_params": tracking_params,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _cj_create_link(self, affiliate_id: str, product_url: str) -> Optional[str]:
        if not self.cj_api_key:
            return None
        async with httpx.AsyncClient(timeout=30.0) as client:
            # CJ Links API v3 - correct endpoint
            response = await client.post(
                "https://links.api.cj.com/v3/links",
                headers={
                    "Authorization": f"Bearer {self.cj_api_key}",
                    "Content-Type": "application/json",
                },
                json={"websiteId": affiliate_id, "redirectUrl": product_url},
            )
            if response.status_code in (200, 201):
                data = response.json()
                return data.get("link") or data.get("url") or product_url
            logger.warning(f"CJ API error: {response.status_code} {response.text}")
            return None


class LeadGenerationTool(Tool):
    """Generate and qualify leads"""

    def __init__(self):
        super().__init__(
            name="lead_generation",
            description="Generate and qualify sales leads",
            cost=0.01,
        )

    async def execute(
        self,
        industry: str,
        company_size: str = "any",
        location: str = "any",
        count: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate leads based on criteria"""
        # In production, this would integrate with lead databases
        # For now, return mock data structure

        mock_leads = []
        for i in range(min(count, 10)):
            mock_leads.append({
                "id": f"lead_{i}",
                "company": f"{industry.title()} Company {i+1}",
                "contact": f"Contact {i+1}",
                "email": f"contact{i+1}@company{i+1}.com",
                "role": "Decision Maker",
                "company_size": company_size,
                "location": location,
                "score": 0.8 - (i * 0.05),
            })

        return {
            "status": "success",
            "criteria": {"industry": industry, "company_size": company_size, "location": location},
            "leads": mock_leads,
            "total_found": len(mock_leads),
        }


class OutreachTool(Tool):
    """Generate personalized outreach messages"""

    def __init__(self):
        super().__init__(
            name="generate_outreach",
            description="Generate personalized sales outreach messages",
            cost=0.005,
        )
        from ..execution.llm_providers import get_llm_provider
        self.llm = get_llm_provider()

    async def execute(
        self,
        lead_data: Dict[str, Any],
        product: str,
        tone: str = "professional",
        channel: str = "email",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate outreach message"""

        prompt = f"""
Generate a {tone} {channel} outreach for:
- Company: {lead_data.get('company', 'Unknown')}
- Contact: {lead_data.get('contact', 'Unknown')}
- Role: {lead_data.get('role', 'Unknown')}
- Product: {product}

Include: subject line, personalized opening, value proposition, social proof, CTA.
Return as JSON with 'subject' and 'body' fields.
"""

        result = await self.llm.generate(prompt, max_tokens=1000, temperature=0.7)

        if result["status"] == "success":
            try:
                import json
                outreach = json.loads(result["output"])
                return {
                    "status": "success",
                    "channel": channel,
                    "lead": lead_data,
                    "outreach": outreach,
                }
            except json.JSONDecodeError:
                return {
                    "status": "success",
                    "channel": channel,
                    "lead": lead_data,
                    "outreach": {"subject": "Partnership Opportunity", "body": result["output"]},
                }
        return result


class ConversionTrackingTool(Tool):
    """Track real conversions and commissions from affiliate networks"""

    def __init__(self):
        super().__init__(
            name="track_conversions",
            description="Fetch real conversion/commission data from affiliate networks",
            cost=0.001,
        )
        from config.settings import settings
        self.settings = settings
        self.cj_api_key = settings.cj_api_key or os.getenv("CJ_API_KEY")
        self.cj_affiliate_id = settings.cj_affiliate_id or os.getenv("CJ_AFFILIATE_ID")
        self.shareasale_id = settings.shareasale_id or os.getenv("SHAREASALE_ID")
        self.amazon_tag = settings.amazon_associate_tag or os.getenv("AMAZON_ASSOCIATE_TAG")

    async def execute(
        self,
        network: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch conversion data from affiliate network"""

        if network == "cj":
            return await self._fetch_cj_commissions(start_date, end_date)
        elif network == "shareasale":
            return await self._fetch_shareasale_commissions(start_date, end_date)
        elif network == "amazon":
            return await self._fetch_amazon_earnings(start_date, end_date)
        elif network == "all":
            results = {}
            results["cj"] = await self._fetch_cj_commissions(start_date, end_date)
            results["shareasale"] = await self._fetch_shareasale_commissions(start_date, end_date)
            results["amazon"] = await self._fetch_amazon_earnings(start_date, end_date)
            return {"status": "success", "networks": results}
        else:
            return {"status": "failed", "error": f"Network '{network}' not supported for conversion tracking"}

    async def _fetch_cj_commissions(self, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Fetch commissions from CJ Affiliate API"""
        if not self.cj_api_key or not self.cj_affiliate_id:
            return {"status": "failed", "error": "CJ API credentials not configured", "commissions": []}

        try:
            params = {
                "website-id": self.cj_affiliate_id,
                "start-date": start_date or (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end-date": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                # CJ Commissions API v3 - correct endpoint
                response = await client.get(
                    "https://commissions.api.cj.com/v3/commissions",
                    headers={"Authorization": f"Bearer {self.cj_api_key}"},
                    params=params,
                )
                if response.status_code == 200:
                    data = response.json()
                    commissions = data.get("commissions", [])
                    total = sum(float(c.get("commissionAmount", c.get("commission-amount", 0))) for c in commissions)
                    return {
                        "status": "success",
                        "network": "cj",
                        "commissions": commissions,
                        "total_commission": total,
                        "count": len(commissions),
                    }
                else:
                    return {"status": "failed", "error": f"CJ API error: {response.status_code} {response.text}", "commissions": []}
        except Exception as e:
            logger.error(f"CJ conversion fetch failed: {e}")
            return {"status": "failed", "error": str(e), "commissions": []}

    async def _fetch_shareasale_commissions(self, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Fetch commissions from ShareASale API"""
        if not self.shareasale_id:
            return {"status": "failed", "error": "ShareASale credentials not configured", "commissions": []}

        try:
            # ShareASale API requires token-based authentication
            # Check if token is available
            shareasale_token = getattr(self.settings, "shareasale_token", None) or os.getenv("SHAREASALE_TOKEN")
            if not shareasale_token:
                return {
                    "status": "failed",
                    "error": "ShareASale API token not configured. Set SHAREASALE_TOKEN in .env",
                    "commissions": [],
                    "note": "ShareASale requires API token from their developer portal"
                }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    "https://api.shareasale.com/x.cfm",
                    params={
                        "action": "transactiondetail",
                        "affiliateId": self.shareasale_id,
                        "token": shareasale_token,
                        "dateStart": start_date or (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
                        "dateEnd": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "version": "2.1",
                    },
                )
                if response.status_code == 200:
                    # Parse XML response (ShareASale returns XML)
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)
                    commissions = []
                    total = 0.0
                    for trans in root.findall(".//transaction"):
                        amount = float(trans.findtext("commission", "0"))
                        if amount > 0:
                            total += amount
                            commissions.append({
                                "transaction_id": trans.findtext("transactionId"),
                                "date": trans.findtext("date"),
                                "commission": amount,
                                "sale_amount": float(trans.findtext("saleAmount", "0")),
                                "merchant": trans.findtext("merchantName"),
                            })
                    return {
                        "status": "success",
                        "network": "shareasale",
                        "commissions": commissions,
                        "total_commission": total,
                        "count": len(commissions),
                    }
                else:
                    return {"status": "failed", "error": f"ShareASale API error: {response.status_code} {response.text}", "commissions": []}
        except Exception as e:
            logger.error(f"ShareASale conversion fetch failed: {e}")
            return {"status": "failed", "error": str(e), "commissions": []}

    async def _fetch_amazon_earnings(self, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Fetch earnings from Amazon Associates (requires Product Advertising API + Reports)"""
        if not self.amazon_tag:
            return {"status": "failed", "error": "Amazon Associate tag not configured", "commissions": []}

        # Amazon Associates doesn't have a simple real-time API for commissions
        # Would need to use Product Advertising API + download reports
        # For now, return structure for manual CSV upload or future API integration
        return {
            "status": "info",
            "network": "amazon",
            "message": "Amazon Associates earnings require manual report download or Product Advertising API integration",
            "commissions": [],
            "total_commission": 0.0,
            "note": "Integrate with Amazon PA-API 5.0 + Reports API for automated fetching",
        }


class PayoutTool(Tool):
    """Execute real payouts via PayPal, Razorpay, or record external payout events"""

    def __init__(self):
        super().__init__(
            name="payout",
            description="Execute payout via PayPal/Razorpay or record external payout",
            cost=0.0,
        )
        from config.settings import settings
        self.paypal_client_id = getattr(settings, "paypal_client_id", None) or os.getenv("PAYPAL_CLIENT_ID")
        self.paypal_secret = getattr(settings, "paypal_secret", None) or os.getenv("PAYPAL_SECRET")
        self.razorpay_key_id = getattr(settings, "razorpay_key_id", None) or os.getenv("RAZORPAY_KEY_ID")
        self.razorpay_key_secret = getattr(settings, "razorpay_key_secret", None) or os.getenv("RAZORPAY_KEY_SECRET")
        self.stripe_secret_key = settings.stripe_secret_key or os.getenv("STRIPE_SECRET_KEY")

    async def execute(
        self,
        amount: float,
        currency: str = "usd",
        method: Optional[str] = None,
        destination: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        resolved_method = method or getattr(self, "_preferred_method", None) or os.getenv("PAYOUT_METHOD", "external")
        if resolved_method == "paypal":
            return await self._paypal_payout(amount, currency, destination)
        if resolved_method == "razorpay":
            return await self._razorpay_payout(amount, currency, destination)
        if resolved_method == "stripe":
            return await self._stripe_payout(amount, currency, destination)
        if resolved_method == "external":
            return await self._record_external_payout(amount, currency, destination)
        return {"status": "failed", "error": f"Payout method '{resolved_method}' not supported"}

    async def _stripe_payout(self, amount: float, currency: str, destination: Optional[str]) -> Dict[str, Any]:
        if not self.stripe_secret_key:
            return {"status": "failed", "error": "Stripe secret key not configured", "real": False}
        try:
            import stripe
            stripe.api_key = self.stripe_secret_key
            payout = stripe.Payout.create(
                amount=int(amount * 100),
                currency=currency,
                destination=destination,
                method="standard",
            )
            return {
                "status": "success",
                "method": "stripe",
                "payout_id": payout.id,
                "amount": amount,
                "currency": currency,
                "real": True,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e), "real": False}

    async def _paypal_payout(self, amount: float, currency: str, destination: Optional[str]) -> Dict[str, Any]:
        if not self.paypal_client_id or not self.paypal_secret:
            return {
                "status": "failed",
                "error": "PayPal credentials not configured. Set PAYPAL_CLIENT_ID and PAYPAL_SECRET.",
                "real": False,
            }
        try:
            paypal_mode = os.getenv("PAYPAL_MODE", "sandbox")
            base_url = "https://api-m.paypal.com" if paypal_mode == "live" else "https://api-m.sandbox.paypal.com"
            async with httpx.AsyncClient(timeout=60.0) as client:
                auth = (self.paypal_client_id, self.paypal_secret)
                token_resp = await client.post(
                    f"{base_url}/v1/oauth2/token",
                    headers={"Accept": "application/json"},
                    auth=auth,
                    data={"grant_type": "client_credentials"},
                )
                if token_resp.status_code != 200:
                    return {"status": "failed", "error": f"PayPal auth failed: {token_resp.status_code} {token_resp.text}", "real": False}
                access_token = token_resp.json().get("access_token")
                if not access_token:
                    return {"status": "failed", "error": "PayPal auth missing access_token", "real": False}

                payload = {
                    "sender_batch_header": {
                        "sender_batch_id": f"aisurvival-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                        "email_subject": "You have a payout from AI Survival",
                    },
                    "items": [
                        {
                            "recipient_type": "EMAIL",
                            "receiver": destination or os.getenv("PAYOUT_EMAIL", ""),
                            "amount": {"value": f"{amount:.2f}", "currency": currency.upper()},
                            "note": "AI Survival payout",
                            "sender_item_id": f"payout-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                        }
                    ],
                }
                payout_resp = await client.post(
                    f"{base_url}/v1/payments/payouts",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if payout_resp.status_code in (200, 201):
                    data = payout_resp.json()
                    batch_id = data.get("batch_header", {}).get("payout_batch_id")
                    is_live = paypal_mode == "live" and not os.getenv("PAYPAL_CLIENT_ID", "").startswith("AT-")
                    return {
                        "status": "success",
                        "method": "paypal",
                        "payout_id": batch_id,
                        "amount": amount,
                        "currency": currency.upper(),
                        "real": bool(is_live),
                    }
                return {"status": "failed", "error": f"PayPal payout failed: {payout_resp.status_code} {payout_resp.text}", "real": False}
        except Exception as e:
            return {"status": "failed", "error": str(e), "real": False}

    async def _razorpay_payout(self, amount: float, currency: str, destination: Optional[str]) -> Dict[str, Any]:
        if not self.razorpay_key_id or not self.razorpay_key_secret:
            return {
                "status": "failed",
                "error": "Razorpay credentials not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.",
                "real": False,
            }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                auth = (self.razorpay_key_id, self.razorpay_key_secret)
                if not destination:
                    contact_id = os.getenv("RAZORPAY_CONTACT_ID")
                    if not contact_id:
                        return {"status": "failed", "error": "Razorpay destination not provided. Set RAZORPAY_CONTACT_ID or pass destination.", "real": False}
                    destination = contact_id
                payload = {
                    "account_number": os.getenv("RAZORPAY_ACCOUNT_NUMBER", ""),
                    "fund_account_id": destination,
                    "amount": int(amount * 100),
                    "currency": currency.upper(),
                    "mode": "IMPS",
                    "purpose": "payout",
                }
                payout_resp = await client.post(
                    "https://api.razorpay.com/v1/payouts",
                    auth=auth,
                    json=payload,
                )
                if payout_resp.status_code in (200, 201):
                    data = payout_resp.json()
                    return {
                        "status": "success",
                        "method": "razorpay",
                        "payout_id": data.get("id"),
                        "amount": amount,
                        "currency": currency.upper(),
                        "real": True,
                    }
                return {"status": "failed", "error": f"Razorpay payout failed: {payout_resp.status_code} {payout_resp.text}", "real": False}
        except Exception as e:
            return {"status": "failed", "error": str(e), "real": False}

    async def _record_external_payout(self, amount: float, currency: str, destination: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "success",
            "method": "external",
            "amount": amount,
            "currency": currency,
            "destination": destination,
            "note": "External payout recorded; no automated transfer executed",
            "real": True,
        }


# Register tools
tool_registry.register(APICallTool())
tool_registry.register(AffiliateLinkTool())
tool_registry.register(LeadGenerationTool())
tool_registry.register(OutreachTool())
tool_registry.register(ConversionTrackingTool())
tool_registry.register(PayoutTool())