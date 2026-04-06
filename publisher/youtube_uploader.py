import datetime
import logging
import os
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service(client_secret_file, token_file):
    """Authenticates the user and returns the YouTube service object."""
    from google.auth.exceptions import RefreshError
    import json
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(token_file):
        if os.path.getsize(token_file) > 0:
            try:
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except Exception as e:
                logger.error(f"❌ Failed to parse token.json. It may be corrupt or empty: {e}")
                creds = None
        else:
            logger.error("❌ token.json is exactly 0 bytes. Check if your GOOGLE_TOKEN_BASE64 secret is set correctly in GitHub.")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                logger.error(f"❌ Token refresh failed: {e}. You may need to regenerate your token.json locally.")
                return None
        else:
            if not os.path.exists(client_secret_file) or os.path.getsize(client_secret_file) == 0:
                logger.error(f"❌ Cannot find or validate client secret file at {client_secret_file}.")
                logger.error("Please ensure GOOGLE_CLIENT_SECRET_BASE64 secret is configured correctly in GitHub.")
                return None
            
            # If we are strictly headless (like GitHub Actions), run_local_server will hang or crash.
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            try:
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"❌ Cannot open browser for authentication. Are you running on a cloud server? {e}")
                return None

        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def _build_yt_description(riddle_data: dict) -> str:
    hook = riddle_data.get("hook", "")
    riddle = riddle_data.get("riddle", "")
    answer = riddle_data.get("answer", "")
    hashtags = riddle_data.get(
        "hashtags",
        "#riddle #puzzle #brainteaser #riddles #logic #shorts #ytshorts #viralshorts"
    )

    desc = (
        f"🧩 {hook}\n\n"
        f"{riddle}\n\n"
        f"💡 Answer: {answer}\n\n"
        f"Can you solve more riddles? Subscribe for daily puzzles! 👇\n\n"
        f"{hashtags}"
    )
    return desc

def upload_to_youtube(video_path: Path, riddle_data: dict, privacy_status: str = "public", publish_at: str = None) -> str | None:
    """
    Uploads a Reel to YouTube as a Short.
    
    Args:
        video_path: Path to the .mp4 file
        riddle_data: Dictionary with hook, riddle, answer, etc.
        privacy_status: 'public', 'private', or 'unlisted'
        publish_at: ISO 8601 string for scheduling. Only works if privacy_status is 'private'.
        
    Returns:
        The uploaded video ID or None on failure.
    """
    from config import YOUTUBE_CLIENT_SECRET_FILE, YOUTUBE_TOKEN_FILE

    logger.info("Initializing YouTube Uploader...")
    youtube = get_authenticated_service(str(YOUTUBE_CLIENT_SECRET_FILE), str(YOUTUBE_TOKEN_FILE))
    
    if not youtube:
        logger.error("❌ Google authentication failed.")
        return None

    # Limit title to 100 max chars
    title = riddle_data.get("hook", "Daily Brain Teaser!") + " #shorts #riddle"
    if len(title) > 100:
        title = title[:90] + "... #shorts"
        
    description = _build_yt_description(riddle_data)
    
    # Extract tags from hashtags string
    tags_string = riddle_data.get("hashtags", "#shorts #riddles")
    tags = [tag.strip("#") for tag in tags_string.split() if tag.startswith("#")]
    # Add some default shorts tags
    tags.extend(["shorts", "puzzle", "brainteaser", "hindi riddle", "shortsfeed"])

    status_body = {
        'privacyStatus': privacy_status,
        'selfDeclaredMadeForKids': False
    }
    if publish_at and privacy_status == 'private':
        status_body['publishAt'] = publish_at

    # Prepare video meta data
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # 22 is usually "People & Blogs" or "Entertainment"
        },
        'status': status_body
    }

    # Call the API's videos.insert method to create and upload the video.
    logger.info(f"📤 Uploading {video_path.name} to YouTube...")
    try:
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        )
        
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                logger.info(f"Uploading... {int(status.progress() * 100)}%")
                
        video_id = response.get('id')
        logger.info(f"🎉 Successfully uploaded to YouTube! Video ID: {video_id}")
        logger.info(f"📺 Watch here: https://youtube.com/shorts/{video_id}")
        return video_id

    except HttpError as e:
        logger.error(f"❌ An HTTP error {e.resp.status} occurred:\n{e.content}")
        return None
