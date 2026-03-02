"""
Suno.ai Browser Automation using Selenium
- Wait for manual login
- Generate songs from prompts
- Extract audio URLs
- Handle multiple generations
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
import json
import logging
import os

logger = logging.getLogger(__name__)

class SunoBrowserAutomation:
    def __init__(self, headless=False, user_data_dir=None):
        """
        Initialize Suno browser automation

        Args:
            headless (bool): Run browser in headless mode (default: False)
            user_data_dir (str): Path to Chrome user data directory for persistence
        """
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        
        if user_data_dir:
            options.add_argument(f"user-data-dir={user_data_dir}")
            
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Configure download behavior
        prefs = {
            "download.default_directory": os.path.abspath("output/music"),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1920, 1080)

    def safe_click(self, element):
        """
        Robust click method: Try normal click, then JS click.
        """
        try:
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                logger.error(f"Safe click failed: {e}")
                return False

    def handle_captcha(self):
        """
        Check for CAPTCHA/Cloudflare and wait for user to solve it.
        """
        try:
            # Check for common CAPTCHA indicators
            indicators = [
                "//iframe[contains(@title, 'reCAPTCHA')]",
                "//*[contains(text(), 'Verify you are human')]",
                "//*[contains(text(), 'security check')]",
                "//*[contains(text(), 'Cloudflare')]",
                "//div[contains(@class, 'interface-challenge')]",
                "//div[contains(@class, 'display-error') and contains(., 'Please try again')]",
                "//div[contains(@class, 'challenge-breadcrumbs')]"
            ]
            
            captcha_found = False
            for selector in indicators:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and any(e.is_displayed() for e in elements):
                    captcha_found = True
                    break
            
            if captcha_found:
                logger.warning("⚠️ CAPTCHA/Security Check detected!")
                print("\n" + "!"*60)
                print("⚠️  CAPTCHA DETECTED! PLEASE SOLVE MANUALLY IN BROWSER")
                print("!"*60 + "\n")
                
                # Show GUI popup if possible
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    
                    # Create hidden root
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    
                    # Show alert
                    messagebox.showwarning(
                        "🤖 CAPTCHA Detected!",
                        "A CAPTCHA security check has appeared.\n\n"
                        "Please solve it manually in the browser window,\n"
                        "then click OK to continue.\n\n"
                        "The script will wait for you."
                    )
                    root.destroy()
                except Exception as popup_err:
                    logger.warning(f"Popup failed (tkinter issue): {popup_err}. Waiting via console...")
                
                # Wait loop until captcha is gone
                while True:
                    still_there = False
                    for selector in indicators:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            if elements and any(e.is_displayed() for e in elements):
                                still_there = True
                                break
                        except:
                            pass
                    
                    if not still_there:
                        logger.info("✅ CAPTCHA resolved/disappeared. Resuming...")
                        time.sleep(2)
                        return
                        
                    time.sleep(2)
        except Exception as e:
            logger.error(f"Error in captcha handler: {e}")

    def wait_and_click_text(self, texts, timeout=10):
        """
        Wait for and click an element containing any of the provided texts.
        Prioritizes buttons, then spans/divs with role button.
        """
        start = time.time()
        while time.time() - start < timeout:
            for text in texts:
                try:
                    xpath = f"//*[contains(text(), '{text}')]"
                    logger.info(f"[SELECTOR] Looking for text '{text}' with XPath: {xpath}")
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                                time.sleep(0.5)
                                if self.safe_click(el):
                                    return True
                            except:
                                pass
                except:
                    pass
            time.sleep(0.5)
        
        logger.warning(f"❌ Timed out waiting for text(s): {texts}")
        return False

    def navigate_to_suno(self):
        """Navigate to Suno.ai"""
        logger.info("Navigating to Suno.ai...")
        self.driver.get("https://www.suno.ai")
        time.sleep(3)

    def wait_for_login(self, timeout=1800):
        """
        Wait for user to manually login to Suno

        Args:
            timeout (int): Timeout in seconds (default: 30 minutes)

        Returns:
            bool: True if login detected, False if timeout
        """
        logger.info("Waiting for manual login (timeout: 30 minutes)...")
        print("\n" + "="*60)
        print("[!] PLEASE LOGIN TO SUNO.AI IN THE BROWSER")
        print("="*60)
        print("[...] Waiting... (auto-continue after login)")
        print("="*60 + "\n")

        try:
            # Wait for user to reach dashboard (look for "Create" button)
            login_xpath = "//button[contains(., 'Create')]"
            logger.info(f"[SELECTOR] Waiting for Login (Create button) with XPath: {login_xpath}")
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, login_xpath))
            )
            logger.info("✅ Login detected!")
            time.sleep(2)
            return True
        except TimeoutException:
            logger.error("❌ Login timeout - no action detected")
            return False

    def upload_audio(self, file_path):
        """
        Upload audio file for remixing
        Args:
            file_path (str): Path to audio file
        Returns:
            bool: Success
        """
        try:
            logger.info(f"Uploading audio: {file_path}")
            
            # Find file input - Suno usually has strict file input hidden or standard
            # We try standard input first
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            
            file_input.send_keys(os.path.abspath(file_path))
            logger.info("✅ File path sent to input")
            
            # Wait for upload to likely finish (e.g. check for audio player or specific UI change)
            # This is tricky without live site access, so we wait a bit
            time.sleep(10) 
            return True
            
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return False

    def generate_remix(self, prompt, audio_path, title=None, style="", wait_for_generation=True, max_wait=600):
        """
        Generate remix/cover via Browser using detailed user steps
        """
        try:
            logger.info(f"Generating remix for: {audio_path}")
            
            # Step 1: Navigate to Create
            logger.info("[STEP 1/9] Navigating to Create page...")
            self.driver.get("https://suno.com/create")
            self.handle_captcha()
            time.sleep(3)
            
            # Step 2: Enter Prompt
            logger.info("[STEP 2/9] Entering Prompt...")
            try:
                prompt_xpath = '//*[@id="main-container"]/div/div/div/div/div/div[3]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div[1]/div/textarea'
                logger.info(f"[SELECTOR] Looking for Prompt Textarea with XPath: {prompt_xpath}")
                prompt_area = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, prompt_xpath))
                )
                prompt_area.clear()
                final_prompt = prompt if prompt else f"Cover of uploaded song, {style}"
                prompt_area.send_keys(final_prompt)
                logger.info("✅ Entered prompt")
            except Exception as e:
                logger.warning(f"Using fallback prompt selector: {e}")
                try:
                    fallback_xpath = "//textarea[contains(@class, 'resize-none')]"
                    logger.info(f"[SELECTOR] Using fallback Prompt XPath: {fallback_xpath}")
                    prompt_area = self.driver.find_element(By.XPATH, fallback_xpath)
                    prompt_area.send_keys(prompt if prompt else f"Cover, {style}")
                except:
                    pass
            time.sleep(2)

            # Step 3: Send File Directly (Matching debug_full_process.py)
            logger.info("[STEP 3/9] Sending File to Input...")
            try:
                # Find file input directly - matching debug script
                file_input_css = "input[type='file']"
                logger.info(f"[SELECTOR] Looking for File Input with CSS: {file_input_css}")
                file_input = self.driver.find_element(By.CSS_SELECTOR, file_input_css)
                file_input.send_keys(os.path.abspath(audio_path))
                logger.info("✅ File sent to input")
                time.sleep(5)  # Wait for modal to appear (matching debug)
            except Exception as e:
                logger.error(f"Upload step failed: {e}")
                raise Exception("Critical: Could not upload file.")

            # Step 4: Agree to Terms
            logger.info("[STEP 4/9] Check 'Agree to Terms'...")
            if self.wait_and_click_text(["Agree to Terms", "Agree", "I Agree"], timeout=3):
                logger.info("✅ SUCCESS: Accepted Terms.")
            else:
                 logger.info("ℹ️ Terms button not found (Already accepted or skipped).")
            time.sleep(1)

            # Step 4.5: RENAME SONG
            logger.info("[STEP 4.5/9] Renaming song...")
            try:
                # Use passed title or fallback
                song_title = title if title else (prompt[:50] if prompt else "Remix Song")
                renamed = False
                
                # Strategy 1: Find Input directly (if visible)
                try:
                    title_input = self.driver.find_element(By.XPATH, "//input[@placeholder='Title' or @name='title']")
                    if title_input.is_displayed():
                        title_input.clear()
                        title_input.send_keys(song_title)
                        renamed = True
                        logger.info("✅ Renamed via direct input")
                except: pass
                
                # Strategy: PROVEN Full XPath + Active Element Focus
                # XPath: /html/body/div[9]/div[3]/div/section/div/div[2]/div[1]/div/button
                if not renamed:
                    try:
                        # Strategy 2: User-Proven Full XPath
                        logger.info("Using proven Full XPath for Rename...")
                        try:
                            # Exact XPath from user debug
                            edit_xpath = "/html/body/div[9]/div[3]/div/section/div/div[2]/div[1]/div/button"
                            
                            # Wait slightly for animation
                            # Use WebDriverWait exactly like debug_full_process.py
                            edit_btn = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, edit_xpath))
                            )
                            logger.info(f"✅ Found Edit Button (Full XPath)")
                            
                            # Highlight for visual confirmation
                            self.driver.execute_script("arguments[0].style.border='3px solid red'", edit_btn)
                            
                            self.driver.execute_script("arguments[0].click();", edit_btn)
                            logger.info("✅ Clicked Edit Button")
                            time.sleep(1.5) # Wait for input focus
                            
                            # Target Active Element (Focus)
                            try:
                                title_input = self.driver.switch_to.active_element
                                # Clear existing
                                title_input.send_keys(Keys.CONTROL + "a")
                                title_input.send_keys(Keys.BACKSPACE)
                                # Type new
                                title_input.send_keys(song_title)
                                title_input.send_keys(Keys.RETURN)
                                renamed = True
                                logger.info(f"✅ Renamed to '{song_title}'")
                                time.sleep(2)
                            except Exception as focus_err:
                                logger.warning(f"Focus input failed: {focus_err}")

                        except Exception as e:
                             logger.warning(f"Full XPath strategy failed: {e}")
                        
                    except Exception as e:
                         logger.warning(f"Rename via Full XPath failed: {e}")
            
            except Exception as e:
                logger.warning(f"Rename flow error: {e}")

                # Step 5: Save (Optional if Enter key worked)
            logger.info("[STEP 5/9] Checking 'Save' button...")
            time.sleep(1)
            # Try to find Save button quickly
            try:
                save_btn = self.driver.find_elements(By.XPATH, "//button[contains(., 'Save')]")
                visible_save = [b for b in save_btn if b.is_displayed()]
                
                if visible_save:
                    logger.info("✅ Found 'Save' button. Clicking...")
                    self.driver.execute_script("arguments[0].click();", visible_save[0])
                    time.sleep(3)
                else:
                    logger.info("ℹ️ 'Save' button not found (Modal likely closed by Enter key).")
            except Exception as e:
                logger.warning(f"Save step skipped: {e}")

            # Step 6: Click Cover (CRITICAL for remix)
            logger.info("[STEP 6/9] Click 'Cover' mode...")
            cover_clicked = False
            
            # Strategy 1: Find by text "Cover" in section/modal
            try:
                cover_btns = self.driver.find_elements(By.XPATH, "//section//button[contains(., 'Cover')]")
                for btn in cover_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].style.border='3px solid purple'", btn)
                        self.driver.execute_script("arguments[0].click();", btn)
                        logger.info("✅ Clicked Cover Button (text search in section)")
                        cover_clicked = True
                        break
            except Exception as e:
                logger.warning(f"Cover text search failed: {e}")
            
            # Strategy 2: Find by aria-label or data attribute
            if not cover_clicked:
                try:
                    cover_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Cover') or contains(@data-testid, 'cover')]")
                    if cover_btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", cover_btn)
                        logger.info("✅ Clicked Cover Button (aria-label)")
                        cover_clicked = True
                except:
                    pass
            
            # Strategy 3: Original hardcoded XPath as last resort
            if not cover_clicked:
                try:
                    cover_xpath = "/html/body/div[9]/div[3]/div/section/div/div/div[1]/div[3]/button[1]"
                    cover_btn = self.driver.find_element(By.XPATH, cover_xpath)
                    self.driver.execute_script("arguments[0].click();", cover_btn)
                    logger.info("✅ Clicked Cover Button (hardcoded XPath)")
                    cover_clicked = True
                except:
                    pass
            
            if not cover_clicked:
                logger.warning("⚠️ Cover button not found - proceeding anyway")
            
            time.sleep(2)
            
            time.sleep(1)

            # Step 7: Click Continue
            logger.info("[STEP 7/9] Check 'Continue'...")
            continue_clicked = False
            
            # Strategy 1: Find by text "Continue" in section/modal
            try:
                cont_btns = self.driver.find_elements(By.XPATH, "//section//button[contains(., 'Continue')]")
                for btn in cont_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        logger.info("✅ Clicked Continue (text search in section)")
                        continue_clicked = True
                        break
            except:
                pass
            
            # Strategy 2: Generic text search
            if not continue_clicked:
                if self.wait_and_click_text(["Continue"], timeout=5):
                    logger.info("✅ Clicked Continue (generic text)")
                    continue_clicked = True
            
            # Strategy 3: Original hardcoded XPath
            if not continue_clicked:
                try:
                    continue_xpath = "/html/body/div[9]/div[3]/div/section/div/div/div[2]/button/span"
                    cont_btn = self.driver.find_element(By.XPATH, continue_xpath)
                    self.driver.execute_script("arguments[0].click();", cont_btn)
                    logger.info("✅ Clicked Continue (hardcoded XPath)")
                    continue_clicked = True
                except:
                    pass
            
            if not continue_clicked:
                logger.info("ℹ️ Continue button not found - may already be on next step")
            time.sleep(2)

            # Step 8: Wait for Success (CRITICAL) - NOW WAITING FOR COVER ELEMENT
            logger.info("[STEP 8/9] Waiting for 'Success' signal (Cover Appearance)...")
            try:
                # User provided specific XPath for the cover element
                ready_cover_xpath = "/html/body/div[1]/div[1]/div[2]/div[1]/div/div/div/div/div/div/div/div[3]/div/div[2]/div[3]/div[1]/div[2]/div[1]/div[1]/div[2]/button/span"
                logger.info(f"[SELECTOR] Waiting for visibility of: {ready_cover_xpath}")
                
                WebDriverWait(self.driver, 60).until(
                    EC.visibility_of_element_located((By.XPATH, ready_cover_xpath))
                )
                logger.info("✅ SUCCESS: Cover element appeared. Upload complete.")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Wait for cover signal timed out: {e}")

            # Step 9: Click Create (Final)
            logger.info("[STEP 9/9] Clicking Create Button...")
            self.handle_captcha() # Check one last time before creating
            
            try:
                # User provided specific XPath
                create_xpath = "/html/body/div[1]/div[1]/div[2]/div[1]/div/div/div/div/div/div/div/div[3]/div/div[3]/button[2]/span"
                try:
                    logger.info(f"[SELECTOR] Trying specific Create Button XPath: {create_xpath}")
                    create_btn = self.driver.find_element(By.XPATH, create_xpath)
                    
                    # Scroll to element to ensure visibility
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", create_btn)
                    time.sleep(2) 
                    
                    if self.safe_click(create_btn):
                        logger.info("✅ Clicked Create (User XPath)")
                    else:
                        raise Exception("Click failed")
                except Exception as xpath_error:
                    logger.warning(f"Create button user-XPath failed, trying text search... {xpath_error}")
                    if self.wait_and_click_text(["Create", "Generate"], timeout=15):
                        logger.info("✅ Clicked Create/Generate (Text Search)")
                    else:
                        raise Exception("Create button missing (Text Search Failed)")
            except Exception as e:
                raise Exception(f"Could not click Create final button: {e}")
            
            # CAPTCHA CHECK: Wait for CAPTCHA to appear after Create
            logger.info("[CAPTCHA CHECK] Waiting 3 seconds for potential CAPTCHA...")
            time.sleep(3)
            
            logger.info("[CAPTCHA CHECK] Detecting CAPTCHA...")
            self.handle_captcha()
            
            logger.info("✅ ALL STEPS COMPLETED via Selenium.")
            
            # Download will happen separately, no need to wait for generation
            return {
                "status": "success",
                "remix_file": None  # Will be retrieved by get_latest_songs
            }

        except Exception as e:
            logger.error(f"Remix generation failed: {str(e)}")
            return {"status": "error", "error": str(e)}

    def generate_song(self, prompt, style="", tags="", wait_for_generation=True, max_wait=180):
        """
        Generate a song on Suno

        Args:
            prompt (str): Song description/prompt
            style (str): Music style (optional)
            tags (str): Additional tags (optional)
            wait_for_generation (bool): Wait for generation to complete
            max_wait (int): Max wait time in seconds

        Returns:
            dict: Song info with ID and status
        """
        try:
            logger.info(f"Generating song: {prompt}")

            # Click "Create" or "+" button
            create_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Create')]"))
            )
            create_btn.click()
            time.sleep(2)

            # Fill in prompt
            prompt_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@placeholder='Describe the music you want to generate' or contains(@placeholder, 'Describe')]"))
            )
            prompt_input.clear()
            prompt_input.send_keys(prompt)

            # Fill style if provided
            if style:
                try:
                    style_dropdown = self.driver.find_element(By.XPATH, "//select[@name='style'] or //input[@placeholder='Style']")
                    style_dropdown.send_keys(style)
                except:
                    logger.warning(f"Could not set style: {style}")

            # Click Generate button
            generate_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Generate') or contains(., 'Create')]"))
            )
            generate_btn.click()

            logger.info(f"✅ Generation submitted: {prompt}")

            if wait_for_generation:
                logger.info(f"⏳ Waiting for generation to complete (max {max_wait}s)...")
                time.sleep(max_wait)

            return {
                "prompt": prompt,
                "status": "submitted",
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"Error generating song: {str(e)}")
            return {
                "prompt": prompt,
                "status": "error",
                "error": str(e)
            }

    def get_latest_songs(self, count=5):
        """
        Get latest generated songs from dashboard

        Args:
            count (int): Number of songs to retrieve

        Returns:
            list: List of song data
        """
        try:
            logger.info(f"Retrieving {count} latest songs...")

            songs = []
            
            # Strategy: Find song rows using data-testid='clip-row'
            # Verified by user as the reliable container
            rows = self.driver.find_elements(By.XPATH, "//div[@data-testid='clip-row']")
            
            # Limit to count
            rows = rows[:count]
            
            if not rows:
                logger.warning("[SELECTOR] No rows found with data-testid='clip-row'. Trying fallback class...")
                rows = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'clip-row')]")

            logger.info(f"[SELECTOR] Found {len(rows)} song rows.")
            
            for i, row in enumerate(rows):
                # Try to extract title for logging
                title = "Unknown Song"
                try:
                    title_el = row.find_element(By.XPATH, ".//a[contains(@href, '/song/')]")
                    title = title_el.text
                except:
                    pass
                    
                songs.append({
                    "title": title,
                    "audio_url": "", # Will be downloaded
                    "index": i,
                    "element": row, # Store the ROW element for right-clicking
                    "more_btn": None 
                })

            logger.info(f"✅ Retrieved {len(songs)} song rows")
            return songs

        except Exception as e:
            logger.error(f"Error retrieving songs: {str(e)}")
            return []

    def get_cookies_as_string(self):
        """
        Get cookies in string format for storage/API use
        Returns:
            str: "name=value; name2=value2"
        """
        try:
            cookies = self.driver.get_cookies()
            cookie_pairs = []
            for cookie in cookies:
                cookie_pairs.append(f"{cookie['name']}={cookie['value']}")
            return "; ".join(cookie_pairs)
        except Exception as e:
            logger.error(f"Error getting cookies: {str(e)}")
            return ""

    def download_song_files(self, song_element, output_dir):
        """
        Download MP3 and Video for a song element using Right-Click Context Menu
        UPDATED: Re-finds row element to avoid stale reference after waiting.
        """
        try:
            from selenium.webdriver import ActionChains
            
            song_index = song_element.get('index', 0)
            song_title = song_element.get('title', 'Unknown')
            logger.info(f"Processing download for: {song_title} (index: {song_index})")
            
            # RE-FIND ROW to avoid stale element (critical after long wait)
            current_rows = self.driver.find_elements(By.XPATH, "//div[@data-testid='clip-row']")
            if song_index >= len(current_rows):
                logger.error(f"❌ Row index {song_index} out of range (only {len(current_rows)} rows found)")
                return False
            
            row_element = current_rows[song_index]
            logger.info(f"Re-found row at index {song_index}")
            
            # 1. Scroll row into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row_element)
            time.sleep(1)
            
            # 2. Right Click on the Song Row
            actions = ActionChains(self.driver)
            actions.context_click(row_element).perform()
            time.sleep(1.0)

            # 3. Find "Download" and click
            try:
                download_menu = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
                )
                logger.info(f"Found Download: {download_menu.text}")
                download_menu.click()
                time.sleep(1.0)
            except Exception as e:
                logger.warning(f"Download menu item not found: {e}")
                try: self.driver.find_element(By.TAG_NAME, "body").click()
                except: pass
                return False
            
            # 4. STRATEGY: Find BOTH Audio and Video elements BEFORE clicking
            try:
                audio_opt = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'MP3 Audio')]"))
                )
                video_opt = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Video')]")
                
                logger.info(f"Found Audio: '{audio_opt.text}'")
                logger.info(f"Found Video: '{video_opt.text}'")
                
                # Click Audio first - WITH EXPLICIT TRY/EXCEPT
                try:
                    audio_opt.click()
                    logger.info("✅ Clicked Audio")
                except Exception as audio_err:
                    logger.error(f"❌ Audio click FAILED: {audio_err}")
                time.sleep(0.3)
                
                # Immediately click Video (before menu closes) - WITH EXPLICIT TRY/EXCEPT
                try:
                    video_opt.click()
                    logger.info("✅ Clicked Video")
                except Exception as video_err:
                    logger.warning(f"⚠️ Video click failed: {video_err}. Reopening menu...")
                    # Re-open menu
                    try: self.driver.find_element(By.TAG_NAME, "body").click()
                    except: pass
                    time.sleep(0.5)
                    
                    actions.context_click(row_element).perform()
                    time.sleep(1.0)
                    download_menu = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
                    )
                    download_menu.click()
                    time.sleep(1.0)
                    video_opt = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Video')]"))
                    )
                    video_opt.click()
                    logger.info("✅ Clicked Video (on retry)")
                
                # Brief wait for downloads to initiate
                logger.info("⏳ Waiting for downloads to start...")
                time.sleep(5)
                logger.info("✅ Download sequence completed")
                return True
                
            except Exception as e:
                logger.error(f"Audio/Video selection failed: {e}")
                import traceback
                traceback.print_exc()
                return False

        except Exception as e:
            logger.error(f"Download flow failed: {e}")
            return False

    # ==================== BATCH METHODS ====================
    
    def create_song_only(self, audio_path, title, prompt, log_callback=None, max_upload_retries=10):
        """
        Create a song on Suno WITHOUT waiting for completion.
        Used for batch creation - just clicks Create and returns immediately.
        
        Args:
            audio_path: Path to audio file
            title: Song title
            prompt: Prompt/style for remix
            log_callback: Optional function to call with log messages (for GUI)
            max_upload_retries: Max retries with different pitch/tempo if upload fails
        
        Returns:
            bool: True if Create was clicked successfully
        """
        import random
        
        def log(msg):
            """Log to both logger and callback"""
            logger.info(msg)
            if log_callback:
                log_callback(f"  {msg}\n")
        
        # Gradual pitch decrease per attempt (fine 0.1 semitone steps)
        # Negative pitch = lower tone, sounds more natural than raising
        pitch_steps = [-0.5, -0.6, -0.7, -0.8, -0.9, -1.0, -1.1, -1.2, -1.3, -1.4]
        tempo_steps = [1.02, 1.02, 1.03, 1.03, 1.04, 1.04, 1.05, 1.05, 1.06, 1.06]
        
        # Prepare modified audio file
        modified_audio_path = None
        current_audio = audio_path
        
        for attempt in range(max_upload_retries):
            try:
                if attempt > 0:
                    log(f"[RETRY {attempt+1}/{max_upload_retries}] Adjusting pitch/tempo more...")
                
                # Step 0: Modify pitch/tempo
                log(f"[STEP 0/8] Processing audio (pitch/tempo adjustment)...")
                try:
                    # Import audio processor
                    import sys
                    from pathlib import Path
                    scripts_dir = Path(__file__).parent / "scripts"
                    if str(scripts_dir) not in sys.path:
                        sys.path.insert(0, str(scripts_dir))
                    
                    try:
                        from scripts.modules.audio_processor import audio_processor
                    except:
                        # Fallback import
                        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
                        from modules.audio_processor import audio_processor
                    
                    # Gradual escalation: pick from steps based on attempt number
                    step_idx = min(attempt, len(pitch_steps) - 1)
                    pitch_shift = pitch_steps[step_idx]
                    tempo_mult = tempo_steps[step_idx]
                    
                    log(f"  Pitch: {pitch_shift:+.1f} semitones, Tempo: {tempo_mult:.2f}x")
                    
                    # Create output path in temp folder
                    temp_dir = os.path.join(os.path.dirname(audio_path), "..", "temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    base_name = os.path.splitext(os.path.basename(audio_path))[0]
                    modified_audio_path = os.path.join(temp_dir, f"{base_name}_p{pitch_shift}_t{int(tempo_mult*100)}.wav")
                    
                    # Modify audio
                    current_audio = audio_processor.modify_pitch_tempo(
                        audio_path, 
                        pitch_shift=pitch_shift, 
                        tempo_multiplier=tempo_mult,
                        output_path=modified_audio_path
                    )
                    log(f"✅ Audio processed: {os.path.basename(current_audio)}")
                    
                except Exception as e:
                    log(f"⚠️ Audio processing failed: {str(e)[:50]}, using original")
                    current_audio = audio_path
                
                log(f"[BATCH] Creating song: {title}")
                
                # Step 1: Navigate to Create (clear old toasts by going to blank first on retry)
                log("[STEP 1/8] Navigating to Create page...")
                if attempt > 0:
                    # Clear cached violation toasts by navigating away first
                    log("  🔄 Clearing cached page data...")
                    self.driver.get("about:blank")
                    time.sleep(1)
                self.driver.get("https://suno.com/create")
                self.handle_captcha()
                time.sleep(3)
                log("✅ On Create page")
                
                # Step 2: Enter Prompt
                log("[STEP 2/8] Entering Prompt...")
                try:
                    prompt_xpath = '//*[@id="main-container"]/div/div/div/div/div/div[3]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div[1]/div/textarea'
                    prompt_area = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, prompt_xpath))
                    )
                    prompt_area.clear()
                    prompt_area.send_keys(prompt if prompt else "Cover of uploaded song")
                    log("✅ Entered prompt")
                except Exception as e:
                    log(f"⚠️ Prompt entry issue: {str(e)[:50]}")
                    # Try fallback
                    try:
                        fallback_xpath = "//textarea[contains(@class, 'resize-none')]"
                        prompt_area = self.driver.find_element(By.XPATH, fallback_xpath)
                        prompt_area.send_keys(prompt if prompt else "Cover")
                        log("✅ Entered prompt (fallback)")
                    except:
                        log("⚠️ Prompt fallback also failed")
                time.sleep(2)

                # Step 3: Send File to Input
                log("[STEP 3/8] Sending File to Input...")
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    file_input.send_keys(os.path.abspath(current_audio))
                    log(f"✅ File sent: {os.path.basename(current_audio)}")
                    time.sleep(5)
                    
                    # Check for Suno violation/copyright toast
                    # IMPORTANT: Only match EXACT violation text, not generic toasts
                    violation_detected = False
                    violation_keywords = [
                        'upload a different audio file',
                        'copyrighted lyrics',
                        'copyrighted',
                        'contains copyrighted',
                    ]
                    
                    # Check all visible text elements for violation keywords
                    try:
                        # Check toast area specifically
                        toast_elements = self.driver.find_elements(By.XPATH, "//*[@id='chakra-toast-manager-bottom']//*")
                        for el in toast_elements:
                            try:
                                if el.is_displayed() and el.text.strip():
                                    el_text = el.text.strip().lower()
                                    for keyword in violation_keywords:
                                        if keyword in el_text:
                                            log(f"⚠️ SUNO VIOLATION DETECTED: {el.text[:80]}")
                                            log(f"   → Will retry with different pitch/tempo from scratch")
                                            violation_detected = True
                                            break
                                    if violation_detected:
                                        break
                            except:
                                pass
                    except:
                        pass
                    
                    # Also check for copyrighted message outside toast
                    if not violation_detected:
                        try:
                            h3_elements = self.driver.find_elements(By.TAG_NAME, "h3")
                            for el in h3_elements:
                                try:
                                    if el.is_displayed() and el.text.strip():
                                        el_text = el.text.strip().lower()
                                        for keyword in violation_keywords:
                                            if keyword in el_text:
                                                log(f"⚠️ SUNO VIOLATION (h3): {el.text[:80]}")
                                                violation_detected = True
                                                break
                                        if violation_detected:
                                            break
                                except:
                                    pass
                        except:
                            pass
                    
                    if violation_detected:
                        raise Exception("Suno violation detected, will retry with different pitch/tempo")
                    
                    # Check for other upload errors
                    error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error') or contains(text(), 'failed')]")
                    if error_elements:
                        for el in error_elements:
                            if el.is_displayed():
                                error_text = el.text[:80]
                                log(f"⚠️ Upload error detected: {error_text}")
                                raise Exception(f"Upload error: {error_text}")
                    
                except Exception as e:
                    error_msg = str(e)
                    log(f"❌ Upload issue: {error_msg[:80]}")
                    if attempt < max_upload_retries - 1:
                        log(f"   → Retrying with higher pitch/tempo (attempt {attempt + 2}/{max_upload_retries})...")
                        log(f"   → Restarting entire process from scratch...")
                        time.sleep(2)
                        continue  # Retry from scratch (loop restarts from Step 0)
                    return False

                # Step 4: Agree to Terms (if present)
                log("[STEP 4/8] Check 'Agree to Terms'...")
                if self.wait_and_click_text(["Agree to Terms", "Agree", "I Agree"], timeout=3):
                    log("✅ Accepted Terms.")
                else:
                    log("ℹ️ Terms not found (may already be accepted)")
                time.sleep(1)

                # Step 5: Rename Song
                log("[STEP 5/8] Renaming song...")
                renamed = False
                
                # Strategy 1: Find edit button by SVG icon (pencil) in section
                try:
                    edit_btns = self.driver.find_elements(By.XPATH, "//section//button[.//svg]")
                    for btn in edit_btns:
                        try:
                            # Look for small button that might be edit icon
                            if btn.is_displayed() and btn.size['width'] < 50:
                                self.driver.execute_script("arguments[0].click();", btn)
                                time.sleep(1)
                                
                                title_input = self.driver.switch_to.active_element
                                title_input.send_keys(Keys.CONTROL + "a")
                                title_input.send_keys(Keys.BACKSPACE)
                                title_input.send_keys(title)
                                title_input.send_keys(Keys.RETURN)
                                log(f"✅ Renamed to '{title}' (SVG button)")
                                renamed = True
                                break
                        except:
                            continue
                except:
                    pass
                
                # Strategy 2: Hardcoded XPath (try multiple div indices)
                if not renamed:
                    for div_idx in [9, 8, 10, 7, 11]:
                        try:
                            edit_xpath = f"/html/body/div[{div_idx}]/div[3]/div/section/div/div[2]/div[1]/div/button"
                            edit_btn = self.driver.find_element(By.XPATH, edit_xpath)
                            if edit_btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", edit_btn)
                                time.sleep(1.5)
                                
                                title_input = self.driver.switch_to.active_element
                                title_input.send_keys(Keys.CONTROL + "a")
                                title_input.send_keys(Keys.BACKSPACE)
                                title_input.send_keys(title)
                                title_input.send_keys(Keys.RETURN)
                                log(f"✅ Renamed to '{title}' (div[{div_idx}])")
                                renamed = True
                                time.sleep(2)
                                break
                        except:
                            continue
                
                if not renamed:
                    log("⚠️ Could not rename song (will use default name)")

                # Step 5.5: Click Save button after rename
                log("[STEP 5.5/8] Clicking 'Save' button...")
                save_clicked = False
                
                # Strategy 1: chakra-modal Save button (from user's xpath)
                try:
                    # The modal ID changes (rc9, rc10, etc), so we use contains
                    save_btns = self.driver.find_elements(By.XPATH, "//*[contains(@id, 'chakra-modal')]//button[contains(., 'Save')]")
                    for btn in save_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            log("✅ Clicked Save (chakra-modal)")
                            save_clicked = True
                            break
                except:
                    pass
                
                # Strategy 2: Generic Save button search
                if not save_clicked:
                    try:
                        save_btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Save')]")
                        for btn in save_btns:
                            if btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", btn)
                                log("✅ Clicked Save (generic)")
                                save_clicked = True
                                break
                    except:
                        pass
                
                # Strategy 3: section Save button
                if not save_clicked:
                    try:
                        save_btn = self.driver.find_element(By.XPATH, "//section//button[contains(., 'Save')]")
                        if save_btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", save_btn)
                            log("✅ Clicked Save (section)")
                            save_clicked = True
                    except:
                        pass
                
                if not save_clicked:
                    log("ℹ️ Save button not found (may not be needed)")
                time.sleep(2)

                # Step 6: Click Cover
                log("[STEP 6/8] Click 'Cover' mode...")
                cover_clicked = False
                
                # Strategy 1: Find by text in section
                try:
                    cover_btns = self.driver.find_elements(By.XPATH, "//section//button[contains(., 'Cover')]")
                    for btn in cover_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            log("✅ Clicked Cover (text search)")
                            cover_clicked = True
                            break
                except:
                    pass
                
                # Strategy 2: Aria-label
                if not cover_clicked:
                    try:
                        cover_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Cover') or contains(@data-testid, 'cover')]")
                        self.driver.execute_script("arguments[0].click();", cover_btn)
                        log("✅ Clicked Cover (aria-label)")
                        cover_clicked = True
                    except:
                        pass
                
                # Strategy 3: Hardcoded XPath
                if not cover_clicked:
                    try:
                        cover_xpath = "/html/body/div[9]/div[3]/div/section/div/div/div[1]/div[3]/button[1]"
                        cover_btn = self.driver.find_element(By.XPATH, cover_xpath)
                        self.driver.execute_script("arguments[0].click();", cover_btn)
                        log("✅ Clicked Cover (hardcoded)")
                        cover_clicked = True
                    except:
                        pass
                
                if not cover_clicked:
                    log("⚠️ Cover button not found")
                time.sleep(2)

                # Step 7: Click Continue
                log("[STEP 7/8] Click 'Continue'...")
                continue_clicked = False
                
                # Strategy 1: Find by text in section
                try:
                    cont_btns = self.driver.find_elements(By.XPATH, "//section//button[contains(., 'Continue')]")
                    for btn in cont_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            log("✅ Clicked Continue (text search)")
                            continue_clicked = True
                            break
                except:
                    pass
                
                # Strategy 2: Generic text search
                if not continue_clicked:
                    if self.wait_and_click_text(["Continue"], timeout=5):
                        log("✅ Clicked Continue (generic)")
                        continue_clicked = True
                
                # Strategy 3: Hardcoded XPath
                if not continue_clicked:
                    try:
                        continue_xpath = "/html/body/div[9]/div[3]/div/section/div/div/div[2]/button/span"
                        cont_btn = self.driver.find_element(By.XPATH, continue_xpath)
                        self.driver.execute_script("arguments[0].click();", cont_btn)
                        log("✅ Clicked Continue (hardcoded)")
                        continue_clicked = True
                    except:
                        pass
                
                if not continue_clicked:
                    log("ℹ️ Continue not found - may already be on next step")
                time.sleep(2)

                # Wait for upload success signal (canvas element appears)
                log("[WAIT] Waiting for upload success (max 3 min)...")
                upload_success = False
                
                # Success signal: canvas element appears (waveform visualization)
                success_xpath = '//*[@id="main-container"]/div/div/div/div/div/div[3]/div/div[2]/div[3]/div[1]/div[2]/div[1]/div[2]/div/div/div[1]/canvas'
                
                violation_during_upload = False
                for wait_attempt in range(36):  # 36 x 5s = 180s = 3 minutes
                    try:
                        # Check for violation toast DURING upload wait (text-based only)
                        # Only match specific violation keywords, not any random toast
                        violation_kw = ['upload a different audio file', 'copyrighted lyrics', 'copyrighted']
                        try:
                            toast_els = self.driver.find_elements(By.XPATH, "//*[@id='chakra-toast-manager-bottom']//*")
                            for vel in toast_els:
                                try:
                                    if vel.is_displayed() and vel.text.strip():
                                        vel_text = vel.text.strip().lower()
                                        for kw in violation_kw:
                                            if kw in vel_text:
                                                log(f"⚠️ VIOLATION during upload: {vel.text[:80]}")
                                                violation_during_upload = True
                                                break
                                        if violation_during_upload:
                                            break
                                except:
                                    pass
                        except:
                            pass
                        
                        if violation_during_upload:
                            break
                        
                        # Check for canvas element (upload success indicator - waveform visualization)
                        # This is the DEFINITIVE success signal
                        canvas_elements = self.driver.find_elements(By.XPATH, success_xpath)
                        if canvas_elements and any(el.is_displayed() for el in canvas_elements):
                            log("✅ Upload success! Canvas/waveform appeared")
                            upload_success = True
                            break
                            
                        if wait_attempt % 6 == 0:  # Log every 30s
                            log(f"  ⏳ Still uploading... ({(wait_attempt+1)*5}s)")
                        
                        time.sleep(5)
                        
                    except Exception as e:
                        time.sleep(5)
                
                # If violation detected during upload, retry immediately
                if violation_during_upload:
                    if attempt < max_upload_retries - 1:
                        log(f"   → Retrying with higher pitch/tempo (attempt {attempt + 2}/{max_upload_retries})...")
                        continue  # Restart from Step 0 with higher pitch/tempo
                    else:
                        log(f"❌ All {max_upload_retries} attempts had violations")
                        return False
                
                if not upload_success:
                    log("⚠️ Upload signal timeout - proceeding anyway")
                time.sleep(2)

                # Click Create
                log("[FINAL] Clicking Create Button...")
                try:
                    create_xpath = "/html/body/div[1]/div[1]/div[2]/div[1]/div/div/div/div/div/div/div/div[3]/div/div[3]/button[2]/span"
                    create_btn = self.driver.find_element(By.XPATH, create_xpath)
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", create_btn)
                    time.sleep(1)
                    self.safe_click(create_btn)
                    log("✅ Clicked Create - Song submitted!")
                except Exception as e:
                    # Fallback to text search
                    if self.wait_and_click_text(["Create", "Generate"], timeout=10):
                        log("✅ Clicked Create (fallback)")
                    else:
                        log(f"❌ Create button failed: {str(e)[:50]}")
                        return False

                time.sleep(3)  # Brief pause before next song
                log("🎵 Song creation complete!")
                return True  # Success, exit retry loop

            except Exception as e:
                log(f"❌ Error in attempt: {str(e)[:50]}")
                if attempt < max_upload_retries - 1:
                    continue
                return False

        # If we get here, all retries failed
        log(f"❌ All {max_upload_retries} attempts failed")
        return False

    def batch_download(self, num_songs, log_callback=None, stop_check_callback=None):
        """
        Download cover songs from Suno dashboard.
        Each input creates 2 cover outputs. Each output = 1 MP3 + 1 Video.
        Total files = num_songs * 2 outputs * 2 files = num_songs * 4
        
        Args:
            num_songs: Number of input songs uploaded
            log_callback: Optional function for GUI logging
            stop_check_callback: Optional function that returns True if process should stop
        
        Returns:
            int: Number of successful song downloads (each song = mp3 + video)
        """
        from selenium.webdriver import ActionChains
        
        def log(msg):
            logger.info(msg)
            if log_callback:
                log_callback(f"  {msg}\n")
        
        total_outputs = num_songs * 2  # Each input creates 2 cover outputs
        log(f"[DOWNLOAD] Starting download of {total_outputs} cover songs...")
        log(f"  Expected files: {total_outputs} MP3 + {total_outputs} Video = {total_outputs * 2} total")
        
        # Step 1: Navigate to create page
        if stop_check_callback and stop_check_callback(): return 0
        log("[STEP 1] Navigating to Suno Create page...")
        self.driver.get("https://suno.com/create")
        time.sleep(5)
        
        # Step 2: Click Filter button
        if stop_check_callback and stop_check_callback(): return 0
        log("[STEP 2] Clicking Filter button...")
        filter_clicked = False
        
        # Strategy 1: Robust XPath search
        try:
            log("  [DEBUG] Searching for Filter button with robust XPaths...")
            
            # Expanded xpath list - Added USER provided paths first
            filter_xpaths = [
                # User provided specific XPath (Filter)
                "//*[@id='main-container']/div/div/div/div/div/div[5]/div/div/div[2]/div[2]/button",
                "//*[@id='main-container']/div/div/div/div/div/div[5]/div/div/div[2]/div[2]/button/span",
                
                # General robust paths
                "//button[contains(., 'Filters')]",
                "//button[contains(., 'Filter')]",
                "//div[@role='button'][contains(., 'Filters')]",
                "//div[@role='button'][contains(., 'Filter')]",
                "//*[text()[contains(.,'Filters')]]/ancestor::button",  # Find text node and get parent button
                "//*[text()[contains(.,'Filter')]]/ancestor::button",
                "//span[contains(@class, 'relative') and contains(@class, 'flex-row') and contains(., 'Filters')]",
                "//span[contains(., 'Filters')]",
                "//span[contains(., 'Filter')]"
            ]
            
            for xpath in filter_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            log(f"    Found candidate: '{el.text}' (Tag: {el.tag_name})")
                            # Highlight
                            self.driver.execute_script("arguments[0].style.border='3px solid red';", el)
                            time.sleep(1.0) # Wait a bit for user to see
                            
                            # Click Strategy: Try multiple ways to ensure it clicks
                            filter_clicked_success = False
                            
                            # 1. ActionChains (Real Mouse Click) - REQUESTED BY USER
                            try:
                                log("    Attempting ActionChains (Real Mouse) click...")
                                actions = ActionChains(self.driver)
                                actions.move_to_element(el).click().perform()
                                log("    ✅ ActionChains click performed")
                                filter_clicked_success = True
                                time.sleep(1) # Wait for reaction
                            except Exception as ac_err:
                                log(f"    ⚠️ ActionChains click failed: {ac_err}")

                            # 2. JS Click (Fallback)
                            if not filter_clicked_success:
                                try:
                                    log("    Attempting JS click...")
                                    if el.tag_name == "span" or el.tag_name == "svg":
                                        try:
                                            parent_btn = el.find_element(By.XPATH, "./ancestor::button")
                                            self.driver.execute_script("arguments[0].click();", parent_btn)
                                            log("    ✅ Clicked parent button (JS)")
                                        except:
                                            self.driver.execute_script("arguments[0].click();", el)
                                            log("    ✅ Clicked span/element directly (JS)")
                                    else:
                                        self.driver.execute_script("arguments[0].click();", el)
                                        log("    ✅ Clicked element directly (JS)")
                                        
                                    filter_clicked_success = True
                                except Exception as click_err:
                                    log(f"    ❌ JS Click failed: {click_err}")
                            
                            if filter_clicked_success:
                                filter_clicked = True
                                break
                    
                    if filter_clicked:
                        break
                except Exception as e:
                    pass
        except Exception as e:
            log(f"⚠️ Filter search error: {str(e)[:50]}")
        
        # Debug if still failed
        if not filter_clicked:
            log("⚠️ Filter button still not found. Dumping visible buttons:")
            try:
                btns = self.driver.find_elements(By.TAG_NAME, "button")
                visible_btns = [b for b in btns if b.is_displayed()]
                log(f"  Found {len(visible_btns)} visible buttons:")
                for b in visible_btns[:10]:
                    log(f"    - '{b.text}'")
            except:
                pass
                
        # Strategy 2: Original xpath fallback is now largely redundant but kept for safety

        if not filter_clicked:
            try:
                filter_xpath = '//*[@id="main-container"]//button//span[contains(., "Filter")]'
                filter_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, filter_xpath))
                )
                self.driver.execute_script("arguments[0].click();", filter_btn)
                log("✅ Clicked Filter (fallback xpath)")
                filter_clicked = True
            except:
                pass
        
        if not filter_clicked:
            log("⚠️ Filter button not found - will try to download all visible")
        
        time.sleep(3) # Increase wait time for menu to open
        
        # Step 3: Select "Covers" filter
        if stop_check_callback and stop_check_callback(): return 0
        log("[STEP 3] Selecting 'Covers' filter (User Specific Path)...")
        cover_clicked = False
        
        # USER PROVIDED SPECIFIC PATHS FOR COVER - EXCLUSIVE STRATEGY
        try:
            user_cover_xpaths = [
                "/html/body/div[9]/div/div[7]/button/span/div/div/span[2]", # User provided (NEW - 2026-02-09)
                "/html/body/div[8]/div/div[7]/button/span/div/div/span[1]/svg", # User provided icon (Old)
                "/html/body/div[8]/div/div[7]/button/span/div/div/span[2]", # User provided text (Old)
                "//div[@role='dialog']//button[.//span[text()='Cover'] or .//span[text()='Covers']]", # Specific dialog button
                "//div[@role='menu']//button[.//span[text()='Cover'] or .//span[text()='Covers']]" # Specific menu button
            ]
            
            for xpath in user_cover_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        log(f"  [DEBUG] Found candidate with specific path: {xpath}")
                        
                    for el in elements:
                        if el.is_displayed():
                            # Highlight
                            self.driver.execute_script("arguments[0].style.border='3px solid red';", el)
                            time.sleep(0.5)
                            
                            try:
                                # Try clicking parent button first if it's a span/div/svg
                                try:
                                    parent_btn = el.find_element(By.XPATH, "./ancestor::button")
                                    # ActionChains click for parent
                                    ActionChains(self.driver).move_to_element(parent_btn).click().perform()
                                    log(f"✅ Selected Covers filter (ActionChains > Parent)")
                                except:
                                    # ActionChains click for element
                                    ActionChains(self.driver).move_to_element(el).click().perform()
                                    log(f"✅ Selected Covers filter (ActionChains > Direct)")
                                
                                cover_clicked = True
                                break
                            except Exception as e:
                                log(f"    Click specific failed: {e}")
                                # Fallback to JS
                                try:
                                    self.driver.execute_script("arguments[0].click();", el)
                                    log("    ✅ Selected Covers filter (JS Fallback)")
                                    cover_clicked = True
                                    break
                                except:
                                    pass
                    if cover_clicked: break
                except:
                    pass
        except Exception as e:
            log(f"  [DEBUG] User strategy failed: {e}")
            
        if not cover_clicked:
            log("⚠️ Specific Covers filter button not found. Proceeding anyway.")
            
        time.sleep(2)
        
        # Step 3.5: Click Filter button AGAIN to close menu (Requested by User)
        if stop_check_callback and stop_check_callback(): return 0
        log("[STEP 3.5] Clicking Filter button again to close menu...")
        
        try:
             # Reuse robust search strategies to find Filter button again
            filter_btn_found = False
            # Same list as Step 2, focusing on the main Filter button
            for xpath in filter_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            log(f"  Found Filter button to close: '{el.text}'")
                            # ActionChains Click (Real Mouse)
                            try:
                                ActionChains(self.driver).move_to_element(el).click().perform()
                                log("  ✅ Clicked Filter button again (ActionChains)")
                                filter_btn_found = True
                            except:
                                self.driver.execute_script("arguments[0].click();", el)
                                log("  ✅ Clicked Filter button again (JS fallback)")
                                filter_btn_found = True
                            break
                    if filter_btn_found: break
                except:
                    pass
        except Exception as e:
            log(f"⚠️ Failed to click Filter button again: {e}")
            
        time.sleep(2) # Wait for menu to close
        
        # Step 4: Download each song
        
        time.sleep(3)
        
        # Step 4: Download each song
        if stop_check_callback and stop_check_callback(): return 0
        log(f"[STEP 4] Downloading {total_outputs} songs...")
        successful = 0
        actions = ActionChains(self.driver)
        
        for i in range(total_outputs):
            if stop_check_callback and stop_check_callback(): 
                log("⚠️ Process stopped by user")
                break
                
            try:
                log(f"  [{i+1}/{total_outputs}] Processing song...")
                
                # Re-find rows each time to avoid stale elements
                rows = self.driver.find_elements(By.XPATH, "//div[@data-testid='clip-row']")
                if i >= len(rows):
                    log(f"⚠️ Only {len(rows)} rows found, stopping at {i}")
                    break
                
                row = rows[i]
                
                # Scroll into view
                log(f"    [Step 4.1] Scrolling to row {i+1}...")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                self.driver.execute_script("arguments[0].style.border='3px solid magenta';", row) # VISUAL DEBUG
                time.sleep(1.5) # Slow down
                
                # Right-click
                log(f"    [Step 4.2] Right-clicking row {i+1}...")
                ActionChains(self.driver).context_click(row).perform()
                time.sleep(1.5)
                
                # Click Download menu
                log(f"    [Step 4.3] Waiting for 'Download' option...")
                
                # Try NEW user-provided XPath first (2026-02-09)
                download_menu = None
                try:
                    download_menu = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "/html/body/div[9]/div/div/div[3]/div[2]/div/button/span/span[1]"))
                    )
                    log("    Found Download with NEW XPath")
                except:
                    # Fallback to old selector
                    download_menu = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
                    )
                    log("    Found Download with fallback XPath")
                self.driver.execute_script("arguments[0].style.border='3px solid red';", download_menu) # VISUAL DEBUG
                time.sleep(1.0)
                
                log(f"    [Step 4.4] Clicking 'Download' option...")
                download_menu.click()
                time.sleep(1.5)
                
                # Find Audio and Video options
                log(f"    [Step 4.5] Waiting for 'MP3 Audio' option...")
                audio_opt = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'MP3 Audio')]"))
                )
                self.driver.execute_script("arguments[0].style.border='3px solid red';", audio_opt) # VISUAL DEBUG
                time.sleep(1.0)
                
                # Click Audio
                log(f"    [Step 4.6] Clicking 'MP3 Audio'...")
                audio_opt.click()
                log(f"    ✅ Downloaded MP3")
                time.sleep(1.0)
                
                # Close menu and reopen for video
                # USER REQUEST: Remove 4.7a (Clicking body) as it might be interfering.
                # Instead, immediately repeat Step 4.1 (Find row -> Scroll -> Right Click)
                
                log(f"    [Step 4.7] Preparing for Video download (Repeating Row Search)...")
                time.sleep(1.5)
                
                # RE-FIND ROW to avoid StaleElementReferenceException
                log(f"    [Step 4.7] Preparing for Video download (Repeating Row Search)...")
                
                video_downloaded = False
                retry_count = 0
                
                while not video_downloaded:
                    if stop_check_callback and stop_check_callback(): 
                        log("⚠️ Process stopped by user during video wait")
                        break
                        
                    retry_count += 1
                    if retry_count > 1:
                        log(f"    ⏳ Video not ready yet? Retrying attempt {retry_count} (Waiting 10s)...")
                        # User requested NO TIMEOUT, so we wait indefinitely until it appears
                        
                    # 1. Scroll & Find Row
                    rows = self.driver.find_elements(By.XPATH, "//div[@data-testid='clip-row']")
                    if i < len(rows):
                        row = rows[i]
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                        time.sleep(1.0)
                        
                        # 2. Right Click
                        log(f"    [Step 4.7d] Opening context menu for Video (Attempt {retry_count})...")
                        ActionChains(self.driver).context_click(row).perform()
                        time.sleep(1.5)
                        
                        # 3. Click Download Option (USE SAME NEW XPATH AS MP3!)
                        try:
                            # Try NEW XPath first (same as MP3 download)
                            download_menu = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "/html/body/div[9]/div/div/div[3]/div[2]/div/button/span/span[1]"))
                            )
                            log("    Found Download with NEW XPath (video)")
                        except:
                            # Fallback to old selector
                            download_menu = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
                            )
                            log("    Found Download with fallback XPath (video)")
                        
                        download_menu.click()
                        time.sleep(1.5)
                        
                        # 4. Check & Click Video Option
                        try:
                            video_opt = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Video')]"))
                            )
                            self.driver.execute_script("arguments[0].style.border='3px solid red';", video_opt)
                            time.sleep(1.0)
                            
                            # Use JS Click to avoid "Element click intercepted" (e.g. by Toast or other overlays)
                            log(f"    [Step 4.10] Clicking 'Video' (via JS force)...")
                            
                            # MONITOR DOWNLOAD DIRECTORY
                            download_dir = os.path.abspath("output/music")
                            if not os.path.exists(download_dir):
                                os.makedirs(download_dir)
                                
                            existing_files = set(os.listdir(download_dir))
                            
                            self.driver.execute_script("arguments[0].click();", video_opt)
                            
                            log(f"    ⏳ Waiting for Video file to appear in {download_dir}...")
                            # Wait for download to start and finish
                            video_downloaded_file = None
                            wait_start = time.time()
                            
                            while True:
                                if stop_check_callback and stop_check_callback():
                                    log("⚠️ Process stopped by user during download wait")
                                    return 0
                                
                                current_files = set(os.listdir(download_dir))
                                new_files = current_files - existing_files
                                
                                # Check for any new MP4 file
                                potential_videos = [f for f in new_files if f.endswith('.mp4')]
                                
                                if potential_videos:
                                    # Check if it's still downloading (crdownload usually, or .part)
                                    # But usually new_files contains the final name or the temp name.
                                    # If chrome uses .crdownload, it will be in new_files too if we didn't filter extension.
                                    
                                    # Let's check if there are ANY .crdownload or .tmp files corresponding to this?
                                    # Actually, simplifies: wait until we see an .mp4 and NO corresponding .crdownload
                                    
                                    is_downloading = any(f.endswith('.crdownload') or f.endswith('.tmp') for f in new_files)
                                    
                                    if not is_downloading:
                                        # Verify file size > 0
                                        valid_video = False
                                        for vid in potential_videos:
                                                try:
                                                    if os.path.getsize(os.path.join(download_dir, vid)) > 0:
                                                        valid_video = True
                                                        video_downloaded_file = vid
                                                        break
                                                except: pass
                                        
                                        if valid_video:
                                            log(f"    ✅ Downloaded Video File: {video_downloaded_file}")
                                            video_downloaded = True
                                            break
                                    
                                    # Check for "Generating" state via UI if file not found yet?
                                    # User wanted NO TIMEOUT, just wait.
                                    # But check if stop requested.
                                    time.sleep(1.0)
                                    # Log every 10 seconds
                                    if time.time() - wait_start > 10 and int(time.time() - wait_start) % 10 == 0:
                                         log(f"    ... Still waiting for video file ({int(time.time() - wait_start)}s)...")

                        except TimeoutException:
                                log("    ⚠️ 'Video' option not found/clickable in menu (Generation likely in progress)")
                                # Close menu to reset
                                try:
                                    self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.TAG_NAME, "body"))
                                except: pass
                                time.sleep(10) # Wait 10s before retry as requested
                                continue
                                
                        except Exception as e:
                            log(f"    ⚠️ Error clicking Download menu: {e}")
                            try:
                                self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.TAG_NAME, "body"))
                            except: pass
                            time.sleep(5)
                            continue
                    else:
                        log(f"    ❌ Row {i+1} not found during video retry loop!")
                        break
                
                time.sleep(5.0) # Longer wait between songs for safety
                successful += 1
                log(f"  ✅ Song {i+1} complete (MP3 + Video)")
                
            except Exception as e:
                log(f"  ❌ Song {i+1} failed: {str(e)[:50]}")
                # Try to close any open menus
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except: pass
                time.sleep(1)
        
        log(f"\n[DOWNLOAD COMPLETE] {successful}/{total_outputs} songs downloaded")
        log(f"  Files: {successful} MP3 + {successful} Video = {successful * 2} total")
        return successful

    def close(self):
        """Close browser"""
        logger.info("Closing browser...")
        try:
             self.driver.quit()
        except:
             pass

