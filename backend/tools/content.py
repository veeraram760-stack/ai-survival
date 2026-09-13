"""
Content generation and publishing tools for agents
"""
import os
import base64
import hmac
import hashlib
import secrets
import time
import urllib.parse
import httpx
from typing import Dict, Any, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.content")


def _oauth1_auth_header(method: str, url: str, query_params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return an OAuth 1.0a 'Authorization' header (HMAC-SHA1) for a request.

    Used for X (formerly Twitter) API v2 calls that require user context (posting tweets).
    The Bearer token is read-only; posting requires a full 4-credential set:
    TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET.
    """
    consumer_key = os.getenv("TWITTER_API_KEY", "")
    consumer_secret = os.getenv("TWITTER_API_SECRET", "")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")

    def _enc(s: str) -> str:
        return urllib.parse.quote(str(s), safe="-._~")

    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    if query_params:
        params.update(query_params)

    # Normalize: percent-encode names and values, sort by encoded name, join with '&'
    encoded = {_enc(k): _enc(v) for k, v in params.items()}
    sorted_items = sorted(encoded.items())
    param_str = "&".join(f"{k}={v}" for k, v in sorted_items)

    # JSON bodies are not part of an OAuth 1.0 signature, so no body params here.
    base_string = "&".join([
        method.upper(),
        _enc(url.split("?")[0]),
        _enc(param_str),
    ])

    signing_key = f"{_enc(consumer_secret)}&{_enc(access_token_secret)}"
    signature = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    signature_b64 = base64.b64encode(signature).decode()

    header_params = {k: v for k, v in params.items() if k.startswith("oauth_")}
    header_params["oauth_signature"] = signature_b64
    header = ", ".join(f'{k}="{_enc(v)}"' for k, v in header_params.items())
    return {"Authorization": f"OAuth {header}"}


class ContentGenerationTool(Tool):
    """Generate content using LLM"""

    def __init__(self, provider: Optional[str] = None):
        super().__init__(
            name="generate_content",
            description="Generate content (articles, scripts, posts, etc.) using AI",
            cost=0.01,
        )
        self.llm = get_llm_provider(provider)

    async def execute(
        self,
        content_type: str,
        topic: str,
        style: str = "professional",
        length: str = "medium",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate content based on parameters"""

        prompts = {
            "article": f"Write a {length} {style} article about {topic}. Include title, headings, and conclusion.",
            "script": f"Write a {length} {style} video script about {topic}. Include hook, body, and CTA.",
            "tweet": f"Write a {style} tweet about {topic}. Include hashtags.",
            "linkedin": f"Write a {style} LinkedIn post about {topic}. Include hashtags and engagement hook.",
            "email": f"Write a {style} email about {topic}. Include subject line and body.",
            "product_description": f"Write a {style} product description for {topic}. Include features and benefits.",
        }

        prompt = prompts.get(content_type, f"Write {content_type} about {topic} in {style} style.")

        result = await self.llm.generate(prompt, max_tokens=2000, temperature=0.7)

        if result["status"] == "success":
            content = result["output"]
            word_count = len(content.split())
            return {
                "status": "success",
                "content_type": content_type,
                "topic": topic,
                "content": content,
                "model": result["model"],
                "word_count": word_count,
            }
        return result


class ContentPublishingTool(Tool):
    """Publish content to various platforms via webhook or native APIs"""

    def __init__(self):
        super().__init__(
            name="publish_content",
            description="Publish content to webhook or social media platforms",
            cost=0.005,
        )
        # OAuth 1.0a credentials required to POST tweets (Bearer token is read-only)
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        self.linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")

    async def execute(
        self,
        platform: str = "webhook",
        content: str = "",
        media_urls: Optional[list] = None,
        webhook_url: Optional[str] = None,
        affiliate_url: Optional[str] = None,
        campaign_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        from config.settings import settings
        target_url = webhook_url or settings.webhook_publish_url

        # Auto-append affiliate link to content if provided and not already present
        final_content = content
        if affiliate_url and affiliate_url not in content:
            final_content = f"{content}\n\n{affiliate_url}"

        if platform == "webhook":
            return await self._publish_webhook(final_content, target_url, affiliate_url, campaign_id, agent_id)
        elif platform == "twitter":
            return await self._publish_twitter(final_content, media_urls, affiliate_url, campaign_id, agent_id)
        elif platform == "linkedin":
            return await self._publish_linkedin(final_content, affiliate_url, campaign_id, agent_id)
        else:
            return {"status": "failed", "error": f"Platform '{platform}' not supported"}

    async def _publish_webhook(self, content: str, webhook_url: Optional[str], affiliate_url: Optional[str] = None, campaign_id: Optional[str] = None, agent_id: Optional[str] = None) -> Dict[str, Any]:
        if not webhook_url:
            return {
                "status": "failed",
                "platform": "webhook",
                "error": "Webhook URL not configured. Set WEBHOOK_PUBLISH_URL in .env or pass webhook_url.",
                "revenue": 0.0,
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "content": content,
                    "affiliate_url": affiliate_url,
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                }
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                return {
                    "status": "success",
                    "platform": "webhook",
                    "response": response.json(),
                    "revenue": 0.0,
                    "content": content,
                    "url": webhook_url,
                    "note": "Content published; revenue tracked via affiliate conversions",
                    "affiliate_url_tracked": bool(affiliate_url),
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                }
        except Exception as e:
            return {"status": "failed", "platform": "webhook", "error": str(e), "revenue": 0.0}

    async def _publish_twitter(self, content: str, media_urls: Optional[list], affiliate_url: Optional[str] = None, campaign_id: Optional[str] = None, agent_id: Optional[str] = None) -> Dict[str, Any]:
        missing = [
            name for name, val in {
                "TWITTER_API_KEY": self.twitter_api_key,
                "TWITTER_API_SECRET": self.twitter_api_secret,
                "TWITTER_ACCESS_TOKEN": self.twitter_access_token,
                "TWITTER_ACCESS_TOKEN_SECRET": self.twitter_access_token_secret,
            }.items() if not val
        ]
        if missing:
            return {
                "status": "failed",
                "platform": "twitter",
                "error": (
                    f"X OAuth 1.0a not fully configured. Missing: {', '.join(missing)}. "
                    "The Bearer token (TWITTER_BEARER_TOKEN) is read-only and cannot post. "
                    "Generate an API v2 access token + secret on the X Developer Portal "
                    "(developer.x.com > your app > User authentication settings > enable 'Read and write'; "
                    "then Keys and tokens > regenerate Access Token and Secret) and add them to .env."
                ),
                "revenue": 0.0,
            }

        try:
            # X's API host is still api.twitter.com — only the marketing/web domain (and developer portal) rebranded to x.com.
            auth_headers = _oauth1_auth_header("POST", "https://api.twitter.com/2/tweets")
            headers = {**auth_headers, "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.twitter.com/2/tweets",
                    headers=headers,
                    json={"text": content[:280]},
                )
                response.raise_for_status()
                tweet_id = response.json().get("data", {}).get("id")
                return {
                    "status": "success",
                    "platform": "twitter",
                    "tweet_id": tweet_id,
                    "revenue": 0.0,
                    "content": content,
                    "url": f"https://x.com/i/status/{tweet_id}" if tweet_id else None,
                    "note": "Posted via OAuth 1.0a. Social posts build brand awareness; revenue tracked via affiliate conversions separately",
                    "affiliate_url_tracked": bool(affiliate_url),
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                }
        except Exception as e:
            # Surface the API response body so missing-permission / wrong-signature failures are debuggable
            detail = str(e)
            if getattr(e, "response", None) is not None and e.response is not None:
                detail = f"{detail} — {e.response.text[:300]}"
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 403:
                detail = (f"403: the app likely lacks 'Read and write' permission "
                          f"(OAuth 1.0a posting requires it). {detail}")
            return {"status": "failed", "platform": "twitter", "error": detail, "revenue": 0.0}

    async def _publish_linkedin(self, content: str, affiliate_url: Optional[str] = None, campaign_id: Optional[str] = None, agent_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.linkedin_token:
            return {"status": "failed", "error": "LinkedIn API not configured", "revenue": 0.0}

        person_id = os.getenv("LINKEDIN_PERSON_ID")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {self.linkedin_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "author": f"urn:li:person:{person_id}" if person_id else "urn:li:person:UNKNOWN",
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
                    "revenue": 0.0,
                    "content": content,
                    "url": f"https://linkedin.com/feed/update/{post_id}" if post_id else None,
                    "note": "Social media posts build brand awareness; revenue tracked via affiliate conversions separately",
                    "affiliate_url_tracked": bool(affiliate_url),
                    "campaign_id": campaign_id,
                    "agent_id": agent_id,
                }
        except Exception as e:
            return {"status": "failed", "error": str(e), "revenue": 0.0}


class SocialMediaAnalyticsTool(Tool):
    """Get analytics for published content"""

    def __init__(self):
        super().__init__(
            name="social_analytics",
            description="Get analytics for published social media content",
            cost=0.001,
        )

    async def execute(self, platform: str, content_id: str, **kwargs) -> Dict[str, Any]:
        # Mock implementation - would integrate with platform APIs
        return {
            "status": "success",
            "platform": platform,
            "content_id": content_id,
            "metrics": {
                "impressions": 0,
                "engagements": 0,
                "clicks": 0,
                "conversions": 0,
            },
        }


# Register tools
tool_registry.register(ContentGenerationTool())
tool_registry.register(ContentPublishingTool())
tool_registry.register(SocialMediaAnalyticsTool())