#!/usr/bin/env python3
"""
pull_TII.py - Script to pull data from TII endpoint

This script fetches task data from the TII crowdlabel API endpoint
and prints it to the console. Future versions will add functionality
to push the data into the hotlabel-tasks service.

Usage:
    python pull_TII.py
    python pull_TII.py --api-key YOUR_API_KEY
    python pull_TII.py --verify  # Only use this if you want SSL verification
"""

import requests
import json
import logging
import argparse
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TII_API_ENDPOINT = "https://crowdlabel.tii.ae/api/2025.2/tasks/pick"
# Base headers without API key
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# API Key - Set your API key here
API_KEY = "N1mCCAl-w2mDOufWPHHat5gbELyGpVqv"

# SSL Verification default (SSL verification is disabled by default)
VERIFY_SSL = False

# Task Service Configuration
KONG_URL = "http://localhost:8000"  # Kong Gateway URL
TASKS_BASE_URL = f"{KONG_URL}/api/v1/tasks"
TASKS_API_KEY = "pk_I-H8edmX0ffJvpNJ8joGdT5xNdawyqE56V7jrIC8Kps"  # Set your task service API key
TASKS_HEADERS = {"X-API-Key": TASKS_API_KEY}

# Default provider ID (replace with your actual provider ID)
DEFAULT_PROVIDER_ID = "76662eb8-daf6-4509-9bc1-4ff76fa35d71"


def fetch_tii_tasks(api_key, verify_ssl=False):
    """
    Fetch tasks from the TII endpoint
    
    Args:
        api_key (str): API key for authentication
        verify_ssl (bool): Whether to verify SSL certificates (default: False)
    
    Returns:
        dict: JSON response from the API or None if request failed
    """
    try:
        logger.info(f"Fetching tasks from TII endpoint: {TII_API_ENDPOINT}")
        
        if not verify_ssl:
            logger.info("SSL certificate verification is disabled.")
        
        # Add API key to headers
        headers = BASE_HEADERS.copy()
        headers["x-api-key"] = api_key
        
        # Log the request details (masking API key for security)
        masked_key = "****" if api_key else ""
        logger.info(f"Making GET request with headers: Content-Type, Accept, x-api-key: {masked_key}")
        
        # Make the GET request
        response = requests.get(TII_API_ENDPOINT, headers=headers, verify=verify_ssl)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        return data
    
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error: {e}")
        logger.info("Consider using --verify if this is a testing environment")
        return None
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401 or status_code == 403:
            logger.error(f"Authentication failed. Please check your API key. Status code: {status_code}")
            logger.error(f"Response details: {e.response.text}")
        else:
            logger.error(f"HTTP Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from TII endpoint: {e}")
        return None


def transform_tii_to_task_format(tii_data: List[Dict[str, Any]], provider_id: str = None) -> List[Dict[str, Any]]:
    """
    Transform TII API data to the format required by the hotlabel-tasks service
    
    Args:
        tii_data (list): List of task data from TII API
        provider_id (str, optional): Provider ID to use for creating tasks
        
    Returns:
        list: List of transformed task data ready for submission to hotlabel-tasks service
    """
    if provider_id is None:
        provider_id = DEFAULT_PROVIDER_ID
        
    transformed_tasks = []
    
    for task in tii_data:
        # Extract the necessary information
        tii_id = task.get("id", "")
        category = task.get("category", "unknown")
        complexity = task.get("complexity", 1)
        task_type = task.get("type", "text")
        topic = task.get("topic", "general")
        
        # Get image URL if available
        image_url = None
        if "content" in task and "image" in task["content"] and "url" in task["content"]["image"]:
            image_url = task["content"]["image"]["url"]
        
        # Get question text
        question = None
        if "task" in task and "text" in task["task"]:
            question = task["task"]["text"]
        
        # Get choices if available
        choices = None
        if "task" in task and "choices" in task["task"]:
            choices = task["task"]["choices"]
        
        # Create the task data structure
        transformed_task = {
            "title": f"TII Task: {tii_id}",
            "description": f"Task imported from TII with topic: {topic}",
            "provider_id": provider_id,
            "task_type": category,  # Use TII category as task_type
            "content": {
                "question": question
            },
            "language": "en",  # Assume English for now
            "category": category,
            "complexity_level": complexity,
            "options": {
                "tii_id": tii_id,
                "task_type": task_type,
                "choices": choices
            },
            "time_estimate_seconds": 300,  # Default time estimate
            "tags": [f"tii", category, topic, task_type],
            "golden_set": False,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "pending"
        }
        
        # Add image URL if available
        if image_url:
            transformed_task["content"]["image_url"] = image_url
        
        transformed_tasks.append(transformed_task)
    
    return transformed_tasks


