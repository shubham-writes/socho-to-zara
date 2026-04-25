"""
Stage 2: Voiceover — Text-to-Speech Generator

Uses the Azure Cognitive Services Speech SDK for natural,
human-like Hindi voiceovers with word-level timestamps for captions.
"""

import json
import logging
import time
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk

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


def _build_ssml(text: str, voice: str, rate: str) -> str:
    """
    Builds SSML markup for Azure Speech with the given voice and rate.
    """
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="hi-IN">'
        f'<voice name="{voice}">'
        f'<prosody rate="{rate}">'
        f'{text}'
        '</prosody>'
        '</voice>'
        '</speak>'
    )


def _synthesize_to_file(
    text: str,
    output_audio: Path,
    output_subs: Path,
    voice: str,
    rate: str,
    speech_key: str,
    speech_region: str,
) -> None:
    """
    Synthesize speech using Azure SDK, saving audio and word-level timestamps.
    """
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_audio))

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # Collect word-level timestamps
    word_boundaries = []

    def on_word_boundary(evt):
        word_boundaries.append({
            "start": round(evt.audio_offset / 10_000_000, 3),  # ticks → seconds
            "end": round((evt.audio_offset + evt.duration) / 10_000_000, 3),
            "text": evt.text
        })

    synthesizer.synthesis_word_boundary.connect(on_word_boundary)

    ssml = _build_ssml(text, voice, rate)
    logger.info("🗣️ Synthesizing with Azure voice: %s", voice)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        logger.info("🎙️ Audio saved: %s (%d word boundaries)", output_audio, len(word_boundaries))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        logger.error("❌ Azure TTS canceled: %s", cancellation.reason)
        if cancellation.error_details:
            logger.error("❌ Error details: %s", cancellation.error_details)
        raise RuntimeError(f"Azure TTS failed: {cancellation.reason} — {cancellation.error_details}")

    # Save subtitle entries
    with open(output_subs, "w", encoding="utf-8") as f:
        json.dump(word_boundaries, f, indent=2, ensure_ascii=False)


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
    from config import AUDIO_DIR, TTS_VOICE, TTS_RATE, AZURE_API_KEY, AZURE_REGION

    voice = voice or TTS_VOICE
    rate = rate or TTS_RATE

    if not AZURE_API_KEY or not AZURE_REGION:
        raise RuntimeError("AZURE_API_KEY or AZURE_REGION not set. Please add them to your .env file.")

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

    _synthesize_to_file(text1, output_audio1, output_subs1, voice, rate, AZURE_API_KEY, AZURE_REGION)
    _synthesize_to_file(text2, output_audio2, output_subs2, voice, rate, AZURE_API_KEY, AZURE_REGION)

    return output_audio1, output_subs1, output_audio2, output_subs2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Quick test with a sample riddle
    sample = {
        "id": 2,
        "hook": "क्या आप इसे सुलझा सकते हैं?",
        "riddle": "काला घोड़ा, सफ़ेद की सवारी। एक उतरा तो दूसरे की बारी।",
        "answer": "तवा और रोटी!",
    }
    a1, s1, a2, s2 = generate_voiceover(sample)
    print(f"Audio 1: {a1}")
    print(f"Audio 2: {a2}")
