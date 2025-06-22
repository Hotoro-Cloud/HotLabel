#!/usr/bin/env python3
"""
test_tii_ssl.py - Test SSL connectivity to TII API

This script tests different SSL configurations with the TII API
to help diagnose SSL-related issues.

Usage:
    python3 test_tii_ssl.py
    python3 test_tii_ssl.py --verify
"""

import requests
import urllib3
import ssl
import logging
from typing import Dict, Any

# Disable SSL warnings for unverified requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TII_API_ENDPOINT = "https://crowdlabel.tii.ae/api/2025.2/tasks/pick"
API_KEY = "N1mCCAl-w2mDOufWPHHat5gbELyGpVqv"

# Base headers
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "x-api-key": API_KEY
}


def test_ssl_connection(verify_ssl: bool = False) -> Dict[str, Any]:
    """
    Test SSL connection to TII API
    
    Args:
        verify_ssl (bool): Whether to verify SSL certificates
        
    Returns:
        dict: Test results
    """
    result = {
        "success": False,
        "error": None,
        "response_type": None,
        "response_length": None,
        "ssl_verified": verify_ssl
    }
    
    try:
        logger.info(f"Testing TII API connection with SSL verification: {verify_ssl}")
        logger.info(f"Endpoint: {TII_API_ENDPOINT}")
        
        # Make the request
        response = requests.get(TII_API_ENDPOINT, headers=BASE_HEADERS, verify=verify_ssl)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Log response details
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response type: {type(data)}")
        
        if isinstance(data, list):
            logger.info(f"Response is a list with {len(data)} items")
            result["response_type"] = "list"
            result["response_length"] = len(data)
        elif isinstance(data, dict):
            logger.info(f"Response is a dict with keys: {list(data.keys())}")
            result["response_type"] = "dict"
            result["response_length"] = 1
        else:
            logger.info(f"Response is {type(data)}")
            result["response_type"] = str(type(data))
            result["response_length"] = 0
        
        result["success"] = True
        logger.info("✅ SSL connection test successful")
        
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL Error: {e}"
        logger.error(f"❌ SSL Error: {e}")
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP Error: {e}"
        logger.error(f"❌ HTTP Error: {e}")
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request Error: {e}"
        logger.error(f"❌ Request Error: {e}")
    except Exception as e:
        result["error"] = f"Unexpected Error: {e}"
        logger.error(f"❌ Unexpected Error: {e}")
    
    return result


def test_custom_ssl_context() -> Dict[str, Any]:
    """
    Test with custom SSL context
    
    Returns:
        dict: Test results
    """
    result = {
        "success": False,
        "error": None,
        "response_type": None,
        "response_length": None,
        "ssl_verified": "custom"
    }
    
    try:
        logger.info("Testing TII API connection with custom SSL context")
        
        # Create custom SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Make the request
        response = requests.get(TII_API_ENDPOINT, headers=BASE_HEADERS, verify=ssl_context)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Log response details
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response type: {type(data)}")
        
        if isinstance(data, list):
            result["response_type"] = "list"
            result["response_length"] = len(data)
        elif isinstance(data, dict):
            result["response_type"] = "dict"
            result["response_length"] = 1
        else:
            result["response_type"] = str(type(data))
            result["response_length"] = 0
        
        result["success"] = True
        logger.info("✅ Custom SSL context test successful")
        
    except Exception as e:
        result["error"] = f"Custom SSL Error: {e}"
        logger.error(f"❌ Custom SSL Error: {e}")
    
    return result


def main():
    """Main function to run SSL tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SSL connectivity to TII API")
    parser.add_argument('--verify', action='store_true', 
                        help='Test with SSL verification enabled')
    args = parser.parse_args()
    
    print("=" * 60)
    print("TII API SSL CONNECTIVITY TEST")
    print("=" * 60)
    
    # Test 1: SSL verification disabled (default)
    print("\n1. Testing with SSL verification DISABLED (default)")
    result1 = test_ssl_connection(verify_ssl=False)
    
    # Test 2: SSL verification enabled (if requested)
    if args.verify:
        print("\n2. Testing with SSL verification ENABLED")
        result2 = test_ssl_connection(verify_ssl=True)
    else:
        result2 = None
    
    # Test 3: Custom SSL context
    print("\n3. Testing with custom SSL context")
    result3 = test_custom_ssl_context()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    print(f"\nSSL Disabled: {'✅ SUCCESS' if result1['success'] else '❌ FAILED'}")
    if result1['error']:
        print(f"  Error: {result1['error']}")
    else:
        print(f"  Response: {result1['response_type']} ({result1['response_length']} items)")
    
    if result2:
        print(f"\nSSL Enabled: {'✅ SUCCESS' if result2['success'] else '❌ FAILED'}")
        if result2['error']:
            print(f"  Error: {result2['error']}")
        else:
            print(f"  Response: {result2['response_type']} ({result2['response_length']} items)")
    
    print(f"\nCustom SSL: {'✅ SUCCESS' if result3['success'] else '❌ FAILED'}")
    if result3['error']:
        print(f"  Error: {result3['error']}")
    else:
        print(f"  Response: {result3['response_type']} ({result3['response_length']} items)")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if result1['success']:
        print("✅ Use SSL verification DISABLED for development/testing")
    else:
        print("❌ SSL disabled also failed - check network connectivity")
    
    if result2 and result2['success']:
        print("✅ SSL verification ENABLED works - use for production")
    elif result2:
        print("❌ SSL verification ENABLED failed - TII API has certificate issues")
    
    if result3['success']:
        print("✅ Custom SSL context works - alternative approach available")
    else:
        print("❌ Custom SSL context failed")
    
    print("\nFor the main script, use:")
    if result1['success']:
        print("  python3 scripts/pull_TII_all_categories.py --dry-run")
    elif result3['success']:
        print("  (Modify script to use custom SSL context)")
    else:
        print("  (Contact TII support about SSL issues)")


if __name__ == "__main__":
    main() 