def submit_tasks_to_service(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Submit transformed tasks to the hotlabel-tasks service
    
    Args:
        tasks (list): List of transformed task data
        
    Returns:
        dict: Response from the tasks service
    """
    try:
        logger.info(f"Submitting {len(tasks)} tasks to tasks service: {TASKS_BASE_URL}")
        
        # For multiple tasks, use the batch endpoint
        if len(tasks) > 1:
            endpoint = f"{TASKS_BASE_URL}/batch"
            logger.info(f"Using batch endpoint: {endpoint}")
        else:
            endpoint = TASKS_BASE_URL
            tasks = tasks[0]  # Get the single task instead of the list
            logger.info(f"Using single task endpoint: {endpoint}")
        
        # Make the POST request
        response = requests.post(endpoint, json=tasks, headers=TASKS_HEADERS)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Log success
        logger.info(f"Successfully submitted tasks to service. Status code: {response.status_code}")
        
        # Parse and return JSON response
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error when submitting tasks: {e}")
        logger.error(f"Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting tasks to service: {e}")
        return {"error": str(e)}


def print_task_data(data):
    """
    Pretty print the task data to console
    
    Args:
        data (dict): Task data from TII API
    """
    if not data:
        logger.warning("No data to display")
        return
    
    print("\n========== TII TASK DATA ==========")
    print(json.dumps(data, indent=4))
    print("===================================\n")
    
    # Print summary information if data structure allows
    try:
        if isinstance(data, list):
            print(f"Total tasks: {len(data)}")
        elif isinstance(data, dict):
            if 'tasks' in data:
                print(f"Total tasks: {len(data['tasks'])}")
            elif 'task' in data:
                print(f"Retrieved task ID: {data['task'].get('id', 'unknown')}")
    except Exception as e:
        logger.error(f"Error printing summary: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Fetch task data from TII endpoint")
    parser.add_argument('--api-key', 
                        help='API key for authenticating with the TII endpoint')
    parser.add_argument('--verify', action='store_true', 
                        help='Enable SSL certificate verification (disabled by default)')
    parser.add_argument('--submit', action='store_true',
                        help='Submit fetched tasks to the hotlabel-tasks service')
    parser.add_argument('--provider-id',
                        help='Provider ID to use when submitting tasks')
    return parser.parse_args()


def main():
    """Main function to execute the script"""
    args = parse_arguments()
    logger.info("Starting TII data pull script")
    
    # Use command line API key if provided, otherwise use the one defined in the file
    api_key = args.api_key if args.api_key else API_KEY
    
    # Determine SSL verification setting
    verify_ssl = args.verify
    
    # Fetch the data
    tii_data = fetch_tii_tasks(api_key=api_key, verify_ssl=verify_ssl)
    
    # Print the original TII data
    print_task_data(tii_data)
    
    # If submitting to tasks service is requested
    if args.submit and tii_data:
        # Transform TII data
        provider_id = args.provider_id if args.provider_id else DEFAULT_PROVIDER_ID
        transformed_tasks = transform_tii_to_task_format(tii_data, provider_id)
        
        # Print transformed task data
        print("\n========== TRANSFORMED TASK DATA ==========")
        print(json.dumps(transformed_tasks, indent=4))
        print("==========================================\n")
        
        # Submit to tasks service
        response = submit_tasks_to_service(transformed_tasks)
        
        # Print response from tasks service
        print("\n========== TASK SUBMISSION RESPONSE ==========")
        print(json.dumps(response, indent=4))
        print("==============================================\n")
    
    logger.info("TII data pull completed")


if __name__ == "__main__":
    main()
