"""
Publishing service.
Priority: try real API → if not configured, return ready-to-use package.
Supports: Facebook, Instagram (Meta Graph API), TikTok (basic).
"""
import logging
import requests
from config import settings

logger = logging.getLogger(__name__)


def _fb_post(content: str) -> dict:
    pid = getattr(settings, "meta_page_id", None)
    token = getattr(settings, "meta_access_token", None)
    if not pid or not token:
        return {"success": False, "reason": "no_keys"}
    try:
        url = f"https://graph.facebook.com/v19.0/{pid}/feed"
        r = requests.post(url, data={"message": content, "access_token": token}, timeout=15)
        data = r.json()
        if "id" in data:
            logger.info("[FB] Posted: %s", data["id"])
            return {"success": True, "post_id": data["id"]}
        err = data.get("error", {}).get("message", "Unknown error")
        return {"success": False, "reason": err}
    except Exception as e:
        return {"success": False, "reason": str(e)}


def _ig_post(content: str, image_url: str = None) -> dict:
    account_id = getattr(settings, "instagram_account_id", None)
    token = getattr(settings, "meta_access_token", None)
    if not account_id or not token:
        return {"success": False, "reason": "no_keys"}
    if not image_url:
        return {"success": False, "reason": "instagram_needs_image"}
    try:
        container_url = f"https://graph.facebook.com/v19.0/{account_id}/media"
        c = requests.post(container_url, data={
            "caption": content, "image_url": image_url, "access_token": token
        }, timeout=15).json()
        if "id" not in c:
            return {"success": False, "reason": c.get("error", {}).get("message")}
        pub_url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
        p = requests.post(pub_url, data={
            "creation_id": c["id"], "access_token": token
        }, timeout=15).json()
        if "id" in p:
            return {"success": True, "post_id": p["id"]}
        return {"success": False, "reason": p.get("error", {}).get("message")}
    except Exception as e:
        return {"success": False, "reason": str(e)}


def _ready_package(content: str, platform: str, task_title: str) -> dict:
    """Returns a structured ready-to-publish package when APIs aren't available."""
    char_count = len(content)
    limits = {"facebook": 63206, "instagram": 2200, "tiktok": 2200}
    within_limit = char_count <= limits.get(platform, 5000)
    return {
        "ready_to_publish": True,
        "platform": platform,
        "task_title": task_title,
        "content": content,
        "character_count": char_count,
        "within_platform_limit": within_limit,
        "instructions": f"העתק את התוכן ופרסם ב-{platform}",
    }


def publish_content(content: str, platform: str, task_title: str,
                    image_url: str = None) -> dict:
    """
    Try to publish to the requested platform(s).
    Returns dict with per-platform result + package fallback.
    """
    results = {}

    platforms = ["facebook", "instagram", "tiktok"] if platform == "all" else [platform]

    for p in platforms:
        if p == "facebook":
            r = _fb_post(content)
        elif p == "instagram":
            r = _ig_post(content, image_url)
        elif p == "tiktok":
            r = {"success": False, "reason": "tiktok_needs_video"}
        else:
            r = {"success": False, "reason": "unknown_platform"}

        if not r["success"]:
            r["package"] = _ready_package(content, p, task_title)
            logger.info("[PUBLISH] %s not published (%s) – package ready", p, r.get("reason"))
        else:
            logger.info("[PUBLISH] %s published – post_id=%s", p, r.get("post_id"))

        results[p] = r

    return results
