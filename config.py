"""
Central configuration for the RiddleAnPuzzle pipeline.
Loads environment variables and defines project-wide paths and settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env ───────────────────────────────────────────────────────────────
load_dotenv()

# ─── Project Root ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()

# ─── Output Directories ─────────────────────────────────────────────────────
OUTPUT_DIR      = PROJECT_ROOT / "output"
AUDIO_DIR       = OUTPUT_DIR / "audio"
BACKGROUNDS_DIR = OUTPUT_DIR / "backgrounds"
REELS_DIR       = OUTPUT_DIR / "reels"
FONTS_DIR       = PROJECT_ROOT / "fonts"
ASSETS_DIR      = PROJECT_ROOT / "assets"
BG_MUSIC_DIR    = PROJECT_ROOT / "bg_music"

# Create directories if they don't exist
for d in [AUDIO_DIR, BACKGROUNDS_DIR, REELS_DIR, FONTS_DIR, ASSETS_DIR, BG_MUSIC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Asset Paths ---
TIMER_AUDIO_PATH = ASSETS_DIR / "count_down_sound.mp3"
MUSIC_TRACKER_FILE = PROJECT_ROOT / "music_tracker.json"

# ─── API Keys ────────────────────────────────────────────────────────────────
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "")
PEXELS_API_KEY       = os.getenv("PEXELS_API_KEY", "")
VIDEO_HOST_BASE_URL  = os.getenv("VIDEO_HOST_BASE_URL", "")

# ─── YouTube Credentials ─────────────────────────────────────────────────────
YOUTUBE_CLIENT_SECRET_FILE = PROJECT_ROOT / "client_secret.json"
YOUTUBE_TOKEN_FILE         = PROJECT_ROOT / "token.json"

# ─── Telegram Bot Secrets ──────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN         = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID           = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── TTS Settings ────────────────────────────────────────────────────────────
TTS_VOICE = os.getenv("TTS_VOICE", "hi-IN-MadhurNeural")
TTS_RATE  = os.getenv("TTS_RATE", "+5%")

# ─── Video Settings ──────────────────────────────────────────────────────────
VIDEO_WIDTH   = 1080
VIDEO_HEIGHT  = 1920
VIDEO_FPS     = 30
VIDEO_CODEC   = "libx264"
AUDIO_CODEC   = "aac"

# ─── Font Settings ───────────────────────────────────────────────────────────
CAPTION_FONT       = str(FONTS_DIR / "TiroDevanagariHindi-Regular.ttf")
CAPTION_COLOR          = "white"
CAPTION_HIGHLIGHT      = "#FFE600"   # vivid yellow (was plain "yellow")
CAPTION_STROKE_COLOR   = "black"
CAPTION_STROKE_WIDTH   = 5           # increased from 3 → bolder outline
CAPTION_FONTSIZE       = 72          # slightly larger for readability

# ─── Content Settings ────────────────────────────────────────────────────────
USED_RIDDLES_LOG = PROJECT_ROOT / "generators" / "used_riddles.json"
RIDDLES_BANK     = PROJECT_ROOT / "generators" / "riddles_bank.json"

# ─── Pexels Search Keywords ─────────────────────────────────────────────────
PEXELS_SEARCH_QUERIES = [
    "mystery dark abstract",
    "warm cinematic India",
    "vintage paper texture dark",
    "subtle nature background moody",
    "traditional Indian art aesthetic",
    "night sky stars",
    "fire flames dark",
    "water droplets macro",
    "warm candle light dark",
    "neon lights city",
]

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_FILE = OUTPUT_DIR / "pipeline.log"
