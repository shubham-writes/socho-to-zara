"""
Stage 5: Auto-Posting — Instagram Graph API Uploader

Uploads finished Reels to Instagram via the Graph API.
Requires a Business/Creator account with a long-lived access token.

Flow:
  1. Video must be hosted at a public URL (configured in .env)
  2. Create media container → POST /{ig-user-id}/media
  3. Poll status until FINISHED
  4. Publish → POST /{ig-user-id}/media_publish
"""

import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def _create_media_container(
    ig_user_id: str,
    access_token: str,
    video_url: str,
    caption: str,
) -> str | None:
    """
    Step 1: Create a media container for the Reel.
    Returns the container/creation ID or None on failure.
    """
    url = f"{GRAPH_API_BASE}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
    }

    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        container_id = data.get("id")
        logger.info("📦 Media container created: %s", container_id)
        return container_id
    except requests.RequestException as e:
        logger.error("Failed to create media container: %s", e)
        if hasattr(e, "response") and e.response is not None:
            logger.error("Response: %s", e.response.text)
        return None


def _check_container_status(
    container_id: str,
    access_token: str,
) -> str:
    """
    Step 2: Check the upload/processing status of the container.
    Returns status string: FINISHED, IN_PROGRESS, ERROR, EXPIRED
    """
    url = f"{GRAPH_API_BASE}/{container_id}"
    params = {
        "fields": "status_code,status",
        "access_token": access_token,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        status = data.get("status_code", "UNKNOWN")
        logger.info("⏳ Container %s status: %s", container_id, status)
        return status
    except requests.RequestException as e:
        logger.error("Status check failed: %s", e)
        return "ERROR"


def _publish_container(
    ig_user_id: str,
    access_token: str,
    container_id: str,
) -> str | None:
    """
    Step 3: Publish the processed container as a Reel.
    Returns the published media ID or None.
    """
    url = f"{GRAPH_API_BASE}/{ig_user_id}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": access_token,
    }

    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        media_id = data.get("id")
        logger.info("🎉 Reel published! Media ID: %s", media_id)
        return media_id
    except requests.RequestException as e:
        logger.error("Failed to publish Reel: %s", e)
        if hasattr(e, "response") and e.response is not None:
            logger.error("Response: %s", e.response.text)
        return None


def _build_caption(riddle_data: dict) -> str:
    """
    Build the Instagram caption with riddle content and hashtags.
    """
    hook = riddle_data.get("hook", "")
    riddle = riddle_data.get("riddle", "")
    answer = riddle_data.get("answer", "")
    hashtags = riddle_data.get(
        "hashtags",
        "#riddle #puzzle #brainteaser #riddles #IQ #logic #thinkhard #canyousolveit #viral #reels"
    )

    caption = (
        f"🧩 {hook}\n\n"
        f"{riddle}\n\n"
        f"💡 Answer: {answer}\n\n"
        f"Tag someone who needs to try this! 👇\n\n"
        f"{hashtags}"
    )
    return caption


def post_to_instagram(
    video_path: Path,
    riddle_data: dict,
    access_token: str = "",
    ig_user_id: str = "",
    video_host_base_url: str = "",
    max_wait_seconds: int = 120,
) -> str | None:
    """
    Upload and publish a Reel to Instagram.

    Args:
        video_path: local path to the .mp4 file
        riddle_data: dict with hook, riddle, answer, hashtags
        access_token: Instagram Graph API access token
        ig_user_id: Instagram Business account user ID
        video_host_base_url: base URL where the video is hosted publicly
        max_wait_seconds: max time to wait for processing

    Returns:
        Published media ID or None
    """
    from config import IG_ACCESS_TOKEN, IG_USER_ID, VIDEO_HOST_BASE_URL

    access_token = access_token or IG_ACCESS_TOKEN
    ig_user_id = ig_user_id or IG_USER_ID
    video_host_base_url = video_host_base_url or VIDEO_HOST_BASE_URL

    # Validate credentials
    if not access_token or not ig_user_id:
        logger.error("❌ Instagram credentials not configured. Set IG_ACCESS_TOKEN and IG_USER_ID in .env")
        return None

    if not video_host_base_url:
        logger.error(
            "❌ VIDEO_HOST_BASE_URL not configured. "
            "Instagram requires the video at a public URL. See setup_guide.md"
        )
        return None

    # Build public video URL
    video_url = f"{video_host_base_url.rstrip('/')}/{video_path.name}"
    logger.info("🌐 Video URL: %s", video_url)

    # Build caption
    caption = _build_caption(riddle_data)

    # Step 1: Create container
    container_id = _create_media_container(ig_user_id, access_token, video_url, caption)
    if not container_id:
        return None

    # Step 2: Wait for processing
    elapsed = 0
    poll_interval = 5
    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval
        status = _check_container_status(container_id, access_token)

        if status == "FINISHED":
            break
        elif status in ("ERROR", "EXPIRED"):
            logger.error("❌ Container processing failed with status: %s", status)
            return None

    if status != "FINISHED":
        logger.error("❌ Timed out waiting for container processing (%ds)", max_wait_seconds)
        return None

    # Step 3: Publish
    media_id = _publish_container(ig_user_id, access_token, container_id)
    return media_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Instagram poster module loaded.")
    print("Configure IG_ACCESS_TOKEN, IG_USER_ID, and VIDEO_HOST_BASE_URL in .env")
    print("Then call post_to_instagram() to publish a Reel.")
