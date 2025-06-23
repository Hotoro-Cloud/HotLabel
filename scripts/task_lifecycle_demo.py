#!/usr/bin/env python3
"""
Task Lifecycle Demo

This script demonstrates the complete lifecycle of a task in the Hotlabel platform:
1. Use existing tasks from the database (created by pull_TII_all_categories script)
2. Multiple publishers register and receive API keys
3. Publishers receive auto-assigned tasks
4. Publishers submit results with different patterns
5. QA service validates results and calculates consensus
6. Final results are made available to providers
7. Test various consensus scenarios and edge cases
8. Track publisher sessions and their contributions
"""

import requests
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sys
import random
import os
import subprocess
from enum import Enum

# Configuration
KONG_URL = "http://localhost:8000"  # API Gateway URL
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
PROVIDERS_API_URL = f"{KONG_URL}/api/v1/providers"
PUBLISHERS_API_URL = f"{KONG_URL}/api/v1/publishers"
QA_API_URL = f"{KONG_URL}/api/v1/consensus"
SESSIONS_API_URL = f"{KONG_URL}/api/v1/sessions"

# Direct service URLs (if needed for endpoints not exposed through Kong)
TASKS_SERVICE_URL = "http://localhost:8002"
PUBLISHERS_SERVICE_URL = "http://localhost:8004"
QA_SERVICE_URL = "http://localhost:8003"
USERS_SERVICE_URL = "http://localhost:8005"

# QA Service endpoints
VALIDATION_URL = f"{QA_SERVICE_URL}/api/v1/validation"
METRICS_URL = f"{QA_SERVICE_URL}/api/v1/metrics"
QA_API_KEY = "test_api_key_qa_service"  # QA service API key

class TaskScenario(Enum):
    HIGH_AGREEMENT = "high_agreement"
    MEDIUM_AGREEMENT = "medium_agreement"
    LOW_AGREEMENT = "low_agreement"
    HIGH_CONFIDENCE = "high_confidence"
    MIXED_CONFIDENCE = "mixed_confidence"
    EDGE_CASE = "edge_case"
    VQA_LIVING_ROOM = "vqa_living_room"
    VQA_FASHION = "vqa_fashion"
    VQA_AMBIGUOUS = "vqa_ambiguous"

def print_header(title: str) -> None:
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def print_step(step: str) -> None:
    """Print a step in the process"""
    print(f"\n--- {step} ---")

def print_response(response: requests.Response, title: str) -> None:
    """Print API response in a readable format"""
    print(f"\n=== {title} ===")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(f"Raw response text: {response.text}")
    print("-" * 50)

