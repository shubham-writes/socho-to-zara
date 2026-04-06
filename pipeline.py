"""
🚀 RiddleAnPuzzle — Main Pipeline Orchestrator

Ties all stages together into a single automated flow.
Now updated for dual-generation (2 reels per run) and native YouTube scheduling.
"""

import argparse
import logging
import sys
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Setup Logging ───────────────────────────────────────────────────────────

def setup_logging(log_file: Path):
    """Configure logging to both console and file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )

def cleanup_files(file_paths):
    """Deletes temporary files after successful upload."""
    logger = logging.getLogger(__name__)
    logger.info("🗑️ Cleaning up intermediate files...")
    for file_path in file_paths:
        if file_path and Path(file_path).exists():
            try:
                os.remove(file_path)
                logger.info(f"  Deleted: {Path(file_path).name}")
            except Exception as e:
                logger.warning(f"  Failed to delete {Path(file_path).name}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="🧩 RiddleAnPuzzle — Automated YouTube Shorts Pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the videos but skip YouTube posting",
    )
    args = parser.parse_args()

    # ── Import config & modules ──
    import config
    from generators.riddle_generator import generate_riddle
    from tts.voice_generator import generate_voiceover
    from visuals.video_fetcher import fetch_background_video
    from assembler.video_assembler import assemble_reel
    from publisher.youtube_uploader import upload_to_youtube

    setup_logging(config.LOG_FILE)
    logger = logging.getLogger(__name__)

    # ── Calculate Target Schedule Date ──
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    
    target_date = now.date()
    # If the script is run past 2:00 PM IST, force the base target to tomorrow to prevent missing the first slot
    if now.hour >= 14:
        target_date = now.date() + timedelta(days=1)

    schedule_file = config.OUTPUT_DIR / "last_schedule_date.txt"
    if schedule_file.exists():
        try:
            last_date_str = schedule_file.read_text().strip()
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            if last_date >= target_date:
                # We've already booked this date, push to the next available day
                target_date = last_date + timedelta(days=1)
        except Exception as e:
            logger.warning(f"Could not read last schedule date: {e}")

    logger.info("=" * 60)
    logger.info(f"📅 Target Schedule Date for this run: {target_date.strftime('%Y-%m-%d')}")
    logger.info("=" * 60)

    # We want to schedule one for 2:00 PM (14:00) and one for 7:30 PM (19:30)
    schedules = [
        {"time_name": "2:00 PM IST", "hour": 14, "minute": 0},
        {"time_name": "7:30 PM IST", "hour": 19, "minute": 30}
    ]

    all_uploads_successful = True
    success_list = []

    for loop_idx, sched in enumerate(schedules):
        logger.info("=" * 60)
        logger.info("🎬 LAUNCHING GENERATION %d/2 — Target Schedule: %s", loop_idx + 1, sched["time_name"])
        logger.info("=" * 60)

        # ── Determine run counter (day) ──
        day_log = config.OUTPUT_DIR / "day_counter.txt"
        if day_log.exists():
            day = int(day_log.read_text().strip()) + 1
        else:
            day = 1
        day_log.write_text(str(day))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ══════════════════════════════════════════════════════════════
        # STAGE 1: Content Generation
        # ══════════════════════════════════════════════════════════════
        logger.info("━━━ STAGE 1: Generating riddle content ━━━")
        riddle_data = generate_riddle(api_key=config.GEMINI_API_KEY)
        
        # ODD/EVEN ID Logic implementation
        try:
            r_id = int(riddle_data.get("id", 0))
        except ValueError:
            r_id = 0
            
        if r_id % 2 != 0:
            # It's odd! Hide the answer
            logger.info("Odd Riddle ID detected. Hiding answer!")
            random_prompts = [
                "अपना जवाब कमेंट में ज़रूर दें",
                "देखते हैं कौन सही जवाब देता है",
                "आपका जवाब क्या है? कमेंट में लिखो",
                "जीनियस हो तो जवाब कमेंट में दो",
                "90% लोग गलत हो जाते हैं , आप try करो",
                "90% लोग गलत हो जाते हैं , आप अपना जवाब कमेंट में दें"
            ]
            riddle_data["answer"] = random.choice(random_prompts)

        logger.info("Hook:   %s", riddle_data.get("hook"))
        logger.info("Riddle: %s", riddle_data.get("riddle"))
        logger.info("Answer: %s", riddle_data.get("answer"))

        # ══════════════════════════════════════════════════════════════
        # STAGE 2: TTS Voiceover
        # ══════════════════════════════════════════════════════════════
        logger.info("━━━ STAGE 2: Generating voiceover ━━━")
        audio1 = config.AUDIO_DIR / f"day{day}_{timestamp}_part1.mp3"
        subs1 = config.AUDIO_DIR / f"day{day}_{timestamp}_part1_subs.json"
        audio2 = config.AUDIO_DIR / f"day{day}_{timestamp}_part2.mp3"
        subs2 = config.AUDIO_DIR / f"day{day}_{timestamp}_part2_subs.json"

        audio1_res, subs1_res, audio2_res, subs2_res = generate_voiceover(
            riddle_data=riddle_data,
            output_audio1=audio1,
            output_subs1=subs1,
            output_audio2=audio2,
            output_subs2=subs2,
        )

        # ══════════════════════════════════════════════════════════════
        # STAGE 3: Background Video
        # ══════════════════════════════════════════════════════════════
        logger.info("━━━ STAGE 3: Fetching background video ━━━")
        bg_path = config.BACKGROUNDS_DIR / f"day{day}_{timestamp}_bg.mp4"

        search_query = riddle_data.get("search_query", "dark abstract mystery")
        bg_path = fetch_background_video(
            search_query=search_query,
            output_path=bg_path,
        )

        if bg_path is None:
            logger.error("❌ Cannot proceed without a background video!")
            sys.exit(1)

        # ══════════════════════════════════════════════════════════════
        # STAGE 4: Video Assembly
        # ══════════════════════════════════════════════════════════════
        logger.info("━━━ STAGE 4: Assembling Reel ━━━")
        export_dir = Path(r"C:\Users\Shubham\Downloads\TEMPORARY\riddleReels")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        riddle_id = riddle_data.get("id", "unknown")
        reel_path = export_dir / f"riddleReel_{riddle_id}_{timestamp}.mp4"

        reel_path = assemble_reel(
            background_video_path=bg_path,
            audio_path1=audio1_res,
            subs_path1=subs1_res,
            audio_path2=audio2_res,
            subs_path2=subs2_res,
            riddle_data=riddle_data,
            output_path=reel_path,
        )

        logger.info("🎥 Reel ready: %s", reel_path)

        # ══════════════════════════════════════════════════════════════
        # STAGE 5: Publishing to YouTube
        # ══════════════════════════════════════════════════════════════
        if args.dry_run:
            logger.info("━━━ STAGE 5: SKIPPED (dry run) ━━━")
            logger.info("🏁 Dry run complete! Video saved at: %s", reel_path)
            all_uploads_successful = False
        else:
            logger.info("━━━ STAGE 5: Scheduled Native YouTube Upload ━━━")

            if not config.YOUTUBE_CLIENT_SECRET_FILE.exists():
                logger.error("❌ YouTube client_secret.json not found — CANNOT UPLOAD. ")
                all_uploads_successful = False
            else:
                # Calculate the exact ISO 8601 target for this loop's specific slot on the chosen target date
                dt_target = datetime(
                    target_date.year, target_date.month, target_date.day,
                    sched["hour"], sched["minute"], 0, tzinfo=ist
                )
                publish_target = dt_target.isoformat()
                
                logger.info(f"Target YouTube Publish Time: {publish_target} (ISO 8601)")
                
                yt_media_id = upload_to_youtube(
                    video_path=reel_path,
                    riddle_data=riddle_data,
                    privacy_status="private",
                    publish_at=publish_target
                )

                if yt_media_id:
                    logger.info("🎉 Successfully uploaded and scheduled to YouTube! Video ID: %s", yt_media_id)
                    success_list.append({
                        "title": riddle_data.get("hook", "Daily Brain Teaser!"),
                        "scheduled_time": publish_target,
                        "video_id": yt_media_id
                    })
                    # Because upload was successful, clean up temporary files to save space!
                    files_to_delete = [
                        audio1_res, subs1_res, audio2_res, subs2_res, bg_path, reel_path
                    ]
                    cleanup_files(files_to_delete)
                else:
                    logger.error("❌ Failed to post to YouTube")
                    all_uploads_successful = False

        # ── Summary ──
        logger.info("=" * 60)
        logger.info("📊 PIPELINE SUMMARY — GENERATION %d", loop_idx + 1)
        logger.info("  Riddle ID: %s", riddle_id)
        if reel_path.exists():
            logger.info("  Size:   %.1f MB", reel_path.stat().st_size / (1024 * 1024))
        logger.info("=" * 60)
        print("\n")

    # If both loops finished, securely save the target successfully exhausted today
    if all_uploads_successful and not args.dry_run:
        schedule_file.write_text(target_date.strftime("%Y-%m-%d"))
        logger.info(f"✅ State fully recorded. Future runs will queue starting { (target_date + timedelta(days=1)).strftime('%Y-%m-%d') }.")
        
        try:
            from utils.telegram_bot import alert_success
            alert_success(success_list)
        except Exception as e:
            logger.error(f"Failed to send Telegram success alert: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        import logging
        error_trace = traceback.format_exc()
        logging.getLogger(__name__).error(f"Pipeline crashed:\n{error_trace}")
        try:
            from utils.telegram_bot import alert_failure
            alert_failure(error_trace)
        except Exception as telegram_err:
            logging.getLogger(__name__).error(f"Failed to send Telegram error alert: {telegram_err}")
        sys.exit(1)
