#!/usr/bin/env python3
"""
pull_TII_all_categories.py - Script to pull random tasks from all TII categories

This script fetches random task data from the TII crowdlabel API endpoint
for all available categories, types, languages, topics, and complexity levels,
and creates them in the hotlabel-tasks service.

Usage:
    python pull_TII_all_categories.py
    python pull_TII_all_categories.py --api-key YOUR_API_KEY
    python pull_TII_all_categories.py --verify  # Only use this if you want SSL verification
    python pull_TII_all_categories.py --dry-run  # Only fetch and display, don't submit
    python pull_TII_all_categories.py --max-tasks 10  # Limit number of tasks per category
"""

import requests
import json
import logging
import argparse
import os
import time
import urllib3
import ssl
import codecs
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from itertools import product

# Disable SSL warnings for unverified requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TII_API_BASE_ENDPOINT = "https://crowdlabel.tii.ae/api/2025.2/tasks/pick"

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
TASKS_API_KEY = "pk_9QbdCwEi2QTQTqVH-MgXP6M9mx2BF43C1y4BF3yG-DM"  # Set your task service API key
TASKS_HEADERS = {"X-API-Key": TASKS_API_KEY}

# Default provider ID (replace with your actual provider ID)
DEFAULT_PROVIDER_ID = "1acc64ba-7821-4a93-9101-6a02db5b09b3"

# TII API Categories and Options (from latest documentation)
TII_CATEGORIES = ["vqa"]  # Visual Question Analysis
TII_TYPES = ["true-false", "numeric", "mcq"]  # Task types
TII_LANGUAGES = ["en", "ar"]  # English and Arabic
TII_TOPICS = [
    "animals", "construction-site", "fashion", "garage-workshop", 
    "kitchen", "living-room", "medical-field", "music", 
    "office", "school", "uae", "underwater"
]
TII_COMPLEXITY_LEVELS = [1, 2, 3, 4]  # 1=least complex, 4=most complex

# Rate limiting - delay between requests to avoid overwhelming the API
REQUEST_DELAY = 1.0  # seconds


def decode_unicode_escapes(text):
    """
    Decode Unicode escape sequences in text.
    
    Args:
        text (str): Text that may contain Unicode escape sequences
        
    Returns:
        str: Decoded text with proper Unicode characters
    """
    if not isinstance(text, str):
        return text
    
    try:
        # Handle Unicode escape sequences like \u0645\u0637\u0627\u0637
        return codecs.decode(text, 'unicode_escape')
    except (UnicodeDecodeError, ValueError):
        # If decoding fails, return the original text
        logger.warning(f"Failed to decode Unicode escapes in text: {text[:50]}...")
        return text


def process_choices(choices):
    """
    Process choices to decode Unicode escape sequences.
    
    Args:
        choices: List of choice strings or dicts with 'label' or 'value' field
        
    Returns:
        list: Processed choices with decoded Unicode
    """
    if not choices:
        return choices
    
    processed_choices = []
    for choice in choices:
        if isinstance(choice, dict):
            # Handle choice objects with 'label' or 'value' field
            processed_choice = choice.copy()
            if 'label' in choice:
                processed_choice['label'] = decode_unicode_escapes(choice['label'])
            if 'value' in choice:
                processed_choice['value'] = decode_unicode_escapes(choice['value'])
            processed_choices.append(processed_choice)
        elif isinstance(choice, str):
            # Handle simple string choices
            processed_choices.append(decode_unicode_escapes(choice))
        else:
            # Handle other types as-is
            processed_choices.append(choice)
    
    return processed_choices


