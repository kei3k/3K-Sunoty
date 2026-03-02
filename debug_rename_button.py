"""
Debug script specifically for testing the Rename button click
Using exact XPath provided by user
"""
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def debug_rename():
    # Setup Driver with saved profile
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Use saved profile
    user_data_dir = os.path.join(os.getcwd(), "selenium_data")
    options.add_argument(f"user-data-dir={user_data_dir}")
    print(f"Using Profile: {user_data_dir}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("\n" + "="*60)
        print("DEBUG: RENAME BUTTON TEST")
        print("="*60)
        driver.get("https://suno.com/create")
        
        print("\n👉 Please UPLOAD an audio file to open the modal.")
        print("👉 WAITING 30 seconds...")
        time.sleep(30)
        
        # TEST 1: Full XPath (Exact)
        print("\n--- TEST: Click Rename & Find Input ---")
        try:
            # User's exact XPath
            edit_btn = driver.find_element(By.XPATH, "/html/body/div[9]/div[3]/div/section/div/div[2]/div[1]/div/button")
            print(f"✅ FOUND Edit Button via Full XPath!")
            
            driver.execute_script("arguments[0].style.border='3px solid red'", edit_btn)
            driver.execute_script("arguments[0].click();", edit_btn)
            print("   ✅ Clicked Button!")
            time.sleep(2) # Wait for input to appear
            
            # NOW FIND THE INPUT
            print("\n   [INSPECTION] Looking for input field...")
            
            # 1. Check Active Element (Focus)
            try:
                active = driver.switch_to.active_element
                print(f"   👉 Active Element (Focus): Tag='{active.tag_name}', ID='{active.get_attribute('id')}', Class='{active.get_attribute('class')}'")
                if active.tag_name in ['input', 'textarea']:
                    print("   ✅ Active element is an input! Typing...")
                    active.send_keys("ABC FOCUS TEST")
                    time.sleep(1)
            except:
                print("   ❌ Could not check active element.")
            
            # 2. Check Global Inputs (Visible only)
            print("   👉 Checking ALL visible inputs on page...")
            inputs = driver.find_elements(By.XPATH, "//input[@type='text'] | //textarea")
            visible_inputs = [i for i in inputs if i.is_displayed()]
            print(f"   Found {len(visible_inputs)} visible text inputs on page.")
            
            for i, inp in enumerate(visible_inputs):
                ph = inp.get_attribute("placeholder")
                val = inp.get_attribute("value")
                loc = inp.location
                print(f"     [{i}] Tag='{inp.tag_name}', Placeholder='{ph}', Value='{val}', Location={loc}")
                
                # Heuristic: If it has 'Title' placeholder or is near the click location?
                if "Title" in str(ph) or "Name" in str(ph):
                    print(f"     🌟 POTENTIAL MATCH! Typing...")
                    inp.clear()
                    inp.send_keys("ABC GLOBAL TEST")
                    time.sleep(1)

        except Exception as e:
            print(f"❌ Test Failed: {e}")
            
        print("\n" + "="*60)
        print("DEBUG COMPLETE. Did 'ABC TEST' appear in the Title?")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("\nClosing in 60s...")
        time.sleep(60)
        driver.quit()

if __name__ == "__main__":
    debug_rename()
