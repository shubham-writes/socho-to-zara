"""
Stage 4: Video Assembly & Captions — The Engine

Combines background video, TTS audio, and word-by-word captions into a
final Instagram Reel (9:16 portrait, 1080×1920, 30fps).

Uses MoviePy for compositing and Pillow for advanced text rendering.
"""

import json
import logging
from pathlib import Path

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np

logger = logging.getLogger(__name__)


# ─── Caption Rendering with Pillow ──────────────────────────────────────────

def _create_text_image(
    text: str,
    width: int,
    height: int,
    font_path: str,
    font_size: int = 70,
    text_color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 3,
    highlight_word: str = "",
    highlight_color: str = "yellow",
) -> np.ndarray:
    """
    Render text onto a transparent RGBA image using Pillow.
    Optionally highlights a specific word in a different color.

    Returns a numpy RGBA array.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except (IOError, OSError):
        logger.warning("Font not found at %s — using default", font_path)
        font = ImageFont.load_default()

    # Word wrap the text
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= width - 80:  # 40px padding on each side
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Calculate total text height
    line_height = font_size + 10
    total_height = len(lines) * line_height
    y_start = (height // 2) - (total_height // 2)  # Vertically center

    # Draw each line
    for i, line in enumerate(lines):
        y = y_start + i * line_height

        # If we have a highlight word, render word by word
        if highlight_word:
            line_words = line.split()
            # Calculate total line width for centering
            full_bbox = draw.textbbox((0, 0), line, font=font)
            full_width = full_bbox[2] - full_bbox[0]
            x = (width - full_width) // 2

            for w in line_words:
                color = highlight_color if w.strip(".,!?;:") == highlight_word.strip(".,!?;:") else text_color
                # Draw stroke
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), w + " ", font=font, fill=stroke_color)
                # Draw text
                draw.text((x, y), w + " ", font=font, fill=color)
                w_bbox = draw.textbbox((0, 0), w + " ", font=font)
                x += w_bbox[2] - w_bbox[0]
        else:
            # Simple centered text
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = (width - line_width) // 2
            # Draw stroke
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=stroke_color)
            # Draw text
            draw.text((x, y), line, font=font, fill=text_color)

    return np.array(img)


def _make_caption_clips(
    subtitles: list[dict],
    video_width: int,
    video_height: int,
    font_path: str,
    font_size: int,
    text_color: str,
    highlight_color: str,
    stroke_color: str,
    stroke_width: int,
    words_per_group: int = 4,
) -> list[ImageClip]:
    """
    Create word-by-word caption ImageClips from subtitle data.

    Groups words into phrases of `words_per_group` for readability,
    and highlights the currently-spoken word.
    """
    clips = []
    total_words = len(subtitles)

    for group_start in range(0, total_words, words_per_group):
        group_end = min(group_start + words_per_group, total_words)
        group = subtitles[group_start:group_end]

        # Full phrase text
        phrase = " ".join(w["text"] for w in group)
        group_start_time = group[0]["start"]
        group_end_time = group[-1]["end"]
        group_duration = group_end_time - group_start_time

        if group_duration <= 0:
            group_duration = 0.5  # Minimum duration

        # Create one clip per word in the group (with highlight)
        for i, word_data in enumerate(group):
            word = word_data["text"]
            word_start = word_data["start"]
            word_end = word_data["end"]
            word_duration = word_end - word_start

            if word_duration <= 0:
                word_duration = 0.3

            # Render the full phrase with this word highlighted
            img_array = _create_text_image(
                text=phrase,
                width=video_width,
                height=video_height,
                font_path=font_path,
                font_size=font_size,
                text_color=text_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                highlight_word=word,
                highlight_color=highlight_color,
            )

            clip = (
                ImageClip(img_array, transparent=True)
                .with_duration(word_duration)
                .with_start(word_start)
            )
            clips.append(clip)

    return clips


def _make_hook_clip(
    hook_text: str,
    duration: float,
    video_width: int,
    video_height: int,
    font_path: str,
) -> ImageClip:
    """
    Create an intro overlay showing the hook text.
    Bold white text with thick black stroke and a yellow accent underline.
    """
    img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(font_path, 88)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Word wrap
    words = hook_text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= video_width - 80:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    line_height = 100
    total_h = len(lines) * line_height
    y = (video_height // 2) - (total_h // 2)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (video_width - lw) // 2

        # Thick black stroke
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))

        # Yellow main text
        draw.text((x, y), line, font=font, fill=(255, 230, 0, 255))

        y += line_height

    clip = (
        ImageClip(np.array(img), transparent=True)
        .with_duration(duration)
        .with_start(0)
    )
    return clip


def _make_persistent_riddle_clip(
    riddle_text: str,
    duration: float,
    video_width: int,
    video_height: int,
    font_path: str,
) -> ImageClip:
    """
    Create an overlay showing the riddle text persistently at the top.
    """
    img_array = _create_text_image(
        text=riddle_text,
        width=video_width,
        height=video_height // 2 - 100,  # leave room
        font_path=font_path,
        font_size=55,
        text_color="white",
        stroke_color="black",
        stroke_width=3,
    )
    clip = (
        ImageClip(img_array, transparent=True)
        .with_duration(duration)
        .with_start(0)
        .with_position(("center", "top"))
    )
    return clip


def _make_persistent_answer_clip(
    answer_text: str,
    duration: float,
    start_time: float,
    video_width: int,
    video_height: int,
    font_path: str,
) -> ImageClip:
    """
    Create an overlay showing the answer text persistently in the center.
    """
    img_array = _create_text_image(
        text=answer_text,
        width=video_width,
        height=video_height // 2,
        font_path=font_path,
        font_size=90,
        text_color="#00FF88",  # Neon green to stand out
        stroke_color="black",
        stroke_width=6,
    )
    
    from moviepy.video.fx import CrossFadeIn
    clip = (
        ImageClip(img_array, transparent=True)
        .with_duration(duration - start_time)
        .with_start(start_time)
        .with_position(("center", "center"))
        .with_effects([CrossFadeIn(0.5)])
    )
    return clip


def _make_timer_clips(
    start_time: float,
    video_width: int,
    video_height: int,
    font_path: str,
) -> list[ImageClip]:
    """
    Create a 5-4-3-2-1 countdown sequence of ImageClips.
    Each number is bold, centered, with a dark semi-transparent circle behind it.
    """
    clips = []
    for i in range(5, 0, -1):
        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw a dark semi-transparent circle background
        cx, cy = video_width // 2, video_height // 2
        r = 160
        draw.ellipse(
            [(cx - r, cy - r), (cx + r, cy + r)],
            fill=(0, 0, 0, 180)
        )

        # Draw the countdown number
        try:
            font = ImageFont.truetype(font_path, 260)
        except (IOError, OSError):
            font = ImageFont.load_default()

        text = str(i)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = cx - tw // 2
        y = cy - th // 2 - bbox[1]

        # Thick stroke
        stroke_w = 10
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))

        # Pick a color per number: 5→red, 4→orange, 3→yellow, 2→lime, 1→green
        colors = {5: "#FF3B3B", 4: "#FF8C00", 3: "#FFE600", 2: "#AAFF00", 1: "#00FF88"}
        draw.text((x, y), text, font=font, fill=colors.get(i, "white"))

        clip = (
            ImageClip(np.array(img), transparent=True)
            .with_duration(1.0)
            .with_start(start_time + (5 - i))
        )
        clips.append(clip)
    return clips


def _get_next_bg_music(bg_music_dir: Path, tracker_file: Path) -> Path | None:
    """
    Sequentially cycles through mp3 files in bg_music_dir.
    Maintains the state in a JSON file to remember the last used track block.
    """
    if not bg_music_dir.exists():
        return None
        
    tracks = sorted([f for f in bg_music_dir.iterdir() if f.suffix.lower() == ".mp3"])
    if not tracks:
        return None
        
    current_index = 0
    if tracker_file.exists():
        try:
            with open(tracker_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                current_index = data.get("next_index", 0)
        except Exception:
            current_index = 0
            
    current_index = current_index % len(tracks)
    selected_track = tracks[current_index]
    
    try:
        with open(tracker_file, "w", encoding="utf-8") as f:
            json.dump({"next_index": (current_index + 1) % len(tracks)}, f)
    except Exception as e:
        logger.error("Failed to update music tracker: %s", e)
        
    return selected_track


# ─── Main Assembly Function ─────────────────────────────────────────────────

def assemble_reel(
    background_video_path: Path,
    audio_path1: Path,
    subs_path1: Path,
    audio_path2: Path,
    subs_path2: Path,
    riddle_data: dict,
    output_path: Path | None = None,
) -> Path:
    """
    Assemble the final Instagram Reel.

    1. Load & resize background video to 1080×1920
    2. Add TTS audio 1 (hook+riddle), inject timer visuals, then audio 2 (answer)
    3. Burn word-by-word captions with highlight effect
    4. Add hook text intro overlay
    5. Export final .mp4
    """
    from config import (
        REELS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_CODEC,
        AUDIO_CODEC, CAPTION_FONT, CAPTION_FONTSIZE, CAPTION_COLOR,
        CAPTION_HIGHLIGHT, CAPTION_STROKE_COLOR, CAPTION_STROKE_WIDTH,
    )

    if output_path is None:
        output_path = REELS_DIR / "reel.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("🎬 Assembling Reel...")

    # ── Load audios ──
    original_audio1 = AudioFileClip(str(audio_path1))
    original_audio2 = AudioFileClip(str(audio_path2))
    audio1 = original_audio1
    audio2 = original_audio2

    t_split = audio1.duration
    pause_duration = 5.0
    
    # ── Assemble audio track ──
    try:
        from config import TIMER_AUDIO_PATH
        if TIMER_AUDIO_PATH.exists():
            original_timer = AudioFileClip(str(TIMER_AUDIO_PATH))
            timer_audio = original_timer.subclipped(0, min(pause_duration, original_timer.duration))
            timer_audio = timer_audio.with_start(t_split)
            audio2_placed = audio2.with_start(t_split + pause_duration)
            final_audio = CompositeAudioClip([audio1, timer_audio, audio2_placed])
        else:
            audio2_placed = audio2.with_start(t_split + pause_duration)
            final_audio = CompositeAudioClip([audio1, audio2_placed])
    except Exception as e:
        logger.warning("Could not load timer audio: %s", e)
        audio2_placed = audio2.with_start(t_split + pause_duration)
        final_audio = CompositeAudioClip([audio1, audio2_placed])
        
    total_duration = audio1.duration + pause_duration + audio2.duration + 1.5

    # ── Background Music Mixing ──
    from config import BG_MUSIC_DIR, MUSIC_TRACKER_FILE
    from moviepy.audio.fx import AudioLoop, AudioFadeOut, MultiplyVolume

    bg_music_path = _get_next_bg_music(BG_MUSIC_DIR, MUSIC_TRACKER_FILE)
    if bg_music_path:
        logger.info(f"🎵 Applying Background Music: {bg_music_path.name}")
        original_bg_music = AudioFileClip(str(bg_music_path))
        
        if original_bg_music.duration < total_duration:
            bg_music = original_bg_music.with_effects([AudioLoop(duration=total_duration)])
        else:
            bg_music = original_bg_music.subclipped(0, total_duration)
            
        bg_music = bg_music.with_effects([MultiplyVolume(0.15), AudioFadeOut(2.0)])
        final_audio = CompositeAudioClip([bg_music, final_audio])

    # ── Load subtitles ──
    try:
        with open(subs_path1, "r", encoding="utf-8") as f:
            subs1 = json.load(f)
    except Exception:
        subs1 = []
        
    try:
        with open(subs_path2, "r", encoding="utf-8") as f:
            subs2 = json.load(f)
    except Exception:
        subs2 = []

    # Shift subtitles 2 by (t_split + pause_duration)
    for sub in subs2:
        sub["start"] += (t_split + pause_duration)
        sub["end"] += (t_split + pause_duration)
        
    subtitles = subs1 + subs2

    # Create timer visuals explicitly starting when audio1 finishes
    timer_clips = _make_timer_clips(
        start_time=t_split,
        video_width=VIDEO_WIDTH,
        video_height=VIDEO_HEIGHT,
        font_path=CAPTION_FONT,
    )

    # ── Load & prepare background ──
    original_bg = VideoFileClip(str(background_video_path))
    bg = _resize_cover(original_bg, VIDEO_WIDTH, VIDEO_HEIGHT)
    if bg.audio is not None:
        bg = bg.without_audio()

    # Apply cinematic slow motion and Boomerang loop (Forward-Reverse)
    from moviepy.video.fx import MultiplySpeed, TimeMirror
    bg = bg.with_effects([MultiplySpeed(0.5)])
    
    # Create the seamless boomerang block
    bg_reverse = bg.with_effects([TimeMirror()])
    boomerang_block = concatenate_videoclips([bg, bg_reverse])

    # Loop the boomerang block if shorter than audio
    if boomerang_block.duration < total_duration:
        n_loops = int(total_duration / boomerang_block.duration) + 1
        bg = concatenate_videoclips([boomerang_block] * n_loops)
    else:
        bg = boomerang_block

    # Trim to exact duration
    bg = bg.subclipped(0, total_duration)

    # ── Create caption clips ──
    caption_clips = _make_caption_clips(
        subtitles=subtitles,
        video_width=VIDEO_WIDTH,
        video_height=VIDEO_HEIGHT,
        font_path=CAPTION_FONT,
        font_size=CAPTION_FONTSIZE,
        text_color=CAPTION_COLOR,
        highlight_color=CAPTION_HIGHLIGHT,
        stroke_color=CAPTION_STROKE_COLOR,
        stroke_width=CAPTION_STROKE_WIDTH,
    )

    # ── Create hook intro ──
    hook_text = riddle_data.get("hook", "")
    hook_clip = None
    if hook_text:
        hook_duration = min(2.5, subtitles[0]["start"] if subtitles else 2.5)
        if hook_duration < 0.5:
            hook_duration = 2.0
        hook_clip = _make_hook_clip(
            hook_text=hook_text,
            duration=hook_duration,
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            font_path=CAPTION_FONT,
        )

    # ── Create persistent riddle clip ──
    riddle_text = riddle_data.get("riddle", "")
    riddle_clip = None
    if riddle_text:
        riddle_clip = _make_persistent_riddle_clip(
            riddle_text=riddle_text,
            duration=total_duration,
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            font_path=CAPTION_FONT,
        )

    # ── Create persistent answer clip ──
    answer_text = riddle_data.get("answer", "")
    answer_clip = None
    if answer_text:
        # Delay by ~1.5s so it appears when the word is spoken, not during "iska jawab hai.."
        ans_start_time = min(t_split + pause_duration + 1.5, total_duration - 0.5)
        answer_clip = _make_persistent_answer_clip(
            answer_text=answer_text,
            duration=total_duration,
            start_time=ans_start_time,
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            font_path=CAPTION_FONT,
        )

    # ── Composite everything ──
    layers = [bg]
    if riddle_clip:
        layers.append(riddle_clip)
    if hook_clip:
        layers.append(hook_clip)
    if answer_clip:
        layers.append(answer_clip)
    layers.extend(caption_clips)
    if timer_clips:
        layers.extend(timer_clips)
        
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    final = final.with_duration(total_duration)
    final = final.with_audio(final_audio)

    # ── Export ──
    logger.info("📼 Rendering to %s ...", output_path)
    final.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec=VIDEO_CODEC,
        audio_codec=AUDIO_CODEC,
        preset="ultrafast",  # Use ultrafast for testing/dry-runs
    )

    # Clean up
    original_audio1.close()
    original_audio2.close()
    if 'original_timer' in locals():
        original_timer.close()
    if 'original_bg_music' in locals():
        original_bg_music.close()
    original_bg.close()
    final.close()
    if hook_clip:
        hook_clip.close()
    if riddle_clip:
        riddle_clip.close()
    if answer_clip:
        answer_clip.close()
    for c in caption_clips:
        c.close()
    for c in timer_clips:
        c.close()
    if bg is not original_bg: bg.close()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("✅ Reel assembled: %s (%.1f MB)", output_path.name, size_mb)
    return output_path


def _resize_cover(clip: VideoFileClip, target_w: int, target_h: int) -> VideoFileClip:
    """
    Resize a video clip to cover the target dimensions (crop to fill).
    Similar to CSS `object-fit: cover`.
    """
    from moviepy.video.fx import Resize, Crop

    clip_w, clip_h = clip.size
    target_ratio = target_w / target_h
    clip_ratio = clip_w / clip_h

    if clip_ratio > target_ratio:
        # Video is wider — scale by height, crop width
        new_h = target_h
        new_w = int(clip_w * (target_h / clip_h))
    else:
        # Video is taller — scale by width, crop height
        new_w = target_w
        new_h = int(clip_h * (target_w / clip_w))

    clip = clip.with_effects([Resize(new_size=(new_w, new_h))])

    # Center crop
    x_center = new_w // 2
    y_center = new_h // 2
    x1 = x_center - target_w // 2
    y1 = y_center - target_h // 2

    clip = clip.with_effects([Crop(x1=x1, y1=y1, width=target_w, height=target_h)])

    return clip


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Video assembler module loaded. Use assemble_reel() to create a Reel.")
