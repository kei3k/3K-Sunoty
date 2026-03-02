
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_upload_flow():
    # 1. Setup Driver
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # [PERSISTENCE] Use same user data dir as main app
    base_dir = os.getcwd()
    user_data_dir = os.path.join(base_dir, "selenium_data")
    options.add_argument(f"user-data-dir={user_data_dir}")
    print(f"DEBUG: Using Profile Path: {user_data_dir}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # 2. Navigate
        print("\n\n" + "="*50)
        print("DEBUG: UPLOAD FLOW CHECK")
        print("="*50)
        driver.get("https://suno.com/create")
        
        print("👉 PLEASE MANUALLY LOGIN IF NEEDED (Should be auto-logged in).")
        print("👉 THEN CLICK 'UPLOAD AUDIO' MANUALLY TO OPEN THE MODAL.")
        print("👉 DO NOT CLICK ANYTHING ELSE. WAITING 30 SECONDS...")
        time.sleep(30)
        
        # 3. Check Selectors Step-by-Step
        print("\n--- [STEP 1] Checking 'Agree to Terms' ---")
        try:
            agree_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Agree to Terms') or contains(text(), 'I Agree')]"))
            )
            print(f"✅ FOUND 'Agree' Button: {agree_btn.text}")
            agree_btn.click()
            print("   Clicked 'Agree'.")
        except:
            print("❌ 'Agree' Button NOT Found (already agreed?).")

        time.sleep(2)
        
        print("\n--- [STEP 2] DOM INSPECTION (RENAME) ---")
        try:
            # Find Modal
            modal = driver.find_element(By.XPATH, "//*[contains(@id, 'chakra-modal')] | //section[contains(@role, 'dialog')] | //section[contains(@id, 'popover')] | //div[contains(@id, 'popover-content')]")
            print(f"✅ FOUND Container: {modal.tag_name}, ID: {modal.get_attribute('id')}")
            
            # Recursive function to print tree
            def print_tree(element, indent=0):
                tag = element.tag_name
                classes = element.get_attribute("class")
                aria = element.get_attribute("aria-label")
                try: text = element.text.strip().replace("\n", " ")[:20]
                except: text = ""
                
                info = f"{tag}"
                if classes: info += f" .{classes.replace(' ', '.')}"
                if aria: info += f" [aria-label='{aria}']"
                if text: info += f" '{text}'"
                
                print(" " * indent + f"-> {info}")
                
                children = element.find_elements(By.XPATH, "./*")
                for child in children:
                    print_tree(child, indent + 2)

            print("DUMPING MODAL STRUCTURE:")
            print_tree(modal)

        except Exception as e:
            print(f"❌ INSPECTION Failed: {e}")
            

            
        print("\n--- [STEP 3] Checking 'Save' ---")
        try:
            save_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Save')]"))
            )
            print(f"✅ FOUND 'Save' Button: {save_btn.text}")
            save_btn.click()
            print("   Clicked 'Save'. Waiting for modal to close...")
            time.sleep(2)
        except:
            print("❌ 'Save' Button NOT Found.")

        print("\n--- [STEP 4] Checking 'Cover' (Main Page) ---")
        # Now we assume we are back on main page. Look for Cover button there.
        try:
             print("   Looking for 'Cover' on main page...")
             # Look for ANY element containing Cover
             els = driver.find_elements(By.XPATH, "//*[contains(text(), 'Cover')]")
             found_cover = False
             for el in els:
                 if el.is_displayed():
                     print(f"   Found 'Cover' text in: <{el.tag_name}>")
                     driver.execute_script("arguments[0].style.border='3px solid purple'", el)
                     
                     # Check if clickable
                     parent = el
                     for _ in range(3):
                         if parent.tag_name in ['button', 'a', 'input'] or parent.get_attribute('role') == 'button':
                             print(f"      ✅ Clickable Parent Found: <{parent.tag_name}>")
                             parent.click()
                             found_cover = True
                             break
                         try: parent = parent.find_element(By.XPATH, "..")
                         except: break
                     if found_cover: break
             
             if not found_cover:
                 print("   ❌ Could not identify clickable 'Cover' button.")
            
        except Exception as e:
            print(f"❌ Cover Check Failed: {e}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        print("\nClosing in 60s...")
        time.sleep(60)
        driver.quit()

if __name__ == "__main__":
    debug_upload_flow()
