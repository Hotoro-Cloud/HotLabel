#!/usr/bin/env python3
import requests
import json
import uuid
from datetime import datetime, timedelta
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use Kong API Gateway for all service URLs
KONG_URL = "http://localhost:8000"
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
PROVIDERS_API_URL = f"{KONG_URL}/api/v1/providers"
PUBLISHERS_API_URL = f"{KONG_URL}/api/v1/publishers"
QA_API_URL = f"{KONG_URL}/api/v1/consensus"
SESSIONS_API_URL = f"{KONG_URL}/api/v1/sessions"

def register_provider():
    """Register a new provider and return their API key."""
    data = {
        "name": "Demo Provider",
        "description": "A demo provider for quick demo",
        "contact_email": f"provider_{uuid.uuid4()}@example.com",
        "website": "https://example.com"
    }
    response = requests.post(PROVIDERS_API_URL, json=data)
    response.raise_for_status()
    provider = response.json()
    logger.info(f"Registered provider: {provider['id']}")
    return provider

def register_publisher():
    """Register a new publisher and return their API key."""
    data = {
        "name": "Demo Publisher",
        "description": "A demo publisher for quick demo",
        "email": f"publisher_{uuid.uuid4()}@example.com",
        "website": "https://example.com"
    }
    response = requests.post(PUBLISHERS_API_URL, json=data)
    response.raise_for_status()
    publisher = response.json()
    logger.info(f"Registered publisher: {publisher['id']}")
    return publisher

def create_session(publisher_id, api_key):
    """Create a new session for the publisher."""
    data = {
        "publisher_id": publisher_id,
        "start_time": datetime.utcnow().isoformat(),
        "metadata": {
            "source": "quick_demo",
            "device": "desktop"
        }
    }
    headers = {"X-API-Key": api_key}
    response = requests.post(SESSIONS_API_URL, json=data, headers=headers)
    response.raise_for_status()
    session = response.json()
    logger.info(f"Created session: {session['id']}")
    return session

def create_task(provider_id, api_key):
    """Create a simple text classification task."""
    data = {
        "title": "Demo Task",
        "description": "A demo task for quick demo",
        "provider_id": provider_id,
        "task_type": "text_classification",
        "content": {
            "text": "This is a test task for quick demo",
            "labels": ["positive", "negative", "neutral"]
        },
        "language": "en",
        "category": "demo",
        "complexity_level": 2,
        "tags": ["demo", "classification"],
        "options": {"demo_option": True},
        "time_estimate_seconds": 120,
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "agreement_threshold": 0.8,  # 80% agreement required
        "confidence_threshold": 0.7   # 70% confidence required
    }
    headers = {"X-API-Key": api_key}
    response = requests.post(TASKS_API_URL, json=data, headers=headers)
    response.raise_for_status()
    task = response.json()
    logger.info(f"Created task: {task['id']}")
    return task

def get_available_tasks(publisher_id, api_key):
    """Get available tasks for the publisher."""
    headers = {"X-API-Key": api_key}
    time.sleep(2)  # Pause to allow task assignment to complete
    response = requests.get(
        f"{PUBLISHERS_API_URL}/{publisher_id}/tasks",
        headers=headers
    )
    response.raise_for_status()
    tasks = response.json()
    logger.info(f"Retrieved {len(tasks)} available tasks")
    return tasks

def submit_task_result(publisher_id, task_id, session_id, api_key):
    """Submit a result for the task."""
    data = {
        "publisher_id": publisher_id,
        "session_id": session_id,
        "result": {
            "label": "positive",
            "confidence": 0.5,
            "time_spent_ms": 5000
        },
        "confidence": 0.5,
        "labels": ["positive"],
        "result_metadata": {
            "source": "quick_demo",
            "time_spent_ms": 5000
        },
        "quality_score": 0.6
    }
    headers = {"X-API-Key": api_key}
    response = requests.post(
        f"{TASKS_API_URL}/{task_id}/result",
        json=data,
        headers=headers
    )
    response.raise_for_status()
    result = response.json()
    logger.info(f"Submitted result for task {task_id}")
    return result

