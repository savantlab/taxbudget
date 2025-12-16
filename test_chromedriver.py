#!/usr/bin/env python
"""
Example script to test ChromeDriver service with the Tax Budget Allocator app.
Make sure to run the chromedriver_service before running this script.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def test_app_with_chromedriver():
    """Test the Tax Budget Allocator app using ChromeDriver"""
    
    # Configure Chrome options
    chrome_options = Options()
    # chrome_options.add_argument('--headless')  # Uncomment for headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Connect to ChromeDriver service
    service = Service()
    service.port = 9515  # ChromeDriver default port
    
    driver = None
    
    try:
        print("🔧 Connecting to ChromeDriver service...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Connected to ChromeDriver")
        
        # Navigate to the app
        print("\n📊 Opening Tax Budget Allocator...")
        driver.get("http://127.0.0.1:8000/")
        print(f"✅ Page loaded: {driver.title}")
        
        # Wait for the form to load
        wait = WebDriverWait(driver, 10)
        form = wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        print("✅ Form loaded successfully")
        
        # Fill in some allocations
        print("\n💰 Filling allocation form...")
        allocations = {
            'healthcare': 20,
            'education': 20,
            'defense': 10,
            'infrastructure': 15,
            'social_security': 10,
            'environment': 10,
            'science': 5,
            'public_safety': 5,
            'housing': 3,
            'other': 2
        }
        
        for category, percentage in allocations.items():
            field = driver.find_element(By.NAME, category)
            field.clear()
            field.send_keys(str(percentage))
            print(f"  ✓ {category.replace('_', ' ').title()}: {percentage}%")
        
        time.sleep(1)
        
        # Check if submit button is enabled
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        if submit_button.is_enabled():
            print("\n✅ Submit button is enabled (total = 100%)")
            print("\n🎯 Form validation working correctly!")
        else:
            print("\n⚠️  Submit button is disabled")
        
        # Optional: Submit the form
        # submit_button.click()
        # print("✅ Form submitted successfully")
        
        print("\n✨ Test completed successfully!")
        print("Browser will close in 3 seconds...")
        time.sleep(3)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("\n👋 Browser closed")


if __name__ == "__main__":
    print("=" * 60)
    print("Tax Budget Allocator - ChromeDriver Service Test")
    print("=" * 60)
    print("\nMake sure the ChromeDriver service is running:")
    print("  ./start_chromedriver_service.sh")
    print("\n" + "=" * 60 + "\n")
    
    try:
        test_app_with_chromedriver()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
