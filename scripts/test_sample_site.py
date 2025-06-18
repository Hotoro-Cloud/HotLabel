#!/usr/bin/env python3
"""
Simple test script to verify the sample site is working correctly
"""

import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

SAMPLE_SITE_URL = "http://localhost:5001"

def test_sample_site_connectivity():
    """Test if the sample site is accessible"""
    print("Testing sample site connectivity...")
    try:
        response = requests.get(SAMPLE_SITE_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Sample site is accessible")
            return True
        else:
            print(f"❌ Sample site returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Sample site is not accessible: {e}")
        return False

def test_sample_site_navigation():
    """Test navigation through the sample site"""
    print("\nTesting sample site navigation...")
    
    driver = None
    try:
        # Create webdriver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to sample site
        print("  Navigating to sample site...")
        driver.get(SAMPLE_SITE_URL)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print(f"  Page title: {driver.title}")
        print(f"  Current URL: {driver.current_url}")
        
        # Look for Start Quiz button
        print("  Looking for Start Quiz button...")
        start_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Start Quiz')]"))
        )
        print("  Found Start Quiz button")
        
        # Click Start Quiz button
        print("  Clicking Start Quiz button...")
        start_button.click()
        
        # Wait for quiz page to load
        print("  Waiting for quiz page...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        
        print(f"  Quiz page loaded: {driver.current_url}")
        
        # Check for quiz questions
        radio_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        print(f"  Found {len(radio_buttons)} radio buttons (quiz questions)")
        
        if len(radio_buttons) > 0:
            print("✅ Sample site navigation test passed")
            return True
        else:
            print("❌ No quiz questions found")
            return False
            
    except Exception as e:
        print(f"❌ Sample site navigation test failed: {e}")
        if driver:
            try:
                print(f"  Current URL: {driver.current_url}")
                print(f"  Page title: {driver.title}")
                page_source = driver.page_source[:500]
                print(f"  Page source (first 500 chars): {page_source}")
            except:
                pass
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    """Main test function"""
    print("Sample Site Test")
    print("=" * 50)
    
    # Test connectivity
    if not test_sample_site_connectivity():
        print("\n❌ Sample site connectivity test failed")
        print("Please ensure the sample site is running:")
        print("  cd hotlabel-samplesite")
        print("  docker-compose up -d")
        return False
    
    # Test navigation
    if not test_sample_site_navigation():
        print("\n❌ Sample site navigation test failed")
        return False
    
    print("\n✅ All tests passed! Sample site is working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 