import httpx
from config import settings
from database import db
import logging

logger = logging.getLogger(__name__)


class SocialPublisher:
    """Handles publishing approved content to social media platforms."""

    # ─── FACEBOOK ────────────────────────────────────────────────────────────

    async def publish_facebook(self, content: str,
                                 image_url: str = None) -> dict:
        if not settings.meta_access_token or not settings.meta_page_id:
            return {"success": False, "error": "Meta credentials not configured"}

        url = f"https://graph.facebook.com/v19.0/{settings.meta_page_id}/feed"
        payload = {
            "message": content,
            "access_token": settings.meta_access_token
        }
        if image_url:
            payload["link"] = image_url

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload)
            data = resp.json()

        if "id" in data:
            return {"success": True, "post_id": data["id"], "platform": "facebook"}
        return {"success": False, "error": data.get("error", {}).get("message"), "platform": "facebook"}

    # ─── INSTAGRAM ───────────────────────────────────────────────────────────

    async def publish_instagram(self, caption: str,
                                  image_url: str = None) -> dict:
        if not settings.meta_access_token or not settings.instagram_account_id:
            return {"success": False, "error": "Instagram credentials not configured"}

        if not image_url:
            return {"success": False, "error": "Instagram requires an image URL"}

        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            container_url = f"https://graph.facebook.com/v19.0/{settings.instagram_account_id}/media"
            container_resp = await client.post(container_url, data={
                "image_url": image_url,
                "caption": caption,
                "access_token": settings.meta_access_token
            })
            container_data = container_resp.json()

            if "id" not in container_data:
                return {"success": False, "error": container_data.get("error", {}).get("message"), "platform": "instagram"}

            # Step 2: Publish container
            publish_url = f"https://graph.facebook.com/v19.0/{settings.instagram_account_id}/media_publish"
            publish_resp = await client.post(publish_url, data={
                "creation_id": container_data["id"],
                "access_token": settings.meta_access_token
            })
            publish_data = publish_resp.json()

        if "id" in publish_data:
            return {"success": True, "post_id": publish_data["id"], "platform": "instagram"}
        return {"success": False, "error": publish_data.get("error", {}).get("message"), "platform": "instagram"}

    # ─── TIKTOK ──────────────────────────────────────────────────────────────

    async def publish_tiktok(self, caption: str,
                               video_url: str = None) -> dict:
        if not settings.tiktok_access_token:
            return {"success": False, "error": "TikTok credentials not configured"}

        # TikTok Content Posting API v2
        url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {settings.tiktok_access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            data = resp.json()

        if data.get("error", {}).get("code") == "ok":
            return {"success": True, "publish_id": data["data"]["publish_id"], "platform": "tiktok"}
        return {"success": False, "error": data.get("error", {}).get("message"), "platform": "tiktok"}

    # ─── UNIFIED PUBLISH ─────────────────────────────────────────────────────

    async def publish_to_platforms(self, publication_id: str,
                                    platforms: list, content: str,
                                    media_url: str = None) -> list:
        results = []

        for platform in platforms:
            try:
                if platform == "facebook":
                    result = await self.publish_facebook(content, media_url)
                elif platform == "instagram":
                    result = await self.publish_instagram(content, media_url)
                elif platform == "tiktok":
                    result = await self.publish_tiktok(content, media_url)
                else:
                    result = {"success": False, "error": f"Unknown platform: {platform}"}

                results.append(result)

                if result["success"]:
                    db.mark_published(publication_id, result.get("post_id") or result.get("publish_id"))
                    logger.info(f"Published to {platform}: {result}")
                else:
                    logger.error(f"Failed to publish to {platform}: {result}")

            except Exception as e:
                logger.error(f"Error publishing to {platform}: {e}")
                results.append({"success": False, "error": str(e), "platform": platform})

        return results
