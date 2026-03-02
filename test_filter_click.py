
import logging
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_filter_click_logic():
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    if os.path.exists(user_data_dir):
        options.add_argument(f"user-data-dir={user_data_dir}")
    else:
        print("Note: Custom chrome_profile not found, using default or temp profile")
        
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1920, 1080)
    
    try:
        logger.info("Navigating to Suno Create page...")
        driver.get("https://suno.com/create")
        time.sleep(5)
        
        print("\n" + "="*60)
        print("TEST SESSION: FILTER BUTTON CLICK")
        print("="*60)
        print("Please manually log in if needed. Waiting 10s...")
        time.sleep(10)
        
        print("\n[TEST] Looking for Filter Button...")
        
        filter_clicked = False
        
        # New robust XPaths
        filter_xpaths = [
            "//button[contains(., 'Filters')]",
            "//button[contains(., 'Filter')]",
            "//div[@role='button'][contains(., 'Filters')]",
            "//div[@role='button'][contains(., 'Filter')]",
            "//span[contains(@class, 'relative') and contains(@class, 'flex-row') and contains(., 'Filters')]",
            "//span[contains(., 'Filters')]",
            "//span[contains(., 'Filter')]"
        ]
        
        for i, xpath in enumerate(filter_xpaths):
            print(f"  Attempt {i+1}: Checking XPath: {xpath}")
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                print(f"    Found {len(elements)} elements")
                
                for el in elements:
                    if el.is_displayed():
                        print(f"    Element is visible: {el.text} (Tag: {el.tag_name})")
                        # Highlight it
                        driver.execute_script("arguments[0].style.border='3px solid red';", el)
                        time.sleep(1)
                        
                        # Try to click
                        try:
                            # Try clicking parent button if it's a span inside button, otherwise click element itself
                            if el.tag_name == "span":
                                try:
                                    parent_btn = el.find_element(By.XPATH, "./ancestor::button")
                                    print("    Clicking parent button...")
                                    driver.execute_script("arguments[0].click();", parent_btn)
                                except:
                                    print("    Clicking span directly...")
                                    driver.execute_script("arguments[0].click();", el)
                            else:
                                print("    Clicking element directly...")
                                driver.execute_script("arguments[0].click();", el)
                                
                            print("    ✅ Click action performed successfully")
                            filter_clicked = True
                            time.sleep(2)
                            break
                        except Exception as click_err:
                            print(f"    ❌ Click failed: {click_err}")
                
            except Exception as e:
                print(f"    Error checking xpath: {e}")
                
            if filter_clicked:
                break
                
        if filter_clicked:
            print("\n✅ SUCCESS: Filter button was found and clicked.")
        else:
            print("\n❌ FAILURE: Filter button not found with any strategy.")
            
            # Save debug info
            driver.save_screenshot("debug_test_filter_fail.png")
            print("Saved screenshot to debug_test_filter_fail.png")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    test_filter_click_logic()