def update_task_status(publisher_id, task_id, status, api_key):
    """Update the status of a task through the tasks service."""
    data = {
        "status": status,
        "result": {
            "label": "positive",
            "confidence": 0.95
        },
        "quality_score": 0.9
    }
    headers = {"X-API-Key": api_key}
    try:
        # Update task status through the tasks service
        response = requests.post(
            f"{TASKS_API_URL}/{task_id}/status",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Updated task {task_id} status to {status}")
        return result
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to update task status: {str(e)}")
        raise

def get_task_status(task_id, api_key):
    """Get the current status of a task from the tasks service."""
    headers = {"X-API-Key": api_key}
    try:
        response = requests.get(
            f"{TASKS_API_URL}/{task_id}",
            headers=headers
        )
        response.raise_for_status()
        task = response.json()
        logger.info(f"Current task status: {task.get('status')}")
        return task
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise

def check_consensus(task_id, provider_api_key):
    """Check the consensus status for a task with retry logic."""
    headers = {"X-API-Key": provider_api_key}
    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        response = requests.get(
            f"{QA_API_URL}/{task_id}",
            headers=headers
        )
        if response.status_code == 404:
            logger.warning(f"No consensus yet for task {task_id} (404 Not Found). Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue
        response.raise_for_status()
        consensus = response.json()
        logger.info(f"Consensus status for task {task_id}:")
        logger.info(json.dumps(consensus, indent=2))
        return consensus

    logger.error(f"Failed to retrieve consensus for task {task_id} after {max_retries} attempts.")
    return None

def check_publisher_statistics(publisher_id, api_key):
    """Check publisher statistics."""
    logger.info(f"\nChecking statistics for Publisher {publisher_id}")
    
    # Get publisher statistics
    headers = {"X-API-Key": api_key}
    response = requests.get(
        f"{PUBLISHERS_API_URL}/{publisher_id}/statistics",
        headers=headers
    )
    response.raise_for_status()
    stats = response.json()
    
    # Print statistics
    logger.info("\nPublisher Statistics:")
    logger.info(json.dumps(stats, indent=2))
    
    # Get recent tasks
    response = requests.get(
        f"{PUBLISHERS_API_URL}/{publisher_id}/tasks",
        headers=headers,
        params={"task_status": "completed", "limit": 5}  # Get last 5 completed tasks
    )
    response.raise_for_status()
    tasks = response.json()
    
    # Print recent task details
    logger.info(f"\nRecent completed tasks ({len(tasks)}):")
    for task in tasks:
        logger.info(f"\nTask {task['id']}:")
        logger.info(f"Status: {task.get('status', 'N/A')}")
        logger.info(f"Result: {task.get('result', 'N/A')}")
        logger.info(f"Confidence: {task.get('confidence', 'N/A')}")
        logger.info(f"Labels: {task.get('labels', 'N/A')}")
        logger.info(f"Quality Score: {task.get('quality_score', 'N/A')}")
    
    return stats

def main():
    try:
        # Step 1: Register a provider
        provider = register_provider()
        provider_id = provider["id"]
        provider_api_key = provider["api_key"]
        
        # Step 2: Register a publisher
        publisher = register_publisher()
        publisher_id = publisher["id"]
        publisher_api_key = publisher["api_key"]
        
        # Step 3: Create a session for the publisher
        session = create_session(publisher_id, publisher_api_key)
        session_id = session["id"]
        
        # Step 4: Create a task
        task = create_task(provider_id, provider_api_key)
        task_id = task["id"]
        
        # Step 5: Get available tasks for the publisher
        available_tasks = get_available_tasks(publisher_id, publisher_api_key)
        
        # Step 6: Submit task result
        result = submit_task_result(publisher_id, task_id, session_id, publisher_api_key)
        
        # Step 8: Get current task status
        current_task = get_task_status(task_id, publisher_api_key)
        
        # Step 9: Check consensus status
        consensus = check_consensus(task_id, provider_api_key)
        
        # Step 10: Check publisher statistics
        stats = check_publisher_statistics(publisher_id, publisher_api_key)
        
        logger.info("Quick demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in quick demo: {str(e)}")
        raise

if __name__ == "__main__":
    main() 