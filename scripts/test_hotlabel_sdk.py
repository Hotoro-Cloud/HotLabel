#!/usr/bin/env python3
"""
Test script to verify HotLabel SDK functionality
"""

import requests
import json
from datetime import datetime

# Configuration
KONG_URL = "http://localhost:8000"
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
SESSIONS_API_URL = f"{KONG_URL}/api/v1/sessions"

# Sample site publisher credentials
PUBLISHER_ID = "89b03a6d-614f-4775-81c8-e6bef9543024"
PUBLISHER_API_KEY = "pk_irO3iU11g4GSLMK1HYVCJ9ovTpSw7mBSy-W1Rw7EOOE"

def test_hotlabel_sdk_flow():
    """Test the complete HotLabel SDK flow"""
    
    print("=== Testing HotLabel SDK Flow ===")
    
    # Step 1: Get available tasks
    print("\n1. Getting available tasks...")
    response = requests.get(
        f"{TASKS_API_URL}/available?publisher_id={PUBLISHER_ID}",
        headers={"X-API-Key": PUBLISHER_API_KEY}
    )
    
    if response.status_code != 200:
        print(f"Failed to get tasks: {response.status_code}")
        return
    
    tasks = response.json()
    print(f"Found {tasks['total']} available tasks")
    
    if tasks['total'] == 0:
        print("No tasks available")
        return
    
    # Get the first assigned task
    assigned_tasks = [t for t in tasks['items'] if t['status'] == 'assigned']
    if not assigned_tasks:
        print("No assigned tasks found")
        return
    
    task = assigned_tasks[0]
    task_id = task['id']
    print(f"Using task: {task_id} - {task['title']}")
    
    # Step 2: Create a session (like the SDK does)
    print("\n2. Creating session...")
    session_data = {
        "publisher_id": PUBLISHER_ID,
        "browser_fingerprint": "test_fingerprint_123",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "language": "en",
        "timezone": "UTC",
        "referrer": "http://localhost:5001/",
        "device_type": "desktop",
        "platform": "Windows",
        "session_metadata": {
            "screen_width": 1920,
            "screen_height": 1080,
            "color_depth": 24,
            "pixel_ratio": 1
        }
    }
    
    session_response = requests.post(
        f"{SESSIONS_API_URL}",
        json=session_data,
        headers={"X-API-Key": PUBLISHER_API_KEY}
    )
    
    if session_response.status_code not in [200, 201]:
        print(f"Failed to create session: {session_response.status_code}")
        print(f"Response: {session_response.text}")
        return
    
    session = session_response.json()
    session_id = session['id']
    print(f"Created session: {session_id}")
    
    # Step 3: Submit a task result (like the SDK does when option is clicked)
    print("\n3. Submitting task result...")
    
    # Simulate the exact payload the SDK sends
    result_data = {
        "publisher_id": PUBLISHER_ID,
        "session_id": session_id,
        "result": {
            "label": "Yes",
            "confidence": 0.8,
            "time_spent_ms": 5000,
            "labels": ["Yes"]
        },
        "confidence": 0.8,
        "labels": ["Yes"],
        "result_metadata": {
            "time_spent_ms": 5000,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "sdk_test"
        }
    }
    
    print(f"Submitting result payload: {json.dumps(result_data, indent=2)}")
    
    result_response = requests.post(
        f"{TASKS_API_URL}/{task_id}/result",
        json=result_data,
        headers={"X-API-Key": PUBLISHER_API_KEY}
    )
    
    print(f"Result submission status: {result_response.status_code}")
    if result_response.status_code == 200:
        result = result_response.json()
        print(f"Result submitted successfully: {result.get('id')}")
        print(f"Result details: {json.dumps(result, indent=2)}")
    else:
        print(f"Failed to submit result: {result_response.text}")
        return
    
    # Step 4: Check task status after submission
    print("\n4. Checking task status...")
    task_response = requests.get(
        f"{TASKS_API_URL}/{task_id}",
        headers={"X-API-Key": PUBLISHER_API_KEY}
    )
    
    if task_response.status_code == 200:
        task_data = task_response.json()
        print(f"Task status: {task_data.get('status')}")
        print(f"Consensus status: {task_data.get('consensus_status')}")
        
        consensus_data = task_data.get('consensus_data', {})
        if consensus_data:
            print(f"Total submissions: {consensus_data.get('total_submissions')}")
            print(f"Current consensus: {consensus_data.get('current_consensus')}")
        else:
            print("No consensus data available")
    
    # Step 5: Check results
    print("\n5. Checking task results...")
    results_response = requests.get(
        f"{TASKS_API_URL}/{task_id}/results",
        headers={"X-API-Key": PUBLISHER_API_KEY}
    )
    
    if results_response.status_code == 200:
        results = results_response.json()
        print(f"Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"  Result {i+1}: {result.get('result')} (confidence: {result.get('confidence')})")
            print(f"    Session ID: {result.get('session_id')}")
            print(f"    Publisher ID: {result.get('publisher_id')}")

if __name__ == "__main__":
    test_hotlabel_sdk_flow() 