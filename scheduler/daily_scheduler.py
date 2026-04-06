"""
Daily Scheduler — Runs the pipeline once per day.

Alternative to Windows Task Scheduler. Run this script and it will
execute the pipeline at the configured time every day.

Usage:
  python scheduler/daily_scheduler.py
  python scheduler/daily_scheduler.py --time 09:00
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

import schedule

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def run_pipeline():
    """Execute the main pipeline."""
    logger.info("⏰ Scheduled run triggered!")
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "pipeline.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        if result.returncode == 0:
            logger.info("✅ Pipeline completed successfully")
        else:
            logger.error("❌ Pipeline failed:\n%s", result.stderr[-500:])
    except subprocess.TimeoutExpired:
        logger.error("❌ Pipeline timed out after 10 minutes")
    except Exception as e:
        logger.error("❌ Scheduler error: %s", e)


def main():
    parser = argparse.ArgumentParser(description="Daily scheduler for RiddleAnPuzzle")
    parser.add_argument(
        "--time",
        type=str,
        default="10:00",
        help="Time to run daily (24h format, e.g. 09:00). Default: 10:00",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("📅 RiddleAnPuzzle Daily Scheduler")
    logger.info("   Scheduled time: %s every day", args.time)
    logger.info("   Press Ctrl+C to stop")

    schedule.every().day.at(args.time).do(run_pipeline)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
