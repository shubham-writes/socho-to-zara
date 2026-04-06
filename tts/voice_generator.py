"""
Stage 2: Voiceover — Text-to-Speech Generator

Uses the `edge-tts` library (Microsoft Edge neural voices) to generate
natural-sounding voiceovers. 100% free, no API key required.

Also produces word-level subtitle timestamps for caption burning.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

import edge_tts

logger = logging.getLogger(__name__)


def _build_tts_text(riddle_data: dict) -> tuple[str, str]:
    """
    Split the TTS script into two distinct pieces.
    Part 1: Hook, riddle, and "थोड़ा सोचिए"
    Part 2: The answer
    """
    hook   = riddle_data.get("hook",   "क्या आप इसे सुलझा सकते हैं?")
    riddle = riddle_data.get("riddle", "")
    answer = riddle_data.get("answer", "")

    try:
        r_id = int(riddle_data.get("id", 0))
    except ValueError:
        r_id = 0

    script1 = f"{hook}। {riddle}। थोड़ा सोचिए।"
    if r_id % 2 != 0:
        script2 = answer
    else:
        script2 = f"इसका जवाब है, {answer}"
    return script1, script2


async def _generate_audio_async(
    text: str,
    output_audio: Path,
    output_subs: Path,
    voice: str = "hi-IN-MadhurNeural",
    rate: str = "+5%",
) -> None:
    """
    Async core: generate audio + subtitle metadata via edge-tts.
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    submaker = edge_tts.SubMaker()
    word_boundary_count = 0

    with open(output_audio, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
                word_boundary_count += 1

    logger.info("📊 WordBoundary events received: %d", word_boundary_count)

    # Generate SRT subtitles
    srt_content = submaker.get_srt()
    subtitle_entries = _parse_srt(srt_content)

    with open(output_subs, "w", encoding="utf-8") as f:
        json.dump(subtitle_entries, f, indent=2, ensure_ascii=False)

    logger.info("🎙️ Audio saved: %s (%d subtitle entries)", output_audio, len(subtitle_entries))


def _parse_srt(srt_text: str) -> list[dict]:
    """
    Parse SRT content into a list of subtitle entries:
    [{"start": 0.5, "end": 1.2, "text": "word"}, ...]
    """
    entries = []
    # Match SRT cue blocks:
    # 1
    # 00:00:00,000 --> 00:00:01,000
    # text
    pattern = re.compile(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*\n(.+?)(?:\n\n|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    for match in pattern.finditer(srt_text):
        h1, m1, s1, ms1, h2, m2, s2, ms2, text = match.groups()
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000.0
        end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000.0
        word = text.strip()
        if word:
            entries.append({"start": round(start, 3), "end": round(end, 3), "text": word})

    return entries


def generate_voiceover(
    riddle_data: dict,
    output_audio1: Path | None = None,
    output_subs1: Path | None = None,
    output_audio2: Path | None = None,
    output_subs2: Path | None = None,
    voice: str | None = None,
    rate: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    """
    Generate TTS audio separately for riddle and answer.
    Returns:
        (audio1, subs1, audio2, subs2)
    """
    from config import AUDIO_DIR, TTS_VOICE, TTS_RATE

    voice = voice or TTS_VOICE
    rate = rate or TTS_RATE

    if output_audio1 is None:
        output_audio1 = AUDIO_DIR / "voiceover1.mp3"
    if output_subs1 is None:
        output_subs1 = AUDIO_DIR / "subtitles1.json"
    if output_audio2 is None:
        output_audio2 = AUDIO_DIR / "voiceover2.mp3"
    if output_subs2 is None:
        output_subs2 = AUDIO_DIR / "subtitles2.json"

    text1, text2 = _build_tts_text(riddle_data)
    logger.info("📝 TTS script Part 1: %s", text1[:80] + "...")
    logger.info("📝 TTS script Part 2: %s", text2[:80] + "...")

    # Run the async functions for both chunks
    asyncio.run(_generate_audio_async(text1, output_audio1, output_subs1, voice, rate))
    asyncio.run(_generate_audio_async(text2, output_audio2, output_subs2, voice, rate))

    return output_audio1, output_subs1, output_audio2, output_subs2

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Quick test with a sample riddle
    sample = {
        "hook": "क्या आप इसे सुलझा सकते हैं?",
        "riddle": "काला घोड़ा, सफ़ेद की सवारी। एक उतरा तो दूसरे की बारी।",
        "answer": "तवा और रोटी!",
    }
    a1, s1, a2, s2 = generate_voiceover(sample)
    print(f"Audio 1: {a1}")
    print(f"Audio 2: {a2}")
