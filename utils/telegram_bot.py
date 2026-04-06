import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_message(text: str, silent: bool = False) -> bool:
    """
    Sends a message to the configured Telegram Chat.
    """
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️  Telegram credentials not set. Skipping Telegram notification.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": silent,
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("📲 Telegram message sent successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram message: {e}")
        return False

def alert_success(success_data_list: list):
    """
    Sends a silent summary of successfully uploaded reels.
    """
    if not success_data_list:
        return

    msg = "✅ <b>Auto-Upload Complete!</b>\n\n"
    for data in success_data_list:
        msg += f"🎬 <b>Vid:</b> {data['title']}\n"
        msg += f"🕒 <b>Scheduled:</b> {data['scheduled_time']}\n"
        msg += f"🔗 <b>Link:</b> https://youtube.com/shorts/{data['video_id']}\n\n"

    send_telegram_message(msg, silent=True)


def alert_failure(error_msg: str):
    """
    Sends a loud alert when something fails.
    """
    msg = "🚨 <b>Riddle Reel Pipeline Failed!</b>\n\n"
    msg += f"<pre>{error_msg}</pre>"
    send_telegram_message(msg, silent=False)
