"""
Stage 1: Content Generation — Riddle Generator

Uses Google AI Studio (Gemini) free tier to generate engaging riddles.
Falls back to a pre-curated bank of 30 riddles if no API key is set
or if the API call fails.
"""

import json
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_json(path: Path) -> list | dict:
    """Safely load a JSON file."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_json(path: Path, data):
    """Write data to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _generate_with_gemini(api_key: str) -> dict | None:
    """
    Call Google AI Studio (Gemini 2.5 Flash) to generate a single riddle.
    Returns a dict with keys: hook, riddle, answer, search_query
    or None on failure.
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")

        prompt = """You are a viral social media content creator specializing in riddles and brain teasers.

Generate ONE highly engaging Hindi Paheli (Riddle) or Kahavat for an Instagram Reel. Return ONLY a valid JSON object with these exact keys:

{
  "hook": "A short, attention-grabbing Hindi hook phrase in Devanagari script (e.g., 'सिर्फ 2% लोग ही इसका जवाब दे पाते हैं!')",
  "riddle": "The full Hindi riddle text in Devanagari, clear and concise (2-3 sentences max)",
  "answer": "The Hindi answer in Devanagari, short and punchy (1-5 words, end with !)",
  "search_query": "3-4 English keywords for finding a moody/dark, warm cinematic, or vintage background video on Pexels"
}

Rules:
- The riddle must be culturally rich, classic, or clever
- The hook must create urgency or curiosity in Hindi
- Keep the riddle under 40 words
- The answer should surprise people
- search_query should be in ENGLISH and describe warm, vintage, or cinematic Indian aesthetic visuals
- Return ONLY the JSON object, no markdown, no explanation"""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up potential markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1]  # Remove first line
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        riddle_data = json.loads(text)

        # Validate all required keys exist
        required = {"hook", "riddle", "answer", "search_query"}
        if not required.issubset(riddle_data.keys()):
            logger.warning("Gemini response missing keys: %s", required - riddle_data.keys())
            return None

        logger.info("✅ Generated riddle via Gemini AI")
        return riddle_data

    except ImportError:
        logger.warning("google-generativeai not installed — falling back to riddle bank")
        return None
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse Gemini response as JSON: %s", e)
        return None
    except Exception as e:
        logger.warning("Gemini API error: %s", e)
        return None


def _pick_from_bank(bank_path: Path, used_log_path: Path) -> dict | None:
    """
    Pick the NEXT sequential unused riddle from the offline bank.
    Tracks used riddle IDs in used_log_path.
    Aborts if all riddles have been used.
    """
    import sys
    bank = _load_json(bank_path)
    if not bank:
        logger.error("Riddle bank is empty at %s", bank_path)
        return None

    used = _load_json(used_log_path)
    if not isinstance(used, list):
        used = []

    # Filter to unused riddles
    unused = [r for r in bank if r.get("id") not in used]

    # Abort if all used
    if not unused:
        logger.error("❌ OUT OF RIDDLES! All riddles in the bank have been used.")
        sys.exit(0)

    # Sort sequentially by ID and pick the absolute first unused one
    unused.sort(key=lambda x: x.get("id", float('inf')))
    riddle = unused[0]

    used.append(riddle["id"])
    _save_json(used_log_path, used)

    logger.info("📖 Picked riddle #%d sequentially from bank", riddle["id"])
    return riddle


def generate_riddle(
    api_key: str = "",
    use_ai: bool = False,
    bank_path: Path | None = None,
    used_log_path: Path | None = None,
) -> dict:
    """
    Generate or pick a riddle.

    Priority:
      1. If use_ai=True and api_key is provided → try Gemini AI
      2. Priority (Default) → pick sequentially from offline bank

    Returns:
        dict with keys: hook, riddle, answer, search_query
    """
    from config import RIDDLES_BANK, USED_RIDDLES_LOG

    bank_path = bank_path or RIDDLES_BANK
    used_log_path = used_log_path or USED_RIDDLES_LOG

    # Try AI generation optionally
    if api_key and use_ai:
        result = _generate_with_gemini(api_key)
        if result:
            return result

    # Fallback to bank
    result = _pick_from_bank(bank_path, used_log_path)
    if result:
        return result

    # Ultimate fallback — hardcoded
    logger.warning("⚠️ Using hardcoded fallback riddle")
    return {
        "hook": "क्या आप इसे सुलझा सकते हैं?",
        "riddle": "काला घोड़ा, सफ़ेद की सवारी। एक उतरा तो दूसरे की बारी।",
        "answer": "तवा और रोटी!",
        "search_query": "warm vintage fire dark",
    }


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    import config

    riddle = generate_riddle(api_key=config.GEMINI_API_KEY)
    print(json.dumps(riddle, indent=2))