def build_query_params(category: Optional[str] = None, 
                      task_type: Optional[str] = None,
                      language: Optional[str] = None,
                      topic: Optional[str] = None,
                      complexity: Optional[int] = None) -> str:
    """
    Build query parameters for TII API request
    
    Args:
        category: Task category filter
        task_type: Task type filter (renamed from 'type' to avoid conflict)
        language: Language filter
        topic: Topic filter
        complexity: Complexity level filter
        
    Returns:
        str: Query parameter string
    """
    params = []
    
    if category:
        params.append(f"category={category}")
    if task_type:
        params.append(f"type={task_type}")
    if language:
        params.append(f"lang={language}")
    if topic:
        params.append(f"topic={topic}")
    if complexity:
        params.append(f"complexity={complexity}")
    
    return "&".join(params) if params else ""


def fetch_tii_task(api_key: str, query_params: str = "", verify_ssl: bool = False) -> Optional[Dict[str, Any]]:
    """
    Fetch a single random task from the TII endpoint with specified filters
    
    Args:
        api_key (str): API key for authentication
        query_params (str): Query parameters string
        verify_ssl (bool): Whether to verify SSL certificates (default: False)
    
    Returns:
        dict: JSON response from the API or None if request failed
    """
    try:
        # Build the full endpoint URL
        endpoint = TII_API_BASE_ENDPOINT
        if query_params:
            endpoint = f"{endpoint}?{query_params}"
        
        logger.info(f"Fetching task from TII endpoint: {endpoint}")
        
        if not verify_ssl:
            logger.info("SSL certificate verification is disabled.")
        
        # Add API key to headers
        headers = BASE_HEADERS.copy()
        headers["x-api-key"] = api_key
        
        # Log the request details (masking API key for security)
        masked_key = "****" if api_key else ""
        logger.info(f"Making GET request with headers: Content-Type, Accept, x-api-key: {masked_key}")
        
        # Make the GET request
        response = requests.get(endpoint, headers=headers, verify=verify_ssl)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Debug: Log the response type and content
        logger.info(f"Response type: {type(data)}")
        if isinstance(data, list):
            logger.info(f"Response is a list with {len(data)} items")
        elif isinstance(data, dict):
            logger.info(f"Response is a dict with keys: {list(data.keys())}")
        
        # Handle different response formats
        if isinstance(data, list):
            # API returned a list, take the first task
            if len(data) > 0:
                logger.info(f"Received list of {len(data)} tasks, using first task")
                return data[0]
            else:
                logger.warning("Received empty list from API")
                return None
        elif isinstance(data, dict):
            # API returned a single task object
            return data
        else:
            logger.error(f"Unexpected response format: {type(data)}")
            return None
    
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error: {e}")
        logger.info("Consider using --verify if this is a testing environment")
        return None
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401 or status_code == 403:
            logger.error(f"Authentication failed. Please check your API key. Status code: {status_code}")
            logger.error(f"Response details: {e.response.text}")
        elif status_code == 404:
            logger.warning(f"No tasks found for the specified filters. Status code: {status_code}")
        else:
            logger.error(f"HTTP Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from TII endpoint: {e}")
        return None


