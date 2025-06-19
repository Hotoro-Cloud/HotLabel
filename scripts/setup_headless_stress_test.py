#!/usr/bin/env python3
"""
Setup script for HotLabel Headless Stress Test Environment (Playwright Version)

This script sets up the environment needed to run the headless stress test:
1. Install required Python dependencies
2. Set up browserless.io or similar headless browser service
3. Configure environment variables
4. Test the setup

Usage:
    python setup_headless_stress_test.py [--browserless-url ws://localhost:3000]
"""

import subprocess
import sys
import os
import argparse
import requests
import time
from pathlib import Path

def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(f"STDOUT: {result.stdout}")
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
    
    return result

def check_python_version() -> bool:
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"Error: Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"Python version: {version.major}.{version.minor}.{version.micro} ✓")
    return True

def install_python_dependencies() -> bool:
    """Install required Python dependencies"""
    print("\n=== Installing Python Dependencies ===")
    
    requirements = [
        "playwright>=1.40.0",
        "requests>=2.31.0",
    ]
    
    try:
        for package in requirements:
            print(f"Installing {package}...")
            run_command(f"pip install {package}")
        
        print("Python dependencies installed successfully ✓")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Python dependencies: {e}")
        return False

def install_playwright_browsers() -> bool:
    """Install Playwright browsers"""
    print("\n=== Installing Playwright Browsers ===")
    
    try:
        print("Installing Playwright browsers...")
        run_command("playwright install chromium")
        print("Playwright browsers installed successfully ✓")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Playwright browsers: {e}")
        return False

def setup_browserless_local() -> bool:
    """Set up browserless locally using Docker"""
    print("\n=== Setting up Browserless (Local Docker) ===")
    
    try:
        # Check if Docker is available
        run_command("docker --version")
        
        # Pull and run browserless/chrome
        print("Pulling browserless/chrome image...")
        run_command("docker pull browserless/chrome:latest")
        
        # Stop any existing browserless container
        try:
            run_command("docker stop browserless-chrome", check=False)
            run_command("docker rm browserless-chrome", check=False)
        except:
            pass
        
        # Start browserless container with proper network configuration
        print("Starting browserless container...")
        run_command("""
            docker run -d \
                --name browserless-chrome \
                -p 3001:3000 \
                -e MAX_CONCURRENT_SESSIONS=10 \
                -e CONNECTION_TIMEOUT=60000 \
                -e MAX_QUEUE_LENGTH=10 \
                -e ENABLE_DEBUGGER=true \
                -e ENABLE_CORS=true \
                -e FUNCTION_ENABLE_INCOGNITO=true \
                browserless/chrome:latest
        """)
        
        # Wait for browserless to start
        print("Waiting for browserless to start...")
        time.sleep(15)  # Increased wait time
        
        # Test browserless connection
        try:
            response = requests.get("http://localhost:3001/json/version", timeout=10)
            if response.status_code == 200:
                print("Browserless started successfully ✓")
                return True
            else:
                print(f"Browserless test failed with status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to browserless: {e}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Failed to set up browserless: {e}")
        return False

def setup_browserless_cloud() -> str:
    """Set up browserless using cloud service (browserless.io)"""
    print("\n=== Setting up Browserless Cloud Service ===")
    
    # For browserless.io, you would need an API key
    # This is a placeholder for the setup process
    api_key = input("Enter your browserless.io API key (or press Enter to skip): ").strip()
    
    if api_key:
        browserless_url = f"wss://chrome.browserless.io?token={api_key}"
        print(f"Browserless cloud URL configured: {browserless_url}")
        return browserless_url
    else:
        print("Skipping browserless cloud setup")
        return ""

def test_playwright_setup(browserless_url: str) -> bool:
    """Test Playwright setup with browserless"""
    print(f"\n=== Testing Playwright Setup with {browserless_url} ===")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Connect to browserless
            browser = p.chromium.connect_over_cdp(browserless_url)
            
            # Create a new page
            page = browser.new_page()
            
            # Navigate to test page
            print("Navigating to test page...")
            page.goto("https://httpbin.org/ip")
            
            # Get page title
            title = page.title()
            print(f"Page title: {title}")
            
            # Get page content
            content = page.content()
            print(f"Page content (first 100 chars): {content[:100]}")
            
            # Close browser
            browser.close()
            
            print("Playwright setup test successful ✓")
            return True
            
    except Exception as e:
        print(f"Playwright setup test failed: {e}")
        return False

