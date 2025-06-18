#!/usr/bin/env python3
"""
Setup script for HotLabel System Stress Test

This script prepares the environment for running the stress test:
1. Checks if all services are running
2. Verifies sample site is accessible
3. Installs required dependencies
4. Sets up Chrome webdriver
"""

import requests
import subprocess
import sys
import os
import time
from pathlib import Path

# Configuration
SERVICES = {
    "Kong API Gateway": "http://localhost:8000/health",
    "Tasks Service": "http://localhost:8002/health",
    "Publishers Service": "http://localhost:8004/health",
    "QA Service": "http://localhost:8003/health",
    "Users Service": "http://localhost:8005/health",
    "Sample Site": "http://localhost:5001"
}

def check_service_health(url: str, name: str) -> bool:
    """Check if a service is healthy"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name}: Healthy")
            return True
        else:
            print(f"❌ {name}: Unhealthy (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {name}: Unreachable ({e})")
        return False

def check_all_services() -> bool:
    """Check if all required services are running"""
    print("Checking service health...")
    
    all_healthy = True
    for name, url in SERVICES.items():
        if not check_service_health(url, name):
            all_healthy = False
    
    return all_healthy

def install_dependencies() -> bool:
    """Install required Python dependencies"""
    print("\nInstalling dependencies...")
    
    try:
        # Install from requirements file
        requirements_file = Path(__file__).parent.parent / "requirements.txt"
        if requirements_file.exists():
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True)
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Requirements file not found")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_chrome_webdriver() -> bool:
    """Check if Chrome webdriver is available"""
    print("\nChecking Chrome webdriver...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("Installing ChromeDriver using webdriver-manager...")
        
        # This will automatically download and install the correct ChromeDriver version
        driver_path = ChromeDriverManager().install()
        print(f"ChromeDriver installed at: {driver_path}")
        
        # Remove quarantine attribute on macOS if needed
        try:
            import subprocess
            subprocess.run(['xattr', '-d', 'com.apple.quarantine', driver_path], 
                         capture_output=True, check=False)
            print("Removed macOS quarantine attribute from ChromeDriver")
        except Exception as e:
            print(f"Note: Could not remove quarantine attribute: {e}")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.quit()
        
        print("✅ Chrome webdriver is working")
        return True
    except Exception as e:
        print(f"❌ Chrome webdriver issue: {e}")
        print("Trying to install ChromeDriver manually...")
        
        try:
            # Try to install ChromeDriver using brew if available
            import subprocess
            result = subprocess.run(['brew', 'install', 'chromedriver'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("ChromeDriver installed via Homebrew")
                # Remove quarantine attribute
                subprocess.run(['xattr', '-d', 'com.apple.quarantine', '/opt/homebrew/bin/chromedriver'], 
                             capture_output=True, check=False)
                print("Removed macOS quarantine attribute")
                return True
            else:
                print("Homebrew installation failed, please install ChromeDriver manually")
                print("Visit: https://chromedriver.chromium.org/downloads")
                return False
        except Exception as brew_error:
            print(f"Homebrew not available: {brew_error}")
            print("Please install ChromeDriver manually from: https://chromedriver.chromium.org/downloads")
            return False

def run_quick_test() -> bool:
    """Run a quick test to verify everything works"""
    print("\nRunning quick test...")
    
    try:
        # Test API connectivity
        response = requests.get("http://localhost:8000/api/v1/providers", timeout=5)
        if response.status_code == 200:
            print("✅ API connectivity test passed")
        else:
            print(f"❌ API connectivity test failed: {response.status_code}")
            return False
        
        # Test sample site
        response = requests.get("http://localhost:5001", timeout=5)
        if response.status_code == 200:
            print("✅ Sample site connectivity test passed")
        else:
            print(f"❌ Sample site connectivity test failed: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("HotLabel System Stress Test Setup")
    print("=" * 50)
    
    # Check services
    if not check_all_services():
        print("\n❌ Some services are not running. Please start all services first:")
        print("   docker-compose -f docker-compose-local.yml up -d")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        return False
    
    # Check webdriver
    if not check_chrome_webdriver():
        print("\n❌ Chrome webdriver setup failed")
        return False
    
    # Run quick test
    if not run_quick_test():
        print("\n❌ Quick test failed")
        return False
    
    print("\n✅ Setup completed successfully!")
    print("\nYou can now run the stress test with:")
    print("   python scripts/stress_test_client_sdk.py")
    print("\nOr with custom parameters:")
    print("   python scripts/stress_test_client_sdk.py --iterations 100 --concurrent 10")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 