def transform_tii_to_task_format(tii_data: Dict[str, Any], provider_id: str = None) -> Dict[str, Any]:
    """
    Transform TII API data to the format required by the hotlabel-tasks service
    
    Args:
        tii_data (dict): Task data from TII API
        provider_id (str, optional): Provider ID to use for creating tasks
        
    Returns:
        dict: Transformed task data ready for submission to hotlabel-tasks service
    """
    if provider_id is None:
        provider_id = DEFAULT_PROVIDER_ID
    
    # Ensure tii_data is a dictionary
    if not isinstance(tii_data, dict):
        logger.error(f"Expected dict for tii_data, got {type(tii_data)}")
        raise ValueError(f"tii_data must be a dictionary, got {type(tii_data)}")
    
    # Debug: Log the actual TII response structure for the first task
    if not hasattr(transform_tii_to_task_format, '_logged_structure'):
        logger.info(f"TII Response structure: {list(tii_data.keys())}")
        logger.info(f"TII Response sample: {json.dumps(tii_data, indent=2)}")
        transform_tii_to_task_format._logged_structure = True
        
    # Extract the necessary information
    tii_id = tii_data.get("id", "")
    category = tii_data.get("category", "unknown")
    complexity = tii_data.get("complexity", 1)
    task_type = tii_data.get("type", "text")
    topic = tii_data.get("topic", "general")
    
    # Language detection - first check if language field exists in response
    language = "en"  # Default to English
    if "language" in tii_data:
        language = tii_data["language"]
        logger.info(f"Found language field in response: {language}")
    else:
        # Fallback to text-based language detection
        logger.info("No language field found in response, using text-based detection")
        question_text = ""
        if "task" in tii_data and "text" in tii_data["task"]:
            question_text = decode_unicode_escapes(tii_data["task"]["text"])
            # Simple language detection based on Arabic characters
            if any('\u0600' <= char <= '\u06FF' for char in question_text) or \
               any('\u0750' <= char <= '\u077F' for char in question_text) or \
               any('\u08A0' <= char <= '\u08FF' for char in question_text):
                language = "ar"
            else:
                language = "en"
    
    track_id = tii_data.get("track_id", "")
    
    # Get image URL if available
    image_url = None
    image_filename = None
    if "content" in tii_data and "image" in tii_data["content"] and "url" in tii_data["content"]["image"]:
        image_url = tii_data["content"]["image"]["url"]
        # Extract filename from URL
        if image_url:
            image_filename = image_url.split("/")[-1]
    
    # Get question text
    question = None
    if "task" in tii_data and "text" in tii_data["task"]:
        question = decode_unicode_escapes(tii_data["task"]["text"])
    
    # Get choices and transform them to the correct format
    options = []
    if "task" in tii_data and "choices" in tii_data["task"]:
        choices = tii_data["task"]["choices"]
        # Process choices to decode Unicode
        processed_choices = process_choices(choices)
        # Transform choices to simple array of strings
        if isinstance(processed_choices, list):
            for choice in processed_choices:
                if isinstance(choice, dict) and "value" in choice:
                    options.append(choice["value"])
                elif isinstance(choice, str):
                    options.append(choice)
    
    # Create the task data structure according to Hotlabel schema
    transformed_task = {
        "title": tii_id,
        "description": "",
        "provider_id": provider_id,
        "task_type": task_type,  # Use TII type as task_type
        "content": {
            "question": question or "What is shown in this image?",  # Ensure question is always present
            "image_url": image_url or "",  # Ensure image_url is always present
            "image_filename": image_filename or "",  # Add image filename
            "options": options  # Store options as array of strings in content
        },
        "language": language,
        "category": category,  # This field exists in Hotlabel
        "topic": topic,        # Always set topic
        "complexity_level": complexity,
        "time_estimate_seconds": 300,  # Default time estimate
        "tags": [],
        "golden_set": False,
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "status": "PENDING"
    }
    
    # Add TII metadata as additional fields (not in content)
    transformed_task["tii_id"] = tii_id
    transformed_task["tii_track_id"] = track_id
    transformed_task["tii_task_type"] = task_type
    transformed_task["tii_topic"] = topic
    
    return transformed_task


