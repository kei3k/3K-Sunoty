"""
YouTube Studio Copyright Checker using Selenium.

Checks each video's dedicated copyright page for accurate results.
Uses existing browser profile with saved cookies.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import os
import logging
import unicodedata

logger = logging.getLogger(__name__)


class YouTubeStudioChecker:
    """Check copyright status via YouTube Studio web interface."""
    
    STUDIO_URL = "https://studio.youtube.com"
    
    def __init__(self, user_data_dir=None, headless=False):
        if not user_data_dir:
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_script_dir))
            self.user_data_dir = os.path.join(project_root, "chrome_profile")
        else:
            self.user_data_dir = user_data_dir
            
        self.headless = headless
        self.driver = None
        
    def _init_browser(self):
        """Initialize Chrome browser with profile."""
        if self.driver:
            return
            
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
            
        if self.user_data_dir:
            options.add_argument(f"user-data-dir={self.user_data_dir}")
            
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1920, 1080)
        
    def close(self):
        """Close browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def _navigate_to_studio(self):
        """Navigate to YouTube Studio and wait for load."""
        self._init_browser()
        self.driver.get(self.STUDIO_URL)
        time.sleep(3)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytcp-icon-button, ytd-masthead"))
            )
            return True
        except TimeoutException:
            return False

    def _normalize_text(self, text: str) -> str:
        """Remove accents and normalize text for robust comparison."""
        if not text:
            return ""
        nfkd_form = unicodedata.normalize('NFKD', text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()

    def check_copyright_by_video_id(self, video_id: str, max_retries: int = 5) -> dict:
        """
        Check copyright by navigating directly to the video's Copyright tab.
        URL: studio.youtube.com/video/{video_id}/copyright
        
        This is MUCH more reliable than scanning the content list.
        """
        try:
            self._init_browser()
            
            copyright_url = f"{self.STUDIO_URL}/video/{video_id}/copyright"
            print(f"[STUDIO] Navigating to copyright page: {copyright_url}")
            self.driver.get(copyright_url)
            time.sleep(5)
            
            for attempt in range(max_retries):
                page_source = self.driver.page_source
                page_text = self._normalize_text(self.driver.find_element(By.TAG_NAME, "body").text)
                
                # Debug: save page text
                try:
                    with open("debug_copyright_page.log", "a", encoding="utf-8") as f:
                        f.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} | Video: {video_id} | Attempt: {attempt+1} ---\n")
                        body_text = self.driver.find_element(By.TAG_NAME, "body").text
                        f.write(body_text[:3000] + "\n")
                except: pass
                
                # Check if still processing
                processing_keywords = ['dang kiem tra', 'checking', 'processing', 'dang xu ly']
                is_processing = any(kw in page_text for kw in processing_keywords)
                
                if is_processing and attempt < max_retries - 1:
                    print(f"[STUDIO] Video still processing... retry {attempt+1}/{max_retries}")
                    time.sleep(30)
                    self.driver.refresh()
                    time.sleep(5)
                    continue
                
                # === DETECTION LOGIC (Using exact YouTube Studio selectors) ===
                
                # CLEAN indicator: this div appears when NO copyright issues found
                # <div class="ytcrVideoContentListNoContentMessage">
                #   Không tìm thấy nội dung có bản quyền trong video của bạn.
                # </div>
                no_copyright_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.ytcrVideoContentListNoContentMessage"
                )
                
                if no_copyright_elements:
                    msg_text = no_copyright_elements[0].text.strip()
                    print(f"[STUDIO] ✅ CLEAN: Found 'no copyright' message: {msg_text}")
                    return {
                        "status": "success",
                        "video_id": video_id,
                        "has_copyright": False,
                        "restriction_text": msg_text or "No copyright found"
                    }
                
                # COPYRIGHT indicator: claim rows have touch feedback shapes
                # <div class="yt-spec-touch-feedback-shape__fill"></div>
                # These appear inside clickable claim rows
                claim_feedback = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.yt-spec-touch-feedback-shape__fill"
                )
                
                if claim_feedback:
                    print(f"[STUDIO] ⚠️ COPYRIGHT: Found {len(claim_feedback)} claim elements")
                    
                    # Try to get claim details from the page
                    claims_detail = []
                    try:
                        body_text = self.driver.find_element(By.TAG_NAME, "body").text
                        claims_detail = [body_text[:500]]
                    except: pass
                    
                    return {
                        "status": "success",
                        "video_id": video_id,
                        "has_copyright": True,
                        "claims": claims_detail,
                        "restriction_text": f"Copyright claims found ({len(claim_feedback)} items)"
                    }
                
                # Neither indicator found — page may not have loaded yet
                if len(page_text) < 100:
                    print(f"[STUDIO] Page seems empty, retrying...")
                    time.sleep(10)
                    self.driver.refresh()
                    time.sleep(5)
                    continue
                
                # Fallback: if page loaded but no clear signal, check text
                page_text_norm = self._normalize_text(
                    self.driver.find_element(By.TAG_NAME, "body").text
                )
                if 'khong tim thay noi dung co ban quyen' in page_text_norm:
                    print(f"[STUDIO] ✅ CLEAN (text fallback)")
                    return {
                        "status": "success",
                        "video_id": video_id,
                        "has_copyright": False,
                        "restriction_text": "No copyright (text match)"
                    }
                
                # If we still can't determine, assume uncertain
                print(f"[STUDIO] ❓ Cannot determine copyright status for {video_id}")
                print(f"[STUDIO] Page text preview: {page_text[:200]}")
                return {
                    "status": "success",
                    "video_id": video_id,
                    "has_copyright": False,
                    "restriction_text": "Could not determine (check manually)"
                }
                    
        except Exception as e:
            logger.error(f"Copyright page check failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e), "video_id": video_id}

    def check_recent_videos(self, limit: int = 20) -> list:
        """Scan content list for recent videos and check each one's copyright page."""
        results = []
        try:
            if not self._navigate_to_studio():
                return results
            
            time.sleep(2)
            
            # Navigate to content page
            current_url = self.driver.current_url
            if "/channel/" in current_url:
                channel_base = current_url.split("/channel/")[0] + "/channel/" + current_url.split("/channel/")[1].split("/")[0]
                content_url = f"{channel_base}/videos/upload"
            else:
                content_url = f"{self.STUDIO_URL}/videos/upload"
            
            self.driver.get(content_url)
            time.sleep(5)
            
            # Find video rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "ytcp-video-row")
            print(f"[STUDIO] Found {len(rows)} video rows on content page")
            
            video_ids = []
            video_titles = []
            
            for row in rows[:limit]:
                try:
                    # Get video title
                    title_elem = row.find_element(By.CSS_SELECTOR, "#video-title")
                    title = title_elem.text.strip()
                    
                    # Get video link to extract ID
                    try:
                        link = row.find_element(By.CSS_SELECTOR, "a[href*='/video/']")
                        href = link.get_attribute("href")
                        if "/video/" in href:
                            vid_id = href.split("/video/")[1].split("/")[0]
                            video_ids.append(vid_id)
                            video_titles.append(title)
                    except:
                        # Try alternate extraction
                        row_html = row.get_attribute("innerHTML")
                        import re
                        match = re.search(r'/video/([a-zA-Z0-9_-]{11})', row_html)
                        if match:
                            video_ids.append(match.group(1))
                            video_titles.append(title)
                except:
                    continue
            
            print(f"[STUDIO] Extracted {len(video_ids)} video IDs to check")
            
            # Now check each video's copyright page individually
            for i, (vid_id, title) in enumerate(zip(video_ids, video_titles)):
                print(f"[STUDIO] Checking [{i+1}/{len(video_ids)}] {title[:50]}...")
                
                result = self.check_copyright_by_video_id(vid_id, max_retries=2)
                
                results.append({
                    "video_title": title,
                    "video_id": vid_id,
                    "has_copyright": result.get("has_copyright", False),
                    "restriction_text": result.get("restriction_text", "Unknown")
                })
                
                time.sleep(2)  # Brief pause between checks
            
            return results
            
        except Exception as e:
            logger.error(f"Recent videos scan failed: {e}")
            import traceback
            traceback.print_exc()
            return results


# Singleton
studio_checker = YouTubeStudioChecker()
