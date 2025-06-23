#!/usr/bin/env python3
"""
Quick Consensus Test

This script quickly tests consensus calculation to verify it's working correctly.
"""

import requests
import uuid
import json
import time
from typing import Dict, Any, List

# Configuration
KONG_URL = "http://localhost:8000"
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
PUBLISHERS_API_URL = f"{KONG_URL}/api/v1/publishers"
USERS_SERVICE_URL = "http://localhost:8005"

def print_step(step: str) -> None:
    """Print a step in the process"""
    print(f"\n--- {step} ---")

def test_consensus():
    """Quick test of consensus calculation"""
    print("=== QUICK CONSENSUS TEST ===")
    
    # Step 1: Get a few tasks
    print_step("STEP 1: Get available tasks")
    response = requests.get(f"http://localhost:8002/api/v1/tasks", headers={"X-Internal-Service": "true"})
    if response.status_code != 200:
        print(f"ERROR: Failed to get tasks: {response.status_code}")
        return
    
    tasks = response.json().get("items", [])
    if not tasks:
        print("ERROR: No tasks found")
        return
    
    # Select 2 tasks for testing
    test_tasks = tasks[:2]
    print(f"Selected {len(test_tasks)} tasks for testing")
    
    # Step 2: Register 1 publisher
    print_step("STEP 2: Register publisher")
    publisher_data = {
        "name": "Quick Test Publisher",
        "email": f"quick_test_{uuid.uuid4().hex[:8]}@example.com",
        "website": "https://example.com/quicktest",
        "description": "Quick consensus test publisher"
    }
    
    response = requests.post(PUBLISHERS_API_URL, json=publisher_data)
    if response.status_code not in [200, 201]:
        print(f"ERROR: Failed to register publisher: {response.status_code}")
        return
    
    publisher = response.json()
    publisher_id = publisher["id"]
    api_key = publisher["api_key"]
    print(f"Registered publisher: {publisher_id}")
    
    # Step 3: Create 1 session
    print_step("STEP 3: Create session")
    session_data = {
        "publisher_id": publisher_id,
        "language": "en",
        "consent_given": True,
        "browser_fingerprint": f"quick_test_{publisher_id}"
    }
    
    response = requests.post(f"{USERS_SERVICE_URL}/api/v1/sessions", json=session_data)
    if response.status_code not in [200, 201]:
        print(f"ERROR: Failed to create session: {response.status_code}")
        return
    
    session = response.json()
    session_id = session["id"]
    print(f"Created session: {session_id}")
    
    # Step 4: Submit results for each task
    print_step("STEP 4: Submit results")
    
    for i, task in enumerate(test_tasks):
        task_id = task["id"]
        task_type = task.get("task_type", "unknown")
        
        print(f"\nTesting task {task_id} ({task_type})")
        
        # Get task options
        content = task.get("content", {})
        options = content.get("options", [])
        if not options:
            if task_type == "true-false":
                options = ["True", "False"]
            else:
                options = ["option1", "option2"]
        
        print(f"Available options: {options}")
        
        # Submit 10 results with high agreement (80% choose first option)
        submitted_results = []
        for j in range(10):
            # 80% choose first option, 20% choose others
            if j < 8:
                answer = options[0]
                confidence = 0.9  # High confidence
            else:
                answer = options[1] if len(options) > 1 else options[0]
                confidence = 0.8  # High confidence
            
            submission_data = {
                "publisher_id": publisher_id,
                "session_id": session_id,
                "result": {
                    "label": answer,
                    "time_spent_ms": 15000
                },
                "confidence": confidence,
                "result_metadata": {
                    "test": "quick_consensus",
                    "submission": j
                }
            }
            
            headers = {"X-API-Key": api_key}
            response = requests.post(f"{TASKS_API_URL}/{task_id}/result", json=submission_data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                submitted_results.append(result)
                print(f"  Submission {j+1}: {answer} (confidence: {confidence:.1f})")
            else:
                print(f"  Failed submission {j+1}: {response.status_code}")
            
            time.sleep(0.2)  # Small delay
        
        print(f"Submitted {len(submitted_results)} results")
        
        # Wait for consensus calculation
        print("Waiting for consensus calculation...")
        time.sleep(5)
        
        # Check consensus status
        response = requests.get(f"{TASKS_API_URL}/{task_id}")
        if response.status_code == 200:
            task_data = response.json()
            status = task_data.get("status", "unknown")
            consensus_status = task_data.get("consensus_status", "unknown")
            consensus_data = task_data.get("consensus_data", {})
            
            print(f"Task Status: {status}")
            print(f"Consensus Status: {consensus_status}")
            
            if consensus_data:
                agreement_score = consensus_data.get("agreement_score", 0)
                confidence_scores = consensus_data.get("confidence_scores", [])
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
                current_consensus = consensus_data.get("current_consensus", {})
                
                print(f"Agreement Score: {agreement_score:.3f}")
                print(f"Average Confidence: {avg_confidence:.3f}")
                print(f"Current Consensus: {current_consensus}")
                
                # Check if consensus should be reached
                agreement_threshold = task_data.get("agreement_threshold", 0.75)
                confidence_threshold = task_data.get("confidence_threshold", 0.6)
                
                if agreement_score >= agreement_threshold and avg_confidence >= confidence_threshold:
                    print("✅ CONSENSUS SHOULD BE REACHED!")
                else:
                    print("❌ CONSENSUS NOT REACHED")
                    print(f"  Agreement: {agreement_score:.3f} >= {agreement_threshold:.3f} = {agreement_score >= agreement_threshold}")
                    print(f"  Confidence: {avg_confidence:.3f} >= {confidence_threshold:.3f} = {avg_confidence >= confidence_threshold}")
            else:
                print("No consensus data available")
        else:
            print(f"Failed to get task status: {response.status_code}")
    
    print("\n=== QUICK CONSENSUS TEST COMPLETED ===")

if __name__ == "__main__":
    test_consensus() 