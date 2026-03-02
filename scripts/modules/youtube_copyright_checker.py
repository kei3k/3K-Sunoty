"""
YouTube copyright checker and video uploader.

Handles unlisted video uploads and Content ID copyright detection polling.
"""

import os
import time
import requests
from typing import Dict, Any, Optional, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from utils.logger import logger
    from utils.config_loader import config
except ImportError:
    from utils.logger import logger
    from utils.config_loader import config


class YouTubeCopyrightChecker:
    """Handles YouTube video uploads and copyright detection."""

    def __init__(self, profile_name='default'):
        """Initialize YouTube client."""
        # NEW: Use OAuth instead of just API Key
        self.profile_name = profile_name
        self._init_service()

    def _init_service(self):
        """Initialize or Switch Service."""
        try:
            from modules.youtube_auth import get_authenticated_service
            self.youtube = get_authenticated_service(self.profile_name)
            logger.info(f"YouTube API client initialized (Profile: {self.profile_name})")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube Client ({self.profile_name}): {e}")
            logger.warning("Fallback to API Key (Read-Only) - Uploads will fail!")
            # Fallback (legacy)
            self.api_key = config.youtube_api_key
            if self.api_key:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def switch_profile(self, new_profile_name):
        """Switch to a different API profile."""
        logger.info(f"Switching API Profile: {self.profile_name} -> {new_profile_name}")
        self.profile_name = new_profile_name
        self._init_service()


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def upload_test_video(
        self,
        audio_file: str,
        video_file: str,
        title: str,
        description: str = "",
        privacy: str = "unlisted"
    ) -> Dict[str, Any]:
        """Upload a REAL video to YouTube."""
        try:
            logger.info(
                f"Uploading VIDEO to YouTube (Real)",
                video_file=video_file,
                title=title,
                privacy=privacy
            )

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': ['test', 'copyright', 'remix'],
                    'categoryId': '10'
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)

            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute REAL upload
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploaded {int(status.progress() * 100)}%")
            
            logger.info(
                f"Video uploaded successfully",
                video_id=response.get('id'),
                title=title
            )
            return response

        except Exception as e:
            logger.error(f"Failed to upload video: {e}")
            raise



    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        retry=retry_if_exception_type(Exception)
    )
    def check_copyright_status(self, video_id: str) -> Dict[str, Any]:
        """Check copyright claims (Real API)."""
        try:
            logger.debug(f"Checking copyright status for {video_id}...")
            # Get video details including copyright information
            request = self.youtube.videos().list(
                part='status,contentDetails,processingDetails',
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                raise Exception(f"Video {video_id} not found")

            video = response['items'][0]
            
            # Real copyright check involves creating a fake claim object if we can't see internal Content ID data via public API.
            # However, the public Data API doesn't expose Content ID claims directly to all users.
            # But 'uploadStatus' == 'rejected' if blocked.
            # Also 'licensedContent' boolean in contentDetails.
            # For standard user uploads, we can infer some issues if the video is blocked.
            
            # NOTE: True Content ID Match details require "YouTube Content ID API" which is restricted.
            # Standard Data API v3 only gives us basic info.
            # We will use what's available.
            
            return self._extract_copyright_info(video)

        except Exception as e:
            logger.error(f"Check failed: {e}")
            raise

    def _extract_copyright_info(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Extract copyright info from video object.
        
        Detection methods:
        1. rejectionReason == 'copyright' -> Video BLOCKED (strongest signal)
        2. licensedContent == True -> Content ID claim exists (may not be blocked)
        """
        
        status = video.get('status', {})
        content_details = video.get('contentDetails', {})
        processing_details = video.get('processingDetails', {})
        
        upload_status = status.get('uploadStatus')
        rejection_reason = status.get('rejectionReason')
        licensed_content = content_details.get('licensedContent', False)
        
        has_copyright = False
        claims = []
        claim_type = None
        
        # Check 1: Video completely blocked
        if rejection_reason == 'copyright':
            has_copyright = True
            claim_type = 'blocked'
            claims.append({
                'status': 'blocked', 
                'reason': 'Video bị chặn hoàn toàn do vi phạm bản quyền',
                'severity': 'critical'
            })
        
        # Check 2: Licensed content = Content ID claim (may still be viewable)
        elif licensed_content:
            has_copyright = True
            claim_type = 'claimed'
            claims.append({
                'status': 'claimed',
                'reason': 'Nội dung đã bị Content ID claim (có thể bị mất tiền quảng cáo)',
                'severity': 'warning'
            })
        
        # Additional checks for other restriction types
        region_restriction = content_details.get('regionRestriction', {})
        if region_restriction:
            blocked_countries = region_restriction.get('blocked', [])
            if blocked_countries:
                claims.append({
                    'status': 'region_blocked',
                    'reason': f'Bị chặn tại {len(blocked_countries)} quốc gia',
                    'severity': 'warning',
                    'countries': blocked_countries[:5]  # Show first 5
                })
        
        return {
            'has_copyright': has_copyright,
            'claim_type': claim_type,  # 'blocked', 'claimed', or None
            'claims': claims,
            'video_status': status,
            'content_details': content_details,
            'processing_details': processing_details,
            'licensed_content': licensed_content,
            'checked_at': time.time(),
            # Include raw data for debugging
            'raw_response': video
        }


    # poll_copyright_status KEPT SAME

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def delete_video(self, video_id: str) -> bool:
        """Delete a video (Real API)."""
        try:
            logger.info(f"Deleting video {video_id}...")
            self.youtube.videos().delete(id=video_id).execute()
            logger.info("✅ Video deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete video: {e}")
            return False

    def poll_copyright_status(
        self,
        video_id: str,
        max_wait_time: int = 300,
        check_interval: int = 30
    ) -> Dict[str, Any]:
        """
        Poll for copyright status until Content ID scan is complete.

        Args:
            video_id: YouTube video ID
            max_wait_time: Maximum time to wait in seconds
            check_interval: Seconds between status checks

        Returns:
            Final copyright status

        Raises:
            TimeoutError: If copyright check doesn't complete within max_wait_time
        """
        start_time = time.time()

        logger.info(
            f"Starting copyright status polling",
            video_id=video_id,
            max_wait_time=max_wait_time
        )

        while time.time() - start_time < max_wait_time:
            try:
                status = self.check_copyright_status(video_id)
                video_status = status.get('video_status', {})
                # FIX: use correct key with underscore (matching _extract_copyright_info)
                processing_details = status.get('processing_details', {})
                
                proc_status = processing_details.get('processingStatus') if processing_details else None
                upload_status = video_status.get('uploadStatus')
                logger.info(f"Video Status: {upload_status} | Processing: {proc_status}")
                
                if proc_status == 'succeeded':
                    # Processing done, check for copyright
                    if status.get('has_copyright'):
                        logger.warning(f"Copyright Found! Stopping poll.")
                        return status
                    
                    # GRACE PERIOD: Wait a bit more because copyright scan often takes 
                    # longer than basic video processing.
                    logger.info("Video processing complete. Waiting 30s grace period for copyright scan...")
                    time.sleep(30)
                    
                    # One last check
                    final_status = self.check_copyright_status(video_id)
                    logger.info("Grace period over. Final scan check complete.")
                    return final_status
                
                elif proc_status == 'failed':
                    logger.error("Video processing failed on YouTube side.")
                    return status
                
                # FALLBACK: If uploadStatus is 'processed' but processingDetails is None/empty
                # This means the video is ready but we didn't get processingDetails (API limitation)
                # Just return the current status
                elif upload_status == 'processed' and not proc_status:
                    logger.info("Video processed (no processingDetails available). Returning current status.")
                    return status

                # Still processing or queued
                logger.info("Still processing... waiting...")

            except Exception as e:
                logger.warning(
                    f"Copyright check failed, retrying",
                    video_id=video_id,
                    error=str(e)
                )

            # Wait before next check
            time.sleep(check_interval)

        logger.warning(f"Timeout reached ({max_wait_time}s). Returning last known status.")
        
        # Instead of raising exception, return last known status with timeout flag
        # This allows UI to handle gracefully
        try:
            last_status = self.check_copyright_status(video_id)
            last_status['timeout'] = True
            last_status['timeout_seconds'] = max_wait_time
            return last_status
        except Exception:
            # If even the final check fails, return a basic timeout response
            return {
                'has_copyright': None,  # Unknown
                'claim_type': 'timeout',
                'claims': [],
                'timeout': True,
                'timeout_seconds': max_wait_time,
                'error': f'Processing timeout after {max_wait_time}s'
            }


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def delete_video(self, video_id: str) -> bool:
        """Delete a video (Real API)."""
        try:
            logger.info(f"Deleting video {video_id}...")
            self.youtube.videos().delete(id=video_id).execute()
            logger.info("✅ Video deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete video: {e}")
            return False

    def upload_and_check_copyright(
        self,
        audio_file: str,
        video_file: str,
        song_name: str,
        max_wait_time: int = 300,
        keep_video: bool = False
    ) -> Dict[str, Any]:
        """
        Upload test video and check for copyright issues.

        Args:
            audio_file: Path to audio file
            video_file: Path to video file
            song_name: Song name for metadata
            max_wait_time: Maximum time to wait for copyright check

        Returns:
            Dictionary containing copyright check results
        """
        try:
            # Get upload settings from config
            upload_settings = config.get_test_upload_settings()

            # Format title
            title_template = upload_settings.get('title', '[TEST] Copyright Check - {song_name}')
            title = title_template.format(song_name=song_name)

            description = upload_settings.get('description', 'Testing for copyright claims')
            privacy = upload_settings.get('privacy', 'unlisted')

            logger.info(
                f"Starting upload and copyright check",
                audio_file=audio_file,
                video_file=video_file,
                song_name=song_name
            )

            # Upload video
            upload_result = self.upload_test_video(
                audio_file=audio_file,
                video_file=video_file,
                title=title,
                description=description,
                privacy=privacy
            )

            video_id = upload_result['id']

            # Poll for copyright status
            copyright_status = self.poll_copyright_status(
                video_id,
                max_wait_time=max_wait_time
            )

            # Clean up test video if configured
            auto_delete = upload_settings.get('auto_delete_after_check', True)
            
            if keep_video:
                auto_delete = False
                logger.info("Keep Video requested - skipping auto-delete.")
            
            if auto_delete:
                self.delete_video(video_id)

            result = {
                'video_id': video_id,
                'upload_result': upload_result,
                'copyright_status': copyright_status,
                'video_deleted': auto_delete,
                'song_name': song_name
            }

            logger.info(
                f"Upload and copyright check completed",
                video_id=video_id,
                has_copyright=copyright_status.get('has_copyright', False)
            )

            return result

        except Exception as e:
            error_result = {
                'status': 'failed',
                'error': str(e),
                'song_name': song_name
            }

            logger.error(
                f"Upload and copyright check failed",
                **error_result
            )

            return error_result

    def evaluate_copyright_risk(self, copyright_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate copyright risk level.

        Args:
            copyright_status: Copyright check results

        Returns:
            Risk assessment
        """
        has_copyright = copyright_status.get('has_copyright', False)
        claims = copyright_status.get('claims', [])

        if not has_copyright:
            return {
                'risk_level': 'safe',
                'match_percent': 0,
                'recommendation': 'proceed'
            }

        # Find highest match percentage
        max_match = 0
        for claim in claims:
            match_percent = claim.get('matchPercent', 0)
            max_match = max(max_match, match_percent)

        # Determine risk level
        if max_match >= config.copyright_match_threshold:
            risk_level = 'high'
            recommendation = 'retry_with_changes'
        elif max_match >= config.safe_match_threshold:
            risk_level = 'medium'
            recommendation = 'retry_or_manual_review'
        else:
            risk_level = 'low'
            recommendation = 'proceed_with_caution'

        return {
            'risk_level': risk_level,
            'match_percent': max_match,
            'recommendation': recommendation,
            'claims_count': len(claims)
        }


# Global YouTube client instance
youtube_checker = YouTubeCopyrightChecker()