class TaskLifecycle:
    """Class to manage the task lifecycle demonstration"""
    
    def __init__(self):
        self.task_ids = []  # List of task IDs for different scenarios
        self.publisher_ids = []
        self.publisher_api_keys = []
        self.sessions = {}  # Map publisher_id to list of session IDs
        self.session_data = {}  # Map session_id to session metadata
        self.scenario_results = {}  # Map task_id to scenario type
        
    def get_existing_tasks(self) -> List[Dict[str, Any]]:
        """Get existing tasks from the database"""
        print_step("STEP 1: Get existing tasks from database")
        
        # Get tasks from the tasks service
        response = requests.get(f"{TASKS_SERVICE_URL}/api/v1/tasks", headers={"X-API-Key": "internal-service"})
        print_response(response, "Get Existing Tasks")
        
        if response.status_code >= 300:
            print("ERROR: Failed to get existing tasks")
            sys.exit(1)
            
        tasks = response.json().get("items", [])
        print(f"Found {len(tasks)} existing tasks in the database")
        
        # Filter for pending tasks only
        pending_tasks = [task for task in tasks if task.get("status") == "PENDING"]
        print(f"Found {len(pending_tasks)} pending tasks available for assignment")
        
        # Select a subset of tasks for demonstration
        selected_tasks = pending_tasks[:5]  # Use first 5 pending tasks
        
        for task in selected_tasks:
            self.task_ids.append(task["id"])
            # Assign scenario based on task type
            if task.get("task_type") == "true-false":
                self.scenario_results[task["id"]] = TaskScenario.HIGH_AGREEMENT
            elif task.get("task_type") == "numeric":
                self.scenario_results[task["id"]] = TaskScenario.MEDIUM_AGREEMENT
            elif task.get("task_type") == "mcq":
                self.scenario_results[task["id"]] = TaskScenario.LOW_AGREEMENT
            else:
                self.scenario_results[task["id"]] = TaskScenario.HIGH_CONFIDENCE
        
        print(f"Selected {len(selected_tasks)} tasks for demonstration:")
        for task in selected_tasks:
            print(f"  - Task ID: {task['id']}, Type: {task.get('task_type')}, Category: {task.get('category')}")
        
        return selected_tasks

    def register_multiple_publishers(self, count: int = 12) -> List[Dict[str, Any]]:
        """Register multiple publishers"""
        print_step(f"STEP 2: Register {count} publishers")
        
        publishers = []
        for i in range(count):
            publisher_data = {
                "name": f"Demo Publisher {i+1}",
                "email": f"publisher_{i+1}_{uuid.uuid4().hex[:8]}@example.com",
                "website": f"https://example.com/publisher{i+1}",
                "description": f"Demo publisher {i+1} for task lifecycle testing"
            }
            
            response = requests.post(PUBLISHERS_API_URL, json=publisher_data)
            if response.status_code >= 300:
                print(f"ERROR: Failed to register publisher {i+1}")
                continue
                
            result = response.json()
            self.publisher_ids.append(result["id"])
            self.publisher_api_keys.append(result["api_key"])
            publishers.append(result)
            
            print(f"Publisher {i+1} registered: {result['id']}")
        
        print(f"Successfully registered {len(publishers)} publishers")
        return publishers

    def create_sessions_for_publishers(self, sessions_per_publisher: int = 2) -> Dict[str, List[str]]:
        """Create sessions for publishers"""
        print_step(f"STEP 3: Create {sessions_per_publisher} sessions per publisher")
        
        for i, publisher_id in enumerate(self.publisher_ids):
            publisher_sessions = []
            for j in range(sessions_per_publisher):
                session_data = {
                    "publisher_id": publisher_id,
                    "language": "en",
                    "consent_given": True,
                    "browser_fingerprint": f"fingerprint_{publisher_id}_{j}"
                }
                
                response = requests.post(f"{USERS_SERVICE_URL}/api/v1/sessions", json=session_data)
                if response.status_code >= 300:
                    print(f"ERROR: Failed to create session {j+1} for publisher {i+1}")
                    continue
                    
                session = response.json()
                session_id = session["id"]
                publisher_sessions.append(session_id)
                self.session_data[session_id] = session
                
                print(f"Created session {session_id} for publisher {publisher_id}")
            
            self.sessions[publisher_id] = publisher_sessions
        
        total_sessions = sum(len(sessions) for sessions in self.sessions.values())
        print(f"Created {total_sessions} sessions across {len(self.publisher_ids)} publishers")
        return self.sessions

    def get_assignments_for_task(self, task_id: str, headers: dict) -> List[Dict[str, Any]]:
        """Get task assignments for a specific task"""
        response = requests.get(f"{TASKS_API_URL}/{task_id}/assignments", headers=headers)
        if response.status_code == 200:
            return response.json().get("assignments", [])
        return []

    def generate_result_for_scenario(self, scenario: TaskScenario, publisher_index: int, submission_count: int = 0) -> Dict[str, Any]:
        """Generate a result based on the scenario"""
        if scenario == TaskScenario.HIGH_AGREEMENT:
            # High agreement scenario - most publishers choose the same answer
            if publisher_index < 8:  # 80% choose True
                return {"answer": "True", "confidence": random.uniform(0.8, 1.0)}
            else:  # 20% choose False
                return {"answer": "False", "confidence": random.uniform(0.6, 0.9)}
                
        elif scenario == TaskScenario.MEDIUM_AGREEMENT:
            # Medium agreement scenario - mixed responses
            if publisher_index < 6:  # 60% choose True
                return {"answer": "True", "confidence": random.uniform(0.7, 0.9)}
            else:  # 40% choose False
                return {"answer": "False", "confidence": random.uniform(0.7, 0.9)}
                
        elif scenario == TaskScenario.LOW_AGREEMENT:
            # Low agreement scenario - very mixed responses
            if publisher_index < 5:  # 50% choose True
                return {"answer": "True", "confidence": random.uniform(0.6, 0.8)}
            else:  # 50% choose False
                return {"answer": "False", "confidence": random.uniform(0.6, 0.8)}
                
        elif scenario == TaskScenario.HIGH_CONFIDENCE:
            # High confidence scenario - all high confidence but mixed answers
            if publisher_index % 2 == 0:
                return {"answer": "True", "confidence": random.uniform(0.9, 1.0)}
            else:
                return {"answer": "False", "confidence": random.uniform(0.9, 1.0)}
                
        elif scenario == TaskScenario.MIXED_CONFIDENCE:
            # Mixed confidence scenario
            if publisher_index < 4:
                return {"answer": "True", "confidence": random.uniform(0.9, 1.0)}
            elif publisher_index < 8:
                return {"answer": "True", "confidence": random.uniform(0.5, 0.7)}
            else:
                return {"answer": "False", "confidence": random.uniform(0.3, 0.6)}
                
        else:  # EDGE_CASE
            # Edge case scenario - very low confidence
            return {"answer": "True" if publisher_index % 2 == 0 else "False", "confidence": random.uniform(0.1, 0.3)}

    def submit_results_for_scenario(self, task_id: str, results_per_session: int = 1) -> List[Dict[str, Any]]:
        """Submit results for a specific task scenario"""
        print_step(f"Submitting results for task {task_id}")
        
        scenario = self.scenario_results.get(task_id, TaskScenario.HIGH_AGREEMENT)
        print(f"Using scenario: {scenario.value}")
        
        submitted_results = []
        publisher_index = 0
        
        for publisher_id, sessions in self.sessions.items():
            for session_id in sessions:
                for submission in range(results_per_session):
                    # Generate result based on scenario
                    result_data = self.generate_result_for_scenario(scenario, publisher_index, submission)
                    
                    # Submit result
                    submission_data = {
                        "task_id": task_id,
                        "session_id": session_id,
                        "answer": result_data["answer"],
                        "confidence": result_data["confidence"],
                        "time_spent_ms": random.randint(5000, 30000)
                    }
                    
                    headers = {"X-API-Key": self.publisher_api_keys[self.publisher_ids.index(publisher_id)]}
                    response = requests.post(f"{TASKS_API_URL}/{task_id}/submit", json=submission_data, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        submitted_results.append(result)
                        print(f"Submitted result for session {session_id}: {result_data['answer']} (confidence: {result_data['confidence']:.2f})")
                    else:
                        print(f"Failed to submit result for session {session_id}: {response.status_code}")
                
                publisher_index += 1
        
        print(f"Submitted {len(submitted_results)} results for task {task_id}")
        return submitted_results

    def check_consensus_status(self) -> Dict[str, Any]:
        """Check consensus status for all tasks"""
        print_step("STEP 4: Check consensus status for all tasks")
        
        consensus_results = {}
        for task_id in self.task_ids:
            response = requests.get(f"{TASKS_API_URL}/{task_id}")
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("status", "unknown")
                consensus_results[task_id] = {
                    "status": status,
                    "assignments_count": len(task_data.get("assignments", [])),
                    "results_count": len(task_data.get("results", [])),
                    "consensus_reached": status == "COMPLETED",
                    "final_answer": task_data.get("final_answer"),
                    "confidence": task_data.get("confidence"),
                    "agreement_rate": task_data.get("agreement_rate")
                }
                print(f"Task {task_id}: {status} (assignments: {consensus_results[task_id]['assignments_count']}, results: {consensus_results[task_id]['results_count']})")
        
        return consensus_results

    def check_publisher_contributions(self):
        """Check publisher contributions and statistics"""
        print_step("STEP 5: Check publisher contributions")
        
        for i, publisher_id in enumerate(self.publisher_ids):
            print(f"\nPublisher {i+1} ({publisher_id}):")
            
            # Get publisher details
            headers = {"X-API-Key": self.publisher_api_keys[i]}
            response = requests.get(f"{PUBLISHERS_API_URL}/{publisher_id}", headers=headers)
            
            if response.status_code == 200:
                publisher_data = response.json()
                print(f"  Name: {publisher_data.get('name')}")
                print(f"  Email: {publisher_data.get('email')}")
                print(f"  Sessions: {len(self.sessions.get(publisher_id, []))}")
                
                # Check session statistics
                for session_id in self.sessions.get(publisher_id, []):
                    session_response = requests.get(f"{USERS_SERVICE_URL}/api/v1/sessions/{session_id}/stats")
                    if session_response.status_code == 200:
                        session_stats = session_response.json()
                        print(f"    Session {session_id}: {session_stats.get('tasks_completed', 0)} tasks completed")
            else:
                print(f"  Failed to get publisher details: {response.status_code}")

def main():
    """Main function to run the task lifecycle demonstration"""
    print_header("HOTLABEL TASK LIFECYCLE DEMONSTRATION")
    print("This demo uses existing tasks from the database (created by pull_TII_all_categories.py)")
    
    # Initialize the task lifecycle
    lifecycle = TaskLifecycle()
    
    try:
        # Step 1: Get existing tasks from database
        existing_tasks = lifecycle.get_existing_tasks()
        if not existing_tasks:
            print("ERROR: No existing tasks found in database. Please run pull_TII_all_categories.py first.")
            sys.exit(1)
        
        # Step 2: Register publishers
        publishers = lifecycle.register_multiple_publishers(count=8)
        if not publishers:
            print("ERROR: Failed to register publishers")
            sys.exit(1)
        
        # Step 3: Create sessions for publishers
        sessions = lifecycle.create_sessions_for_publishers(sessions_per_publisher=2)
        if not sessions:
            print("ERROR: Failed to create sessions")
            sys.exit(1)
        
        # Step 4: Submit results for each task
        for task_id in lifecycle.task_ids:
            lifecycle.submit_results_for_scenario(task_id, results_per_session=1)
            time.sleep(2)  # Small delay between tasks
        
        # Step 5: Check consensus status
        consensus_results = lifecycle.check_consensus_status()
        
        # Step 6: Check publisher contributions
        lifecycle.check_publisher_contributions()
        
        # Summary
        print_header("DEMONSTRATION SUMMARY")
        print(f"Tasks used: {len(lifecycle.task_ids)}")
        print(f"Publishers registered: {len(lifecycle.publisher_ids)}")
        print(f"Total sessions created: {sum(len(sessions) for sessions in lifecycle.sessions.values())}")
        
        completed_tasks = sum(1 for result in consensus_results.values() if result.get("consensus_reached"))
        print(f"Tasks with consensus reached: {completed_tasks}/{len(lifecycle.task_ids)}")
        
        print("\nDemonstration completed successfully!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 