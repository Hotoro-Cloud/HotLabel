#!/usr/bin/env python3
"""
Task Lifecycle Demo

This script demonstrates the complete lifecycle of a task in the Hotlabel platform:
1. Provider registers and receives API key
2. Provider creates a task
3. Publisher registers and receives API key
4. Publisher receives auto-assigned task
5. Publisher submits result for task
6. QA service receives task result and validates it
7. Final result is appended to task and is made available to provider
8. Test consensus calculation and notification system
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
        self.task_id = None
        self.publisher_id = None
        self.publisher_api_key = None
        self.result_id = None
        self.validation_id = None
        self.validator_id = None
        self.publisher_ids = []  # Store multiple publisher IDs for consensus testing
        self.publisher_api_keys = []  # Store multiple publisher API keys
        self.session_ids = []  # Store session IDs
        
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
        
    def create_task_with_consensus_config(self) -> Dict[str, Any]:
        """Create a new task with consensus configuration"""
        print_step("STEP 2: Provider creates a task with consensus config")
        
        task_data = {
            "title": "Demo Text Classification Task with Consensus",
            "description": "A demo task for testing consensus and notifications",
            "provider_id": self.provider_id,
            "task_type": "text_classification",
            "content": {
                "text": "This is a sample text for classification",
                "labels": ["positive", "negative", "neutral"]
            },
            "language": "en",
            "category": "demo",
            "complexity_level": 2,
            "tags": ["demo", "classification", "consensus"],
            "options": {"demo_option": True},
            "time_estimate_seconds": 120,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "pending",
            # Consensus configuration
            "agreement_threshold": 0.75,  # 75% agreement required
            "confidence_threshold": 0.70,  # 70% confidence required
            "consensus_status": "pending",  # Initial consensus status
            "consensus_data": {  # Initial consensus data structure
                "total_submissions": 0,
                "agreement_count": 0,
                "confidence_scores": [],
                "current_consensus": None
            }
        }
        
        print("Task Creation Payload:")
        print(json.dumps(task_data, indent=2))
        
        headers = {"X-API-Key": self.provider_api_key}
        response = requests.post(TASKS_API_URL, json=task_data, headers=headers)
        print_response(response, "Task Creation with Consensus Config")
        
        if response.status_code >= 300:
            print("ERROR: Failed to create task")
            sys.exit(1)
            
        result = response.json()
        self.task_id = str(result["id"])
        
        print(f"Task created successfully!")
        print(f"Task ID: {self.task_id}")
        
        return result
        
    def register_multiple_publishers(self, count: int = 3) -> List[Dict[str, Any]]:
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
        
    def create_sessions_for_publishers(self) -> List[Dict[str, Any]]:
        """Create sessions for each publisher"""
        print_step("STEP 4: Create sessions for publishers")
        
        sessions = []
        for i, publisher_id in enumerate(self.publisher_ids):
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
            print_response(response, f"Session Creation for Publisher {i+1}")
            
            if response.status_code >= 300:
                print(f"ERROR: Failed to create session for publisher {i+1}")
                continue
                
            result = response.json()
            self.session_ids.append(result["id"])
            sessions.append(result)
            
            print(f"Session created successfully for Publisher {i+1}!")
            print(f"Session ID: {result['id']}")
        
        return sessions
    
    def get_assignments_for_task(self, task_id: str, headers: dict) -> List[Dict[str, Any]]:
        """Get all assignments for a task"""
        response = requests.get(
            f"{TASKS_API_URL}/{task_id}/assignments",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return []
    
    def submit_multiple_results(self) -> List[Dict[str, Any]]:
        """Submit results from multiple publishers for consensus testing"""
        print_step("STEP 5: Multiple publishers submit results for consensus")
        
        results = []
        labels = ["positive", "negative", "neutral"]
        
        for i, (publisher_id, api_key, session_id) in enumerate(zip(
            self.publisher_ids, 
            self.publisher_api_keys,
            self.session_ids
        )):
            try:
                # Set up headers with API key
                headers = {
                    "X-API-Key": api_key, 
                    "Content-Type": "application/json"
                }
                
                # Simulate different confidence levels and labels
                label = random.choice(["positive", "negative", "neutral"])
                confidence = random.uniform(0.8, 0.95)
                time_spent = random.randint(3000, 10000)
                
                # Prepare task result payload - using 'result' to match the TaskResult model
                result_data = {
                    "label": f"label_{i+1}",
                    "confidence": 0.9 - (i * 0.1),  # Vary confidence slightly
                    "time_spent_ms": 2000 + (i * 100)  # Vary time spent
                }
                
                result_payload = {
                    "publisher_id": str(publisher_id),
                    "result": result_data,  # Main result data
                    "session_id": str(session_id),
                    "quality_score": float(0.9 - (i * 0.1)),  # Ensure it's a float
                    "result_metadata": {  # Changed from metadata to result_metadata
                        "source": "demo_script",
                        "time_spent_ms": 2000 + (i * 100)
                    },
                    "confidence": float(0.9 - (i * 0.1)),  # Confidence at top level
                    "labels": [f"label_{i+1}"]  # Labels for classification
                }
                
                # Log the request payload for debugging
                print(f"\nSubmitting result for publisher {i+1} (ID: {publisher_id}):")
                print("Request URL:", f"{TASKS_API_URL}/{self.task_id}/result")
                print("Headers:", headers)
                print("Payload:", json.dumps(result_payload, indent=2))
                
                try:
                    # Submit the result using the task result endpoint
                    response = requests.post(
                        f"{TASKS_API_URL}/{self.task_id}/result",
                        json=result_payload,
                        headers=headers,
                        timeout=10  # Add timeout to prevent hanging
                    )
                    
                    print_response(response, f"Result Submission for Publisher {i+1}")
                    
                    # Log the full response for debugging
                    print("Full response:", response.text)
                    
                    if response.status_code >= 300:
                        print(f"ERROR: Failed to submit result for publisher {i+1}")
                        print(f"Status Code: {response.status_code}")
                        # Try to get more detailed error information
                        try:
                            error_details = response.json()
                            print("Error details:", json.dumps(error_details, indent=2))
                        except:
                            print("Response text:", response.text)
                        continue
                        
                except requests.exceptions.RequestException as e:
                    print(f"ERROR: Request failed for publisher {i+1}")
                    print(f"Exception: {str(e)}")
                    continue
                    
                try:
                    result = response.json()
                    results.append(result)
                    print(f"Result submitted successfully for Publisher {i+1}!")
                    print(f"Result ID: {result.get('id', 'N/A')}")
                    print(f"- Task: {result.get('task_id')}")
                    print(f"  Result: {result.get('result')}")
                    print(f"  Confidence: {result.get('confidence')}")
                    print(f"  Labels: {result.get('labels')}")
                    print(f"  Quality Score: {result.get('quality_score')}")
                except Exception as e:
                    print(f"ERROR: Failed to parse response for publisher {i+1}: {str(e)}")
                    print(f"Response: {response.text}")
                
                # Add a small delay between submissions
                time.sleep(1)
                
            except Exception as e:
                print(f"ERROR: Exception occurred for publisher {i+1}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return results
    
    def check_consensus_status(self) -> Dict[str, Any]:
        """Check task consensus status"""
        print_step("STEP 6: Check task consensus status")
        try:
            headers = {"X-API-Key": self.provider_api_key}
            response = requests.get(f"{QA_SERVICE_URL}/api/v1/consensus/{self.task_id}", headers=headers)
            if response.status_code == 200:
                print_response(response, "Task Consensus Status")
            else:
                print("ERROR: Failed to retrieve consensus status")
        except Exception as e:
            print(f"Error checking consensus status: {str(e)}")
    
    def check_publisher_contributions(self) -> None:
        """Check contributions made by each publisher"""
        print_step("STEP 7: Check publisher contributions")
        
        for i, (publisher_id, session_id) in enumerate(zip(self.publisher_ids, self.session_ids)):
            print(f"\nPublisher {i+1} Contributions:")
            print(f"Publisher ID: {publisher_id}")
            print(f"Session ID: {session_id}")
            
            # Get publisher's session details
            response = requests.get(f"{SESSIONS_API_URL}/{session_id}")
            if response.status_code == 200:
                session_data = response.json()
                print(f"Session Duration: {session_data.get('duration_ms', 'N/A')}ms")
                print(f"Session Start: {session_data.get('started_at', 'N/A')}")
                print(f"Session End: {session_data.get('ended_at', 'N/A')}")
            
            # Get publisher's results
            headers = {"X-API-Key": self.publisher_api_keys[i]}
            response = requests.get(
                f"{TASKS_API_URL}/results?session_id={session_id}",
                headers=headers
            )
            if response.status_code == 200:
                results = response.json().get('items', [])
                filtered_results = [r for r in results if r.get('session_id') == session_id]
                print(f"Total Results: {len(filtered_results)}")
                for result in filtered_results:
                    print(f"- Task: {result.get('task_id')}")
                    print(f"  Result: {result.get('result')}")
                    print(f"  Confidence: {result.get('confidence')}")
                    print(f"  Labels: {result.get('labels')}")
                    print(f"  Quality Score: {result.get('quality_score')}")

def main():
    """Run the task lifecycle demonstration"""
    print_header("Task Lifecycle Demonstration")
    
    lifecycle = TaskLifecycle()
    
    # Register provider
    lifecycle.register_provider()
    
    # Create task with consensus config
    lifecycle.create_task_with_consensus_config()
    
    # Register multiple publishers
    lifecycle.register_multiple_publishers(count=3)
    
    # Create sessions for publishers
    lifecycle.create_sessions_for_publishers()
    
    # Submit results from multiple publishers
    lifecycle.submit_multiple_results()
    
    # Wait for consensus calculation
    print("\nWaiting for consensus calculation...")
    time.sleep(5)
    
    # Check consensus status
    lifecycle.check_consensus_status()
    
    # Check publisher contributions
    lifecycle.check_publisher_contributions()
    
    print_header("Task Lifecycle Demonstration Completed")

if __name__ == "__main__":
    main() 