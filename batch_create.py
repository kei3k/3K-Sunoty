"""
Batch create module for Suno - to be imported by selenium_suno.py
Contains the create_song_only function with audio processing
"""

import os
import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)


def create_song_only(self, audio_path, title, prompt, log_callback=None, max_upload_retries=10):
    """
    Create a song on Suno WITHOUT waiting for completion.
    Includes pitch/tempo adjustment to avoid upload errors.
    
    Args:
        audio_path: Path to audio file
        title: Song title  
        prompt: Prompt/style for remix
        log_callback: Optional function for GUI logging
        max_upload_retries: Max retries with different pitch/tempo
    
    Returns:
        bool: True if Create was clicked successfully
    """
    
    def log(msg):
        """Log to both logger and callback"""
        logger.info(msg)
        if log_callback:
            log_callback(f"  {msg}\n")
    
    # Gradual pitch decrease per attempt (fine 0.1 semitone steps)
    # Negative pitch = lower tone, sounds more natural than raising
    pitch_steps = [-0.5, -0.6, -0.7, -0.8, -0.9, -1.0, -1.1, -1.2, -1.3, -1.4]
    tempo_steps = [1.02, 1.02, 1.03, 1.03, 1.04, 1.04, 1.05, 1.05, 1.06, 1.06]
    
    for attempt in range(max_upload_retries):
        try:
            if attempt > 0:
                log(f"[RETRY {attempt+1}/{max_upload_retries}] Adjusting pitch/tempo more...")
            
            # Step 0: Modify pitch/tempo
            log(f"[STEP 0/8] Processing audio (pitch/tempo adjustment)...")
            current_audio = audio_path
            
            try:
                # Import audio processor
                import sys
                from pathlib import Path
                scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                
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
                
                # Check toast area for violation keywords
                try:
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
                
                # Also check h3 elements for copyrighted message
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
                    raise Exception("Suno violation detected")
                
                # Check for other upload errors
                error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error')]")
                for el in error_elements:
                    if el.is_displayed() and len(el.text) < 100:
                        log(f"⚠️ Upload error detected: {el.text[:50]}")
                        raise Exception("Upload error detected")
                        
            except Exception as e:
                log(f"❌ Upload issue: {str(e)[:80]}")
                if attempt < max_upload_retries - 1:
                    log(f"   → Retrying with higher pitch/tempo (attempt {attempt + 2}/{max_upload_retries})...")
                    log(f"   → Restarting entire process from scratch...")
                    time.sleep(2)
                    continue  # Retry from scratch
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
            
            # Strategy 1: Find edit button by SVG icon in section
            try:
                edit_btns = self.driver.find_elements(By.XPATH, "//section//button[.//svg]")
                for btn in edit_btns:
                    try:
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
            
            # Strategy 1: chakra-modal Save button
            try:
                save_btns = self.driver.find_elements(By.XPATH, "//*[contains(@id, 'chakra-modal')]//button[contains(., 'Save')]")
                for btn in save_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        log("✅ Clicked Save (chakra-modal)")
                        save_clicked = True
                        break
            except:
                pass
            
            # Strategy 2: Generic Save button
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
                    cover_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Cover')]")
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

            # Wait for upload indicator
            log("[WAIT] Waiting for upload to complete (max 60s)...")
            try:
                ready_cover_xpath = "/html/body/div[1]/div[1]/div[2]/div[1]/div/div/div/div/div/div/div/div[3]/div/div[2]/div[3]/div[1]/div[2]/div[1]/div[1]/div[2]/button/span"
                WebDriverWait(self.driver, 60).until(
                    EC.visibility_of_element_located((By.XPATH, ready_cover_xpath))
                )
                log("✅ Upload complete signal received")
            except:
                log("⚠️ Upload signal timeout - proceeding anyway")

            # Step 8: Click Create
            log("[STEP 8/8] Clicking Create Button...")
            try:
                create_xpath = "/html/body/div[1]/div[1]/div[2]/div[1]/div/div/div/div/div/div/div/div[3]/div/div[3]/button[2]/span"
                create_btn = self.driver.find_element(By.XPATH, create_xpath)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", create_btn)
                time.sleep(1)
                self.safe_click(create_btn)
                log("✅ Clicked Create - Song submitted!")
            except Exception as e:
                if self.wait_and_click_text(["Create", "Generate"], timeout=10):
                    log("✅ Clicked Create (fallback)")
                else:
                    log(f"❌ Create button failed: {str(e)[:50]}")
                    if attempt < max_upload_retries - 1:
                        continue
                    return False

            # CAPTCHA CHECK: Wait for CAPTCHA to appear (if it will)
            log("[CAPTCHA CHECK] Waiting 3 seconds for potential CAPTCHA...")
            time.sleep(3)
            
            # Check for CAPTCHA and handle it
            log("[CAPTCHA CHECK] Detecting CAPTCHA...")
            self.handle_captcha()
            
            time.sleep(3)
            log("🎵 Song creation complete!")
            return True  # Success!

        except Exception as e:
            log(f"❌ Error in attempt {attempt+1}: {str(e)[:100]}")
            if attempt < max_upload_retries - 1:
                continue
            return False
    
    log(f"❌ All {max_upload_retries} attempts failed")
    return False
