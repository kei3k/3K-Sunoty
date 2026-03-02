"""
YouTube Studio Copyright Checker using Selenium.

Scrapes YouTube Studio directly to check for Content ID claims and copyright status.
Uses existing browser profile with saved cookies (same as Suno).
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
        """
        Initialize checker with browser profile.
        """
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

    def check_copyright_by_video_id(self, video_id: str, max_retries: int = 15) -> dict:
        """
        NEW STRATEGY: Instead of the fragile Edit page, we use the Search feature 
        on the Content page to isolate the video row. 
        This is much more stable and matches our successful 'scan' logs.
        """
        try:
            if not self._navigate_to_studio():
                return {"status": "error", "message": "Cannot access YouTube Studio"}
            
            # 1. Navigate to Content page (Wait for redirect if needed)
            time.sleep(2)
            current_url = self.driver.current_url
            if "/channel/" in current_url:
                channel_base = current_url.split("/channel/")[0] + "/channel/" + current_url.split("/channel/")[1].split("/")[0]
                content_url = f"{channel_base}/videos/upload"
            else:
                content_url = f"{self.STUDIO_URL}/videos/upload"
            
            self.driver.get(content_url)
            time.sleep(4)

            # 2. Search for the video ID to isolate the row
            try:
                search_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#search-icon, ytcp-icon-button[id='search-icon']"))
                )
                search_btn.click()
                time.sleep(1)
                
                search_input = self.driver.find_element(By.CSS_SELECTOR, "input#search-input, input[type='text']")
                search_input.clear()
                search_input.send_keys(video_id)
                search_input.send_keys(Keys.RETURN)
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Search UI failed, attempting direct scan: {e}")

            # 3. Polling for final result
            for attempt in range(max_retries):
                # Look for video rows
                rows = self.driver.find_elements(By.CSS_SELECTOR, "ytcp-video-row")
                
                if not rows:
                    if attempt < 3: # Give it some time to load search results
                        time.sleep(3)
                        continue
                    return {"status": "not_found", "message": f"Video {video_id} not found in list", "has_copyright": None}
                
                # Check first row (should be our video)
                row = rows[0]
                
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(1)
                
                # Get text
                raw_row_text = self.driver.execute_script("return arguments[0].innerText;", row)
                row_text = self._normalize_text(raw_row_text)
                
                # DEBUG Log
                with open("debug_copyright_text.log", "a", encoding="utf-8") as f:
                    f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} (Search ID: {video_id}) ---\n")
                    f.write(f"Row Text: {raw_row_text}\n\n")

                # Keywords
                checking_keywords = ['checking', 'dang kiem tra', 'dang xu ly', 'processing', 'cho xu ly', 'qua trinh xu ly']
                copyright_keywords = ['ban quyen', 'copyright', 'blocked', 'chan', 'da chan', 'claim', 'khieu nai', 'han che']
                # Exact values that indicate "safe" (no restrictions)
                safe_exact_values = ['khong co', 'none', 'no issues']

                is_checking = any(kw in row_text for kw in checking_keywords)
                
                if is_checking and attempt < max_retries - 1:
                    logger.info(f"Video {video_id} still processing... retry {attempt+1}")
                    time.sleep(15)
                    self.driver.refresh()
                    time.sleep(5)
                    continue

                # Not checking, let's look for claims
                # Strategy: Check the #restrictions-text element directly for the exact value
                has_copyright = False
                res_text = "Unknown"
                
                try:
                    res_div = row.find_element(By.CSS_SELECTOR, "#restrictions-text")
                    res_text = res_div.text.strip()
                    norm_res = self._normalize_text(res_text)
                    
                    # Check for EXACT match of safe values (not substring)
                    # "khong co" = "none" (safe), but "khong cong khai" = "unlisted" (different)
                    if norm_res in safe_exact_values:
                        has_copyright = False
                    elif norm_res and any(kw in norm_res for kw in copyright_keywords):
                        has_copyright = True
                    elif norm_res and norm_res not in safe_exact_values:
                        # If there's text but it's not explicitly safe, assume claim
                        has_copyright = True
                except:
                    # Fallback to full row text - look for copyright keywords
                    # Be conservative: if we see copyright keywords, it's a claim
                    has_copyright = any(kw in row_text for kw in copyright_keywords)
                
                return {
                    "status": "success",
                    "video_id": video_id,
                    "has_copyright": has_copyright,
                    "is_checking": is_checking,
                    "restriction_text": res_text
                }
                
        except Exception as e:
            logger.error(f"ID check failed: {e}")
            return {"status": "error", "message": str(e), "video_id": video_id}

    def check_recent_videos(self, limit: int = 20) -> list:
        """Original list scan method (kept for compatibility)"""
        results = []
        try:
            if not self._navigate_to_studio(): return results
            time.sleep(2)
            self.driver.get(f"{self.driver.current_url.split('/channel/')[0]}/channel/{self.driver.current_url.split('/channel/')[1].split('/')[0]}/videos/upload")
            time.sleep(5)
            rows = self.driver.find_elements(By.CSS_SELECTOR, "ytcp-video-row")
            for row in rows[:limit]:
                try:
                    title = row.find_element(By.CSS_SELECTOR, "#video-title").text
                    status = self._extract_copyright_from_row(row, title)
                    if status: results.append(status)
                except: continue
            return results
        except: return results

    def _extract_copyright_from_row(self, row, title: str) -> dict:
        """Helper for batch scan"""
        raw_text = self.driver.execute_script("return arguments[0].innerText;", row)
        norm_text = self._normalize_text(raw_text)
        
        # Try to find the restrictions column specifically
        res_text = ""
        try:
            res_div = row.find_element(By.CSS_SELECTOR, "#restrictions-text, .restrictions-text, [id*='restrictions']")
            res_text = self._normalize_text(res_div.text.strip())
        except:
            # Fallback: look for line-by-line in row text
            # The restrictions value is typically on its own line
            lines = [self._normalize_text(line) for line in raw_text.split('\n') if line.strip()]
            for line in lines:
                # Check if this line is ONLY a restriction status (not mixed with other text)
                if line in ['khong co', 'ban quyen', 'han che', 'none', 'copyright']:
                    res_text = line
                    break
        
        # Check the restrictions text specifically, not the whole row
        # "khong co" means "none" (no restrictions) - but ONLY if it's the exact restriction value
        # "khong cong khai" means "unlisted" (privacy setting) - should NOT trigger safe
        if res_text:
            safe = res_text in ['khong co', 'none', 'no issues']
            has_cp = res_text in ['ban quyen', 'copyright', 'han che', 'claim', 'blocked']
        else:
            # Fallback: use full text but be more careful
            # Check for copyright keywords first
            has_cp = any(kw in norm_text for kw in ['ban quyen', 'copyright', 'claim', 'han che'])
            # Only mark safe if "khong co" appears AND NOT as part of "khong cong khai"
            # Use regex or check for exact phrase on newline
            import re
            safe = bool(re.search(r'\bkhong co\b', norm_text)) and 'khong cong khai' not in norm_text
            # If both, copyright wins (more conservative)
            if has_cp:
                safe = False
        
        return {"video_title": title, "has_copyright": has_cp, "restriction_text": raw_text}

# Singleton
studio_checker = YouTubeStudioChecker()
