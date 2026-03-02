"""
YouTube uploader using official API
"""

import os
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import yt_dlp
import time

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeUploader:
    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        """
        Initialize YouTube uploader

        Args:
            credentials_file (str): Path to OAuth credentials JSON
            token_file (str): Path to token cache file
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with YouTube API"""
        logger.info("Authenticating with YouTube API...")

        creds = None

        # Load cached token if exists
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # If no valid credentials, refresh or create new
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    logger.warning("Token refresh failed, re-authenticating...")
                    creds = self.get_new_credentials()
            else:
                creds = self.get_new_credentials()

        if creds:
             # Save token for next time
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

            self.service = build("youtube", "v3", credentials=creds)
            logger.info("✅ YouTube API authenticated")
        else:
            logger.warning("⚠️ YouTube API NOT authenticated (running in offline mode)")
            self.service = None

    def get_new_credentials(self):
        """Get new OAuth credentials"""
        if not os.path.exists(self.credentials_file):
            logger.warning(f"❌ {self.credentials_file} not found! YouTube features will be disabled.")
            return None

        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_file, SCOPES
        )
        creds = flow.run_local_server(port=0)
        return creds

    def download_audio(self, url, output_file):
        """
        Download audio from URL

        Args:
            url (str): Audio URL
            output_file (str): Output file path

        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Downloading audio from: {url}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': output_file.replace('.mp3', ''),
                'quiet': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            logger.info(f"✅ Downloaded: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            return False

    def upload_video(self, title, description, audio_file, thumbnail_file=None,
                     privacy_status="private", category_id="10"):
        """
        Upload video to YouTube

        Args:
            title (str): Video title
            description (str): Video description
            audio_file (str): Path to audio file
            thumbnail_file (str): Path to thumbnail image
            privacy_status (str): 'private', 'unlisted', or 'public'
            category_id (str): YouTube category ID

        Returns:
            dict: Upload result with video ID
        """
        try:
            logger.info(f"Uploading video: {title}")
            
            if self.service is None:
                logger.warning("YouTube service not available. Skipping upload.")
                return {"status": "skipped", "message": "No credentials"}

            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file not found: {audio_file}")

            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': ['suno', 'ai music', 'generated music'],
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'madeForKids': False
                }
            }

            # Upload video
            media = MediaFileUpload(
                audio_file,
                mimetype="audio/mpeg",
                resumable=True,
                chunksize=1024*1024
            )

            request = self.service.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media,
                notifySubscribers=False
            )

            response = None
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        logger.info(f"Upload progress: {int(status.progress()*100)}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        logger.error(f"Upload failed: {e}")
                        return {"status": "error", "error": str(e)}
                    raise

            video_id = response['id']
            logger.info(f"✅ Video uploaded: {video_id}")

            return {
                "status": "success",
                "video_id": video_id,
                "url": f"https://youtube.com/watch?v={video_id}"
            }

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            return {"status": "error", "error": str(e)}