def test_browserless_connection(browserless_url: str) -> bool:
    """Test browserless connection using requests"""
    print("\n=== Testing Browserless Connection ===")
    
    try:
        # Extract port from browserless URL
        if "ws://localhost:" in browserless_url:
            port = browserless_url.split(":")[-1]
        elif "wss://localhost:" in browserless_url:
            port = browserless_url.split(":")[-1]
        else:
            port = "3000"  # Default fallback
        
        # Test basic connectivity
        response = requests.get(f"http://localhost:{port}/json/version", timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            print(f"Browserless version: {version_info}")
            return True
        else:
            print(f"Browserless version check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to browserless: {e}")
        return False

def test_hotlabel_services() -> bool:
    """Test if HotLabel services are running"""
    print("\n=== Testing HotLabel Services ===")
    
    services = [
        ("Kong API Gateway", "http://localhost:8000/status"),
        ("Tasks Service", "http://localhost:8002/health"),
        ("QA Service", "http://localhost:8003/health"),
        ("Publishers Service", "http://localhost:8004/health"),
        ("Users Service", "http://localhost:8005/health"),
        ("Sample Site", "http://localhost:5001"),
    ]
    
    all_services_ok = True
    
    for service_name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 400:
                print(f"{service_name}: ✓ ({response.status_code})")
            else:
                print(f"{service_name}: ✗ ({response.status_code})")
                all_services_ok = False
        except requests.exceptions.RequestException as e:
            print(f"{service_name}: ✗ (Connection failed: {e})")
            all_services_ok = False
    
    return all_services_ok

def create_config_file(browserless_url: str) -> None:
    """Create a configuration file for the headless stress test"""
    print("\n=== Creating Configuration File ===")
    
    config_content = f"""# HotLabel Headless Stress Test Configuration (Playwright Version)
# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}

# Browserless Configuration
BROWSERLESS_URL={browserless_url}

# HotLabel Services
KONG_URL=http://localhost:8000
TASKS_SERVICE_URL=http://localhost:8002
QA_SERVICE_URL=http://localhost:8003
PUBLISHERS_SERVICE_URL=http://localhost:8004
USERS_SERVICE_URL=http://localhost:8005
SAMPLE_SITE_URL=http://localhost:5001

# Test Configuration
DEFAULT_ITERATIONS=10
DEFAULT_CONCURRENT=2
DEFAULT_TASKS_PER_SESSION=1

# Performance Settings
REQUEST_TIMEOUT=30
PAGE_LOAD_TIMEOUT=30
IMPLICIT_WAIT=10
"""
    
    config_file = Path("headless_stress_test.conf")
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"Configuration file created: {config_file}")

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup HotLabel Headless Stress Test Environment (Playwright)")
    parser.add_argument("--browserless-url", type=str, default="ws://localhost:3001", 
                       help="Browserless service URL")
    parser.add_argument("--use-cloud", action="store_true", 
                       help="Use browserless.io cloud service instead of local Docker")
    parser.add_argument("--skip-docker", action="store_true", 
                       help="Skip Docker setup (assume browserless is already running)")
    
    args = parser.parse_args()
    
    print("HotLabel Headless Stress Test Environment Setup (Playwright Version)")
    print("=" * 70)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("Failed to install Python dependencies")
        sys.exit(1)
    
    # Install Playwright browsers
    if not install_playwright_browsers():
        print("Failed to install Playwright browsers")
        sys.exit(1)
    
    # Set up browserless
    browserless_url = args.browserless_url
    
    if args.use_cloud:
        cloud_url = setup_browserless_cloud()
        if cloud_url:
            browserless_url = cloud_url
    elif not args.skip_docker:
        if not setup_browserless_local():
            print("Failed to set up browserless locally")
            print("You can:")
            print("1. Install Docker and try again")
            print("2. Use --skip-docker if browserless is already running")
            print("3. Use --use-cloud to use browserless.io cloud service")
            sys.exit(1)
    
    # Test browserless connection
    if not test_browserless_connection(browserless_url):
        print("Failed to connect to browserless")
        sys.exit(1)
    
    # Test Playwright setup
    if not test_playwright_setup(browserless_url):
        print("Failed to test Playwright setup")
        print("\nTroubleshooting tips:")
        print("1. Make sure browserless is running: docker ps | grep browserless")
        print("2. Check browserless logs: docker logs browserless-chrome")
        print("3. Try restarting browserless: docker restart browserless-chrome")
        print("4. Check if port 3001 is available: lsof -i :3001")
        sys.exit(1)
    
    # Test HotLabel services
    if not test_hotlabel_services():
        print("Warning: Some HotLabel services are not responding")
        print("Make sure all services are running before running the stress test")
    
    # Create configuration file
    create_config_file(browserless_url)
    
    print("\n" + "=" * 70)
    print("Setup completed successfully!")
    print(f"Browserless URL: {browserless_url}")
    print("\nTo run the headless stress test:")
    print(f"python scripts/stress_test_client_sdk_headless.py --browserless-url {browserless_url}")
    print("\nExample with custom parameters:")
    print(f"python scripts/stress_test_client_sdk_headless.py --iterations 20 --concurrent 5 --browserless-url {browserless_url}")

if __name__ == "__main__":
    main()