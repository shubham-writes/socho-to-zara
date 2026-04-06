import logging
from config import BACKGROUNDS_DIR, AUDIO_DIR, REELS_DIR
from assembler.video_assembler import assemble_reel

logging.basicConfig(level=logging.INFO)

bg_path = REELS_DIR / "temp_bg.mp4"
if not bg_path.exists():
    from moviepy import ColorClip
    ColorClip(size=(1080, 1920), color=(50, 50, 80)).with_duration(5).write_videofile(
        str(bg_path), fps=30, preset="ultrafast", logger=None
    )
audio_path = list(AUDIO_DIR.glob("*.mp3"))[-1]
subs_path = list(AUDIO_DIR.glob("*.json"))[-1]
reel_path = REELS_DIR / "test_reel.mp4"

# Set a generic riddle data for hook text
riddle_data = {
    "hook": "क्या आप इसे सुलझा सकते हैं?",
    "riddle": "काला घोड़ा, सफ़ेद की सवारी। एक उतरा तो दूसरे की बारी।",
    "answer": "तवा और रोटी!"
}

assemble_reel(
    background_video_path=bg_path,
    audio_path=audio_path,
    subtitles_path=subs_path,
    riddle_data=riddle_data,
    output_path=reel_path
)