def submit_task_to_service(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a single transformed task to the hotlabel-tasks service
    
    Args:
        task (dict): Transformed task data
        
    Returns:
        dict: Response from the tasks service
    """
    try:
        logger.info(f"Submitting task to tasks service: {TASKS_BASE_URL}")
        
        # Make the POST request
        response = requests.post(TASKS_BASE_URL, json=task, headers=TASKS_HEADERS)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Log success
        logger.info(f"Successfully submitted task to service. Status code: {response.status_code}")
        
        # Parse and return JSON response
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error when submitting task: {e}")
        logger.error(f"Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting task to service: {e}")
        return {"error": str(e)}


def print_task_summary(tasks_fetched: List[Dict[str, Any]], tasks_created: List[Dict[str, Any]], unique_tasks_fetched: List[Dict[str, Any]], duplicate_count: int):
    """
    Print detailed summary of fetched and created tasks
    
    Args:
        tasks_fetched (list): List of all tasks fetched from TII (including duplicates)
        tasks_created (list): List of tasks successfully created in Hotlabel
        unique_tasks_fetched (list): List of unique tasks fetched from TII
        duplicate_count (int): Count of duplicate tasks encountered
    """
    print("\n" + "=" * 60)
    print("DETAILED TASK SUMMARY")
    print("=" * 60)
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"  Total API requests made: {len(tasks_fetched)}")
    print(f"  Total unique tasks fetched: {len(unique_tasks_fetched)}")
    print(f"  Total duplicates encountered: {duplicate_count}")
    print(f"  Duplicate rate: {(duplicate_count/len(tasks_fetched)*100):.1f}%" if tasks_fetched else "N/A")
    print(f"  Total tasks created in Hotlabel: {len(tasks_created)}")
    print(f"  Success rate (unique tasks): {(len(tasks_created)/len(unique_tasks_fetched)*100):.1f}%" if unique_tasks_fetched else "N/A")
    print(f"  Success rate (all requests): {(len(tasks_created)/len(tasks_fetched)*100):.1f}%" if tasks_fetched else "N/A")
    
    if not unique_tasks_fetched:
        print("\n❌ No unique tasks were fetched from TII API")
        print("=" * 60)
        return
    
    # Group by different criteria (use unique tasks for breakdowns)
    categories = {}
    types = {}
    languages = {}
    topics = {}
    complexities = {}
    
    for task in unique_tasks_fetched:
        # Category breakdown
        category = task.get("category", "unknown")
        categories[category] = categories.get(category, 0) + 1
        
        # Type breakdown
        task_type = task.get("type", "unknown")
        types[task_type] = types.get(task_type, 0) + 1
        
        # Language breakdown - use same detection logic as transform function
        language = "en"  # Default to English
        
        # First, try to get language from the response field (as per official docs)
        if "language" in task:
            language = task["language"]
        else:
            # Fallback to text-based language detection
            question_text = ""
            if "task" in task and "text" in task["task"]:
                question_text = decode_unicode_escapes(task["task"]["text"])
                
                # Simple language detection based on Arabic characters
                if any('\u0600' <= char <= '\u06FF' for char in question_text):
                    language = "ar"
                elif any('\u0750' <= char <= '\u077F' for char in question_text):  # Arabic Supplement
                    language = "ar"
                elif any('\u08A0' <= char <= '\u08FF' for char in question_text):  # Arabic Extended-A
                    language = "ar"
                else:
                    language = "en"  # Default to English for non-Arabic text
        
        languages[language] = languages.get(language, 0) + 1
        
        # Topic breakdown
        topic = task.get("topic", "unknown")
        topics[topic] = topics.get(topic, 0) + 1
        
        # Complexity breakdown
        complexity = task.get("complexity", "unknown")
        complexities[complexity] = complexities.get(complexity, 0) + 1
    
    # Print breakdowns
    print(f"\n📂 BREAKDOWN BY CATEGORY (Unique Tasks):")
    for category, count in sorted(categories.items()):
        percentage = (count / len(unique_tasks_fetched)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")
    
    print(f"\n🎯 BREAKDOWN BY TYPE (Unique Tasks):")
    for task_type, count in sorted(types.items()):
        percentage = (count / len(unique_tasks_fetched)) * 100
        print(f"  {task_type}: {count} ({percentage:.1f}%)")
    
    print(f"\n🌐 BREAKDOWN BY LANGUAGE (Unique Tasks):")
    for language, count in sorted(languages.items()):
        percentage = (count / len(unique_tasks_fetched)) * 100
        print(f"  {language}: {count} ({percentage:.1f}%)")
    
    print(f"\n📚 BREAKDOWN BY TOPIC (Unique Tasks):")
    for topic, count in sorted(topics.items()):
        percentage = (count / len(unique_tasks_fetched)) * 100
        print(f"  {topic}: {count} ({percentage:.1f}%)")
    
    print(f"\n⚡ BREAKDOWN BY COMPLEXITY (Unique Tasks):")
    for complexity, count in sorted(complexities.items()):
        percentage = (count / len(unique_tasks_fetched)) * 100
        complexity_desc = {
            1: "Very Easy",
            2: "Easy", 
            3: "Medium",
            4: "Hard"
        }.get(complexity, "Unknown")
        print(f"  Level {complexity} ({complexity_desc}): {count} ({percentage:.1f}%)")
    
    # Show sample task details
    print(f"\n🔍 SAMPLE TASK DETAILS:")
    if unique_tasks_fetched:
        sample_task = unique_tasks_fetched[0]
        print(f"  TII ID: {sample_task.get('id', 'unknown')}")
        print(f"  Category: {sample_task.get('category', 'unknown')}")
        print(f"  Type: {sample_task.get('type', 'unknown')}")
        
        # Show detected language
        sample_language = "en"
        if "language" in sample_task:
            sample_language = sample_task["language"]
        else:
            # Fallback to text-based detection
            if "task" in sample_task and "text" in sample_task["task"]:
                question_text = decode_unicode_escapes(sample_task["task"]["text"])
                if any('\u0600' <= char <= '\u06FF' for char in question_text):
                    sample_language = "ar"
                elif any('\u0750' <= char <= '\u077F' for char in question_text):
                    sample_language = "ar"
                elif any('\u08A0' <= char <= '\u08FF' for char in question_text):
                    sample_language = "ar"
        print(f"  Language (detected): {sample_language}")
        
        print(f"  Topic: {sample_task.get('topic', 'unknown')}")
        print(f"  Complexity: {sample_task.get('complexity', 'unknown')}")
        
        # Show question text if available
        if "task" in sample_task and "text" in sample_task["task"]:
            question = decode_unicode_escapes(sample_task["task"]["text"])
            if len(question) > 100:
                question = question[:100] + "..."
            print(f"  Question: {question}")
        
        # Show choices if available
        if "task" in sample_task and "choices" in sample_task["task"]:
            choices = sample_task["task"]["choices"]
            print(f"  Choices: {len(choices)} options")
            for choice in choices[:3]:  # Show first 3 choices
                print(f"    - {choice.get('key', '')}: {choice.get('value', '')}")
            if len(choices) > 3:
                print(f"    ... and {len(choices) - 3} more")
        
        # Show image info if available
        if "content" in sample_task and "image" in sample_task["content"]:
            print(f"  Has Image: Yes")
            if "url" in sample_task["content"]["image"]:
                print(f"  Image URL: {sample_task['content']['image']['url']}")
    
    # Show unique combinations
    print(f"\n🎲 UNIQUE COMBINATIONS:")
    unique_combinations = set()
    for task in unique_tasks_fetched:
        # Use same language detection logic
        language = "en"
        if "language" in task:
            language = task["language"]
        else:
            # Fallback to text-based detection
            if "task" in task and "text" in task["task"]:
                question_text = decode_unicode_escapes(task["task"]["text"])
                if any('\u0600' <= char <= '\u06FF' for char in question_text):
                    language = "ar"
                elif any('\u0750' <= char <= '\u077F' for char in question_text):
                    language = "ar"
                elif any('\u08A0' <= char <= '\u08FF' for char in question_text):
                    language = "ar"
        
        combo = f"{task.get('category', 'unknown')}-{task.get('type', 'unknown')}-{language}-{task.get('topic', 'unknown')}"
        unique_combinations.add(combo)
    
    print(f"  Total unique combinations: {len(unique_combinations)}")
    if len(unique_combinations) <= 10:
        for combo in sorted(unique_combinations):
            print(f"    - {combo}")
    else:
        print(f"  Showing first 10 combinations:")
        for combo in sorted(list(unique_combinations)[:10]):
            print(f"    - {combo}")
        print(f"    ... and {len(unique_combinations) - 10} more")
    
    # Show task creation status
    if tasks_created:
        print(f"\n✅ TASK CREATION STATUS:")
        print(f"  Successfully created: {len(tasks_created)} tasks")
        if len(tasks_created) != len(unique_tasks_fetched):
            failed_count = len(unique_tasks_fetched) - len(tasks_created)
            print(f"  Failed to create: {failed_count} tasks")
    else:
        print(f"\n⚠️  TASK CREATION STATUS:")
        print(f"  No tasks were created (dry run mode or errors)")
    
    print("\n" + "=" * 60)


def generate_filter_combinations(max_combinations: int = 50) -> List[Dict[str, Any]]:
    """
    Generate filter combinations for fetching diverse tasks
    
    Args:
        max_combinations (int): Maximum number of combinations to generate
        
    Returns:
        list: List of filter dictionaries
    """
    filters = []
    
    # Start with basic combinations
    basic_combinations = [
        # Single filter combinations
        {"category": "vqa"},
        {"task_type": "true-false"},
        {"task_type": "numeric"},
        {"task_type": "mcq"},
        {"language": "en"},
        {"language": "ar"},
        {"topic": "uae"},
        {"topic": "animals"},
        {"topic": "medical-field"},
        {"complexity": 1},
        {"complexity": 2},
        {"complexity": 3},
        {"complexity": 4},
        
        # Common combinations
        {"category": "vqa", "language": "en"},
        {"category": "vqa", "language": "ar"},
        {"task_type": "true-false", "language": "en"},
        {"task_type": "mcq", "language": "en"},
        {"topic": "uae", "language": "en"},
        {"topic": "uae", "language": "ar"},
        {"topic": "medical-field", "language": "en"},
        {"complexity": 1, "language": "en"},
        {"complexity": 2, "language": "en"},
        {"complexity": 3, "language": "en"},
        {"complexity": 4, "language": "en"},
    ]
    
    filters.extend(basic_combinations)
    
    # Add some random combinations if we haven't reached max
    if len(filters) < max_combinations:
        import random
        remaining_slots = max_combinations - len(filters)
        
        # Generate random combinations
        for _ in range(remaining_slots):
            filter_combo = {}
            
            # Randomly add filters
            if random.choice([True, False]):
                filter_combo["category"] = random.choice(TII_CATEGORIES)
            if random.choice([True, False]):
                filter_combo["task_type"] = random.choice(TII_TYPES)
            if random.choice([True, False]):
                filter_combo["language"] = random.choice(TII_LANGUAGES)
            if random.choice([True, False]):
                filter_combo["topic"] = random.choice(TII_TOPICS)
            if random.choice([True, False]):
                filter_combo["complexity"] = random.choice(TII_COMPLEXITY_LEVELS)
            
            # Only add if not empty and not already in list
            if filter_combo and filter_combo not in filters:
                filters.append(filter_combo)
    
    return filters[:max_combinations]


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Fetch random tasks from all TII categories and create them in Hotlabel")
    parser.add_argument('--api-key', 
                        help='API key for authenticating with the TII endpoint')
    parser.add_argument('--verify', action='store_true', 
                        help='Enable SSL certificate verification (disabled by default)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Only fetch and display tasks, do not submit to Hotlabel')
    parser.add_argument('--max-tasks', type=int, default=50,
                        help='Maximum number of tasks to fetch (default: 50)')
    parser.add_argument('--provider-id',
                        help='Provider ID to use when creating tasks')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between API requests in seconds (default: 1.0)')
    parser.add_argument('--language', choices=['en', 'ar'],
                        help='Filter tasks by language (en=English, ar=Arabic)')
    return parser.parse_args()


def main():
    """Main function to execute the script"""
    args = parse_arguments()
    logger.info("Starting TII all categories task pull script")
    
    # Use command line API key if provided, otherwise use the one defined in the file
    api_key = args.api_key if args.api_key else API_KEY
    
    # Determine SSL verification setting
    verify_ssl = args.verify
    
    # Set request delay
    global REQUEST_DELAY
    REQUEST_DELAY = args.delay
    
    # Generate filter combinations
    filter_combinations = generate_filter_combinations(args.max_tasks)
    
    # If language filter is specified, add it to all combinations
    if args.language:
        logger.info(f"Filtering tasks by language: {args.language}")
        for combo in filter_combinations:
            combo['language'] = args.language
    
    logger.info(f"Generated {len(filter_combinations)} filter combinations")
    
    tasks_fetched = []
    tasks_created = []
    unique_tasks_fetched = []  # Track unique tasks by TII ID
    seen_tii_ids = set()  # Track seen TII IDs to avoid duplicates
    duplicate_count = 0  # Count of duplicate tasks encountered
    
    # Fetch tasks for each filter combination
    for i, filters in enumerate(filter_combinations, 1):
        logger.info(f"Processing combination {i}/{len(filter_combinations)}: {filters}")
        
        # Build query parameters
        query_params = build_query_params(**filters)
        
        # Fetch task from TII
        tii_task = fetch_tii_task(api_key=api_key, query_params=query_params, verify_ssl=verify_ssl)
        
        if tii_task:
            tii_id = tii_task.get('id', 'unknown')
            tasks_fetched.append(tii_task)  # Keep all fetched tasks for debugging
            
            # Check if this is a unique task
            if tii_id not in seen_tii_ids:
                seen_tii_ids.add(tii_id)
                unique_tasks_fetched.append(tii_task)
                
                # Transform task
                provider_id = args.provider_id if args.provider_id else DEFAULT_PROVIDER_ID
                transformed_task = transform_tii_to_task_format(tii_task, provider_id)
                
                # Print task details
                print(f"\n--- Task {len(unique_tasks_fetched)} (Unique) ---")
                print(f"TII ID: {tii_id}")
                print(f"Category: {tii_task.get('category', 'unknown')}")
                print(f"Type: {tii_task.get('type', 'unknown')}")
                
                # Show detected language
                detected_language = "en"
                if "language" in tii_task:
                    detected_language = tii_task["language"]
                else:
                    # Fallback to text-based detection
                    if "task" in tii_task and "text" in tii_task["task"]:
                        question_text = tii_task["task"]["text"]
                        if any('\u0600' <= char <= '\u06FF' for char in question_text):
                            detected_language = "ar"
                        elif any('\u0750' <= char <= '\u077F' for char in question_text):
                            detected_language = "ar"
                        elif any('\u08A0' <= char <= '\u08FF' for char in question_text):
                            detected_language = "ar"
                
                print(f"Language: {detected_language}")
                print(f"Topic: {tii_task.get('topic', 'unknown')}")
                print(f"Complexity: {tii_task.get('complexity', 'unknown')}")
                
                # Submit to Hotlabel if not dry run
                if not args.dry_run:
                    response = submit_task_to_service(transformed_task)
                    if "error" not in response:
                        tasks_created.append(transformed_task)
                        print(f"✅ Task created successfully")
                    else:
                        print(f"❌ Failed to create task: {response.get('error', 'Unknown error')}")
                else:
                    print("🔍 Dry run mode - task not submitted")
            else:
                duplicate_count += 1
                print(f"\n--- Task {i} (Duplicate) ---")
                print(f"TII ID: {tii_id} (already seen)")
                print("⏭️  Skipping duplicate task")
        else:
            logger.warning(f"No task found for filters: {filters}")
        
        # Rate limiting delay
        if i < len(filter_combinations):
            time.sleep(REQUEST_DELAY)
    
    # Print summary with both raw and unique statistics
    print_task_summary(tasks_fetched, tasks_created, unique_tasks_fetched, duplicate_count)
    
    logger.info("TII all categories task pull completed")


if __name__ == "__main__":
    main() 