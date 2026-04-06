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
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_file):
                logger.error(f"❌ Cannot find client secret file at {client_secret_file}.")
                logger.error("Please set up Google Cloud Console and download the OAuth 2.0 Client ID JSON file as client_secret.json.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
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
