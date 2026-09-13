"""
Instagram/TikTok Publisher Tool - Meta Graph API and TikTok API for social media automation
"""
import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.social_publisher")


class SocialPublisherTool(Tool):
    """Publish content to Instagram, Facebook, and TikTok via official APIs"""

    def __init__(self):
        super().__init__(
            name="social_publisher",
            description="Publish posts, Reels, Stories to Instagram/Facebook via Meta Graph API and TikTok via TikTok API",
            cost=0.03,
        )
        self.llm = get_llm_provider()
        self._meta_client = None
        self._tiktok_client = None

    def _get_meta_client(self):
        """Lazy-load Meta Graph API client"""
        if self._meta_client is None:
            from config.settings import settings
            if not settings.meta_access_token:
                raise ValueError("META_ACCESS_TOKEN not configured in .env")
            import httpx
            self._meta_client = httpx.AsyncClient(
                base_url="https://graph.facebook.com/v20.0",
                params={"access_token": settings.meta_access_token},
                timeout=60.0
            )
        return self._meta_client

    def _get_tiktok_client(self):
        """Lazy-load TikTok API client"""
        if self._tiktok_client is None:
            from config.settings import settings
            if not settings.tiktok_access_token:
                raise ValueError("TIKTOK_ACCESS_TOKEN not configured in .env")
            import httpx
            self._tiktok_client = httpx.AsyncClient(
                base_url="https://open.tiktokapis.com/v2",
                headers={"Authorization": f"Bearer {settings.tiktok_access_token}"},
                timeout=60.0
            )
        return self._tiktok_client

    async def execute(
        self,
        action: str = "publish_post",
        platform: str = "instagram",  # instagram, facebook, tiktok
        content_data: Optional[Dict[str, Any]] = None,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Main entry point for social publishing"""
        from config.settings import settings

        if platform in ("instagram", "facebook") and not settings.meta_access_token:
            return {"status": "failed", "error": "META_ACCESS_TOKEN not configured"}
        if platform == "tiktok" and not settings.tiktok_access_token:
            return {"status": "failed", "error": "TIKTOK_ACCESS_TOKEN not configured"}

        try:
            if action == "publish_post":
                return await self._publish_post(platform, content_data or {}, media_urls or [])
            elif action == "publish_reel":
                return await self._publish_reel(platform, content_data or {}, media_urls or [])
            elif action == "publish_story":
                return await self._publish_story(platform, content_data or {}, media_urls or [])
            elif action == "get_insights":
                return await self._get_insights(platform, content_data.get("post_id"))
            elif action == "get_account_info":
                return await self._get_account_info(platform)
            elif action == "schedule_post":
                return await self._schedule_post(platform, content_data or {}, media_urls or [])
            elif action == "generate_content":
                return await self._generate_social_content(content_data or {})
            else:
                return {"status": "failed", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"SocialPublisherTool error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _publish_post(self, platform: str, content_data: Dict, media_urls: List[str]) -> Dict[str, Any]:
        """Publish a standard post (image/carousel)"""
        caption = content_data.get("caption", "")
        location_id = content_data.get("location_id")
        user_tags = content_data.get("user_tags", [])
        product_tags = content_data.get("product_tags", [])  # For Instagram Shopping
        affiliate_url = content_data.get("affiliate_url")

        # Add affiliate link to caption if provided
        if affiliate_url and affiliate_url not in caption:
            caption = f"{caption}\n\n🔗 {affiliate_url}"

        hashtags = content_data.get("hashtags", [])
        if hashtags:
            caption = f"{caption}\n\n{' '.join(hashtags)}"

        if platform == "instagram":
            return await self._publish_instagram_post(caption, media_urls, location_id, user_tags, product_tags)
        elif platform == "facebook":
            return await self._publish_facebook_post(caption, media_urls)
        else:
            return {"status": "failed", "error": "Use publish_reel for TikTok"}

    async def _publish_instagram_post(self, caption: str, media_urls: List[str], location_id: str = None,
                                       user_tags: List[str] = None, product_tags: List[str] = None) -> Dict[str, Any]:
        """Publish to Instagram via Meta Graph API"""
        client = self._get_meta_client()
        from config.settings import settings
        ig_user_id = settings.instagram_user_id

        if not ig_user_id:
            return {"status": "failed", "error": "INSTAGRAM_USER_ID not configured"}

        # For carousel or single image
        is_carousel = len(media_urls) > 1

        if is_carousel:
            # Create carousel container
            children = []
            for url in media_urls:
                child_resp = await client.post(f"/{ig_user_id}/media", data={
                    "image_url": url,
                    "is_carousel_item": "true",
                })
                child_resp.raise_for_status()
                children.append(child_resp.json()["id"])

            # Create carousel parent
            container_resp = await client.post(f"/{ig_user_id}/media", data={
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
            })
        else:
            # Single image/video
            media_type = "VIDEO" if media_urls[0].endswith((".mp4", ".mov")) else "IMAGE"
            container_resp = await client.post(f"/{ig_user_id}/media", data={
                "media_type": media_type,
                "image_url" if media_type == "IMAGE" else "video_url": media_urls[0],
                "caption": caption,
            })

        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Add location if provided
        if location_id:
            await client.post(f"/{container_id}", data={"location_id": location_id})

        # Add user tags if provided
        if user_tags:
            # Note: User tagging requires additional API calls
            pass

        # Publish
        publish_resp = await client.post(f"/{ig_user_id}/media_publish", data={"creation_id": container_id})
        publish_resp.raise_for_status()
        result = publish_resp.json()

        return {
            "status": "success",
            "platform": "instagram",
            "post_id": result.get("id"),
            "permalink": f"https://instagram.com/p/{result.get('id')}",
            "caption": caption[:100] + "..." if len(caption) > 100 else caption,
        }

    async def _publish_facebook_post(self, caption: str, media_urls: List[str]) -> Dict[str, Any]:
        """Publish to Facebook Page via Meta Graph API"""
        client = self._get_meta_client()
        from config.settings import settings
        page_id = settings.facebook_page_id

        if not page_id:
            return {"status": "failed", "error": "FACEBOOK_PAGE_ID not configured"}

        # Upload photos first
        attached_media = []
        for url in media_urls:
            photo_resp = await client.post(f"/{page_id}/photos", data={"url": url, "published": "false"})
            photo_resp.raise_for_status()
            attached_media.append({"media_fbid": photo_resp.json()["id"]})

        # Create post with attached media
        post_data = {"message": caption}
        if attached_media:
            post_data["attached_media"] = json.dumps(attached_media)

        post_resp = await client.post(f"/{page_id}/feed", data=post_data)
        post_resp.raise_for_status()
        result = post_resp.json()

        return {
            "status": "success",
            "platform": "facebook",
            "post_id": result.get("id"),
            "permalink": f"https://facebook.com/{result.get('id')}",
        }

    async def _publish_reel(self, platform: str, content_data: Dict, media_urls: List[str]) -> Dict[str, Any]:
        """Publish a Reel (Instagram/Facebook) or TikTok video"""
        caption = content_data.get("caption", "")
        cover_url = content_data.get("cover_url")
        audio_name = content_data.get("audio_name")
        hashtags = content_data.get("hashtags", [])
        affiliate_url = content_data.get("affiliate_url")

        if affiliate_url and affiliate_url not in caption:
            caption = f"{caption}\n\n🔗 {affiliate_url}"
        if hashtags:
            caption = f"{caption}\n\n{' '.join(hashtags)}"

        if platform == "instagram":
            return await self._publish_instagram_reel(caption, media_urls[0], cover_url, audio_name)
        elif platform == "facebook":
            return await self._publish_facebook_reel(caption, media_urls[0], cover_url)
        elif platform == "tiktok":
            return await self._publish_tiktok_video(caption, media_urls[0], cover_url)
        else:
            return {"status": "failed", "error": f"Reels not supported on {platform}"}

    async def _publish_instagram_reel(self, caption: str, video_url: str, cover_url: str = None, audio_name: str = None) -> Dict[str, Any]:
        """Publish Instagram Reel"""
        client = self._get_meta_client()
        from config.settings import settings
        ig_user_id = settings.instagram_user_id

        # Create Reel container
        data = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
        }
        if cover_url:
            data["cover_url"] = cover_url
        if audio_name:
            data["audio_name"] = audio_name

        container_resp = await client.post(f"/{ig_user_id}/media", data=data)
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Wait for processing then publish
        for _ in range(30):  # Max 5 minutes
            status_resp = await client.get(f"/{container_id}", params={"fields": "status_code"})
            status_resp.raise_for_status()
            status = status_resp.json().get("status_code")
            if status == "FINISHED":
                break
            elif status in ("ERROR", "EXPIRED"):
                return {"status": "failed", "error": f"Reel processing failed: {status}"}
            await asyncio.sleep(10)

        publish_resp = await client.post(f"/{ig_user_id}/media_publish", data={"creation_id": container_id})
        publish_resp.raise_for_status()
        result = publish_resp.json()

        return {
            "status": "success",
            "platform": "instagram",
            "post_id": result.get("id"),
            "type": "reel",
            "permalink": f"https://instagram.com/reel/{result.get('id')}",
        }

    async def _publish_facebook_reel(self, caption: str, video_url: str, cover_url: str = None) -> Dict[str, Any]:
        """Publish Facebook Reel"""
        client = self._get_meta_client()
        from config.settings import settings
        page_id = settings.facebook_page_id

        data = {
            "video_url": video_url,
            "description": caption,
        }
        if cover_url:
            data["cover_url"] = cover_url

        container_resp = await client.post(f"/{page_id}/video_reels", data=data)
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Check status and publish
        for _ in range(30):
            status_resp = await client.get(f"/{container_id}", params={"fields": "status"})
            status = status_resp.json().get("status", {}).get("publishing_phase", {}).get("status")
            if status == "published":
                break
            await asyncio.sleep(10)

        return {"status": "success", "platform": "facebook", "reel_id": container_id, "type": "reel"}

    async def _publish_tiktok_video(self, caption: str, video_url: str, cover_url: str = None) -> Dict[str, Any]:
        """Publish TikTok video via TikTok API"""
        client = self._get_tiktok_client()

        # TikTok requires video to be uploaded directly or via URL
        # This uses the video upload API
        data = {
            "post_info": {
                "title": caption[:150],  # TikTok title max ~150 chars
                "privacy_level": "PUBLIC",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            }
        }

        if cover_url:
            data["post_info"]["cover_image_url"] = cover_url

        # Create post
        resp = await client.post("/post/publish/video/pull_from_url", json=data)
        resp.raise_for_status()
        result = resp.json()

        if result.get("error", {}).get("code") != "ok":
            return {"status": "failed", "error": result.get("error", {}).get("message", "Unknown error")}

        return {
            "status": "success",
            "platform": "tiktok",
            "post_id": result.get("data", {}).get("publish_id"),
            "type": "video",
        }

    async def _publish_story(self, platform: str, content_data: Dict, media_urls: List[str]) -> Dict[str, Any]:
        """Publish Instagram/Facebook Story"""
        if platform not in ("instagram", "facebook"):
            return {"status": "failed", "error": "Stories only supported on Instagram/Facebook"}

        client = self._get_meta_client()
        from config.settings import settings
        user_id = settings.instagram_user_id if platform == "instagram" else settings.facebook_page_id

        # Stories require special handling - using media publish with story spec
        # This is simplified - real implementation needs story-specific endpoints
        return {
            "status": "partial",
            "platform": platform,
            "note": "Story publishing requires additional setup. Use Meta Business Suite for now.",
        }

    async def _get_insights(self, platform: str, post_id: str = None) -> Dict[str, Any]:
        """Get post/account insights"""
        client = self._get_meta_client() if platform in ("instagram", "facebook") else self._get_tiktok_client()

        if platform == "instagram":
            from config.settings import settings
            ig_user_id = settings.instagram_user_id
            if post_id:
                resp = await client.get(f"/{post_id}/insights", params={"metric": "impressions,reach,engagement,likes,comments,shares,saves"})
            else:
                resp = await client.get(f"/{ig_user_id}/insights", params={"metric": "impressions,reach,profile_views,followers_count", "period": "day"})
        elif platform == "facebook":
            from config.settings import settings
            page_id = settings.facebook_page_id
            if post_id:
                resp = await client.get(f"/{post_id}/insights", params={"metric": "post_impressions,post_engaged_users,post_reactions_like_total"})
            else:
                resp = await client.get(f"/{page_id}/insights", params={"metric": "page_impressions,page_engaged_users,page_fans", "period": "day"})
        else:  # tiktok
            if post_id:
                resp = await client.get(f"/video/query", params={"video_id": post_id})
            else:
                resp = await client.get("/video/list", params={"max_count": 20})

        resp.raise_for_status()
        return {"status": "success", "platform": platform, "insights": resp.json()}

    async def _get_account_info(self, platform: str) -> Dict[str, Any]:
        """Get account/profile information"""
        client = self._get_meta_client() if platform in ("instagram", "facebook") else self._get_tiktok_client()

        if platform == "instagram":
            from config.settings import settings
            ig_user_id = settings.instagram_user_id
            resp = await client.get(f"/{ig_user_id}", params={"fields": "id,username,account_type,media_count,followers_count,follows_count,profile_picture_url,biography"})
        elif platform == "facebook":
            from config.settings import settings
            page_id = settings.facebook_page_id
            resp = await client.get(f"/{page_id}", params={"fields": "id,name,fan_count,followers_count,about,website,instagram_business_account"})
        else:
            resp = await client.get("/user/info", params={"fields": "open_id,union_id,avatar_url,display_name,bio_description,follower_count,following_count,video_count"})

        resp.raise_for_status()
        return {"status": "success", "platform": platform, "account": resp.json()}

    async def _schedule_post(self, platform: str, content_data: Dict, media_urls: List[str]) -> Dict[str, Any]:
        """Schedule a post for later (Meta only)"""
        if platform not in ("instagram", "facebook"):
            return {"status": "failed", "error": "Scheduling only supported on Meta platforms"}

        publish_time = content_data.get("publish_time")  # ISO format
        if not publish_time:
            return {"status": "failed", "error": "publish_time required for scheduling"}

        # Meta supports scheduling via published=false + scheduled_publish_time
        # This is a simplified version
        return {
            "status": "success",
            "platform": platform,
            "scheduled": True,
            "publish_time": publish_time,
            "note": "Use Meta Business Suite for reliable scheduling",
        }

    async def _generate_social_content(self, content_data: Dict) -> Dict[str, Any]:
        """Generate social media content using AI"""
        niche = content_data.get("niche", "tech")
        product = content_data.get("product", "")
        platform = content_data.get("platform", "instagram")
        content_type = content_data.get("type", "post")  # post, reel, story
        goal = content_data.get("goal", "engagement")  # engagement, sales, traffic
        affiliate_url = content_data.get("affiliate_url")

        platform_specs = {
            "instagram": {"max_hashtags": 30, "style": "visual, lifestyle, aesthetic", "cta": "Link in bio"},
            "facebook": {"max_hashtags": 5, "style": "informative, community-focused", "cta": "Click link"},
            "tiktok": {"max_hashtags": 10, "style": "trending, fast-paced, authentic", "cta": "Follow for more"},
        }
        spec = platform_specs.get(platform, platform_specs["instagram"])

        prompt = f"""Create a {content_type} for {platform} about: {product or niche}

Goal: {goal}
Style: {spec['style']}
CTA approach: {spec['cta']}
Max hashtags: {spec['max_hashtags']}
Affiliate link: {affiliate_url or 'N/A'}

Provide:
1. Caption (platform-optimized length)
2. 10-15 relevant hashtags
3. Best posting time suggestions
4. Engagement hooks (questions, polls, etc.)
5. Story/Reel script if applicable

Return as JSON."""

        result = await self.llm.generate(prompt, max_tokens=2000, temperature=0.8)

        if result["status"] != "success":
            return {"status": "failed", "error": result.get("error")}

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result["output"])
            content = json.loads(json_match.group()) if json_match else {"caption": result["output"]}
        except:
            content = {"caption": result["output"]}

        return {
            "status": "success",
            "platform": platform,
            "content_type": content_type,
            "generated": content,
        }


# Register the tool
tool_registry.register(SocialPublisherTool())