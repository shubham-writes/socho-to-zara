"""
Stage 3: Background Visuals — Pexels Video Fetcher

Fetches high-quality, royalty-free portrait-orientation background videos
from the Pexels API. Caches downloads locally to minimize API usage.
"""

import logging
import random
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"


def _search_pexels_videos(
    api_key: str,
    query: str,
    orientation: str = "portrait",
    per_page: int = 10,
) -> list[dict]:
    """
    Search Pexels for videos matching the query.
    Returns a list of video metadata dicts.
    """
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "orientation": orientation,
        "per_page": per_page,
        "size": "medium",  # medium quality is fine for Reels
    }

    try:
        response = requests.get(PEXELS_VIDEO_SEARCH_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("videos", [])
    except requests.RequestException as e:
        logger.warning("Pexels API error: %s", e)
        return []


def _pick_best_video_file(video: dict) -> str | None:
    """
    From a Pexels video object, pick the best download URL.
    Prefers HD quality files.
    """
    video_files = video.get("video_files", [])
    if not video_files:
        return None

    # Sort by quality: prefer HD, then SD
    hd_files = [f for f in video_files if f.get("quality") == "hd"]
    sd_files = [f for f in video_files if f.get("quality") == "sd"]

    # Prefer portrait-ish aspect ratios
    candidates = hd_files or sd_files or video_files

    # Try to find one closest to 9:16 portrait
    best = None
    best_score = float("inf")
    target_ratio = 9 / 16  # 0.5625

    for f in candidates:
        w = f.get("width", 0)
        h = f.get("height", 0)
        if h == 0:
            continue
        ratio = w / h
        score = abs(ratio - target_ratio)
        if score < best_score:
            best_score = score
            best = f

    if best is None:
        best = candidates[0]

    return best.get("link")


def _download_video(url: str, output_path: Path) -> bool:
    """
    Download a video from a URL to the specified path.
    """
    try:
        logger.info("⬇️  Downloading video from Pexels...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info("✅ Downloaded: %s (%.1f MB)", output_path.name, size_mb)
        return True
    except requests.RequestException as e:
        logger.error("Download failed: %s", e)
        return False


def _get_cached_videos(cache_dir: Path) -> list[Path]:
    """Get list of previously downloaded videos."""
    return list(cache_dir.glob("*.mp4"))


def fetch_background_video(
    search_query: str = "",
    api_key: str = "",
    output_path: Path | None = None,
) -> Path | None:
    """
    Fetch a background video for the Reel.

    Strategy:
      1. If API key available → search Pexels for the query
      2. If no API key or search fails → pick from cached videos

    Args:
        search_query: Pexels search query (from riddle data)
        api_key: Pexels API key
        output_path: where to save the video

    Returns:
        Path to the downloaded/cached video, or None if failed
    """
    from config import BACKGROUNDS_DIR, PEXELS_API_KEY, PEXELS_SEARCH_QUERIES

    api_key = api_key or PEXELS_API_KEY

    if output_path is None:
        output_path = BACKGROUNDS_DIR / "background.mp4"

    # Strategy 1: Try Pexels API
    if api_key:
        query = search_query or random.choice(PEXELS_SEARCH_QUERIES)
        logger.info("🔍 Searching Pexels for: '%s'", query)

        videos = _search_pexels_videos(api_key, query)

        if videos:
            # Pick a random video from results for variety
            video = random.choice(videos[:5])  # Top 5 results
            download_url = _pick_best_video_file(video)

            if download_url:
                if _download_video(download_url, output_path):
                    # Also cache a copy with a unique name
                    cache_name = f"pexels_{video.get('id', 'unknown')}.mp4"
                    cache_path = BACKGROUNDS_DIR / cache_name
                    if not cache_path.exists():
                        import shutil
                        shutil.copy2(output_path, cache_path)
                    return output_path

        logger.warning("Pexels search returned no usable videos")

    # Strategy 2: Fall back to cached videos
    cached = _get_cached_videos(BACKGROUNDS_DIR)
    if cached:
        chosen = random.choice(cached)
        if chosen != output_path:
            import shutil
            shutil.copy2(chosen, output_path)
        logger.info("📂 Using cached video: %s", chosen.name)
        return output_path

    logger.error("❌ No background video available — provide a PEXELS_API_KEY or place .mp4 files in %s", BACKGROUNDS_DIR)
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import config

    result = fetch_background_video(
        search_query="dark abstract mystery",
        api_key=config.PEXELS_API_KEY,
    )
    if result:
        print(f"✅ Background video: {result}")
    else:
        print("❌ Failed to fetch background video")
