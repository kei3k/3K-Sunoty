"""
YouTube Studio Copyright Scraper.

Uses Selenium to scrape detailed copyright information from YouTube Studio,
which provides more details than the limited Data API v3.
"""

import time
import re
from typing import Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class YouTubeStudioScraper:
    """Scrapes copyright details from YouTube Studio."""
    
    STUDIO_VIDEO_URL = "https://studio.youtube.com/video/{video_id}/copyright"
    
    def __init__(self, chrome_profile_path: Optional[str] = None):
        """Initialize Selenium driver with existing Chrome profile for login session.
        
        Args:
            chrome_profile_path: Path to Chrome user data directory.
                                If None, will look for default profile.
        """
        self.driver = None
        self.chrome_profile_path = chrome_profile_path
        
    def _init_driver(self):
        """Initialize Chrome driver with profile for YouTube login."""
        options = Options()
        
        # Use existing Chrome profile to reuse YouTube login
        if self.chrome_profile_path:
            options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        else:
            # Try default Chrome profile on Windows
            import os
            default_profile = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
            if os.path.exists(default_profile):
                options.add_argument(f"--user-data-dir={default_profile}")
                options.add_argument("--profile-directory=Default")
        
        # Run headless for background operation
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Stealth options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        self.driver = webdriver.Chrome(options=options)
        
    def check_copyright_details(self, video_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Scrape copyright details from YouTube Studio.
        
        Args:
            video_id: YouTube video ID
            timeout: Max seconds to wait for page load
            
        Returns:
            Dictionary with detailed copyright info:
            - has_claims: bool
            - claims: List of claim details
            - raw_text: Raw text from copyright section
        """
        result = {
            'has_claims': False,
            'claims': [],
            'raw_text': '',
            'error': None,
            'checked_at': time.time()
        }
        
        try:
            if not self.driver:
                self._init_driver()
            
            url = self.STUDIO_VIDEO_URL.format(video_id=video_id)
            logger.info(f"Navigating to YouTube Studio: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, timeout)
            
            # Check if we need to login
            if "accounts.google.com" in self.driver.current_url:
                result['error'] = "Login required. Please login to YouTube in Chrome first."
                logger.error(result['error'])
                return result
            
            # Wait for copyright section to load
            # The copyright page shows claims in a table or "No issues found"
            try:
                # Look for "No issues found" message
                no_issues = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'No issues found')]"))
                )
                result['raw_text'] = "No issues found"
                logger.info("✅ No copyright issues found in YouTube Studio")
                return result
                
            except TimeoutException:
                # No "No issues" message, look for claims
                pass
            
            # Look for copyright claim rows
            try:
                # Try to find claim elements
                claim_rows = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "ytcp-video-copyright-issue-row, .copyright-claim-row"
                )
                
                if claim_rows:
                    result['has_claims'] = True
                    for row in claim_rows:
                        claim_text = row.text
                        result['raw_text'] += claim_text + "\n"
                        
                        # Try to parse claim details
                        claim_info = self._parse_claim_row(claim_text)
                        if claim_info:
                            result['claims'].append(claim_info)
                    
                    logger.warning(f"⚠️ Found {len(claim_rows)} copyright claim(s)")
                else:
                    # Try alternative selectors
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    result['raw_text'] = page_text
                    
                    # Check for common copyright phrases
                    copyright_phrases = [
                        "Copyright claim",
                        "Content ID",
                        "Matched content",
                        "Audio may be muted"
                    ]
                    
                    for phrase in copyright_phrases:
                        if phrase.lower() in page_text.lower():
                            result['has_claims'] = True
                            result['claims'].append({
                                'type': 'detected',
                                'reason': f'Found "{phrase}" in page'
                            })
                            
            except Exception as e:
                logger.warning(f"Error parsing claims: {e}")
                # Still try to get page text
                try:
                    result['raw_text'] = self.driver.find_element(By.TAG_NAME, "body").text
                except:
                    pass
                    
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Studio scraping failed: {e}")
            
        return result
    
    def _parse_claim_row(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a claim row text into structured data."""
        if not text:
            return None
            
        claim = {
            'raw': text,
            'type': 'unknown',
            'content': None,
            'claimant': None,
            'action': None,
            'timestamp': None
        }
        
        # Try to extract timestamp (e.g., "0:15 - 2:30")
        timestamp_match = re.search(r'(\d+:\d+)\s*-\s*(\d+:\d+)', text)
        if timestamp_match:
            claim['timestamp'] = f"{timestamp_match.group(1)} - {timestamp_match.group(2)}"
        
        # Try to identify action type
        text_lower = text.lower()
        if 'blocked' in text_lower or 'muted' in text_lower:
            claim['action'] = 'blocked'
            claim['type'] = 'blocked'
        elif 'monetized' in text_lower or 'ads' in text_lower:
            claim['action'] = 'monetized'
            claim['type'] = 'claimed'
        elif 'tracked' in text_lower:
            claim['action'] = 'tracked'
            claim['type'] = 'tracked'
        
        return claim
    
    def poll_until_scanned(
        self, 
        video_id: str, 
        max_wait: int = 300, 
        check_interval: int = 30
    ) -> Dict[str, Any]:
        """Poll YouTube Studio until Content ID scan is complete.
        
        Args:
            video_id: YouTube video ID
            max_wait: Maximum seconds to wait
            check_interval: Seconds between checks
            
        Returns:
            Final copyright status
        """
        start_time = time.time()
        last_result = None
        
        while time.time() - start_time < max_wait:
            result = self.check_copyright_details(video_id)
            last_result = result
            
            if result.get('error'):
                logger.error(f"Scrape error: {result['error']}")
                break
            
            # Check if scan is still in progress
            raw_text = result.get('raw_text', '').lower()
            if 'checking' in raw_text or 'processing' in raw_text or 'scanning' in raw_text:
                logger.info(f"Still scanning... waiting {check_interval}s")
                time.sleep(check_interval)
                continue
            
            # Scan complete
            return result
            
        logger.warning(f"Timeout after {max_wait}s")
        return last_result or {'error': 'Timeout', 'has_claims': None}
    
    def close(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            
    def __del__(self):
        self.close()


# Convenience function
def scrape_studio_copyright(video_id: str, profile_path: Optional[str] = None) -> Dict[str, Any]:
    """One-shot function to scrape copyright details.
    
    Args:
        video_id: YouTube video ID
        profile_path: Chrome profile path (optional)
        
    Returns:
        Copyright details dictionary
    """
    scraper = YouTubeStudioScraper(profile_path)
    try:
        return scraper.check_copyright_details(video_id)
    finally:
        scraper.close()
