#!/usr/bin/env python3
"""
Task Lifecycle Demo

This script demonstrates the complete lifecycle of a task in the Hotlabel platform:
1. Provider registers and receives API key
2. Provider creates multiple tasks with different configurations
3. Multiple publishers register and receive API keys
4. Publishers receive auto-assigned tasks
5. Publishers submit results with different patterns
6. QA service validates results and calculates consensus
7. Final results are made available to providers
8. Test various consensus scenarios and edge cases
9. Track publisher sessions and their contributions
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
        self.provider_id = None
        self.provider_api_key = None
        self.task_ids = []  # List of task IDs for different scenarios
        self.publisher_ids = []
        self.publisher_api_keys = []
        self.sessions = {}  # Map publisher_id to list of session IDs
        self.session_data = {}  # Map session_id to session metadata
        self.scenario_results = {}  # Map task_id to scenario type
        
    def register_provider(self) -> Dict[str, Any]:
        """Register a new provider"""
        print_step("STEP 1: Register a provider")
        
        provider_data = {
            "name": "Demo Provider",
            "contact_email": f"provider_{uuid.uuid4().hex[:8]}@example.com",
            "description": "A demo provider for task lifecycle testing",
            "website": "https://example.com/provider"
        }
        
        response = requests.post(PROVIDERS_API_URL, json=provider_data)
        print_response(response, "Provider Registration")
        
        if response.status_code >= 300:
            print("ERROR: Failed to register provider")
            sys.exit(1)
            
        result = response.json()
        self.provider_id = result["id"]
        self.provider_api_key = result["api_key"]
        
        print(f"Provider registered successfully!")
        print(f"Provider ID: {self.provider_id}")
        print(f"Provider API Key: {self.provider_api_key}")
        
        return result

    def create_task_for_scenario(self, scenario: TaskScenario) -> Dict[str, Any]:
        """Create a task with configuration based on the scenario"""
        print_step(f"Creating task for scenario: {scenario.value}")
        
        # Base task configuration
        task_data = {
            "title": f"Demo Task - {scenario.value}",
            "description": f"A demo task for testing {scenario.value} scenario",
            "provider_id": self.provider_id,
            "task_type": "text_classification",
            "content": {
                "text": "This is a sample text for classification",
                "labels": ["positive", "negative", "neutral"]
            },
            "language": "en",
            "category": "demo",
            "complexity_level": 2,
            "tags": ["demo", "classification", "consensus", scenario.value],
            "options": {"demo_option": True},
            "time_estimate_seconds": 120,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "pending",
        }

        # Configure consensus parameters based on scenario
        if scenario == TaskScenario.HIGH_AGREEMENT:
            task_data.update({
                "agreement_threshold": 0.7,  # 70% agreement required
                "confidence_threshold": 0.6,  # 60% confidence required
            })
        elif scenario == TaskScenario.MEDIUM_AGREEMENT:
            task_data.update({
                "agreement_threshold": 0.5,  # 50% agreement required
                "confidence_threshold": 0.6,  # 60% confidence required
            })
        elif scenario == TaskScenario.LOW_AGREEMENT:
            task_data.update({
                "agreement_threshold": 0.3,  # 30% agreement required
                "confidence_threshold": 0.6,  # 60% confidence required
            })
        elif scenario == TaskScenario.HIGH_CONFIDENCE:
            task_data.update({
                "agreement_threshold": 0.5,  # 50% agreement required
                "confidence_threshold": 0.8,  # 80% confidence required
            })
        elif scenario == TaskScenario.MIXED_CONFIDENCE:
            task_data.update({
                "agreement_threshold": 0.5,  # 50% agreement required
                "confidence_threshold": 0.6,  # 60% confidence required
            })
        elif scenario == TaskScenario.EDGE_CASE:
            task_data.update({
                "agreement_threshold": 0.5,  # 50% agreement required
                "confidence_threshold": 0.6,  # 60% confidence required
            })

        # Add consensus data structure
        task_data["consensus_data"] = {
            "total_submissions": 0,
            "agreement_count": 0,
            "confidence_scores": [],
            "current_consensus": None
        }
        
        print("Task Creation Payload:")
        print(json.dumps(task_data, indent=2))
        
        headers = {"X-API-Key": self.provider_api_key}
        response = requests.post(TASKS_API_URL, json=task_data, headers=headers)
        print_response(response, f"Task Creation for {scenario.value}")
        
        if response.status_code >= 300:
            print(f"ERROR: Failed to create task for {scenario.value}")
            return None
            
        result = response.json()
        task_id = str(result["id"])
        self.task_ids.append(task_id)
        self.scenario_results[task_id] = scenario
        
        print(f"Task created successfully for {scenario.value}!")
        print(f"Task ID: {task_id}")
        
        return result

    def create_tasks_for_all_scenarios(self) -> List[Dict[str, Any]]:
        """Create tasks for all scenarios"""
        print_step("STEP 2: Creating tasks for all scenarios")
        tasks = []
        for scenario in TaskScenario:
            task = self.create_task_for_scenario(scenario)
            if task:
                tasks.append(task)
        return tasks

    def register_multiple_publishers(self, count: int = 12) -> List[Dict[str, Any]]:
        """Register multiple publishers for consensus testing"""
        print_step(f"STEP 3: Register {count} publishers for consensus testing")
        
        publishers = []
        for i in range(count):
            publisher_data = {
                "name": f"Demo Publisher {i+1}",
                "email": f"publisher_{uuid.uuid4().hex[:8]}@example.com",
                "description": f"A demo publisher {i+1} for consensus testing",
                "website": f"https://example.com/publisher{i+1}"
            }
            
            response = requests.post(PUBLISHERS_API_URL, json=publisher_data)
            print_response(response, f"Publisher {i+1} Registration")
            
            if response.status_code >= 300:
                print(f"ERROR: Failed to register publisher {i+1}")
                continue
                
            result = response.json()
            self.publisher_ids.append(result["id"])
            self.publisher_api_keys.append(result["api_key"])
            publishers.append(result)
            
            print(f"Publisher {i+1} registered successfully!")
            print(f"Publisher ID: {result['id']}")
            print(f"Publisher API Key: {result['api_key']}")
        
        return publishers

    def create_sessions_for_publishers(self, sessions_per_publisher: int = 2) -> Dict[str, List[str]]:
        """Create multiple sessions for each publisher."""
        print_step("STEP 4: Create multiple sessions for publishers")
        for publisher_id in self.publisher_ids:
            self.sessions[publisher_id] = []
            for i in range(sessions_per_publisher):
                session_data = {
                    "publisher_id": publisher_id,
                    "device_info": {
                        "platform": "web",
                        "browser": "chrome",
                        "version": "120.0.0"
                    },
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0 (Demo Browser)"
                }
                response = requests.post(SESSIONS_API_URL, json=session_data)
                print_response(response, f"Session Creation for Publisher {publisher_id} - Session {i+1}")
                if response.status_code >= 300:
                    print(f"ERROR: Failed to create session for publisher {publisher_id} - Session {i+1}")
                    continue
                result = response.json()
                self.sessions[publisher_id].append(result["id"])
                # Store session metadata
                self.session_data[result["id"]] = {
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }
                print(f"Session created successfully for Publisher {publisher_id} - Session {i+1}!")
                print(f"Session ID: {result['id']}")
        return self.sessions

    def get_assignments_for_task(self, task_id: str, headers: dict) -> List[Dict[str, Any]]:
        """Get all assignments for a task"""
        response = requests.get(
            f"{TASKS_API_URL}/{task_id}/assignments",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return []

    def generate_result_for_scenario(self, scenario: TaskScenario, publisher_index: int) -> Dict[str, Any]:
        """Generate a result based on the scenario"""
        if scenario == TaskScenario.HIGH_AGREEMENT:
            # All publishers submit the same label with high confidence
            label = "positive"
            confidence = random.uniform(0.85, 0.95)
        elif scenario == TaskScenario.MEDIUM_AGREEMENT:
            # 70% of publishers submit the same label
            label = "positive" if publisher_index < 8 else "negative"
            confidence = random.uniform(0.7, 0.9)
        elif scenario == TaskScenario.LOW_AGREEMENT:
            # Random labels with medium confidence
            label = random.choice(["positive", "negative", "neutral"])
            confidence = random.uniform(0.6, 0.8)
        elif scenario == TaskScenario.HIGH_CONFIDENCE:
            # All publishers submit with high confidence
            label = random.choice(["positive", "negative", "neutral"])
            confidence = random.uniform(0.9, 0.95)
        elif scenario == TaskScenario.MIXED_CONFIDENCE:
            # Mixed confidence levels
            label = "positive" if publisher_index < 6 else "negative"
            confidence = random.uniform(0.6, 0.95)
        else:  # EDGE_CASE
            # Edge cases: very low confidence, invalid labels, etc.
            if publisher_index % 3 == 0:
                label = "invalid_label"
                confidence = 0.3
            else:
                label = "positive"
                confidence = random.uniform(0.6, 0.8)

        return {
            "label": label,
            "confidence": confidence,
            "time_spent_ms": random.randint(3000, 10000)
        }

    def submit_results_for_scenario(self, task_id: str, results_per_session: int = 1) -> List[Dict[str, Any]]:
        """Submit results for a specific task based on its scenario"""
        print_step(f"STEP 5: Submitting results for task {task_id} ({self.scenario_results[task_id].value})")
        results = []
        scenario = self.scenario_results[task_id]

        for publisher_index, (publisher_id, api_key) in enumerate(zip(self.publisher_ids, self.publisher_api_keys)):
            for session_id in self.sessions[publisher_id]:
                for i in range(results_per_session):
                    headers = {
                        "X-API-Key": api_key,
                        "Content-Type": "application/json"
                    }

                    result_data = self.generate_result_for_scenario(scenario, publisher_index)
                    
                    result_payload = {
                        "publisher_id": str(publisher_id),
                        "result": result_data,
                        "session_id": str(session_id),
                        "quality_score": float(result_data["confidence"]),
                        "result_metadata": {
                            "source": "demo_script",
                            "time_spent_ms": result_data["time_spent_ms"]
                        },
                        "confidence": float(result_data["confidence"]),
                        "labels": [result_data["label"]]
                    }

                    print(f"\nSubmitting result for publisher {publisher_id} - Session {session_id} - Result {i+1}:")
                    print("Request URL:", f"{TASKS_API_URL}/{task_id}/result")
                    print("Headers:", headers)
                    print("Payload:", json.dumps(result_payload, indent=2))

                    try:
                        response = requests.post(
                            f"{TASKS_API_URL}/{task_id}/result",
                            json=result_payload,
                            headers=headers,
                            timeout=10
                        )
                        print_response(response, f"Result Submission for Publisher {publisher_id} - Session {session_id} - Result {i+1}")
                        
                        if response.status_code >= 300:
                            print(f"ERROR: Failed to submit result for publisher {publisher_id} - Session {session_id} - Result {i+1}")
                            print(f"Status Code: {response.status_code}")
                            try:
                                error_details = response.json()
                                print("Error details:", json.dumps(error_details, indent=2))
                            except:
                                print("Response text:", response.text)
                            continue

                        result = response.json()
                        results.append(result)
                        print(f"Result submitted successfully!")
                        print(f"Result ID: {result.get('id', 'N/A')}")
                        print(f"- Task: {result.get('task_id')}")
                        print(f"  Result: {result.get('result')}")
                        print(f"  Confidence: {result.get('confidence')}")
                        print(f"  Labels: {result.get('labels')}")
                        print(f"  Quality Score: {result.get('quality_score')}")

                    except requests.exceptions.RequestException as e:
                        print(f"ERROR: Request failed for publisher {publisher_id} - Session {session_id} - Result {i+1}")
                        print(f"Exception: {str(e)}")
                        continue

                    time.sleep(1)  # Small delay between submissions

        return results

    def check_consensus_status(self) -> Dict[str, Any]:
        """Check consensus status for all tasks"""
        print_step("STEP 6: Check consensus status for all tasks")
        consensus_data = {}
        for task_id in self.task_ids:
            try:
                headers = {"X-API-Key": self.provider_api_key}
                response = requests.get(f"{QA_API_URL}/{task_id}", headers=headers)
                if response.status_code == 200:
                    print_response(response, f"Task {task_id} Consensus Status")
                    consensus_data[task_id] = response.json()
                else:
                    print(f"ERROR: Failed to retrieve consensus status for task {task_id}")
            except Exception as e:
                print(f"Error checking consensus status for task {task_id}: {str(e)}")
        return consensus_data

    def check_provider_tasks(self):
        """Check final task status and results for provider"""
        print_step("STEP 7: Check final task status and results")
        
        # Get all tasks for this provider
        headers = {"X-API-Key": self.provider_api_key}
        response = requests.get(
            f"{TASKS_API_URL}",
            params={"provider_id": str(self.provider_id)},
            headers=headers
        )
        
        if response.status_code == 200:
            response_data = response.json()
            tasks = response_data.get('items', [])
            total = response_data.get('total', 0)
            print(f"\nTotal tasks created by provider: {total}")
            
            for task in tasks:
                task_id = task.get('id')
                print(f"\nChecking final status for Task {task_id}")
                print("\nTask Details:")
                print(f"Status: {task.get('status', 'N/A')}")
                print(f"Title: {task.get('title', 'N/A')}")
                print(f"Description: {task.get('description', 'N/A')}")
                print(f"Created at: {task.get('created_at', 'N/A')}")
                print(f"Updated at: {task.get('updated_at', 'N/A')}")
                
                # Get consensus data from task response
                consensus_data = task.get('consensus_data', {})
                if consensus_data:
                    print("\nConsensus Results:")
                    print(f"Total Submissions: {consensus_data.get('total_submissions', 'N/A')}")
                    print(f"Agreement Count: {consensus_data.get('agreement_count', 'N/A')}")
                    print(f"Current Consensus: {consensus_data.get('current_consensus', 'N/A')}")
                    print(f"Confidence Scores: {consensus_data.get('confidence_scores', 'N/A')}")
                    print(f"Consensus Status: {task.get('consensus_status', 'N/A')}")
                
                # Get all results for this task
                results_response = requests.get(f"{TASKS_API_URL}/{task_id}/results", headers=headers)
                if results_response.status_code == 200:
                    results = results_response.json()
                    print(f"\nAll Submissions ({len(results)} total):")
                    for result in results:
                        print(f"\nSubmission by Publisher {result.get('publisher_id')}:")
                        print(f"Result: {result.get('result', 'N/A')}")
                        print(f"Confidence: {result.get('confidence', 'N/A')}")
                        print(f"Labels: {result.get('labels', 'N/A')}")
                        print(f"Quality Score: {result.get('quality_score', 'N/A')}")
                        print(f"Submitted at: {result.get('created_at', 'N/A')}")
                else:
                    print(f"Error getting task results: {results_response.status_code}")
                    print(results_response.text)
        else:
            print(f"Error getting provider tasks: {response.status_code}")
            print(response.text)

    def check_publisher_contributions(self):
        """Check publisher contributions and session statistics."""
        print("\n--- STEP 7: Check publisher contributions ---")
        
        for publisher_id in self.publisher_ids:
            print(f"\nChecking contributions for Publisher {publisher_id}")
            
            # Get session statistics
            for session_id in self.sessions[publisher_id]:
                print(f"\nSession {session_id} Statistics:")
                print(f"Created at: {self.session_data[session_id]['created_at']}")
                print(f"Updated at: {self.session_data[session_id]['updated_at']}")
                
                # Get results for this session
                response = requests.get(
                    f"{TASKS_SERVICE_URL}/api/v1/tasks/results",
                    params={"session_id": str(session_id)},
                    headers={"X-API-Key": self.publisher_api_keys[self.publisher_ids.index(publisher_id)]}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"\nResults submitted in this session: {len(results)}")
                    
                    for result in results:
                        print(f"\nTask {result.get('task_id')}:")
                        print(f"Result: {result.get('result', 'N/A')}")
                        print(f"Confidence: {result.get('confidence', 'N/A')}")
                        print(f"Labels: {result.get('labels', 'N/A')}")
                        print(f"Quality Score: {result.get('quality_score', 'N/A')}")
                        print(f"Submitted at: {result.get('created_at', 'N/A')}")
                else:
                    print(f"Error getting session results: {response.status_code}")
                    print(response.text)
            
            # Get total contributions across all sessions
            total_results = 0
            for session_id in self.sessions[publisher_id]:
                response = requests.get(
                    f"{TASKS_SERVICE_URL}/api/v1/tasks/results",
                    params={"session_id": str(session_id)},
                    headers={"X-API-Key": self.publisher_api_keys[self.publisher_ids.index(publisher_id)]}
                )
                if response.status_code == 200:
                    results = response.json()
                    total_results += len(results)
            
            print(f"\nTotal contributions by Publisher {publisher_id}: {total_results} results")

def main():
    """Run the task lifecycle demonstration"""
    print_header("Task Lifecycle Demonstration")
    
    lifecycle = TaskLifecycle()
    
    # Register provider
    lifecycle.register_provider()
    
    # Create tasks for all scenarios
    lifecycle.create_tasks_for_all_scenarios()
    
    # Register multiple publishers
    lifecycle.register_multiple_publishers(count=2)
    
    # Create sessions for publishers
    lifecycle.create_sessions_for_publishers()
    
    # Submit results for each task
    for task_id in lifecycle.task_ids:
        lifecycle.submit_results_for_scenario(task_id)
    
    # Wait for consensus calculation
    print("\nWaiting for consensus calculation...")
    time.sleep(5)
    
    # Check consensus status
    lifecycle.check_consensus_status()
    
    # Check final task status and results
    lifecycle.check_provider_tasks()
    
    # Check publisher contributions
    lifecycle.check_publisher_contributions()
    
    print_header("Task Lifecycle Demonstration Completed")

if __name__ == "__main__":
    main() 