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
                
                # === DETECTION LOGIC ===
                # On the copyright page, YouTube shows either:
                # - "No issues found" / "Không tìm thấy vấn đề nào" (clean)
                # - A table of claims with details (has copyright)
                
                # Method 1: Look for claim rows/elements
                has_claims = False
                claims_detail = []
                
                # Check for claim rows (ytcp-table-row or similar)
                try:
                    # YouTube Studio copyright page uses specific elements for claims
                    claim_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        "ytcp-copyright-issue-row, .copyright-issue-row, "
                        "ytcp-copyright-claim-row, [class*='claim'], "
                        "ytcp-table-body ytcp-table-row")
                    
                    if claim_elements:
                        has_claims = True
                        for elem in claim_elements[:5]:
                            try:
                                claim_text = elem.text.strip()
                                if claim_text:
                                    claims_detail.append(claim_text)
                            except: pass
                        print(f"[STUDIO] Found {len(claim_elements)} claim element(s)")
                except: pass
                
                # Method 2: Text-based detection
                if not has_claims:
                    # Check for "no issues" indicators
                    no_issues_keywords = [
                        'khong tim thay van de', 'no issues found', 'no copyright issues',
                        'khong co van de', 'no issues'
                    ]
                    
                    is_clean = any(kw in page_text for kw in no_issues_keywords)
                    
                    if is_clean:
                        print(f"[STUDIO] ✅ No copyright issues for {video_id}")
                        return {
                            "status": "success",
                            "video_id": video_id,
                            "has_copyright": False,
                            "restriction_text": "No issues found"
                        }
                    
                    # Check for copyright claim keywords
                    claim_keywords = [
                        'ban quyen', 'copyright claim', 'content id', 
                        'khieu nai', 'claim', 'matched third party',
                        'noi dung phu hop', 'visual content', 'audio content',
                        'blocked', 'da chan', 'bi chan',
                        'han che o mot so quoc gia', 'restricted'
                    ]
                    
                    for kw in claim_keywords:
                        if kw in page_text:
                            has_claims = True
                            print(f"[STUDIO] Found copyright keyword: '{kw}'")
                            break
                
                # Method 3: Check for the "issues" count badge
                if not has_claims:
                    try:
                        # Look for issue count indicators
                        issue_badges = self.driver.find_elements(By.CSS_SELECTOR, 
                            "[class*='issue-count'], [class*='copyright-status'], "
                            ".issue-indicator, ytcp-badge")
                        for badge in issue_badges:
                            badge_text = badge.text.strip()
                            if badge_text and badge_text not in ['0', '']:
                                try:
                                    count = int(badge_text)
                                    if count > 0:
                                        has_claims = True
                                        print(f"[STUDIO] Issue badge count: {count}")
                                except: pass
                    except: pass
                
                # Return result
                if has_claims:
                    print(f"[STUDIO] ⚠️ COPYRIGHT CLAIMS FOUND for {video_id}")
                    return {
                        "status": "success",
                        "video_id": video_id,
                        "has_copyright": True,
                        "claims": claims_detail,
                        "restriction_text": "Copyright claims found"
                    }
                else:
                    # If we couldn't determine either way, check if page loaded properly
                    if len(page_text) < 50:
                        print(f"[STUDIO] Page seems empty, retrying...")
                        time.sleep(10)
                        self.driver.refresh()
                        time.sleep(5)
                        continue
                    
                    # Default: if no clear signal, report as clean but flag uncertainty
                    print(f"[STUDIO] No clear copyright signals for {video_id} (may need more processing time)")
                    return {
                        "status": "success",
                        "video_id": video_id,
                        "has_copyright": False,
                        "restriction_text": "No clear copyright signals"
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
